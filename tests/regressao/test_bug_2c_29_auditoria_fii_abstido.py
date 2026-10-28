"""BUG-2C-29: auditoria não pode inventar valor justo de FII abstido (D24)."""

from unittest.mock import Mock

import pytest

import auditoria


@pytest.mark.parametrize("falha", [False, True])
def test_abstencao_fii_preserva_ausencia_e_motivo(monkeypatch, tmp_path, falha):
    import fii_engine

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(auditoria.sys, "argv", ["auditoria.py", "TSTF11"])
    monkeypatch.setattr(auditoria, "_rel", {"meta": {}, "tickers": {"TSTF11": {}}})
    for nome in (
        "auditar_selic",
        "auditar_banco",
        "auditar_tecnica",
        "auditar_prompt",
        "auditar_referencia",
    ):
        monkeypatch.setattr(auditoria, nome, Mock())
    monkeypatch.setattr(
        auditoria,
        "auditar_dados_scraper",
        lambda t: {
            "ticker": t,
            "preco_atual": 100,
            "classe_ativo": "FII",
        },
    )
    engine = Mock()
    if falha:
        engine.analisar.side_effect = ValueError("fonte de teste indisponível")
    else:
        engine.analisar.return_value = {
            "fair_value": None,
            "upside": None,
            "motivo": "fonte de teste indisponível",
        }
    monkeypatch.setattr(fii_engine, "FIIEngine", lambda: engine)
    auditoria.main()
    dados = auditoria.auditar_prompt.call_args.args[1]
    assert dados["fair_value"] is None
    assert dados["upside"] is None
    assert "fonte de teste indisponível" in str(dados)
