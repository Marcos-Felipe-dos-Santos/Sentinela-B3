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
