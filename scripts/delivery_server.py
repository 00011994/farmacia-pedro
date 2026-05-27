"""
Servidor de entregas: HTTP REST (porta 8001) + WebSocket (porta 8766).

Uso:
    python scripts/delivery_server.py

Variáveis de ambiente:
    DELIVERY_PORT          (padrão: 8001)
    DELIVERY_WS_PORT       (padrão: 8766)
    ERP_DB_PATH            (padrão: data/erp_demo.db)
    JWT_SECRET_KEY         (compartilhado com api_server.py)
    DELIVERY_UPLOAD_DIR    (padrão: out/uploads/drivers)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional

import uvicorn
from fastapi import (
    Depends, FastAPI, File, Form, HTTPException, UploadFile, WebSocket,
    WebSocketDisconnect, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.core.config import load_settings
from src.core.db import get_conn
from src.delivery.auth import (
    create_driver_token,
    generate_tracking_token,
    hash_pin,
    verify_driver_token,
    verify_pin,
    verify_staff_token,
)
from src.delivery.eta import calc_eta
from src.delivery.tracker import tracker

# ── Config ────────────────────────────────────────────────────────────────────

settings = load_settings()
DB_PATH = settings.db_path
UPLOAD_DIR = os.getenv("DELIVERY_UPLOAD_DIR", os.path.join("out", "uploads", "drivers"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Delivery API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from out/
os.makedirs("out", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="out/uploads"), name="uploads")


# ── Auth dependencies ─────────────────────────────────────────────────────────

def _bearer(request) -> str:
    from fastapi import Request
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    token = request.query_params.get("token", "")
    return token


def require_staff(request=None):
    from fastapi import Request
    from starlette.requests import Request as StarRequest

    def _dep(request: StarRequest):
        token = _bearer(request)
        staff = verify_staff_token(token)
        if not staff:
            raise HTTPException(status_code=401, detail="Autenticação inválida")
        return staff

    return _dep


def require_gestor(request=None):
    from starlette.requests import Request as StarRequest

    def _dep(request: StarRequest):
        token = _bearer(request)
        staff = verify_staff_token(token)
        if not staff or staff["role"] != "gestor":
            raise HTTPException(status_code=403, detail="Requer perfil gestor")
        return staff

    return _dep


def require_driver(request=None):
    from starlette.requests import Request as StarRequest

    def _dep(request: StarRequest):
        token = _bearer(request)
        driver_id = verify_driver_token(token)
        if driver_id is None:
            raise HTTPException(status_code=401, detail="Token de entregador inválido")
        return driver_id

    return _dep


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class DriverLoginIn(BaseModel):
    driver_id: int
    pin: str


class LocationIn(BaseModel):
    driver_id: int
    lat: float
    lon: float
    order_id: Optional[int] = None


class AssignIn(BaseModel):
    dest_lat: float
    dest_lon: float
    stopped_alert_min: Optional[int] = None


class DeliverySettingsIn(BaseModel):
    avg_speed_kmh: Optional[float] = None
    stopped_alert_min: Optional[int] = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_settings_from_db() -> dict:
    with get_conn(DB_PATH) as conn:
        rows = conn.execute("SELECT key, value FROM delivery_settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


def _get_avg_speed() -> float:
    s = _get_settings_from_db()
    try:
        return float(s.get("avg_speed_kmh", "30"))
    except ValueError:
        return 30.0


def _get_stopped_alert_min() -> int:
    s = _get_settings_from_db()
    try:
        return int(s.get("stopped_alert_min", "5"))
    except ValueError:
        return 5


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"ok": True, "service": "farmacia-pedro-delivery"}


# ── Driver management ─────────────────────────────────────────────────────────

@app.get("/api/drivers")
def list_drivers(staff=Depends(require_staff())):
    with get_conn(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, name, photo_path, status, created_at FROM drivers ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/drivers", status_code=201)
async def create_driver(
    name: str = Form(...),
    pin: str = Form(...),
    photo: Optional[UploadFile] = File(None),
    staff=Depends(require_gestor()),
):
    if len(pin) != 6 or not pin.isdigit():
        raise HTTPException(400, "PIN deve ter exatamente 6 dígitos numéricos")
    pin_hash = hash_pin(pin)
    photo_path = None
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower() or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join(UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(photo.file, f)
        photo_path = f"/uploads/drivers/{filename}"
    with get_conn(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO drivers (name, pin_hash, photo_path) VALUES (?, ?, ?)",
            (name, pin_hash, photo_path),
        )
        conn.commit()
        driver_id = cur.lastrowid
    return {"id": driver_id, "name": name, "photo_path": photo_path, "status": "available"}


@app.get("/api/drivers/{driver_id}/status")
def driver_status(driver_id: int, staff=Depends(require_staff())):
    with get_conn(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, name, status, photo_path FROM drivers WHERE id = ?", (driver_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Entregador não encontrado")
    pos = tracker.get_latest_position(driver_id)
    result = dict(row)
    if pos:
        result["lat"] = pos.lat
        result["lon"] = pos.lon
        result["last_update"] = pos.recorded_at
    return result


# ── Order assignment ──────────────────────────────────────────────────────────

@app.post("/api/drivers/{driver_id}/assign/{order_id}", status_code=201)
def assign_order(driver_id: int, order_id: int, body: AssignIn, staff=Depends(require_staff())):
    with get_conn(DB_PATH) as conn:
        driver = conn.execute(
            "SELECT id, status FROM drivers WHERE id = ?", (driver_id,)
        ).fetchone()
        if not driver:
            raise HTTPException(404, "Entregador não encontrado")
        if driver["status"] not in ("available",):
            raise HTTPException(409, f"Entregador está '{driver['status']}', não disponível")

        order = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(404, "Pedido não encontrado")

        existing = conn.execute(
            "SELECT id FROM delivery_assignments WHERE order_id = ? AND status NOT IN ('completed','cancelled')",
            (order_id,),
        ).fetchone()
        if existing:
            raise HTTPException(409, "Pedido já possui entrega ativa")

        avg_speed = _get_avg_speed()
        eta = None
        if body.dest_lat and body.dest_lon:
            _, eta = calc_eta(body.dest_lat, body.dest_lon, body.dest_lat, body.dest_lon, avg_speed)

        token = generate_tracking_token()
        alert_min = body.stopped_alert_min or _get_stopped_alert_min()

        cur = conn.execute(
            """INSERT INTO delivery_assignments
               (driver_id, order_id, status, tracking_token, eta_minutes,
                dest_lat, dest_lon, stopped_alert_min)
               VALUES (?, ?, 'assigned', ?, ?, ?, ?, ?)""",
            (driver_id, order_id, token, eta, body.dest_lat, body.dest_lon, alert_min),
        )
        conn.execute("UPDATE drivers SET status = 'on_route' WHERE id = ?", (driver_id,))
        conn.commit()
        assignment_id = cur.lastrowid

    return {
        "assignment_id": assignment_id,
        "tracking_token": token,
        "tracking_url": f"/track/{order_id}?token={token}",
    }


# ── Tracking (public, token-gated) ───────────────────────────────────────────

@app.get("/track/{order_id}")
def get_tracking_state(order_id: int, token: str):
    with get_conn(DB_PATH) as conn:
        assignment = conn.execute(
            """SELECT da.*, d.name as driver_name, d.photo_path
               FROM delivery_assignments da
               JOIN drivers d ON d.id = da.driver_id
               WHERE da.order_id = ? AND da.tracking_token = ?""",
            (order_id, token),
        ).fetchone()
    if not assignment:
        raise HTTPException(404, "Entrega não encontrada ou token inválido")

    status_map = {
        "assigned": "confirmed",
        "in_progress": "out_for_delivery",
        "completed": "delivered",
        "cancelled": "cancelled",
    }
    pos = tracker.get_latest_position(assignment["driver_id"])
    return {
        "order_id": order_id,
        "status": status_map.get(assignment["status"], assignment["status"]),
        "driver_name": assignment["driver_name"],
        "driver_photo": assignment["photo_path"],
        "lat": pos.lat if pos else None,
        "lon": pos.lon if pos else None,
        "eta_minutes": assignment["eta_minutes"],
        "dest_lat": assignment["dest_lat"],
        "dest_lon": assignment["dest_lon"],
    }


# Serve the tracking SPA
@app.get("/track/{order_id}/page")
def tracking_page(order_id: int):
    return FileResponse("out/track/index.html")


# ── Driver app endpoints ──────────────────────────────────────────────────────

@app.post("/driver/login")
def driver_login(body: DriverLoginIn):
    with get_conn(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, name, pin_hash, status FROM drivers WHERE id = ?", (body.driver_id,)
        ).fetchone()
    if not row or not verify_pin(body.pin, row["pin_hash"]):
        raise HTTPException(401, "Credenciais inválidas")
    token = create_driver_token(row["id"])
    return {"access_token": token, "token_type": "bearer", "driver_name": row["name"], "status": row["status"]}


@app.post("/driver/location")
async def update_location(body: LocationIn, driver_id: int = Depends(require_driver())):
    if body.driver_id != driver_id:
        raise HTTPException(403, "driver_id não corresponde ao token")

    with get_conn(DB_PATH) as conn:
        assignment = conn.execute(
            """SELECT da.*, d.name as driver_name, d.photo_path
               FROM delivery_assignments da
               JOIN drivers d ON d.id = da.driver_id
               WHERE da.driver_id = ? AND da.status = 'in_progress'""",
            (driver_id,),
        ).fetchone()

        avg_speed = _get_avg_speed()
        eta, distance_km = None, None
        if assignment and assignment["dest_lat"]:
            distance_km, eta = calc_eta(
                body.lat, body.lon,
                assignment["dest_lat"], assignment["dest_lon"],
                avg_speed,
            )
            conn.execute(
                "UPDATE delivery_assignments SET eta_minutes = ? WHERE id = ?",
                (eta, assignment["id"]),
            )

        conn.execute(
            "INSERT INTO driver_locations (driver_id, order_id, lat, lon) VALUES (?, ?, ?, ?)",
            (driver_id, body.order_id, body.lat, body.lon),
        )

        # Update assignment to in_progress if still assigned
        if assignment and assignment["status"] == "assigned":
            conn.execute(
                "UPDATE delivery_assignments SET status = 'in_progress', started_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), assignment["id"]),
            )
        conn.commit()

    alert = await tracker.update_location(
        driver_id=driver_id,
        lat=body.lat,
        lon=body.lon,
        order_id=body.order_id,
        eta_minutes=eta,
        distance_km=distance_km,
        driver_name=assignment["driver_name"] if assignment else None,
        driver_photo=assignment["photo_path"] if assignment else None,
    )
    return {"ok": True, "eta_minutes": eta, "distance_km": distance_km, "stopped_alert": alert}


@app.post("/driver/order/{order_id}/complete")
async def complete_delivery(order_id: int, driver_id: int = Depends(require_driver())):
    with get_conn(DB_PATH) as conn:
        assignment = conn.execute(
            "SELECT id, driver_id FROM delivery_assignments WHERE order_id = ? AND driver_id = ? AND status = 'in_progress'",
            (order_id, driver_id),
        ).fetchone()
        if not assignment:
            raise HTTPException(404, "Entrega ativa não encontrada para este pedido/entregador")
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE delivery_assignments SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, assignment["id"]),
        )
        conn.execute("UPDATE drivers SET status = 'available' WHERE id = ?", (driver_id,))
        conn.commit()

    await tracker.broadcast_delivery_completed(driver_id, order_id)
    return {"ok": True, "completed_at": datetime.now(timezone.utc).isoformat()}


# ── Settings ──────────────────────────────────────────────────────────────────

@app.get("/api/settings/delivery")
def get_delivery_settings(staff=Depends(require_gestor())):
    s = _get_settings_from_db()
    return {
        "avg_speed_kmh": float(s.get("avg_speed_kmh", "30")),
        "stopped_alert_min": int(s.get("stopped_alert_min", "5")),
    }


@app.patch("/api/settings/delivery")
def update_delivery_settings(body: DeliverySettingsIn, staff=Depends(require_gestor())):
    with get_conn(DB_PATH) as conn:
        if body.avg_speed_kmh is not None:
            conn.execute(
                "INSERT OR REPLACE INTO delivery_settings (key, value) VALUES ('avg_speed_kmh', ?)",
                (str(body.avg_speed_kmh),),
            )
            tracker.settings.avg_speed_kmh = body.avg_speed_kmh
        if body.stopped_alert_min is not None:
            conn.execute(
                "INSERT OR REPLACE INTO delivery_settings (key, value) VALUES ('stopped_alert_min', ?)",
                (str(body.stopped_alert_min),),
            )
            tracker.settings.stopped_alert_min = body.stopped_alert_min
        conn.commit()
    return {"ok": True}


# ── WebSocket endpoints ───────────────────────────────────────────────────────

@app.websocket("/ws/driver/{driver_id}")
async def ws_driver(websocket: WebSocket, driver_id: int, token: str = ""):
    staff = verify_staff_token(token)
    if not staff:
        await websocket.close(code=4001)
        return
    channel = f"driver:{driver_id}"
    await websocket.accept()
    tracker.add_connection(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        tracker.remove_connection(channel, websocket)


@app.websocket("/ws/order/{order_id}")
async def ws_order(websocket: WebSocket, order_id: int, token: str = ""):
    with get_conn(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM delivery_assignments WHERE order_id = ? AND tracking_token = ?",
            (order_id, token),
        ).fetchone()
    if not row:
        await websocket.close(code=4001)
        return
    channel = f"order:{order_id}"
    await websocket.accept()
    tracker.add_connection(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        tracker.remove_connection(channel, websocket)


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("DELIVERY_PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "0") in ("1", "true", "yes")
    print(f"Delivery server iniciando em http://{host}:{port}")
    uvicorn.run("scripts.delivery_server:app", host=host, port=port, reload=reload, log_level="info")
