"""Ficha Gordon1.0: referência independente, domínios e regime real."""

from dataclasses import replace
from datetime import date

import pytest

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil, Regime
from sentinela.domain.units import (
    BRL,
    Inflacao,
    ProventosControladores,
    RateReal,
    Ratio,
)
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.gordon import MOTIVO_K_NAO_MAIOR_QUE_G, Gordon, GordonParams

# F2B-4: escopo de companhia (STOCK, modelo empresa pelo BPP consolidado).
ESCOPO = {"classe_ativo": AssetType.STOCK, "modelo": ModeloDemonstracao.EMPRESA}

PARAMS = GordonParams()


# F2B-1: ficha Gordon1.0, valores independentes da fórmula antiga.
def _inputs_ficha(**kw):
    base = {
        "as_of": date(2026, 10, 20),
        "preco": BRL(15.36),
        "lpa": BRL(0.9926913764),
        "roe": Ratio(15503400 / 98642139),
        "dy": Ratio(0.06),
        "custo_capital_real": RateReal(74.38 / 1100 + 0.05),
        "inflacao": Inflacao(0.0426),
        "teto_pib_real": RateReal(0.02),
        "proventos_controladores": ProventosControladores(
            BRL(10903280 / 15616526),
            Ratio(10903280 / 15503400),
            date(2025, 1, 1),
            date(2025, 12, 31),
        ),
    }
    base.update(kw)
    return MethodInputs(**(ESCOPO | base))


def test_k_e_o_custo_de_capital_real():
    r = Gordon().calcular(_inputs_ficha(), PARAMS)
    assert r.obter("k") == RateReal(74.38 / 1100 + 0.05)


def test_g_nominal_vira_real_por_fisher():
    r = Gordon().calcular(_inputs_ficha(), PARAMS)
    assert r.obter("g").valor == pytest.approx(0.00386958636840, abs=1e-12)


def test_sem_taxa_real_abstem():
    r = Gordon().calcular(_inputs_ficha(custo_capital_real=None), PARAMS)
    assert isinstance(r, Abstention)
    assert "custo_capital_real" in r.motivo


def test_exemplo_da_ficha():
    r = Gordon().calcular(_inputs_ficha(), PARAMS)
    assert isinstance(r, MethodResult)
    assert r.valor.valor == pytest.approx(6.161748819933, abs=1e-10)


def test_real_e_nominal_dao_o_mesmo_valor():
    i = _inputs_ficha()
    r = Gordon().calcular(i, PARAMS)
    g = (1 + (15503400 / 98642139) * (1 - 10903280 / 15503400)) / 1.0426 - 1
    d1n = (10903280 / 15616526) * (1 + g) * 1.0426
    kn = (1 + 74.38 / 1100 + 0.05) * 1.0426 - 1
    gn = (1 + g) * 1.0426 - 1
    assert r.valor.valor == pytest.approx(d1n / (kn - gn), abs=1e-10)


@pytest.mark.parametrize("lpa", [0.0, -2.0])
def test_lpa_nao_positivo_abstem(lpa):
    r = Gordon().calcular(_inputs_ficha(lpa=BRL(lpa)), PARAMS)
    assert isinstance(r, Abstention)
    assert r.motivo == "LPA não positivo"
    assert (r.metodo, r.versao) == ("Gordon", "2.1.0")


def test_premissas_exigem_lpa_positivo_sem_fallback():
    assert not any("50%" in a for a in Gordon.assumptions)
    assert any("LPA positivo" in a for a in Gordon.assumptions)


@pytest.mark.parametrize("payout", [0, -0.1, 1.01])
def test_payout_fora_do_dominio_abstem_sem_truncar(payout):
    i = _inputs_ficha()
    p = replace(i.proventos_controladores, payout=Ratio(payout))
    r = Gordon().calcular(replace(i, proventos_controladores=p), PARAMS)
    assert isinstance(r, Abstention) and r.motivo == "payout fora de (0,1]"


def test_payout_um_e_valido():
    i = _inputs_ficha()
    p = replace(i.proventos_controladores, payout=Ratio(1))
    r = Gordon().calcular(replace(i, proventos_controladores=p), PARAMS)
    assert isinstance(r, MethodResult)
    assert r.obter("payout") == Ratio(1)


@pytest.mark.parametrize("roe", [0.01, 0.1, 0.15])
def test_roe_positivo_sem_minimo_de_dez_por_cento(roe):
    assert isinstance(
        Gordon().calcular(_inputs_ficha(roe=Ratio(roe)), PARAMS), MethodResult
    )


@pytest.mark.parametrize("roe", [0, -0.1])
def test_roe_nao_positivo_abstem(roe):
    assert (
        Gordon().calcular(_inputs_ficha(roe=Ratio(roe)), PARAMS).motivo
        == "ROE não positivo"
    )


@pytest.mark.parametrize("dy", [None, Ratio(0.001), Ratio(0)])
def test_dy_nao_cria_d0_nem_veta_o_metodo(dy):
    assert Gordon().calcular(
        _inputs_ficha(dy=dy, dy_confiavel=False), PARAMS
    ).valor.valor == pytest.approx(6.161748819933, abs=1e-10)


def test_fisher_antes_do_teto():
    r = Gordon().calcular(_inputs_ficha(roe=Ratio(0.5), inflacao=Inflacao(0.1)), PARAMS)
    assert r.obter("g") == RateReal(0.02)
    assert r.obter("g_real_bruto").valor > 0.02


