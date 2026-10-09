"""Application services: orchestrate domain rules + persistence (integration layer)."""
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from . import gateway
from .db import Database
from .domain import state as st
from .domain.cancellation import late_checkout_fee, refund_decision
from .domain.errors import StateError, ValidationError
from .domain.metrics import adr, occupancy_pct, revpar
from .domain.payment import validate_amount, validate_card, validate_upi
from .domain.pricing import complimentary_benefits, compute_quote
from .domain.rooms import get_room_type
from .domain.validation import (
    validate_age,
    validate_email,
    validate_guest_count,
    validate_name,
    validate_occupancy,
    validate_password,
    validate_phone,
    validate_room_count,
    validate_stay,
)

MAX_FAILED_LOGINS = 3
LOCKOUT_MINUTES = 15
ACTIVE_STATUSES = (st.PENDING, st.CONFIRMED, st.CHECKED_IN)
PBKDF2_ROUNDS = 120_000


class Clock:
    """Injectable clock so tests can freeze 'now'."""

    def __init__(self, fixed: datetime | None = None):
        self.fixed = fixed

    def now(self) -> datetime:
        return self.fixed or datetime.now()

    def today(self) -> date:
        return self.now().date()


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class AuthError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    _, rounds, salt, digest = stored.split("$")
    test = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
    return hmac.compare_digest(test.hex(), digest)


