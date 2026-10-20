import dataclasses
import math

import pytest

from sentinela.domain.units import (
    BRL,
    Escala,
    Percent,
    QuantidadeAcoes,
    RateNominal,
    RateReal,
    Ratio,
)

TIPOS_ESCALARES = [BRL, Ratio, Percent, RateNominal, RateReal]


def test_taxa_real_e_nominal_nao_se_misturam():
    real, nominal = RateReal(0.06), RateNominal(0.1375)
    with pytest.raises(TypeError, match="RateReal.*RateNominal"):
        real + nominal
    with pytest.raises(TypeError, match="RateNominal.*RateReal"):
        nominal - real
    assert real != nominal
    assert RateReal(0.06) + RateReal(0.01) == RateReal(0.06 + 0.01)
    assert RateNominal(0.1) - RateNominal(0.04) == RateNominal(0.1 - 0.04)


@pytest.mark.parametrize("tipo", TIPOS_ESCALARES)
def test_soma_so_vale_entre_o_mesmo_tipo(tipo):
    assert tipo(2.0) + tipo(3.0) == tipo(5.0)
    assert tipo(2.0) - tipo(3.0) == tipo(-1.0)
    with pytest.raises(TypeError):
        tipo(2.0) + 3.0
    with pytest.raises(TypeError):
        tipo(2.0) - 3
    with pytest.raises(TypeError):
        3.0 + tipo(2.0)


def test_tipos_diferentes_nunca_sao_iguais_nem_somam():
    assert Ratio(1.0) != Percent(1.0)
    assert BRL(1.0) != Ratio(1.0)
    with pytest.raises(TypeError):
        BRL(1.0) + Ratio(1.0)
    with pytest.raises(TypeError):
        Percent(1.0) - Ratio(1.0)


def test_percentual_vira_razao():
    assert Percent(12.5).para_ratio() == Ratio(0.125)
    assert Ratio(0.125).para_percent() == Percent(12.5)
    assert isinstance(Percent(5.0).para_ratio(), Ratio)
    assert isinstance(Ratio(0.05).para_percent(), Percent)
    assert Percent(0.0).para_ratio() == Ratio(0.0)


def test_quantidade_em_milhares_vira_unidades():
    mil = QuantidadeAcoes(1_500.0, Escala.MIL)
    assert mil.em_unidades() == QuantidadeAcoes(1_500_000.0, Escala.UNIDADE)
    unidade = QuantidadeAcoes(750.0, Escala.UNIDADE)
    assert unidade.em_unidades() == unidade
    assert mil.em_unidades().escala is Escala.UNIDADE


def test_quantidade_exige_escala_explicita():
    with pytest.raises(TypeError):
        QuantidadeAcoes(100.0)
    with pytest.raises(TypeError, match="escala deve ser Escala, não int"):
        QuantidadeAcoes(100.0, 1000)


def test_quantidade_so_soma_na_mesma_escala():
    a, b = QuantidadeAcoes(1.0, Escala.MIL), QuantidadeAcoes(2.0, Escala.MIL)
    assert a + b == QuantidadeAcoes(3.0, Escala.MIL)
    assert b - a == QuantidadeAcoes(1.0, Escala.MIL)
    with pytest.raises(TypeError, match="escala"):
        a + QuantidadeAcoes(2.0, Escala.UNIDADE)
    with pytest.raises(TypeError):
        a - 1.0
    assert a != QuantidadeAcoes(1.0, Escala.UNIDADE)


