import json
import os
from datetime import datetime, timezone

from src.core.config import load_settings
from src.core.db import get_conn
from src.core.formatting import to_markdown
from src.core.logging import log_event
from src.agents.operational import run as run_operational
from src.agents.inbound_audit import run as run_inbound_audit
from src.agents.strategist import run as run_strategist
from src.agents.inventory import run as run_inventory
from src.agents.executor_stub import run as run_executor
from src.integrations.whatsapp import WhatsAppIntegration


def build_bonus_alerts(conn, settings):
    rows = conn.execute(
        """
        SELECT sku, name, price, avg_cost
        FROM products
        WHERE avg_cost > 0
        """
    ).fetchall()

    alertas = []
    for row in rows:
        markup = ((row["price"] - row["avg_cost"]) / row["avg_cost"]) * 100
        if markup > settings.bonus_markup_pct:
            alertas.append(
                {
                    "sku": row["sku"],
                    "nome": row["name"],
                    "preco": round(row["price"], 2),
                    "custo_medio": round(row["avg_cost"], 2),
                    "markup_pct": round(markup, 1),
                }
            )
    return alertas


def generate_report(settings):
    os.makedirs(settings.report_dir, exist_ok=True)

    def _run_agent(name, fn, conn, cfg):
        try:
            return fn(conn, cfg)
        except Exception as exc:
            log_event(cfg.report_dir, "agente_erro", {"agente": name, "erro": str(exc)})
            return {"erro": str(exc)}

    with get_conn(settings.db_path) as conn:
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        report = {
            "gerado_em": generated_at,
            "operacional": _run_agent("operacional", run_operational, conn, settings),
            "auditoria_entrada": _run_agent("auditoria_entrada", run_inbound_audit, conn, settings),
            "estrategista": _run_agent("estrategista", run_strategist, conn, settings),
            "estoque": _run_agent("estoque", run_inventory, conn, settings),
            "executor": _run_agent("executor", run_executor, conn, settings),
            "regras": {"alertas_bonus": _run_agent("bonus", build_bonus_alerts, conn, settings)},
        }

    json_path = os.path.join(settings.report_dir, "report.json")
    md_path = os.path.join(settings.report_dir, "report.md")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(to_markdown(report))

    log_event(settings.report_dir, "relatorio_gerado", {"json": json_path, "md": md_path})

    return report, json_path, md_path


def main():
    settings = load_settings()
    _, json_path, md_path = generate_report(settings)
    print(f"Relatorio gerado: {json_path}")
    print(f"Relatorio gerado: {md_path}")

    # Exemplo de uso plug and play
    wa = WhatsAppIntegration()
    # wa.send_message('5511999999999', 'Mensagem de teste!')
    # Para trocar o número, basta:
    # wa.update_number('5511988888888')
    # print(wa.get_number())


if __name__ == "__main__":
    main()
