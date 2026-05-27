import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt_lib
from jose import jwt, JWTError

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "TROQUE-ESSA-CHAVE-EM-PRODUCAO-use-openssl-rand-hex-32")
ALGORITHM = "HS256"
DRIVER_TOKEN_EXPIRE_HOURS = 12


def hash_pin(pin: str) -> str:
    return _bcrypt_lib.hashpw(pin.encode(), _bcrypt_lib.gensalt()).decode()


def verify_pin(pin: str, hashed: str) -> bool:
    try:
        return _bcrypt_lib.checkpw(pin.encode(), hashed.encode())
    except Exception:
        return False


def create_driver_token(driver_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=DRIVER_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(driver_id), "role": "driver", "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_driver_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "driver":
            return None
        sub = payload.get("sub")
        return int(sub) if sub else None
    except (JWTError, ValueError):
        return None


def verify_staff_token(token: str) -> Optional[dict]:
    """Validates a token issued by the main API server (gestor/funcionario)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        if role not in ("gestor", "funcionario"):
            return None
        return {"user_id": int(payload["sub"]), "role": role}
    except (JWTError, ValueError, KeyError):
        return None


def generate_tracking_token() -> str:
    return str(uuid.uuid4())
