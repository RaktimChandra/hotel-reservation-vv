"""SQLite persistence layer."""
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    age INTEGER NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'guest',
    tier TEXT NOT NULL DEFAULT 'NONE',
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rooms (
    room_no TEXT PRIMARY KEY,
    room_type TEXT NOT NULL,
    floor INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    room_type TEXT NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL,
    rooms INTEGER NOT NULL,
    adults INTEGER NOT NULL,
    children INTEGER NOT NULL,
    extra_beds INTEGER NOT NULL,
    refundable INTEGER NOT NULL,
    promo TEXT,
    status TEXT NOT NULL,
    subtotal REAL NOT NULL,
    discount REAL NOT NULL,
    gst REAL NOT NULL,
    total REAL NOT NULL,
    created_at TEXT NOT NULL,
    paid_at TEXT,
    refund_amount REAL,
    late_fee REAL
);
CREATE TABLE IF NOT EXISTS booking_rooms (
    booking_id INTEGER NOT NULL REFERENCES bookings(id),
    room_no TEXT NOT NULL REFERENCES rooms(room_no),
    PRIMARY KEY (booking_id, room_no)
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL REFERENCES bookings(id),
    idempotency_key TEXT NOT NULL UNIQUE,
    method TEXT NOT NULL,
    masked TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor INTEGER,
    action TEXT NOT NULL,
    detail TEXT
);
"""

# 20 rooms over 4 floors
SEED_ROOMS = (
    [(f"1{n:02d}", "STANDARD", 1) for n in range(1, 9)]
    + [(f"2{n:02d}", "DELUXE", 2) for n in range(1, 7)]
    + [(f"3{n:02d}", "FAMILY", 3) for n in range(1, 4)]
    + [(f"4{n:02d}", "SUITE", 4) for n in range(1, 4)]
)


class Database:
    """Thin wrapper; one connection per thread, serialised writes."""

    def __init__(self, path: str = ":memory:"):
        self.path = path
        self._local = threading.local()
        self.write_lock = threading.Lock()
        if path == ":memory:":
            # shared in-memory DB across threads
            self.path = f"file:hrrs_mem_{id(self)}?mode=memory&cache=shared"
        self._keeper = self.connect()  # keeps shared memory DB alive
        self._keeper.executescript(SCHEMA)
        if not self._keeper.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]:
            self._keeper.executemany("INSERT INTO rooms(room_no, room_type, floor) VALUES (?,?,?)", SEED_ROOMS)
        self._keeper.commit()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, uri=self.path.startswith("file:"), check_same_thread=False,
                               timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if not self.path.startswith("file:"):
            # DEF-004: WAL lets readers proceed during writes and avoids an fsync per commit
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    @property
    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = self.connect()
            self._local.conn = c
        return c
