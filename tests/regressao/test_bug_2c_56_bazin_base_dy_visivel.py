"""BUG-2C-56: o critério Bazin precisa identificar o DY e seu preço de referência."""

import pytest
from apoio_escopo import de_empresa

from sentinela.reports.rastreabilidade import renderizar
from tests.test_app_lentes import _helpers
from tests.test_financeiro_pre_refactor import _acao, _processar
from tests.test_rastreabilidade import _contexto


def dados():
    d = _acao(dy=0.056)
    d["proventos_b3"]["fechamentos"] = {
        data: 80.0 for data in d["proventos_b3"]["fechamentos"]
    }
    return de_empresa(d)


def test_ui_explica_dy_b3_e_seu_preco_sem_mudar_distancia():
    r = _processar(dados())
    b = r["lentes"]["Bazin"]
    assert b["dy_bruto_12m"] == pytest.approx(0.07)
    assert b["preco_do_dy"] == 80 and b["preco"] == 100
    assert b["valor"] == pytest.approx(5.6 / 0.06)
    linha = next(l for l in _helpers()["_linhas_lentes"](r) if l["Lente"] == "Bazin")
    assert linha["DY bruto B3 (%)"] == "7.00%"
    assert linha["Preço-base do DY"] == "R$ 80.00"
    assert linha["Data-base do DY"] == "2026-10-19"
    assert linha["Critério Bazin"] == "atinge 6%"
    assert linha["Distância ao preço (%)"] == "-6.67%"


def test_relatorio_explica_dy_b3_e_referencia_distinta():
    html = renderizar(_contexto(dados()))
    assert "DY bruto B3: 7,00%" in html
    assert "preço-base do DY: R$ 80,00" in html
    assert "data-base do DY: 2026-10-19" in html
