from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Driver:
    id: int
    name: str
    pin_hash: str
    photo_path: Optional[str]
    status: str  # available | on_route | paused | offline
    created_at: str


@dataclass
class DriverLocation:
    id: int
    driver_id: int
    order_id: Optional[int]
    lat: float
    lon: float
    recorded_at: str


@dataclass
class DeliveryAssignment:
    id: int
    driver_id: int
    order_id: int
    status: str  # assigned | in_progress | completed | cancelled
    tracking_token: str
    eta_minutes: Optional[int]
    dest_lat: Optional[float]
    dest_lon: Optional[float]
    assigned_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    stopped_alert_min: int


@dataclass
class TrackingState:
    order_id: int
    status: str  # confirmed | preparing | out_for_delivery | delivered
    driver_name: Optional[str]
    driver_photo: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    eta_minutes: Optional[int]
    distance_km: Optional[float]


@dataclass
class DeliverySettings:
    avg_speed_kmh: float = 30.0
    stopped_alert_min: int = 5
