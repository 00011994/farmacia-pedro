import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_current_user, get_settings
from src.core.config import Settings
from src.runner import generate_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/latest")
def get_latest_report(
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    report_path = os.path.join(settings.report_dir, "report.json")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Nenhum relatorio gerado ainda. Execute a automacao primeiro.")

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if user["role"] != "gestor":
        data.pop("auditoria_entrada", None)
        data.pop("regras", None)
        for agent_data in [data.get("estrategista", {}), data.get("estoque", {})]:
            agent_data.pop("alertas_concorrencia", None)

    return data


@router.post("/generate")
def trigger_report(
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    if user["role"] != "gestor":
        raise HTTPException(status_code=403, detail="Apenas gestores podem gerar relatorios manualmente")
    try:
        generate_report(settings)
        return {"ok": True, "message": "Relatorio gerado com sucesso", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatorio: {exc}")


@router.get("/audit-log")
def get_audit_log(
    limit: int = 100,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    if user["role"] != "gestor":
        raise HTTPException(status_code=403, detail="Apenas gestores podem ver o log de auditoria")

    log_path = os.path.join(settings.report_dir, "audit_log.jsonl")
    if not os.path.exists(log_path):
        return {"entries": []}

    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return {"entries": list(reversed(entries))}