@pytest.mark.parametrize("ruim", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("tipo", TIPOS_ESCALARES)
def test_valor_nao_finito_e_rejeitado(tipo, ruim):
    with pytest.raises(ValueError, match="finito"):
        tipo(ruim)


def test_valor_nao_finito_e_rejeitado_na_quantidade():
    with pytest.raises(ValueError, match="finito"):
        QuantidadeAcoes(math.nan, Escala.UNIDADE)
    with pytest.raises(ValueError, match="finito"):
        QuantidadeAcoes(math.inf, Escala.MIL)


@pytest.mark.parametrize(
    ("ruim", "nome"),
    [("1.0", "str"), (None, "NoneType"), (True, "bool"), ([1.0], "list")],
)
def test_valor_que_nao_e_numero_e_rejeitado(ruim, nome):
    with pytest.raises(TypeError, match=f"número, não {nome}"):
        BRL(ruim)


def test_inteiro_vira_float():
    assert type(BRL(3).valor) is float
    assert BRL(3) == BRL(3.0)


def test_conta_que_estoura_para_infinito_e_rejeitada():
    with pytest.raises(ValueError, match="finito"):
        BRL(1e308) + BRL(1e308)
    with pytest.raises(ValueError, match="finito"):
        Percent(1e308).para_ratio().para_percent() + Percent(1e308)


@pytest.mark.parametrize("tipo", TIPOS_ESCALARES)
def test_tipos_sao_imutaveis(tipo):
    x = tipo(1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        x.valor = 2.0
    with pytest.raises(AttributeError):
        x.outro = 1
    assert hash(tipo(1.0)) == hash(tipo(1.0))


def test_quantidade_e_imutavel():
    q = QuantidadeAcoes(1.0, Escala.MIL)
    with pytest.raises(dataclasses.FrozenInstanceError):
        q.valor = 2.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        q.escala = Escala.UNIDADE


def test_escala_tem_o_fator_de_conversao():
    assert Escala.UNIDADE.fator == 1
    assert Escala.MIL.fator == 1000


def test_fisher_ida_e_volta():
    from sentinela.domain.units import Inflacao

    real = RateReal(0.11761818181818182)
    nominal = real.para_nominal(Inflacao(0.0426))
    assert isinstance(nominal, RateNominal)
    assert nominal.valor == pytest.approx(0.16522871636363636, abs=1e-10, rel=0)
    assert nominal.para_real(Inflacao(0.0426)).valor == pytest.approx(
        real.valor, abs=1e-10, rel=0
    )
    assert RateNominal(0.144).para_real(Inflacao(0.04)).valor == pytest.approx(
        0.1, abs=1e-10, rel=0
    )


def test_inflacao_nao_soma_com_taxa():
    from sentinela.domain.units import Inflacao

    for taxa in (RateReal(0.1), RateNominal(0.1)):
        with pytest.raises(TypeError):
            taxa + Inflacao(0.04)
        with pytest.raises(TypeError):
            Inflacao(0.04) + taxa


@pytest.mark.parametrize("pi,nominal", [(0.0, 0.1), (0.04, 0.144), (-0.01, 0.089)])
def test_fisher_com_zero_inflacao_e_deflacao(pi, nominal):
    from sentinela.domain.units import Inflacao

    assert RateReal(0.1).para_nominal(Inflacao(pi)).valor == pytest.approx(
        nominal, abs=1e-10, rel=0
    )
    assert RateNominal(nominal).para_real(Inflacao(pi)).valor == pytest.approx(
        0.1, abs=1e-10, rel=0
    )


@pytest.mark.parametrize("valor", [-1, -1.1, math.nan, math.inf, -math.inf])
def test_inflacao_exige_fator_positivo_finito(valor):
    from sentinela.domain.units import Inflacao

    with pytest.raises(ValueError):
        Inflacao(valor)


@pytest.mark.parametrize("valor", [True, None, "0.04"])
def test_inflacao_exige_numero(valor):
    from sentinela.domain.units import Inflacao

    with pytest.raises(TypeError):
        Inflacao(valor)


@pytest.mark.parametrize("tipo", [RateReal, RateNominal])
@pytest.mark.parametrize("valor", [-1.0, -2.0])
def test_fisher_recusa_taxa_sem_fator_positivo(tipo, valor):
    from sentinela.domain.units import Inflacao

    taxa = tipo(valor)
    converter = taxa.para_nominal if tipo is RateReal else taxa.para_real
    with pytest.raises(ValueError):
        converter(Inflacao(0.04))


@pytest.mark.parametrize("tipo", [RateReal, RateNominal])
@pytest.mark.parametrize("inflacao", [0.04, Ratio(0.04), None])
def test_fisher_exige_inflacao_tipificada(tipo, inflacao):
    taxa = tipo(0.1)
    converter = taxa.para_nominal if tipo is RateReal else taxa.para_real
    with pytest.raises(TypeError):
        converter(inflacao)


def test_fluxos_convertidos_preservam_valor_presente_da_ficha():
    from sentinela.domain.units import Inflacao, fluxo_nominal, fluxo_real

    pi = Inflacao(0.04)
    primeiro_real = BRL(1.02)
    primeiro_nominal = fluxo_nominal(primeiro_real, pi, 1)
    assert primeiro_nominal.valor == pytest.approx(1.0608, abs=1e-10, rel=0)
    assert fluxo_real(primeiro_nominal, pi, 1).valor == pytest.approx(
        1.02, abs=1e-10, rel=0
    )
    assert primeiro_real.valor / (0.1 - 0.02) == pytest.approx(12.75, abs=1e-10, rel=0)
    assert primeiro_nominal.valor / (0.144 - 0.0608) == pytest.approx(
        12.75, abs=1e-10, rel=0
    )
    for t, fator in [(0, 1), (1, 1.04), (2, 1.0816), (3, 1.124864)]:
        real = BRL(20)
        nominal = fluxo_nominal(real, pi, t)
        assert nominal.valor == pytest.approx(20 * fator, abs=1e-10, rel=0)
        assert nominal.valor / (1.144**t) == pytest.approx(
            20 / (1.1**t), abs=1e-10, rel=0
        )
        assert fluxo_real(nominal, pi, t).valor == pytest.approx(20, abs=1e-10, rel=0)


@pytest.mark.parametrize("pi", [0.0, -0.01])
@pytest.mark.parametrize("valor", [0.0, -10.0, 10.0])
def test_fluxo_com_zero_deflacao_e_sinais(pi, valor):
    from sentinela.domain.units import Inflacao, fluxo_nominal, fluxo_real

    nominal = fluxo_nominal(BRL(valor), Inflacao(pi), 2)
    assert nominal.valor == pytest.approx(valor * (1 + pi) ** 2, abs=1e-10, rel=0)
    assert fluxo_real(nominal, Inflacao(pi), 2).valor == pytest.approx(
        valor, abs=1e-10, rel=0
    )


@pytest.mark.parametrize("nome", ["fluxo_nominal", "fluxo_real"])
@pytest.mark.parametrize("t", [math.nan, math.inf, -math.inf, True, "1"])
def test_fluxo_exige_periodo_numerico_finito(nome, t):
    from sentinela.domain import units

    with pytest.raises((TypeError, ValueError)):
        getattr(units, nome)(BRL(10), units.Inflacao(0.04), t)


@pytest.mark.parametrize("nome", ["fluxo_nominal", "fluxo_real"])
def test_fluxo_exige_brl_e_inflacao(nome):
    from sentinela.domain import units

    converter = getattr(units, nome)
    with pytest.raises(TypeError):
        converter(Ratio(10), units.Inflacao(0.04), 1)
    with pytest.raises(TypeError):
        converter(BRL(10), RateReal(0.04), 1)


def test_resultado_nao_finito_de_fisher_ou_fluxo_e_recusado():
    from sentinela.domain.units import Inflacao, fluxo_nominal, fluxo_real

    with pytest.raises(ValueError):
        RateReal(1e308).para_nominal(Inflacao(1e308))
    with pytest.raises(ValueError):
        RateNominal(1e308).para_real(Inflacao(-0.99))
    with pytest.raises(ValueError):
        fluxo_nominal(BRL(1e308), Inflacao(1.0), 1)
    with pytest.raises(ValueError):
        fluxo_real(BRL(1e308), Inflacao(-0.99), 1)


@pytest.mark.parametrize("nome", ["fluxo_nominal", "fluxo_real"])
@pytest.mark.parametrize("valor", [None, True, 10.0])
def test_fluxo_sem_unidade_e_rejeitado(nome, valor):
    from sentinela.domain import units

    with pytest.raises(TypeError):
        getattr(units, nome)(valor, units.Inflacao(0.04), 1)


def test_inflacao_e_imutavel():
    from sentinela.domain.units import Inflacao

    pi = Inflacao(0.04)
    with pytest.raises(dataclasses.FrozenInstanceError):
        pi.valor = 0.05
    with pytest.raises(AttributeError):
        pi.outro = 1


@pytest.mark.parametrize("nome", ["fluxo_nominal", "fluxo_real"])
def test_potencia_de_fluxo_nao_representavel_e_recusada(nome):
    from sentinela.domain import units

    with pytest.raises(ValueError):
        getattr(units, nome)(BRL(1), units.Inflacao(1), 10000)
    if nome == "fluxo_real":
        with pytest.raises(ValueError):
            units.fluxo_real(BRL(1), units.Inflacao(-0.5), 10000)


@pytest.mark.parametrize("tipo", [RateReal, RateNominal])
def test_fisher_preserva_taxa_zero_e_taxa_negativa_admissivel(tipo):
    from sentinela.domain.units import Inflacao

    for valor in (0.0, -0.01):
        taxa = tipo(valor)
        converter = taxa.para_nominal if tipo is RateReal else taxa.para_real
        assert converter(Inflacao(0)).valor == pytest.approx(valor, abs=1e-10, rel=0)
