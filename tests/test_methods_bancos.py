"""Lente bancária: esperado independente da ficha bancos 1.1, sem rede."""

from dataclasses import replace
from datetime import date

import pytest

from sentinela.domain.enums import AssetType
from sentinela.domain.units import (
    BRL,
    Inflacao,
    ProventosControladores,
    RateReal,
    Ratio,
)
from sentinela.methods.base import Abstention, MethodInputs, MethodResult


def _inputs(**extra):
    from sentinela.domain.enums import DocumentoContabil, ModeloDemonstracao

    campos = dict(
        as_of=date(2026, 10, 19),
        classe_ativo=AssetType.STOCK,
        modelo=ModeloDemonstracao.BANCO,
        documento_contabil=DocumentoContabil.DFP,
        base_acionaria_compativel=True,
        lucro_anual_controladores=BRL(44857000000),
        pl_inicial_controladores=BRL(211090000000),
        vpa=BRL(204501000 / 11026524),
        custo_capital_real=RateReal(74.38 / 1100 + 0.05),
        inflacao=Inflacao(0.0426),
        teto_pib_real=RateReal(0.02),
        proventos_controladores=ProventosControladores(
            BRL(33704000 / 11026524),
            Ratio(33704000 / 44857000),
            date(2025, 1, 1),
            date(2025, 12, 31),
        ),
    )
    return MethodInputs(**(campos | extra))


def _calcular(**extra):
    from sentinela.methods.bancos import Bancos, BancosParams

    return Bancos().calcular(_inputs(**extra), BancosParams())


def test_pvp_justificado():
    r = _calcular()
    assert isinstance(r, MethodResult)
    assert r.obter("pvp_justificado").valor == pytest.approx(1.420603401260, abs=1e-12)


def test_exemplo_da_ficha():
    r = _calcular(preco=BRL(44.28))
    assert r.valor.valor == pytest.approx(26.346908251509, abs=1e-12)
    assert r.obter("pvp_mercado").valor == pytest.approx(2.387540807722, abs=1e-12)
    assert r.obter("roe_nominal").valor == pytest.approx(0.212501776493439)
    assert "evento posterior ao último documento entregue não é detectado" in r.alertas


def test_real_e_nominal_dao_o_mesmo_pvp():
    r = _calcular()
    # Mesmos fluxos e múltiplo, sob Fisher exato; não usa a implementação para o esperado.
    roe = 44857000 / 211090000
    g_n = (44857000 - 33704000) / 211090000
    k_n = (1 + 74.38 / 1100 + 0.05) * 1.0426 - 1
    assert r.obter("pvp_justificado").valor == pytest.approx((roe - g_n) / (k_n - g_n))
    assert r.valor.valor == pytest.approx(
        r.obter("d1_real").valor / (r.obter("k_real").valor - r.obter("g_real").valor)
    )


def test_roe_nao_maior_que_g_abstem():
    f = _inputs().proventos_controladores
    r = _calcular(
        proventos_controladores=replace(f, payout=Ratio(1e-30)),
        teto_pib_real=RateReal(1),
    )
    assert isinstance(r, Abstention)

    assert "g >= ROE" in r.motivo


def test_k_nao_maior_que_g_abstem():
    r = _calcular(custo_capital_real=RateReal(-0.03))
    assert isinstance(r, Abstention)
    assert "k" in r.motivo


@pytest.mark.parametrize("vpa", [0, -1])
def test_vpa_nao_positivo_abstem(vpa):
    assert isinstance(_calcular(vpa=BRL(vpa)), Abstention)


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("lucro_anual_controladores", 0),
        ("lucro_anual_controladores", -1),
        ("pl_inicial_controladores", 0),
        ("pl_inicial_controladores", -1),
    ],
)
def test_dominios_contabeis(campo, valor):
    assert isinstance(_calcular(**{campo: BRL(valor)}), Abstention)


@pytest.mark.parametrize("payout", [0, -0.1, 1.0001])
def test_payout_invalido_abstem(payout):
    f = _inputs().proventos_controladores
    r = _calcular(proventos_controladores=replace(f, payout=Ratio(payout)))
    assert isinstance(r, Abstention)
    assert "payout" in r.motivo