@dataclass
class HotelService:
    db: Database
    clock: Clock

    # ------------------------------------------------------------ helpers
    def _audit(self, actor, action, detail=None):
        self.db.conn.execute("INSERT INTO audit_log(at, actor, action, detail) VALUES (?,?,?,?)",
                             (self.clock.now().isoformat(), actor, action, json.dumps(detail or {})))

    # ------------------------------------------------------------ users
    def register(self, name, email, phone, age, password, role="guest", tier="NONE") -> dict:
        name = validate_name(name)
        email = validate_email(email)
        phone = validate_phone(phone)
        age = validate_age(age)
        validate_password(password)
        conn = self.db.conn
        if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise ValidationError("EMAIL_TAKEN", "An account with this email already exists")
        cur = conn.execute(
            "INSERT INTO users(name,email,phone,age,password_hash,role,tier) VALUES (?,?,?,?,?,?,?)",
            (name, email, phone, age, hash_password(password), role, tier))
        self._audit(cur.lastrowid, "register")
        conn.commit()
        return self.get_user(cur.lastrowid)

    def get_user(self, user_id) -> dict:
        row = self.db.conn.execute(
            "SELECT id,name,email,phone,age,role,tier FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            raise NotFound("user")
        return dict(row)

    def login(self, email, password) -> str:
        conn = self.db.conn
        row = conn.execute("SELECT * FROM users WHERE email=?", ((email or "").strip().lower(),)).fetchone()
        now = self.clock.now()
        if not row:
            raise AuthError("AUTH_FAILED", "Invalid email or password")
        if row["locked_until"] and datetime.fromisoformat(row["locked_until"]) > now:
            raise AuthError("ACCOUNT_LOCKED", "Account locked after repeated failures; try later")
        if not verify_password(password or "", row["password_hash"]):
            failed = row["failed_logins"] + 1
            locked = (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat() if failed >= MAX_FAILED_LOGINS else None
            conn.execute("UPDATE users SET failed_logins=?, locked_until=? WHERE id=?",
                         (0 if locked else failed, locked, row["id"]))
            self._audit(row["id"], "login_failed")
            conn.commit()
            if locked:
                raise AuthError("ACCOUNT_LOCKED", "Account locked after repeated failures; try later")
            raise AuthError("AUTH_FAILED", "Invalid email or password")
        token = secrets.token_urlsafe(32)
        conn.execute("UPDATE users SET failed_logins=0, locked_until=NULL WHERE id=?", (row["id"],))
        conn.execute("INSERT INTO sessions(token,user_id,created_at) VALUES (?,?,?)",
                     (token, row["id"], now.isoformat()))
        self._audit(row["id"], "login")
        conn.commit()
        return token

    def user_for_token(self, token) -> dict:
        row = self.db.conn.execute("SELECT user_id FROM sessions WHERE token=?", (token,)).fetchone()
        if not row:
            raise AuthError("AUTH_REQUIRED", "Sign in first")
        return self.get_user(row["user_id"])

    def logout(self, token):
        self.db.conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        self.db.conn.commit()

    def set_tier(self, user_id, tier):
        from .domain.pricing import loyalty_pct
        loyalty_pct(tier)
        self.get_user(user_id)
        self.db.conn.execute("UPDATE users SET tier=? WHERE id=?", (tier.upper(), user_id))
        self.db.conn.commit()
        return self.get_user(user_id)

    # ------------------------------------------------------------ inventory
    def free_rooms(self, room_type, check_in: date, check_out: date, conn=None) -> list[str]:
        conn = conn or self.db.conn
        rt = get_room_type(room_type)
        rows = conn.execute(
            f"""SELECT room_no FROM rooms r WHERE r.room_type=? AND r.active=1 AND r.room_no NOT IN (
                  SELECT br.room_no FROM booking_rooms br JOIN bookings b ON b.id = br.booking_id
                  WHERE b.status IN ({','.join('?' * len(ACTIVE_STATUSES))})
                    AND b.check_in < ? AND b.check_out > ?)
                ORDER BY room_no""",  # noqa: S608 — CI-02: only "?" placeholders are interpolated
            (rt.code, *ACTIVE_STATUSES, check_out.isoformat(), check_in.isoformat())).fetchall()
        return [r["room_no"] for r in rows]

    def availability(self, check_in: date, check_out: date) -> list[dict]:
        nights = validate_stay(check_in, check_out, self.clock.today())
        out = []
        for code in ("STANDARD", "DELUXE", "FAMILY", "SUITE"):
            rt = get_room_type(code)
            free = self.free_rooms(code, check_in, check_out)
            q = compute_quote(code, check_in, check_out)
            out.append({"room_type": code, "name": rt.name, "capacity": rt.capacity,
                        "base_rate": rt.base_rate, "available": len(free), "nights": nights,
                        "from_total": float(q.total)})
        return out

    # ------------------------------------------------------------ booking
    def quote(self, user, room_type, check_in, check_out, rooms=1, extra_beds=0, promo=None):
        validate_stay(check_in, check_out, self.clock.today())
        validate_room_count(rooms)
        q = compute_quote(room_type, check_in, check_out, rooms, extra_beds,
                          (user or {}).get("tier", "NONE"), promo)
        benefits = complimentary_benefits((user or {}).get("tier", "NONE"), q.nights,
                                          (check_in - self.clock.today()).days, room_type)
        return {**q.as_dict(), "benefits": benefits}

    def create_booking(self, user, room_type, check_in: date, check_out: date, rooms=1, adults=1,
                       children=0, extra_beds=0, promo=None, refundable=True) -> dict:
        validate_stay(check_in, check_out, self.clock.today())
        validate_room_count(rooms)
        if extra_beds < 0 or extra_beds > rooms:
            raise ValidationError("EXTRA_BED_COUNT", "At most one extra bed per room")
        # occupancy is checked per room: distribute guests across rooms as evenly as possible
        if adults < rooms:
            raise ValidationError("ADULTS_MIN", "At least one adult is required per room")
        validate_guest_count(adults + children)
        rt = get_room_type(room_type)
        remaining_children = children
        for i in range(rooms):
            a = adults // rooms + (1 if i < adults % rooms else 0)
            room_cap = rt.capacity + (1 if i < extra_beds else 0)
            c = min(remaining_children, max(room_cap - a, 0))
            remaining_children -= c
            validate_occupancy(rt.code, a, c, extra_bed=i < extra_beds)
        if remaining_children:
            raise ValidationError("OCCUPANCY_EXCEEDED", f"{rooms} x {rt.name} cannot hold this party")
        q = compute_quote(rt.code, check_in, check_out, rooms, extra_beds, user.get("tier", "NONE"), promo)

        with self.db.write_lock:  # serialise inventory check + insert → no overbooking (FR-10)
            conn = self.db.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                free = self.free_rooms(rt.code, check_in, check_out, conn)
                if len(free) < rooms:
                    raise ValidationError("NO_AVAILABILITY",
                                          f"Only {len(free)} {rt.name}(s) free for those dates")
                ref = "HRR-" + secrets.token_hex(4).upper()
                cur = conn.execute(
                    """INSERT INTO bookings(ref,user_id,room_type,check_in,check_out,rooms,adults,children,
                       extra_beds,refundable,promo,status,subtotal,discount,gst,total,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ref, user["id"], rt.code, check_in.isoformat(), check_out.isoformat(), rooms, adults,
                     children, extra_beds, int(bool(refundable)), (promo or None), st.PENDING,
                     float(q.subtotal), float(q.discount), float(q.gst), float(q.total),
                     self.clock.now().isoformat()))
                bid = cur.lastrowid
                conn.executemany("INSERT INTO booking_rooms(booking_id, room_no) VALUES (?,?)",
                                 [(bid, r) for r in free[:rooms]])
                self._audit(user["id"], "booking_created", {"booking": bid})
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return self.get_booking(user, bid)

    def get_booking(self, user, booking_id) -> dict:
        row = self.db.conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if not row:
            raise NotFound("booking")
        if user["role"] != "admin" and row["user_id"] != user["id"]:
            raise Forbidden("booking")  # prevents IDOR
        d = dict(row)
        d["refundable"] = bool(d["refundable"])
        d["room_numbers"] = [r["room_no"] for r in self.db.conn.execute(
            "SELECT room_no FROM booking_rooms WHERE booking_id=? ORDER BY room_no", (booking_id,))]
        d["allowed_actions"] = st.allowed_events(d["status"])
        return d

    def list_bookings(self, user) -> list[dict]:
        if user["role"] == "admin":
            rows = self.db.conn.execute("SELECT id FROM bookings ORDER BY id DESC").fetchall()
        else:
            rows = self.db.conn.execute("SELECT id FROM bookings WHERE user_id=? ORDER BY id DESC",
                                        (user["id"],)).fetchall()
        return [self.get_booking(user, r["id"]) for r in rows]

    _UPDATABLE = frozenset({"paid_at", "refund_amount", "late_fee"})

    def _transition(self, booking_id, event, **fields):
        if not set(fields) <= self._UPDATABLE:          # SA-01: column allow-list for dynamic SET clause
            raise ValueError(f"Column(s) not updatable: {set(fields) - self._UPDATABLE}")
        conn = self.db.conn
        cur = conn.execute("SELECT status FROM bookings WHERE id=?", (booking_id,)).fetchone()
        new = st.next_state(cur["status"], event)
        sets = ", ".join(["status=?"] + [f"{k}=?" for k in fields])
        conn.execute(f"UPDATE bookings SET {sets} WHERE id=?", (new, *fields.values(), booking_id))  # noqa: S608 — CI-01: internal column names only
        return new

    def pay(self, user, booking_id, method, details: dict, idempotency_key: str) -> dict:
        if not idempotency_key or len(idempotency_key) > 64:
            raise ValidationError("IDEMPOTENCY_KEY", "Idempotency-Key header (1-64 chars) is required")
        booking = self.get_booking(user, booking_id)
        conn = self.db.conn
        prior = conn.execute("SELECT * FROM payments WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if prior:
            if prior["booking_id"] != booking_id:
                raise ValidationError("IDEMPOTENCY_REUSED", "Key already used for another booking")
            return {"booking": self.get_booking(user, booking_id), "payment_id": prior["id"], "replayed": True}
        if booking["status"] != st.PENDING:
            raise StateError("TRANSITION_INVALID", f"Cannot pay a booking that is {booking['status']}")
        created = datetime.fromisoformat(booking["created_at"])
        if self.clock.now() - created > timedelta(minutes=st.PAYMENT_WINDOW_MINUTES):
            self._transition(booking_id, "expire")
            conn.commit()
            raise StateError("PAYMENT_WINDOW_EXPIRED", "Payment window of 15 minutes has passed")
        amount = validate_amount(booking["total"])
        if method == "card":
            masked = validate_card(details.get("number", ""), int(details.get("exp_month", 0)),
                                   int(details.get("exp_year", 0)), str(details.get("cvv", "")),
                                   self.clock.today())
        elif method == "upi":
            masked = validate_upi(details.get("vpa", ""))
        else:
            raise ValidationError("PAYMENT_METHOD", "Method must be card or upi")
        gateway.charge(amount, method)  # may raise GatewayError -> booking stays PENDING
        cur = conn.execute(
            "INSERT INTO payments(booking_id,idempotency_key,method,masked,amount,status,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (booking_id, idempotency_key, method, masked, float(amount), "CAPTURED", self.clock.now().isoformat()))
        self._transition(booking_id, "pay", paid_at=self.clock.now().isoformat())
        self._audit(user["id"], "payment", {"booking": booking_id})
        conn.commit()
        return {"booking": self.get_booking(user, booking_id), "payment_id": cur.lastrowid, "replayed": False}

    def cancel(self, user, booking_id, hotel_initiated=False) -> dict:
        booking = self.get_booking(user, booking_id)
        if hotel_initiated and user["role"] != "admin":
            raise Forbidden("hotel_initiated")
        if booking["status"] == st.PENDING:
            self._transition(booking_id, "cancel", refund_amount=0.0)
            self.db.conn.commit()
            return {"booking": self.get_booking(user, booking_id), "refund": 0.0, "rule": "UNPAID"}
        days_before = (date.fromisoformat(booking["check_in"]) - self.clock.today()).days
        owner = self.get_user(booking["user_id"])
        st.next_state(booking["status"], "cancel")  # validate first
        decision = refund_decision(booking["refundable"], days_before, hotel_initiated, owner["tier"])
        refund = decision.refund_amount(booking["total"])
        self._transition(booking_id, "cancel", refund_amount=float(refund))
        self._audit(user["id"], "cancel", {"booking": booking_id, "rule": decision.rule})
        self.db.conn.commit()
        return {"booking": self.get_booking(user, booking_id), "refund": float(refund),
                "refund_pct": decision.refund_pct, "fee": decision.fee, "voucher": decision.voucher,
                "rule": decision.rule}

    def check_in(self, admin, booking_id, id_verified: bool) -> dict:
        booking = self.get_booking(admin, booking_id)
        if not id_verified:
            raise ValidationError("ID_NOT_VERIFIED", "Government ID must be verified at check-in")
        if self.clock.today() < date.fromisoformat(booking["check_in"]):
            raise StateError("CHECKIN_TOO_EARLY", "Check-in date has not arrived")
        if self.clock.today() >= date.fromisoformat(booking["check_out"]):
            raise StateError("CHECKIN_TOO_LATE", "Stay window has ended")
        self._transition(booking_id, "check_in")
        self.db.conn.commit()
        return self.get_booking(admin, booking_id)

    def check_out(self, admin, booking_id, at: time) -> dict:
        booking = self.get_booking(admin, booking_id)
        nightly = booking["subtotal"] / max(1, (date.fromisoformat(booking["check_out"])
                                               - date.fromisoformat(booking["check_in"])).days)
        fee = late_checkout_fee(round(nightly, 2), at) if booking["status"] == st.CHECKED_IN else 0
        self._transition(booking_id, "check_out", late_fee=float(fee))
        self.db.conn.commit()
        return self.get_booking(admin, booking_id)

    def expire_pending(self) -> int:
        cutoff = (self.clock.now() - timedelta(minutes=st.PAYMENT_WINDOW_MINUTES)).isoformat()
        conn = self.db.conn
        rows = conn.execute("SELECT id FROM bookings WHERE status=? AND created_at < ?",
                            (st.PENDING, cutoff)).fetchall()
        for r in rows:
            self._transition(r["id"], "expire")
        conn.commit()
        return len(rows)

    def metrics(self, day: date) -> dict:
        conn = self.db.conn
        available = conn.execute("SELECT COUNT(*) FROM rooms WHERE active=1").fetchone()[0]
        rows = conn.execute(
            """SELECT b.subtotal, b.discount, b.check_in, b.check_out, b.rooms FROM bookings b
               WHERE b.status IN ('CONFIRMED','CHECKED_IN','CHECKED_OUT') AND b.check_in <= ? AND b.check_out > ?""",
            (day.isoformat(), day.isoformat())).fetchall()
        sold = sum(r["rooms"] for r in rows)
        revenue = 0.0
        for r in rows:
            nights = (date.fromisoformat(r["check_out"]) - date.fromisoformat(r["check_in"])).days
            revenue += (r["subtotal"] - r["discount"]) / nights
        return {"date": day.isoformat(), "rooms_available": available, "rooms_sold": sold,
                "revenue": round(revenue, 2), "occupancy_pct": float(occupancy_pct(sold, available)),
                "adr": float(adr(round(revenue, 2), sold)), "revpar": float(revpar(round(revenue, 2), available))}
