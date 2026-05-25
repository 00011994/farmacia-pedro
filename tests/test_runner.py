import json
import os

from src.runner import generate_report


def test_generate_report_creates_files(settings, tmp_path):
    report, json_path, md_path = generate_report(settings)
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "gerado_em" in data
    assert "operacional" in data
    assert "estoque" in data
    assert "regras" in data


def test_generate_report_survives_agent_error(settings, monkeypatch):
    def boom(conn, cfg):
        raise RuntimeError("agente explodiu")

    # Patcha no namespace do runner onde a função já foi importada
    monkeypatch.setattr("src.runner.run_operational", boom)
    report, _, _ = generate_report(settings)
    # Não deve lançar exceção; deve incluir chave de erro
    assert "erro" in report["operacional"]


def test_report_files_are_utf8(settings):
    _, json_path, md_path = generate_report(settings)
    # Leitura sem erros confirma encoding UTF-8 correto
    with open(json_path, encoding="utf-8") as f:
        f.read()
    with open(md_path, encoding="utf-8") as f:
        f.read()