def test_payout_ausente_abstem():
    assert isinstance(_calcular(proventos_controladores=None), Abstention)


def test_itr_nao_substitui_janela_anual():
    f = _inputs().proventos_controladores
    assert isinstance(
        _calcular(proventos_controladores=replace(f, fim=date(2025, 9, 30))), Abstention
    )


def test_teto_muda_payout_projetado_sem_mudar_o_observado():
    f = _inputs().proventos_controladores
    r = _calcular(proventos_controladores=replace(f, payout=Ratio(0.5)))
    assert isinstance(r, MethodResult)
    assert r.obter("g_real").valor == 0.02
    assert r.obter("payout_observado").valor == 0.5
    efetivo = 1 - ((1.02 * 1.0426 - 1) / (44857000 / 211090000))
    assert r.obter("payout_projetado").valor == pytest.approx(efetivo)
    assert 0.5 < efetivo <= 1
    assert r.valor.valor == pytest.approx(
        r.obter("d1_real").valor / (74.38 / 1100 + 0.05 - 0.02)
    )


@pytest.mark.parametrize(
    "classe", [AssetType.FII, AssetType.ETF, AssetType.BDR, AssetType.UNKNOWN]
)
def test_classe_fora_do_escopo(classe):
    r = _calcular(classe_ativo=classe)
    assert isinstance(r, Abstention)
    assert "classe" in r.motivo


def test_modelo_ou_base_sem_evidencia_abstem():
    from sentinela.domain.enums import ModeloDemonstracao

    assert isinstance(_calcular(modelo=ModeloDemonstracao.EMPRESA), Abstention)
    assert isinstance(_calcular(modelo=None), Abstention)
    assert isinstance(_calcular(classe_ativo=None), Abstention)
    assert isinstance(_calcular(base_acionaria_compativel=False), Abstention)
    assert isinstance(_calcular(base_acionaria_compativel=None), Abstention)


def test_preco_nao_forma_o_multiplo():
    assert _calcular().valor == _calcular(preco=BRL(-1)).valor


@pytest.mark.parametrize(
    "campo,tipo",
    [
        ("classe_ativo", "AssetType"),
        ("modelo", "ModeloDemonstracao"),
        ("documento_contabil", "DocumentoContabil"),
        ("base_acionaria_compativel", "bool"),
        ("lucro_anual_controladores", "BRL"),
        ("pl_inicial_controladores", "BRL"),
    ],
)
def test_novos_campos_sao_tipados(campo, tipo):
    with pytest.raises(TypeError, match=tipo):
        _inputs(**{campo: "inválido"})
    assert isinstance(_calcular(**{campo: None}), Abstention)


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("custo_capital_real", -1),
        ("custo_capital_real", -1.1),
        ("teto_pib_real", -1),
        ("teto_pib_real", -1.1),
    ],
)
def test_fator_real_invalido(campo, valor):
    assert isinstance(_calcular(**{campo: RateReal(valor)}), Abstention)


@pytest.mark.parametrize(
    "inicio,fim",
    [
        (date(2025, 1, 2), date(2025, 12, 31)),
        (date(2025, 1, 1), date(2025, 12, 30)),
        (date(2025, 2, 1), date(2025, 12, 31)),
    ],
)
def test_janela_completa_e_obrigatoria(inicio, fim):
    f = _inputs().proventos_controladores
    assert isinstance(
        _calcular(proventos_controladores=replace(f, inicio=inicio, fim=fim)),
        Abstention,
    )


@pytest.mark.parametrize(
    "as_of", [date(2025, 12, 31), date(2025, 12, 30), date(2027, 4, 1)]
)
def test_futura_ou_antiga_abstem(as_of):
    assert isinstance(_calcular(as_of=as_of), Abstention)


def test_ultimo_dia_antes_de_nova_dfp_exigivel():
    assert isinstance(_calcular(as_of=date(2027, 3, 31)), MethodResult)


