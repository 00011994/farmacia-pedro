import json
import os

import pytest

from src.chat.data import SqliteGateway, _normalize
from src.chat.flow_atendimento import AtendimentoFlow, _match_delivery_rule, _parse_delivery_rules
from src.chat.state import SessionStore


# ── data.py ──────────────────────────────────────────────────────────────────

def test_normalize_strips_accents():
    assert _normalize("Díprona") == "diprona"


def test_normalize_removes_special_chars():
    result = _normalize("anti-inflamatório!")
    assert "!" not in result
    assert "-" not in result


def test_search_products_finds_by_name(tmp_db, settings):
    gw = SqliteGateway(tmp_db)
    results = gw.search_products("dipirona")
    assert len(results) == 1
    assert results[0].sku == "MED001"


def test_search_products_empty_query_returns_empty(tmp_db):
    gw = SqliteGateway(tmp_db)
    results = gw.search_products("")
    assert results == []


def test_get_product_missing_returns_none(tmp_db):
    gw = SqliteGateway(tmp_db)
    assert gw.get_product("INEXISTENTE") is None


def test_stock_by_sku_missing_returns_none(tmp_db):
    gw = SqliteGateway(tmp_db)
    assert gw.stock_by_sku("NAOEXISTE") is None


# ── flow_atendimento.py ───────────────────────────────────────────────────────

def test_delivery_rule_specificity(settings):
    rules = _parse_delivery_rules("Barra:5:30min;Barra Blue:8:60min")
    result = _match_delivery_rule("Barra Blue", rules)
    assert result is not None
    assert result[0] == "Barra Blue"  # Regra mais específica vence


def test_delivery_rule_no_match_returns_none(settings):
    rules = _parse_delivery_rules("Recreio:8:60min")
    assert _match_delivery_rule("Tijuca", rules) is None


def test_atendimento_flow_start_greets(tmp_db, settings):
    from src.chat.data import SqliteGateway
    gw = SqliteGateway(tmp_db)
    flow = AtendimentoFlow(settings, gw)
    resp, state, _ = flow.handle("START", {}, "oi")
    assert state in {"START", "ASK_QTY", "ASK_PRODUCT_CHOICE"}


def test_atendimento_flow_product_not_found_returns_greeting(tmp_db, settings):
    from src.chat.data import SqliteGateway
    gw = SqliteGateway(tmp_db)
    flow = AtendimentoFlow(settings, gw)
    resp, state, _ = flow.handle("START", {}, "xyzabc produto inexistente")
    assert state == "START"


def test_atendimento_flow_sair_ends_session(tmp_db, settings):
    from src.chat.data import SqliteGateway
    gw = SqliteGateway(tmp_db)
    flow = AtendimentoFlow(settings, gw)
    resp, state, _ = flow.handle("START", {}, "sair")
    assert state == "DONE"


def test_atendimento_flow_choice_empty_opcoes_falls_back(tmp_db, settings):
    from src.chat.data import SqliteGateway
    gw = SqliteGateway(tmp_db)
    flow = AtendimentoFlow(settings, gw)
    # opcoes vazia — não deve lançar exceção
    resp, state, _ = flow.handle("ASK_PRODUCT_CHOICE", {"opcoes": []}, "1")
    assert state == "START"


# ── state.py ─────────────────────────────────────────────────────────────────

def test_session_store_roundtrip(tmp_path):
    store = SessionStore(str(tmp_path))
    store.append("sess1", "user", "ola")
    store.append("sess1", "assistant", "oi tudo bem")
    state = store.load("sess1")
    assert len(state.messages) == 2
    assert state.messages[0].content == "ola"


def test_session_store_corrupted_line_is_skipped(tmp_path, capsys):
    store = SessionStore(str(tmp_path))
    path = store._path("sess_corrupt")
    os.makedirs(tmp_path, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write('{"role":"user","content":"ok"}\n')
        f.write("LINHA CORROMPIDA NAO JSON\n")
        f.write('{"role":"assistant","content":"resp"}\n')
    state = store.load("sess_corrupt")
    assert len(state.messages) == 2
    captured = capsys.readouterr()
    assert "corrompida" in captured.err


def test_session_state_save_and_load(tmp_path):
    store = SessionStore(str(tmp_path))
    store.save_state("sess2", "ASK_QTY", {"produto": {"sku": "MED001"}})
    loaded = store.load_state("sess2")
    assert loaded["state"] == "ASK_QTY"
    assert loaded["data"]["produto"]["sku"] == "MED001"
