"""HRRS REST API (FastAPI)."""
import os
from datetime import date, time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from . import gateway
from .db import Database
from .domain.errors import StateError, ValidationError
from .domain.rooms import ROOM_TYPES
from .services import AuthError, Clock, Forbidden, HotelService, NotFound

STATIC = Path(__file__).parent / "static"


class RegisterIn(BaseModel):
    name: str
    email: str
    phone: str
    age: int
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class StayIn(BaseModel):
    room_type: str
    check_in: date
    check_out: date
    rooms: int = 1
    extra_beds: int = 0
    promo: str | None = None


class BookingIn(StayIn):
    adults: int = 1
    children: int = 0
    refundable: bool = True


class PaymentIn(BaseModel):
    method: str
    number: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None
    cvv: str | None = None
    vpa: str | None = None


class CheckInIn(BaseModel):
    id_verified: bool


class CheckOutIn(BaseModel):
    at: time = Field(default=time(11, 0))


class CancelIn(BaseModel):
    hotel_initiated: bool = False


class TierIn(BaseModel):
    tier: str


def create_app(db_path: str | None = None, clock: Clock | None = None, seed_admin: bool = True) -> FastAPI:
    app = FastAPI(title="HRRS — Hotel Room Reservation System", version="1.0.0")
    db = Database(db_path or os.environ.get("HRRS_DB", ":memory:"))
    svc = HotelService(db, clock or Clock())
    app.state.svc = svc
    if seed_admin:
        try:
            svc.register("Front Desk Admin", "admin@hrrs.test", "9876543210", 30, "Admin@123", role="admin")
        except ValidationError:
            pass

    # ------------------------------------------------------------- errors
    @app.exception_handler(ValidationError)
    async def _validation(_, exc: ValidationError):
        return JSONResponse({"error": exc.code, "message": exc.message}, status_code=422)

    @app.exception_handler(StateError)
    async def _state(_, exc: StateError):
        return JSONResponse({"error": exc.code, "message": exc.message}, status_code=409)

    @app.exception_handler(AuthError)
    async def _auth(_, exc: AuthError):
        code = 423 if exc.code == "ACCOUNT_LOCKED" else 401
        return JSONResponse({"error": exc.code, "message": exc.message}, status_code=code)

    @app.exception_handler(NotFound)
    async def _nf(_, exc):
        return JSONResponse({"error": "NOT_FOUND", "message": f"{exc} not found"}, status_code=404)

    @app.exception_handler(Forbidden)
    async def _forbidden(_, exc):
        return JSONResponse({"error": "FORBIDDEN", "message": "Not allowed"}, status_code=403)

    @app.exception_handler(gateway.GatewayError)
    async def _gw(_, exc):
        return JSONResponse({"error": "PAYMENT_GATEWAY", "message": str(exc)}, status_code=502)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:")
        return response

    # ------------------------------------------------------------- auth deps
    def current_user(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthError("AUTH_REQUIRED", "Sign in first")
        return svc.user_for_token(authorization[7:])

    def admin_user(user=Depends(current_user)):
        if user["role"] != "admin":
            raise Forbidden("admin")
        return user

    # ------------------------------------------------------------- routes
    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/health")
    def health():
        db.conn.execute("SELECT 1")
        return {"status": "ok", "time": svc.clock.now().isoformat()}

    @app.post("/api/auth/register", status_code=201)
    def register(body: RegisterIn):
        return svc.register(body.name, body.email, body.phone, body.age, body.password)

    @app.post("/api/auth/login")
    def login(body: LoginIn):
        token = svc.login(body.email, body.password)
        return {"token": token, "user": svc.user_for_token(token)}

    @app.post("/api/auth/logout")
    def logout(authorization: str = Header()):
        svc.logout(authorization.removeprefix("Bearer "))
        return {"ok": True}

    @app.get("/api/me")
    def me(user=Depends(current_user)):
        return user

    @app.get("/api/rooms/types")
    def room_types():
        return [rt.__dict__ for rt in ROOM_TYPES.values()]

    @app.get("/api/availability")
    def availability(check_in: date, check_out: date):
        return svc.availability(check_in, check_out)

    @app.post("/api/quote")
    def quote(body: StayIn, authorization: str | None = Header(default=None)):
        user = None
        if authorization and authorization.startswith("Bearer "):
            try:
                user = svc.user_for_token(authorization[7:])
            except AuthError:
                user = None
        return svc.quote(user, body.room_type, body.check_in, body.check_out, body.rooms,
                         body.extra_beds, body.promo)

    @app.post("/api/bookings", status_code=201)
    def create_booking(body: BookingIn, user=Depends(current_user)):
        return svc.create_booking(user, body.room_type, body.check_in, body.check_out, body.rooms,
                                  body.adults, body.children, body.extra_beds, body.promo, body.refundable)

    @app.get("/api/bookings")
    def my_bookings(user=Depends(current_user)):
        return svc.list_bookings(user)

    @app.get("/api/bookings/{booking_id}")
    def get_booking(booking_id: int, user=Depends(current_user)):
        return svc.get_booking(user, booking_id)

    @app.post("/api/bookings/{booking_id}/pay")
    def pay(booking_id: int, body: PaymentIn, user=Depends(current_user),
            idempotency_key: str | None = Header(default=None)):
        return svc.pay(user, booking_id, body.method, body.model_dump(), idempotency_key or "")

    @app.post("/api/bookings/{booking_id}/cancel")
    def cancel(booking_id: int, body: CancelIn | None = None, user=Depends(current_user)):
        return svc.cancel(user, booking_id, bool(body and body.hotel_initiated))

    @app.post("/api/bookings/{booking_id}/check-in")
    def check_in(booking_id: int, body: CheckInIn, admin=Depends(admin_user)):
        return svc.check_in(admin, booking_id, body.id_verified)

    @app.post("/api/bookings/{booking_id}/check-out")
    def check_out(booking_id: int, body: CheckOutIn, admin=Depends(admin_user)):
        return svc.check_out(admin, booking_id, body.at)

    @app.post("/api/admin/expire-pending")
    def expire(admin=Depends(admin_user)):
        return {"expired": svc.expire_pending()}

    @app.get("/api/admin/metrics")
    def metrics(day: date | None = None, admin=Depends(admin_user)):
        return svc.metrics(day or svc.clock.today())

    @app.patch("/api/admin/users/{user_id}/tier")
    def set_tier(user_id: int, body: TierIn, admin=Depends(admin_user)):
        return svc.set_tier(user_id, body.tier)

    return app


app = create_app()
