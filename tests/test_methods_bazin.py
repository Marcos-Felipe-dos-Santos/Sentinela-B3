from datetime import date

import pytest

from sentinela.data import proventos_b3
from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil, Regime
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.bazin import (
    ALERTA_DY_ARMADILHA,
    AVISO_PREJUIZO,
    MOTIVO_DY_ABAIXO_DO_MINIMO,
    MOTIVO_DY_NAO_CONFIAVEL,
    MOTIVO_PERFIL_CRESCIMENTO,
    Bazin,
    BazinParams,
)

# F2B-4: escopo de companhia (STOCK, modelo empresa pelo BPP consolidado).
ESCOPO = {"classe_ativo": AssetType.STOCK, "modelo": ModeloDemonstracao.EMPRESA}

PARAMS = BazinParams(dy_min=0.05, dy_armadilha=0.15)


def _inputs(preco=100.0, dy=0.08, selic=0.145, perfil=Perfil.RENDA, **kw):
    return MethodInputs(
        **ESCOPO,
        as_of=date(2026, 10, 2),
        preco=BRL(preco),
        dy=Ratio(dy),
        selic=RateNominal(selic),
        perfil=perfil,
        **kw,
    )


def _bazin(**kw):
    return Bazin().calcular(_inputs(**kw), PARAMS)


@pytest.mark.parametrize("selic", [-0.02, 0.02, 0.03, 0.05, 0.0501, 0.10, 0.1475, 0.25])
def test_taxa_do_bazin_nao_e_a_selic(selic):
    # Ficha Bazin 1.0: critério de rendimento mínimo de 6% fixos, em qualquer Selic.
    r = Bazin().calcular(_inputs(preco=100.0, dy=0.08, selic=selic), PARAMS)
    assert r.obter("taxa_aplicada") == RateNominal(0.06)
    assert r.valor.valor == pytest.approx(0.08 * 100.0 / 0.06, abs=1e-9)


def test_formula_dy_vezes_preco_sobre_6_por_cento():
    r = _bazin(preco=100.0, dy=0.08, selic=0.145)
    assert isinstance(r, MethodResult)
    assert r.valor == BRL((0.08 * 100.0) / 0.06)
    assert r.obter("taxa_aplicada") == RateNominal(0.06)
    assert r.obter("relacao_ao_criterio") == Ratio(0.08 / 0.06 - 1)
    assert (r.metodo, r.versao) == ("Bazin", Bazin.version)
    assert r.alertas == ()


def test_mesma_ordem_de_operacoes():
    dy, p = 0.0713, 37.19
    assert _bazin(preco=p, dy=dy, selic=0.1375).valor.valor == (dy * p) / 0.06


def test_sem_selic_calcula():
    r = Bazin().calcular(
        MethodInputs(
            **ESCOPO,
            as_of=date(2026, 10, 2),
            preco=BRL(100.0),
            dy=Ratio(0.08),
            perfil=Perfil.RENDA,
        ),
        PARAMS,
    )
    assert r.valor.valor == pytest.approx(0.08 * 100.0 / 0.06, abs=1e-9)


@pytest.mark.parametrize("dy", [0.0499, 0.05, 0.0599, 0.06, 0.1501, 0.25])
def test_gate_de_5_por_cento_continua(dy):
    # Gate de 5%, critério de 6%, alerta acima de 15%: limites distintos (ficha, §4). Entre
    # 5% e 6% o método calcula, abaixo do critério (relação negativa).
    r = _bazin(dy=dy)
    if dy < 0.05:
        assert r.motivo == MOTIVO_DY_ABAIXO_DO_MINIMO
        return
    assert r.valor.valor == pytest.approx(dy * 100.0 / 0.06, abs=1e-9)
    assert (r.obter("relacao_ao_criterio").valor < 0) is (dy < 0.06)
    assert (ALERTA_DY_ARMADILHA in r.alertas) is (dy > 0.15)


@pytest.mark.parametrize(("lpa", "aviso"), [(-0.01, True), (0.0, False), (None, False)])
def test_prejuizo_e_elegivel_com_aviso(lpa, aviso):
    r = _bazin(**({} if lpa is None else {"lpa": BRL(lpa)}))
    assert isinstance(r, MethodResult)
    assert (AVISO_PREJUIZO in r.alertas) is aviso


def test_armadilha_e_prejuizo_juntos():
    r = _bazin(dy=0.20, lpa=BRL(-1.0))
    assert r.alertas == (ALERTA_DY_ARMADILHA, AVISO_PREJUIZO)


