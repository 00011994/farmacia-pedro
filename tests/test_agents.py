import sqlite3

from src.core.db import get_conn
from src.agents.operational import run as run_operational
from src.agents.inbound_audit import run as run_inbound_audit
from src.agents.inventory import run as run_inventory
from src.agents.strategist import run as run_strategist
from src.agents.executor_stub import run as run_executor


def test_operational_returns_expected_keys(tmp_db, settings):
    with get_conn(tmp_db) as conn:
        result = run_operational(conn, settings)
    assert "estoque_baixo" in result
    assert "pedidos_recentes" in result


def test_operational_low_stock_orders_by_stock(tmp_db, settings):
    with get_conn(tmp_db) as conn:
        result = run_operational(conn, settings)
    # HIG001 tem estoque=2, deve aparecer antes de MED001 (50)
    skus = [r["sku"] for r in result["estoque_baixo"]]
    assert "HIG001" in skus
    assert skus.index("HIG001") < skus.index("MED001")


def test_inbound_audit_negative_margin_flagged(tmp_db, settings):
    conn_raw = sqlite3.connect(tmp_db)
    conn_raw.row_factory = sqlite3.Row
    # Insere nota com custo > preço para MED001 (preço=12.90)
    conn_raw.execute(
        "INSERT INTO invoices (product_id, unit_cost, invoice_date, supplier) VALUES (1, 20.00, '2026-01-01', 'TesteFornecedor')"
    )
    conn_raw.commit()
    conn_raw.close()

    with get_conn(tmp_db) as conn:
        result = run_inbound_audit(conn, settings)

    anomalias = [r for r in result["margem_baixa"] if r.get("anomalia") == "custo_maior_que_preco"]
    assert len(anomalias) >= 1


def test_inventory_dead_stock_no_crash_without_sales(tmp_db, settings):
    with get_conn(tmp_db) as conn:
        result = run_inventory(conn, settings)
    assert "estoque_parado" in result
    assert "recompras" in result
    # Todos os produtos sem vendas devem aparecer como estoque parado
    skus = [r["sku"] for r in result["estoque_parado"]]
    assert "MED001" in skus


def test_inventory_date_with_timestamp(tmp_db, settings):
    conn_raw = sqlite3.connect(tmp_db)
    conn_raw.row_factory = sqlite3.Row
    # Insere venda com timestamp completo (formato com T)
    conn_raw.execute(
        "INSERT INTO sales (product_id, qty, price, sale_date, region) VALUES (1, 1, 12.90, '2020-01-01T10:30:00', 'centro')"
    )
    conn_raw.commit()
    conn_raw.close()

    with get_conn(tmp_db) as conn:
        result = run_inventory(conn, settings)
    # Não deve lançar exceção; MED001 deve aparecer como parado (venda em 2020)
    skus = [r["sku"] for r in result["estoque_parado"]]
    assert "MED001" in skus


def test_executor_stub_returns_disabled(tmp_db, settings):
    with get_conn(tmp_db) as conn:
        result = run_executor(conn, settings)
    assert result.get("status") == "desabilitado"


def test_strategist_returns_expected_keys(tmp_db, settings):
    with get_conn(tmp_db) as conn:
        result = run_strategist(conn, settings)
    assert "quedas_giro" in result
    assert "alertas_concorrencia" in result