@pytest.mark.parametrize("d0", [0, -1])
def test_distribuicao_nao_positiva(d0):
    f = _inputs().proventos_controladores
    assert isinstance(
        _calcular(proventos_controladores=replace(f, dividendo_anual=BRL(d0))),
        Abstention,
    )


def test_dominios_antes_do_teto_e_resultado_nao_finito():
    r = _calcular(
        lucro_anual_controladores=BRL(1e308), pl_inicial_controladores=BRL(1e-308)
    )
    assert isinstance(r, Abstention)
    assert "antes do teto" in r.motivo
    assert isinstance(_calcular(vpa=BRL(1.7e308)), Abstention)
    assert isinstance(
        _calcular(custo_capital_real=RateReal(1e308), inflacao=Inflacao(1)), Abstention
    )


def test_payout_projetado_nao_e_truncado():
    r = _calcular(teto_pib_real=RateReal(-0.1))
    assert isinstance(r, Abstention)
    assert "payout projetado" in r.motivo


def test_payout_total_e_deflacao_sao_admitidos():
    f = _inputs().proventos_controladores
    r = _calcular(proventos_controladores=replace(f, payout=Ratio(1)))
    assert isinstance(r, MethodResult)
    assert r.obter("payout_projetado").valor == 1
    assert isinstance(
        _calcular(inflacao=Inflacao(-0.01), teto_pib_real=RateReal(0.2)), MethodResult
    )


def test_denominador_pequeno_nao_recebe_piso():
    g = ((1 + (44857000 - 33704000) / 211090000) / 1.0426) - 1
    assert isinstance(_calcular(custo_capital_real=RateReal(g)), Abstention)
    r = _calcular(custo_capital_real=RateReal(g + 1e-10))
    assert isinstance(r, MethodResult)
    assert r.valor.valor > 1e9


def test_comparacao_de_mercado_nao_finita_nao_bloqueia_a_lente():
    r = _calcular(preco=BRL(1e308), vpa=BRL(1e-308))
    assert isinstance(r, MethodResult)
    assert "P/VP de mercado não informado: resultado não finito" in r.alertas


def test_intermediarios_da_identidade_contabil_e_fluxos():
    r = _calcular()
    esperado = {
        "roe_nominal": 44857000 / 211090000,
        "roe_real": (1 + 44857000 / 211090000) / 1.0426 - 1,
        "g_nominal_bruto": (44857000 - 33704000) / 211090000,
        "g_nominal_efetivo": (44857000 - 33704000) / 211090000,
        "g_real_bruto": 0.00981707608704473,
        "g_real": 0.00981707608704473,
        "payout_observado": 33704000 / 44857000,
        "payout_projetado": 33704000 / 44857000,
        "k_real": 74.38 / 1100 + 0.05,
        "k_nominal": 0.16522871636363636,
        "vpa": 204501000 / 11026524,
        "d1_nominal": (33704000 / 211090000) * (204501000 / 11026524),
        "d1_real": (33704000 / 211090000) * (204501000 / 11026524) / 1.0426,
    }
    for nome, valor in esperado.items():
        assert r.obter(nome).valor == pytest.approx(valor, rel=1e-12, abs=1e-14)
    assert _calcular(roe=Ratio(0.99)).valor == r.valor
    assert _calcular(classe_ativo=AssetType.UNIT).valor == r.valor


def test_vpa_da_unit_mantem_o_mesmo_multiplo():
    comum = _calcular()
    unit = _calcular(classe_ativo=AssetType.UNIT, vpa=BRL(3 * 204501000 / 11026524))
    assert unit.obter("pvp_justificado") == comum.obter("pvp_justificado")
    assert unit.valor.valor == pytest.approx(3 * comum.valor.valor)


def test_itr_mesmo_com_janela_anual_nao_substitui_dfp():
    from sentinela.domain.enums import DocumentoContabil

    r = _calcular(documento_contabil=DocumentoContabil.ITR)
    assert isinstance(r, Abstention)
    assert "DFP" in r.motivo
