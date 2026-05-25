import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

from src.core.config import load_settings
from src.core.logging import log_event
from src.runner import generate_report


def _post_json(url: str, payload: dict, timeout: int = 10) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="ignore")
        return {"status": response.status, "body": body}


def send_whatsapp(settings, report: dict, md_path: str, json_path: str) -> dict:
    if not settings.whatsapp_webhook_url:
        log_event(settings.report_dir, "whatsapp_pulado", {"motivo": "webhook_ausente"})
        return {"status": "pulado", "motivo": "webhook_ausente"}

    with open(md_path, "r", encoding="ascii") as handle:
        markdown = handle.read()

    payload = {
        "tipo": "relatorio",
        "gerado_em": report.get("gerado_em"),
        "para": settings.whatsapp_to,
        "remetente": settings.whatsapp_sender,
        "relatorio": report,
        "markdown": markdown,
        "caminho_json": os.path.abspath(json_path),
        "caminho_md": os.path.abspath(md_path),
    }
    try:
        response = _post_json(settings.whatsapp_webhook_url, payload)
        log_event(settings.report_dir, "whatsapp_enviado", {"http_status": response.get("status")})
        return {"status": "enviado", "http_status": response.get("status")}
    except Exception as exc:
        log_event(settings.report_dir, "whatsapp_erro", {"erro": str(exc)})
        return {"status": "erro", "motivo": str(exc)}


def ensure_demo_db(settings) -> None:
    if not settings.automation_seed_demo:
        return
    if os.path.exists(settings.db_path):
        return
    subprocess.check_call([sys.executable, os.path.join("scripts", "seed_demo_db.py")])


def _run_with_retries(fn, retries: int, delay_sec: int):
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            if attempt >= retries:
                raise
            attempt += 1
            time.sleep(delay_sec)


def run_once() -> dict:
    settings = load_settings()
    ensure_demo_db(settings)
    report, json_path, md_path = generate_report(settings)
    delivery = send_whatsapp(settings, report, md_path, json_path)
    log_event(
        settings.report_dir,
        "automacao_executada",
        {"entrega": delivery, "json": json_path, "md": md_path},
    )
    return {"entrega": delivery, "json": json_path, "md": md_path}


def run_loop():
    settings = load_settings()
    interval_sec = max(60, settings.automation_interval_min * 60)
    max_runs = settings.automation_max_runs
    retries = max(0, settings.automation_retries)
    delay_sec = max(1, settings.automation_retry_delay_sec)

    runs = 0
    while True:
        _run_with_retries(run_once, retries, delay_sec)
        runs += 1
        if max_runs and runs >= max_runs:
            break
        time.sleep(interval_sec)


def main():
    settings = load_settings()
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    log_event(settings.report_dir, "automacao_iniciada", {"iniciada_em": started_at})

    mode = settings.automation_mode.lower().strip()
    if mode in {"schedule", "agendado"}:
        run_loop()
    else:
        run_once()


if __name__ == "__main__":
    main()
