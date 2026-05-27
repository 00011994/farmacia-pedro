"""
In-memory state for the delivery system.
Holds the latest GPS position of each driver and manages WebSocket connections.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from .models import DriverLocation, DeliverySettings


class DeliveryTracker:
    def __init__(self) -> None:
        # driver_id -> latest DriverLocation
        self._positions: dict[int, DriverLocation] = {}
        # channel -> set of websockets  (channel = "driver:{id}" or "order:{id}")
        self._connections: dict[str, set] = {}
        self.settings = DeliverySettings()

    # ── WebSocket connection management ──────────────────────────────────────

    def add_connection(self, channel: str, ws) -> None:
        self._connections.setdefault(channel, set()).add(ws)

    def remove_connection(self, channel: str, ws) -> None:
        subs = self._connections.get(channel, set())
        subs.discard(ws)

    async def broadcast(self, channel: str, payload: dict) -> None:
        subs = list(self._connections.get(channel, set()))
        if not subs:
            return
        message = json.dumps(payload)
        await asyncio.gather(*[ws.send_text(message) for ws in subs], return_exceptions=True)

    # ── Location update ───────────────────────────────────────────────────────

    async def update_location(
        self,
        driver_id: int,
        lat: float,
        lon: float,
        order_id: Optional[int],
        eta_minutes: Optional[int],
        distance_km: Optional[float],
        driver_name: Optional[str] = None,
        driver_photo: Optional[str] = None,
    ) -> bool:
        """
        Records new GPS position, checks stopped-alert, and broadcasts to both channels.
        Returns True if a stopped-alert was triggered.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        prev = self._positions.get(driver_id)
        stopped_alert = False

        if prev is not None:
            stopped_alert = self._check_stopped(prev, now_str)

        loc = DriverLocation(
            id=0,
            driver_id=driver_id,
            order_id=order_id,
            lat=lat,
            lon=lon,
            recorded_at=now_str,
        )
        self._positions[driver_id] = loc

        # Broadcast to internal admin channel
        admin_payload: dict = {
            "type": "location_update",
            "driver_id": driver_id,
            "lat": lat,
            "lon": lon,
            "order_id": order_id,
            "eta_minutes": eta_minutes,
            "recorded_at": now_str,
        }
        await self.broadcast(f"driver:{driver_id}", admin_payload)

        if stopped_alert:
            alert_payload = {
                "type": "driver_stopped_alert",
                "driver_id": driver_id,
                "stopped_minutes": self.settings.stopped_alert_min,
                "lat": lat,
                "lon": lon,
            }
            await self.broadcast(f"driver:{driver_id}", alert_payload)

        # Broadcast to customer tracking channel (no driver_id exposed)
        if order_id is not None:
            customer_payload: dict = {
                "type": "location_update",
                "lat": lat,
                "lon": lon,
                "eta_minutes": eta_minutes,
                "distance_km": distance_km,
            }
            await self.broadcast(f"order:{order_id}", customer_payload)

        return stopped_alert

    async def broadcast_status_change(
        self,
        driver_id: int,
        order_id: int,
        order_status: str,
        driver_name: Optional[str] = None,
        driver_photo: Optional[str] = None,
    ) -> None:
        await self.broadcast(f"driver:{driver_id}", {
            "type": "driver_status_changed",
            "driver_id": driver_id,
            "status": order_status,
        })
        customer_payload: dict = {
            "type": "order_status_changed",
            "status": order_status,
        }
        if driver_name:
            customer_payload["driver_name"] = driver_name
        if driver_photo:
            customer_payload["driver_photo"] = driver_photo
        await self.broadcast(f"order:{order_id}", customer_payload)

    async def broadcast_delivery_completed(self, driver_id: int, order_id: int) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        completed_payload = {"type": "delivery_completed", "completed_at": now_str}
        await self.broadcast(f"driver:{driver_id}", {**completed_payload, "driver_id": driver_id, "order_id": order_id})
        await self.broadcast(f"order:{order_id}", completed_payload)
        # Clean up position for this driver
        self._positions.pop(driver_id, None)

    def get_latest_position(self, driver_id: int) -> Optional[DriverLocation]:
        return self._positions.get(driver_id)

    # ── Stopped-alert logic ───────────────────────────────────────────────────

    def _check_stopped(self, prev: DriverLocation, now_str: str) -> bool:
        try:
            prev_dt = datetime.fromisoformat(prev.recorded_at.replace("Z", "+00:00"))
            now_dt = datetime.fromisoformat(now_str.replace("Z", "+00:00"))
            delta_minutes = (now_dt - prev_dt).total_seconds() / 60
            return delta_minutes >= self.settings.stopped_alert_min
        except Exception:
            return False


# Global singleton — shared across all request handlers in the same process
tracker = DeliveryTracker()
