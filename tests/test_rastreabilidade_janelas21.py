"""Janelas aprovadas: rastreabilidade do aviso, cobertura, fontes e unidades."""

from datetime import date

import pytest
from test_cascata_janelas21 import AS_OF, _dados, _ipca

from sentinela.reports import rastreabilidade
from valuation_engine import ValuationEngine


def _contexto(dados):
    motor = ValuationEngine()
    processar = motor.processar
    motor.processar = lambda entrada: processar(entrada, as_of=AS_OF)
    return rastreabilidade.construir_contexto(
        dados, False, date(2026, 10, 20), motor, None
    )


def test_aviso_reorganizacao_e_fontes_documentais_em_cada_lente_e_html():
    dados = _dados()
    dados["ipca_serie"] = _ipca()
    contexto = _contexto(dados)
    metodos = {m["nome"]: m for m in contexto["metodos"]}
    for nome, regime in (("Graham", "nominal na moeda final"), ("Lynch", "nominal")):
        bloco = metodos[nome]
        janela = bloco["janela"]
        assert janela["avisos"] == [
            "reorganização societária no período não é detectada"
        ]
        assert janela["inicio"] == "2021-01-01"
        assert janela["fim"] == "2025-12-31"
        assert janela["regime"] == regime
        assert janela["exercicios"] == list(range(2021, 2026))
        assert janela["fontes_documentais"] == [
            e["proveniencia"] for e in dados["serie_cvm"]["exercicios"]
        ]
        assert janela["fonte_eventos"] == "Composição do Capital de cada documento"
        assert janela["cobertura"] == {"esperados": 5, "disponiveis": 5}
        assert (
            janela["fontes_exigidas"]
            == "CVM por documento; fatores oficiais; IPCA IBGE no Graham"
        )
        assert bloco["abstencao"] is None
    assert metodos["Graham"]["janela"]["fonte_ipca"] == "IBGE sintético"
    assert "fonte_ipca" not in metodos["Lynch"]["janela"]
    html = rastreabilidade.renderizar(contexto)
    assert html.count("reorganização societária no período não é detectada") >= 2
    assert "Janela, fonte e cobertura" in html
    assert "2021-01-01" in html and "2025-12-31" in html
    assert "IBGE sintético" in html


def test_indisponibilidade_ipca_fica_no_graham_e_nominal_lynch_preservado():
    dados = _dados()
    dados["ipca_serie"] = {"abstencao": "IPCA não publicado no calendário"}
    contexto = _contexto(dados)
    metodos = {m["nome"]: m for m in contexto["metodos"]}
    assert metodos["Graham"]["abstencao"] == "IPCA não publicado no calendário"
    assert (
        metodos["Graham"]["janela"]["abstencao"] == "IPCA não publicado no calendário"
    )
    assert metodos["Graham"]["janela"]["cobertura"] == {
        "esperados": 5,
        "disponiveis": 5,
    }
    assert metodos["Lynch"]["abstencao"] is None
    assert metodos["Lynch"]["valor"] == "R$ 41,47"
    assert metodos["Lynch"]["janela"]["crescimento_lpa"] == pytest.approx(0.2)


def test_insumos_derivados_mantem_unidades_monetarias_razoes_e_perfil_textual():
    dados = _dados()
    dados["ipca_serie"] = _ipca()
    contexto = _contexto(dados)
    insumos = {i["campo"]: i for i in contexto["insumos"]}
    assert insumos["dy (normalizado)"]["unidade"] == "razão"
    assert insumos["dy (normalizado)"]["valor"] == "0,0200"
    assert insumos["lpa"]["unidade"] == "BRL"
    assert insumos["vpa"]["unidade"] == "BRL"
    assert insumos["perfil"]["unidade"] == "texto"
    assert insumos["perfil"]["valor"] == "CRESCIMENTO"
    assert insumos["perfil"]["proveniencia"] == "derivado no motor: ROE e DY"
