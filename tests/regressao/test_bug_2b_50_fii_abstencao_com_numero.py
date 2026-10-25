"""BUG-2B-50: a abstenção do FII devolve `fair_value = preço` e `upside = 0`.

Auditoria de fechamento da 2B (Codex, 25/10/2026): sem a lente (fora do escopo, sem Informe
elegível, sem taxa) ou sem DY confiável, o motor de FII devolvia o preço como valor e upside
zero, números que parecem resultado. Sem valor e sem upside numéricos, com o motivo; o score
contextual fica 50, neutro (marcador, seção de 25/10/2026, item 3).
"""

from datetime import date
from unittest.mock import patch

import pytest
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

from fii_engine import FIIEngine

BASE = {"ticker": "TSTF11", "preco_atual": 100.0, "dy": 0.12, "pvp": 1.0}


def _analisar(dados):
    with patch("fii_engine.get_selic_atual", return_value=0.145):
        return FIIEngine().analisar(dados, as_of=AS_OF_GORDON)


def _papel():
    dados = enriquecer_fii(dict(BASE))
    dados["informe_fii"]["composicoes"][0].update(CRI="9000")
    return dados


@pytest.mark.parametrize(
    "dados",
    [_papel(), {**BASE, "dy": 0.40}, {**BASE, "dy": 0.0}],
    ids=["lente-abstida", "dy-invalido", "dy-zero"],
)
def test_abstencao_do_fii_sem_valor_nem_upside(dados):
    r = _analisar(dados)
    assert not {"fair_value", "upside"} & set(r), r
    assert r["score_final"] == 50 and r["recomendacao"] == "NEUTRO"
    assert r["metodos_usados"].startswith("Dados insuficientes (")


def test_relatorio_nao_diz_que_o_valor_e_o_preco():
    from sentinela.reports import rastreabilidade
    from valuation_engine import ValuationEngine

    motor = FIIEngine()
    original = motor.analisar
    motor.analisar = lambda d: original(d, as_of=AS_OF_GORDON)
    dados = {**_papel(), "fonte_preco": "yfinance", "classe_ativo": "FII"}
    with patch("fii_engine.get_selic_atual", return_value=0.145):
        contexto = rastreabilidade.construir_contexto(
            dados, True, date(2026, 10, 20), ValuationEngine(), motor
        )
    sintese = dict(contexto["sintese"])
    assert "Nenhum método calculou: o valor é o próprio preço" not in sintese
    assert sintese["Abstenção da lente"] == (
        "Dados insuficientes (Rendimento do FII: tipo de FII fora do escopo na 2B: papel)"
    )
