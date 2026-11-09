"""Ficha apresentação1.0: leitor não fabrica síntese ausente nem orientação."""

from unittest.mock import MagicMock

import pandas as pd

import auditar_recomendacoes as audit
import auditoria


def test_cli_mostra_lente_abstida_sem_score_ou_valor_zero(monkeypatch):
    mercado = MagicMock()
    mercado.buscar_dados_ticker.return_value = {
        "ticker": "TSTA3",
        "preco_atual": 10,
        "historico": pd.DataFrame({"Close": [10]}),
    }
    motor = MagicMock()
    motor.processar.return_value = {
        "apresentacao_versao": "1.0",
        "lentes": {
            "Graham": {
                "valor": None,
                "abstencao": "insumo ausente",
                "distancia_ao_preco_pct": None,
            },
            "Bazin": {"valor": 12, "abstencao": None, "distancia_ao_preco_pct": 20},
        },
    }
    monkeypatch.setattr(audit, "TICKERS_AUDITORIA", ["TSTA3"])
    monkeypatch.setattr(audit, "tickers_oficiais", lambda *_: ["TSTA3"])
    monkeypatch.setattr(audit, "MarketEngine", lambda: mercado)
    monkeypatch.setattr(audit, "ValuationEngine", lambda: motor)
    monkeypatch.setattr(audit, "FIIEngine", MagicMock)
    monkeypatch.setattr(audit, "TechnicalEngine", MagicMock)
    texto = audit.auditar()
    assert "Graham: abstenção — insumo ausente" in texto
    assert "Bazin: R$ 12.00; distância ao preço 20.0%" in texto
    assert "Score:" not in texto and "Fair Value:" not in texto
    assert "Upside:" not in texto and "Recomendação:" not in texto


def test_auditoria_prompt_atual_expoe_lentes_sem_veredito(monkeypatch, capsys):
    monkeypatch.setattr(auditoria, "_rel", {"tickers": {"TSTA3": {}}})
    analise = {
        "apresentacao_versao": "1.0",
        "lentes": {"Graham": {"valor": None, "abstencao": "sem base"}},
    }
    auditoria.auditar_prompt("TSTA3", {}, analise_dict=analise)
    prompt = auditoria._rel["tickers"]["TSTA3"]["prompt"]["prompt_completo"]
    assert "distância ao preço" in prompt
    assert "Veredito final" not in prompt
    assert "sem base" in prompt
