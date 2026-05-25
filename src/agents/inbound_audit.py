from datetime import datetime
from typing import Dict


def run(conn, settings) -> Dict:
    margem_baixa = []
    if "invoices" not in settings.scopes.get("audit", set()):
        return {"margem_baixa": margem_baixa}

    rows = conn.execute(
        """
        SELECT i.id, p.sku, p.name, p.price, i.unit_cost, i.invoice_date
        FROM invoices i
        JOIN products p ON p.id = i.product_id
        ORDER BY i.invoice_date DESC
        LIMIT 20
        """
    ).fetchall()

    for row in rows:
        price = row["price"]
        cost = row["unit_cost"]
        if price <= 0:
            continue
        margin = (price - cost) / price
        entry = {
            "sku": row["sku"],
            "nome": row["name"],
            "custo_unitario": round(cost, 2),
            "preco": round(price, 2),
            "margem_pct": round(margin * 100, 1),
            "data_nota": row["invoice_date"],
        }
        if margin < 0:
            entry["anomalia"] = "custo_maior_que_preco"
            margem_baixa.append(entry)
        elif margin < settings.low_margin_threshold:
            margem_baixa.append(entry)

    return {"margem_baixa": margem_baixa}