def test_exemplo_da_ficha():
    # Ficha Bazin 1.0, §5: caso de contrato independente, sintético, classe única, cobertura
    # completa. Dividendo 0,40 (data ex 10/12/2025) e JCP bruto 0,20 (data ex 10/06/2026);
    # preço 10,00 em 30/09/2026: D = 0,60, DY = 6%, critério = 10,00. O evento com data ex
    # em 30/09/2025 fica fora, e o de 01/10/2026 não entra. A B3 informa a data com (o
    # pregão anterior à data ex).
    def evento(natureza, valor, data_com):
        return {
            "typeStock": "ON",
            "corporateAction": natureza,
            "valueCash": valor,
            "lastDatePriorEx": data_com,
            "dateApproval": "01/09/2025",
            "quotedPerShares": "1",
        }

    registros = [
        evento("DIVIDENDO", "0,40", "09/12/2025"),
        evento("JRS CAP PROPRIO", "0,20", "09/06/2026"),
        evento("DIVIDENDO", "5,00", "29/09/2025"),
        evento("DIVIDENDO", "7,00", "30/09/2026"),
    ]
    pregoes = [date(2025, 9, d) for d in (26, 29, 30)] + [date(2025, 10, 1)]
    serie = proventos_b3.serie_12_meses(
        registros,
        total=4,
        referencia=date(2026, 9, 30),
        dia_as_of=date(2026, 10, 19),
        especie="ON",
        pregoes=pregoes,
    )
    assert serie["d_bruto_12m"] == pytest.approx(0.60, abs=1e-12)
    assert [e["data_com"] for e in serie["eventos"]] == ["2025-12-09", "2026-06-09"]
    r = Bazin().calcular(_inputs(preco=10.0, dy=serie["d_bruto_12m"] / 10.0), PARAMS)
    assert r.valor.valor == pytest.approx(10.0, abs=1e-6)
    assert r.obter("relacao_ao_criterio").valor == pytest.approx(0.0, abs=1e-10)


def test_dy_no_minimo_calcula_e_abaixo_abstem_se():
    assert isinstance(_bazin(dy=0.05), MethodResult)
    r = _bazin(dy=0.0499)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_DY_ABAIXO_DO_MINIMO


def test_dy_zero_abstem_se():
    assert _bazin(dy=0.0).motivo == MOTIVO_DY_ABAIXO_DO_MINIMO


def test_perfil_crescimento_abstem_se():
    r = _bazin(perfil=Perfil.CRESCIMENTO)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_PERFIL_CRESCIMENTO


def test_dy_nao_confiavel_abstem_se():
    r = _bazin(dy_confiavel=False)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_DY_NAO_CONFIAVEL


def test_dy_acima_de_15_por_cento_gera_alerta_mas_calcula():
    assert _bazin(dy=0.15).alertas == ()
    r = _bazin(dy=0.1501)
    assert isinstance(r, MethodResult)
    assert r.alertas == (ALERTA_DY_ARMADILHA,)
    assert r.valor.valor == (0.1501 * 100.0) / 0.06


@pytest.mark.parametrize(
    "kw",
    [{"perfil": Perfil.CRESCIMENTO}, {"dy_confiavel": False}, {"dy": 0.01}],
)
def test_abstencao_identifica_metodo_e_versao(kw):
    r = _bazin(**kw)
    assert isinstance(r, Abstention)
    assert (r.metodo, r.versao) == ("Bazin", Bazin.version)


@pytest.mark.parametrize("campo", ["preco", "dy", "perfil"])
def test_insumo_ausente_abstem_se(campo):
    base = {
        "preco": BRL(100.0),
        "dy": Ratio(0.08),
        "selic": RateNominal(0.145),
        "perfil": Perfil.RENDA,
    }
    base[campo] = None
    r = Bazin().calcular(
        MethodInputs(**ESCOPO, as_of=date(2026, 10, 2), **base), PARAMS
    )
    assert isinstance(r, Abstention)
    assert r.motivo == f"insumo ausente: {campo}"


def test_resultado_que_estoura_para_infinito_abstem_se():
    r = _bazin(preco=1e308, dy=0.9, selic=0.05)
    assert isinstance(r, Abstention)
    assert r.motivo == "resultado não finito"
    assert (r.metodo, r.versao) == ("Bazin", Bazin.version)


def test_metadados():
    b = Bazin()
    assert b.nome == "Bazin"
    assert b.version == "2.1.0"
    assert b.regime is Regime.NOMINAL
    assert b.requires == ("preco", "dy", "perfil")
    assert b.applies_to == frozenset({AssetType.STOCK, AssetType.UNIT})
    assert b.params_type is BazinParams
    assert b.assumptions
    assert all(isinstance(a, str) and a for a in b.assumptions)


def test_dy_nao_confiavel_tem_prioridade_sobre_o_minimo():
    # Com DY não confiável, o motor zera o DY (`_normalizar_dy`): o motivo certo é a
    # confiança, não o mínimo.
    r = _bazin(dy=0.0, dy_confiavel=False)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_DY_NAO_CONFIAVEL
    assert r.versao == "2.1.0"
