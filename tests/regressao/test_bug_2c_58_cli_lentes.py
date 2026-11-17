"""Ficha apresentação1.0: leitor não fabrica síntese ausente nem orientação."""

import ast
import math
import numbers
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

import auditar_recomendacoes as audit
import auditoria

APP = Path(__file__).resolve().parents[2] / "app.py"
LEGADO = ("score", "fair value", "fair_value", "upside", "recomenda", "valor justo")


def _linhas_lentes():
    """O apresentador real das lentes do app, lido do código-fonte (o app desenha no import)."""
    arvore = ast.parse(APP.read_text(encoding="utf-8"))
    nomes = {"_texto_lente", "_linhas_lentes"}
    nos = [n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name in nomes]
    assert len(nos) == 2
    escopo = {"math": math, "numbers": numbers}
    exec(compile(ast.Module(body=nos, type_ignores=[]), str(APP), "exec"), escopo)  # noqa: S102 -- código do próprio repositório
    return escopo["_linhas_lentes"]


def test_app_mostra_lente_abstida_sem_score_ou_valor_zero():
    # Adaptado do teste da linha de comando (F3-9c-aud): a mesma invariante no apresentador
    # das lentes do app, com campos legados no payload para provar que não vazam.
    linhas = _linhas_lentes()(
        {
            "score_final": 80,
            "fair_value": 0,
            "upside": 25.0,
            "recomendacao": "COMPRA",
            "lentes": {
                "Graham": {
                    "valor": None,
                    "abstencao": "insumo ausente",
                    "distancia_ao_preco_pct": None,
                    "score": 0,
                    "fair_value": 0,
                    "upside": 0,
                    "recomendacao": "VENDA",
                },
                "Bazin": {"valor": 12, "abstencao": None, "distancia_ao_preco_pct": 20},
            },
        }
    )
    graham, bazin = linhas
    assert (graham["Lente"], graham["Valor"], graham["Motivo"]) == (
        "Graham",
        "—",
        "insumo ausente",
    )
    assert graham["Distância ao preço (%)"] == "—"
    assert (bazin["Valor"], bazin["Motivo"], bazin["Distância ao preço (%)"]) == (
        "R$ 12.00",
        "",
        "20.00%",
    )
    for linha in linhas:
        for chave, valor in linha.items():
            texto = f"{chave} {valor}".lower()
            assert not any(termo in texto for termo in LEGADO), (chave, valor)


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
