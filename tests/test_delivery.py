"""
Tests for the delivery logistics system.
All tests use an in-memory SQLite database — no mocks.
"""
import sqlite3
import uuid
from contextlib import contextmanager

import pytest

from src.delivery.auth import generate_tracking_token, hash_pin, verify_pin
from src.delivery.eta import calc_eta, haversine


# ── Fixtures ──────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    avg_cost REAL NOT NULL,
    stock INTEGER NOT NULL
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    customer TEXT NOT NULL,
    total REAL NOT NULL
);
CREATE TABLE drivers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    pin_hash    TEXT NOT NULL,
    photo_path  TEXT,
    status      TEXT NOT NULL DEFAULT 'available',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE driver_locations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id   INTEGER NOT NULL REFERENCES drivers(id),
    order_id    INTEGER,
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE delivery_assignments (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id         INTEGER NOT NULL REFERENCES drivers(id),
    order_id          INTEGER NOT NULL REFERENCES orders(id),
    status            TEXT NOT NULL DEFAULT 'assigned',
    tracking_token    TEXT NOT NULL UNIQUE,
    eta_minutes       INTEGER,
    dest_lat          REAL,
    dest_lon          REAL,
    assigned_at       TEXT NOT NULL DEFAULT (datetime('now')),
    started_at        TEXT,
    completed_at      TEXT,
    stopped_alert_min INTEGER NOT NULL DEFAULT 5
);
CREATE TABLE delivery_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@pytest.fixture
def conn():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    db.execute("INSERT INTO delivery_settings (key, value) VALUES ('avg_speed_kmh', '30')")
    db.execute("INSERT INTO delivery_settings (key, value) VALUES ('stopped_alert_min', '5')")
    # Seed one driver and one order
    db.execute(
        "INSERT INTO drivers (name, pin_hash, status) VALUES ('Test Driver', ?, 'available')",
        (hash_pin("123456"),),
    )
    db.execute(
        "INSERT INTO orders (status, created_at, customer, total) VALUES ('pendente', datetime('now'), 'Cliente Demo', 99.0)"
    )
    db.commit()
    yield db
    db.close()


# ── test_assign_order ─────────────────────────────────────────────────────────

def test_assign_order(conn):
    driver_id = conn.execute("SELECT id FROM drivers LIMIT 1").fetchone()["id"]
    order_id  = conn.execute("SELECT id FROM orders LIMIT 1").fetchone()["id"]
    token = generate_tracking_token()

    conn.execute(
        """INSERT INTO delivery_assignments
           (driver_id, order_id, status, tracking_token, dest_lat, dest_lon)
           VALUES (?, ?, 'assigned', ?, -22.9985, -43.3650)""",
        (driver_id, order_id, token),
    )
    conn.execute("UPDATE drivers SET status = 'on_route' WHERE id = ?", (driver_id,))
    conn.commit()

    row = conn.execute(
        "SELECT * FROM delivery_assignments WHERE tracking_token = ?", (token,)
    ).fetchone()
    assert row is not None
    assert row["driver_id"] == driver_id
    assert row["order_id"] == order_id
    assert row["status"] == "assigned"

    # token is unique — inserting duplicate must fail
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO delivery_assignments (driver_id, order_id, status, tracking_token) VALUES (?, ?, 'assigned', ?)",
            (driver_id, order_id, token),
        )

    driver = conn.execute("SELECT status FROM drivers WHERE id = ?", (driver_id,)).fetchone()
    assert driver["status"] == "on_route"


# ── test_location_update ──────────────────────────────────────────────────────

def test_location_update(conn):
    driver_id = conn.execute("SELECT id FROM drivers LIMIT 1").fetchone()["id"]
    order_id  = conn.execute("SELECT id FROM orders LIMIT 1").fetchone()["id"]

    lat, lon = -22.9870, -43.3520
    conn.execute(
        "INSERT INTO driver_locations (driver_id, order_id, lat, lon) VALUES (?, ?, ?, ?)",
        (driver_id, order_id, lat, lon),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM driver_locations WHERE driver_id = ? ORDER BY id DESC LIMIT 1",
        (driver_id,),
    ).fetchone()
    assert row is not None
    assert row["lat"] == lat
    assert row["lon"] == lon
    assert row["order_id"] == order_id

    # ETA recalculated from the new position
    dest_lat, dest_lon = -22.9985, -43.3650
    distance_km, eta = calc_eta(lat, lon, dest_lat, dest_lon, avg_speed_kmh=30.0)
    assert distance_km > 0
    assert eta >= 1

    conn.execute(
        "UPDATE delivery_assignments SET eta_minutes = ? WHERE driver_id = ? AND order_id = ?",
        (eta, driver_id, order_id),
    )
    conn.commit()


# ── test_status_change ────────────────────────────────────────────────────────

def test_status_change(conn):
    driver_id = conn.execute("SELECT id FROM drivers LIMIT 1").fetchone()["id"]
    order_id  = conn.execute("SELECT id FROM orders LIMIT 1").fetchone()["id"]
    token = generate_tracking_token()

    conn.execute(
        """INSERT INTO delivery_assignments
           (driver_id, order_id, status, tracking_token)
           VALUES (?, ?, 'in_progress', ?)""",
        (driver_id, order_id, token),
    )
    conn.execute("UPDATE drivers SET status = 'on_route' WHERE id = ?", (driver_id,))
    conn.commit()

    # Complete the delivery
    conn.execute(
        "UPDATE delivery_assignments SET status = 'completed', completed_at = datetime('now') WHERE tracking_token = ?",
        (token,),
    )
    conn.execute("UPDATE drivers SET status = 'available' WHERE id = ?", (driver_id,))
    conn.commit()

    assignment = conn.execute(
        "SELECT status, completed_at FROM delivery_assignments WHERE tracking_token = ?", (token,)
    ).fetchone()
    assert assignment["status"] == "completed"
    assert assignment["completed_at"] is not None

    driver = conn.execute("SELECT status FROM drivers WHERE id = ?", (driver_id,)).fetchone()
    assert driver["status"] == "available"


# ── test_eta_calculation ──────────────────────────────────────────────────────

def test_eta_calculation():
    # Known distance: Barra da Tijuca → Recreio dos Bandeirantes ≈ 6–8 km
    lat1, lon1 = -22.9985, -43.3650  # Barra
    lat2, lon2 = -23.0157, -43.4468  # Recreio

    dist = haversine(lat1, lon1, lat2, lon2)
    assert 5.0 < dist < 12.0, f"Distância inesperada: {dist:.2f} km"

    distance_km, eta = calc_eta(lat1, lon1, lat2, lon2, avg_speed_kmh=30.0)
    assert distance_km == round(dist, 2)

    # At 30 km/h, ~8 km ≈ 16 min
    expected_eta = int((dist / 30.0) * 60) + (1 if (dist / 30.0 * 60) % 1 > 0 else 0)
    assert eta == expected_eta

    # Same point → distance = 0, eta = 0
    d, e = calc_eta(lat1, lon1, lat1, lon1)
    assert d == 0.0
    assert e == 0

    # PIN hashing round-trip
    assert verify_pin("123456", hash_pin("123456"))
    assert not verify_pin("999999", hash_pin("123456"))
