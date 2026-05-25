from datetime import datetime, timedelta, timezone
from typing import Dict


def run(conn, settings) -> Dict:
    estoque_parado = []
    recompras = []

    if "turnover" in settings.scopes.get("inventory", set()):
        rows = conn.execute(
            """
            SELECT p.id, p.sku, p.name, p.stock, MAX(s.sale_date) AS last_sale
            FROM products p
            LEFT JOIN sales s ON s.product_id = p.id
            GROUP BY p.id
            """
        ).fetchall()
        today = datetime.now(timezone.utc).date()
        for row in rows:
            last_sale = row["last_sale"]
            if last_sale is None:
                days_no_sales = settings.days_no_sales + 1
                last_sale_str = "nunca"
            else:
                last_sale_clean = last_sale.split("T")[0].split(" ")[0]
                last_sale_date = datetime.strptime(last_sale_clean, "%Y-%m-%d").date()
                days_no_sales = (today - last_sale_date).days
                last_sale_str = last_sale_clean

            if days_no_sales > settings.days_no_sales:
                estoque_parado.append(
                    {
                        "sku": row["sku"],
                        "nome": row["name"],
                        "ultima_venda": last_sale_str,
                        "dias_sem_venda": days_no_sales,
                    }
                )

    if "stock" in settings.scopes.get("inventory", set()):
        since = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()
        rows = conn.execute(
            """
            SELECT p.id, p.sku, p.name, p.stock, COALESCE(SUM(s.qty), 0) AS qty
            FROM products p
            LEFT JOIN sales s ON s.product_id = p.id AND s.sale_date >= ?
            GROUP BY p.id
            """,
            (since,),
        ).fetchall()
        for row in rows:
            avg_daily = row["qty"] / 30.0
            target_stock = avg_daily * settings.safety_stock_days
            if target_stock > row["stock"] + 1:
                reorder_qty = int(round(target_stock - row["stock"], 0))
                recompras.append(
                    {
                        "sku": row["sku"],
                        "nome": row["name"],
                        "quantidade_recompra": max(reorder_qty, 1),
                    }
                )

    return {
        "estoque_parado": estoque_parado,
        "recompras": recompras,
    }
