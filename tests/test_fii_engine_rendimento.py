"""Motor de FII com a lente de rendimento sobre NTN-B + spread (F2B-2; ficha FII 1.1)."""

from unittest.mock import patch

import pytest
from apoio_apresentacao import verificar_lentes
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

import fii_engine
from config import MACRO
from fii_engine import FIIEngine

SPREAD = 0.02


def _fii(dados, selic=0.10, spread=SPREAD):
    with (
        patch.object(fii_engine, "get_selic_atual", return_value=selic),
        patch.object(MACRO, "FII_SPREAD_TIJOLO", spread, create=True),
    ):
        return FIIEngine().analisar(dados, as_of=AS_OF_GORDON)


def _base(**kw):
    dados = {"ticker": "TSTI11", "preco_atual": 100.0, "dy": 0.09, "pvp": 1.0}
    dados.update(kw)
    return dados


def test_fii_tijolo_pela_ntnb_mais_spread():
    dados = enriquecer_fii(_base(), ntnb=0.07)
    r = _fii(dados)
    assert r["fair_value"] == pytest.approx(round(9.0 / 0.09, 2))
    assert r["metodos_usados"] == "Rendimento do FII: R$100.00"
    assert dados["rendimento_fii_cvm"]["dy"] == pytest.approx(0.09)
    assert dados["rendimento_fii_cvm"]["tipo"] == "tijolo"


def test_selic_fica_no_score_e_nao_no_preco_justo():
    dados = enriquecer_fii(_base(dy=0.09), ntnb=0.06)
    baixa = _fii(dict(dados), selic=0.05)
    alta = _fii(dict(dados), selic=0.20)
    assert baixa["fair_value"] == alta["fair_value"] == pytest.approx(112.5)
    # score inalterado na 2B (decisão de 19/10/2026): DY contra a Selic líquida
    verificar_lentes(baixa)
    verificar_lentes(alta)
    assert baixa["lentes"] == alta["lentes"]
    assert alta["selic_liquida"] == pytest.approx(0.20 * MACRO.FII_FATOR_IR)


@pytest.mark.parametrize(
    ("ajuste", "motivo"),
    [
        # F2B-58: a taxa é conferida nas entradas, com os motivos do Gordon.
        (lambda d: d.update(taxa_real={"abstencao": "x"}), "taxa real indisponível: x"),
        (lambda d: d.pop("taxa_real"), "insumo ausente: taxa real"),
        (lambda d: d.pop("informe_fii"), "insumo ausente: Informe Mensal do FII"),
        (
            lambda d: d["informe_fii"]["composicoes"][0].update(CRI="9000"),
            "tipo de FII fora do escopo na 2B: papel",
        ),
        (
            lambda d: d.update(b3_fundo={"abstencao": "sem rede"}),
            "fonte de eventos de cota indisponível: continuidade não demonstrável",
        ),
    ],
)
def test_abstencoes_da_lente(ajuste, motivo):
    dados = enriquecer_fii(_base())
    ajuste(dados)
    r = _fii(dados)
    # F2B-62 (BUG-2B-50): sem valor nem upside numéricos; score contextual 50, neutro.
    assert not {"fair_value", "upside"} & set(r)
    verificar_lentes(r)
    verificar_lentes(r)
    assert r["metodos_usados"] == f"Dados insuficientes (Rendimento do FII: {motivo})"


def test_sem_spread_abstem():
    r = _fii(enriquecer_fii(_base()), spread=None)
    assert (
        r["metodos_usados"]
        == "Dados insuficientes (Rendimento do FII: spread indisponível)"
    )


def test_avisos_da_conferencia_saem_com_o_resultado():
    r = _fii(enriquecer_fii(_base()))
    assert r["avisos_rendimento"][0].startswith(
        "rendimento sem valor da B3 para conferir"
    )
