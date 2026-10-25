"""BUG-2B-46: a lente de FII não confere o corte temporal da taxa nem das coletas.

Auditoria de fechamento da 2B (Codex, 25/10/2026): a lente usa a NTN-B do registro da taxa
real sem conferir o as_of, a data-base e a idade do registro, e aceita o Informe e a resposta
da B3 coletados depois do as_of. Mesmo corte do F2B-30 e do Gordon; sem prova, abstém.
"""

from unittest.mock import patch

import pytest
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

from fii_engine import FIIEngine

BASE = {"ticker": "TSTF11", "preco_atual": 100.0, "dy": 0.12, "pvp": 1.0}
TAXA = {
    "ntnb": 0.07,
    "custo_capital_real": 0.12,
    "premio": 0.05,
    "data_base": "2026-10-16",
    "dias_uteis": 2,
    "as_of": "2026-10-20T12:00:00+00:00",
}


def _rendimento(**mudancas):
    dados = enriquecer_fii({**BASE, "taxa_real": {**TAXA, **mudancas.pop("taxa", {})}})
    dados["informe_fii"]["proveniencia"] = {
        "fonte": "Informe sintético",
        "data_coleta": mudancas.pop("coleta_informe", "2026-10-20T12:00:00+00:00"),
    }
    dados["b3_fundo"]["coleta"] = mudancas.pop("coleta_b3", "2026-10-20T12:00:00+00:00")
    with patch("fii_engine.get_selic_atual", return_value=0.145):
        FIIEngine().analisar(dados, as_of=AS_OF_GORDON)
    return dados


def test_controle_com_corte_valido_calcula():
    dados = _rendimento()
    assert "abstencao" not in dados["rendimento_fii_cvm"], dados["rendimento_fii_cvm"]


@pytest.mark.parametrize(
    ("mudancas", "motivo"),
    [
        ({"taxa": {"as_of": "2026-10-21T12:00:00+00:00"}}, "contexto da taxa real posterior ao as_of"),
        ({"taxa": {"as_of": None}}, "corte temporal da taxa real não demonstrado"),
        ({"taxa": {"as_of": "2026-10-20T12:00:00"}}, "corte temporal da taxa real não demonstrado"),
        ({"taxa": {"data_base": "2026-10-20"}}, "corte temporal da taxa real não demonstrado: data-base não anterior ao as_of"),
        ({"taxa": {"data_base": "x"}}, "corte temporal da taxa real não demonstrado: data-base ilegível"),
        ({"taxa": {"dias_uteis": 6}}, "corte temporal da taxa real não demonstrado: idade da NTN-B"),
        ({"taxa": {"dias_uteis": None}}, "corte temporal da taxa real não demonstrado: idade da NTN-B"),
        ({"taxa": {"dias_uteis": True}}, "corte temporal da taxa real não demonstrado: idade da NTN-B"),
        ({"taxa": {"dias_uteis": -1}}, "corte temporal da taxa real não demonstrado: idade da NTN-B"),
        ({"taxa": {"as_of": "2026-10-19T12:00:00+00:00"}}, "corte temporal da taxa real não demonstrado: registro de outro dia"),
        ({"taxa": {"ntnb": float("nan")}}, "NTN-B real inválida no registro da taxa"),
        ({"coleta_informe": "2026-10-21T00:00:00+00:00"}, "coleta do Informe não demonstrada até o as_of"),
        ({"coleta_informe": None}, "coleta do Informe não demonstrada até o as_of"),
        ({"coleta_b3": "2026-10-21T00:00:00+00:00"}, "coleta da B3 não demonstrada até o as_of"),
        ({"coleta_b3": None}, "coleta da B3 não demonstrada até o as_of"),
    ],
)  # fmt: skip
def test_corte_temporal_nao_demonstrado_abstem(mudancas, motivo):
    dados = _rendimento(**mudancas)
    assert dados["rendimento_fii_cvm"] == {"abstencao": motivo}


def test_escopo_vem_antes_da_taxa():
    # Revisão do F2B-58: o FII de papel sem taxa mostra o motivo de escopo, não o da taxa.
    dados = enriquecer_fii(dict(BASE))
    dados.pop("taxa_real")
    dados["informe_fii"]["composicoes"][0].update(CRI="9000")
    dados["informe_fii"]["proveniencia"]["data_coleta"] = "2026-10-20T12:00:00+00:00"
    with patch("fii_engine.get_selic_atual", return_value=0.145):
        FIIEngine().analisar(dados, as_of=AS_OF_GORDON)
    assert dados["rendimento_fii_cvm"] == {
        "abstencao": "tipo de FII fora do escopo na 2B: papel"
    }