@pytest.mark.parametrize("k", [0.02, 0.019, -0.1])
def test_k_igual_ou_menor_que_g_abstem_se(k):
    r = Gordon().calcular(
        _inputs_ficha(roe=Ratio(0.9), custo_capital_real=RateReal(k)), PARAMS
    )
    assert r.motivo == MOTIVO_K_NAO_MAIOR_QUE_G


@pytest.mark.parametrize("campo", Gordon.requires)
def test_insumo_ausente_abstem_se(campo):
    r = Gordon().calcular(_inputs_ficha(**{campo: None}), PARAMS)
    assert isinstance(r, Abstention)
    assert r.motivo == f"insumo ausente: {campo}"


@pytest.mark.parametrize("campo", ["preco", "lpa"])
def test_preco_lpa_nao_positivos(campo):
    assert isinstance(
        Gordon().calcular(_inputs_ficha(**{campo: BRL(0)}), PARAMS), Abstention
    )


@pytest.mark.parametrize("fim", [date(2026, 12, 31), date(2024, 12, 31)])
def test_janela_futura_ou_antiga_abstem(fim):
    i = _inputs_ficha()
    p = replace(i.proventos_controladores, inicio=date(fim.year, 1, 1), fim=fim)
    assert isinstance(
        Gordon().calcular(replace(i, proventos_controladores=p), PARAMS), Abstention
    )


def test_janela_itr_nao_substitui_dfp():
    i = _inputs_ficha()
    p = replace(i.proventos_controladores, fim=date(2025, 9, 30))
    assert (
        "anual"
        in Gordon().calcular(replace(i, proventos_controladores=p), PARAMS).motivo
    )


def test_resultado_que_estoura_para_infinito_abstem_se():
    i = _inputs_ficha()
    p = replace(i.proventos_controladores, dividendo_anual=BRL(1e308))
    r = Gordon().calcular(replace(i, proventos_controladores=p), PARAMS)
    assert isinstance(r, Abstention) and r.motivo == "resultado não finito"


def test_vale_para_qualquer_perfil():
    assert isinstance(
        Gordon().calcular(_inputs_ficha(perfil=Perfil.CRESCIMENTO), PARAMS),
        MethodResult,
    )


def test_metadados():
    m = Gordon()
    assert m.nome == "Gordon" and m.version == "2.1.0"
    assert m.regime is Regime.REAL
    assert "selic" not in m.requires and "dy" not in m.requires
    assert m.applies_to == frozenset({AssetType.STOCK, AssetType.UNIT})
    assert m.params_type is GordonParams
    assert all(isinstance(a, str) and a for a in m.assumptions)


@pytest.mark.parametrize(
    "inicio,fim",
    [(date(2025, 1, 2), date(2025, 12, 31)), (date(2025, 1, 1), date(2025, 12, 30))],
)
def test_exercicio_exige_primeiro_e_ultimo_dia(inicio, fim):
    i = _inputs_ficha()
    p = replace(i.proventos_controladores, inicio=inicio, fim=fim)
    r = Gordon().calcular(replace(i, proventos_controladores=p), PARAMS)
    assert r.motivo == "janela da DVA incompatível: exige exercício anual completo"


@pytest.mark.parametrize(
    "dia,esperado", [(date(2027, 3, 31), True), (date(2027, 4, 1), False)]
)
def test_idade_limite_exato_de_quinze_meses(dia, esperado):
    r = Gordon().calcular(_inputs_ficha(as_of=dia), PARAMS)
    if esperado:
        assert isinstance(r, MethodResult)
    else:
        assert r.motivo == "DFP anual além do prazo de 15 meses"


def test_exercicio_nao_civil_e_bissexto():
    i = _inputs_ficha()
    p = replace(
        i.proventos_controladores, inicio=date(2023, 3, 1), fim=date(2024, 2, 29)
    )
    r = Gordon().calcular(
        replace(i, as_of=date(2025, 5, 29), proventos_controladores=p), PARAMS
    )
    assert isinstance(r, MethodResult)
    r = Gordon().calcular(
        replace(i, as_of=date(2025, 5, 30), proventos_controladores=p), PARAMS
    )
    assert r.motivo == "DFP anual além do prazo de 15 meses"


@pytest.mark.parametrize("campo", ["custo_capital_real", "teto_pib_real"])
@pytest.mark.parametrize("valor", [-1, -1.01])
def test_fator_real_exige_positivo(campo, valor):
    r = Gordon().calcular(_inputs_ficha(**{campo: RateReal(valor)}), PARAMS)
    assert r.motivo == "taxa real sem fator positivo"


@pytest.mark.parametrize("d0", [0, -1])
def test_distribuicao_nao_positiva_abstem(d0):
    i = _inputs_ficha()
    p = replace(i.proventos_controladores, dividendo_anual=BRL(d0))
    r = Gordon().calcular(replace(i, proventos_controladores=p), PARAMS)
    assert r.motivo == "distribuição não positiva"


def test_intermediarios_do_exemplo_na_unidade_correta():
    i = _inputs_ficha()
    r = Gordon().calcular(i, PARAMS)
    assert r.obter("d0") == i.proventos_controladores.dividendo_anual
    assert r.obter("roe_nominal") == i.roe
    assert r.obter("g_nominal_bruto").valor == pytest.approx(0.04663443074769496)
    assert r.obter("g_real_bruto").valor == pytest.approx(0.0038695863684)
    assert r.obter("teto_pib_real") == RateReal(0.02)
    assert r.obter("dividendo_proximo").valor == pytest.approx(0.7008902737816887)
