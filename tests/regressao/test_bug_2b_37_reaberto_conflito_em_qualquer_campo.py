"""BUG-2B-37 (reaberto): o conflito de mesma versão no Informe só compara DY e valor da cota.

Auditoria de fechamento da 2B (Codex, 25/10/2026): duas linhas da mesma versão com cotas ou
amortização diferentes não são conflito, e a ordem das linhas muda a elegibilidade. A ficha
FII 1.3 (§3c) manda abster por conflito em qualquer campo usado (DY, VP, cotas, amortização,
composição), nas duas ordens.
"""

import pytest

from sentinela.data import rendimento_fii as rf
from tests.test_fii_rendimento_elegivel import _avaliar, _composicao, _registros


@pytest.mark.parametrize("ordem", [1, -1])
@pytest.mark.parametrize(
    ("campo", "outro"),
    [("Cotas_Emitidas", "1500"), ("Percentual_Amortizacao_Cotas_Mes", "0.01")],
)
def test_conflito_no_complemento_abstem_nas_duas_ordens(campo, outro, ordem):
    registros = _registros()
    conflitante = {**registros[5], campo: outro}
    linhas = [registros[5], conflitante][::ordem]
    r = _avaliar([*registros[:5], *linhas, *registros[6:]])
    assert isinstance(r, rf.Abstencao), r
    assert r.motivo.startswith(rf.MOTIVO_CONFLITO)


@pytest.mark.parametrize("ordem", [1, -1])
def test_conflito_na_composicao_abstem_nas_duas_ordens(ordem):
    tijolo = _composicao()[0]
    papel = {**tijolo, "Imoveis_Renda_Acabados": "10", "CRI": "90"}
    r = _avaliar(composicoes=[tijolo, papel][::ordem])
    assert isinstance(r, rf.Abstencao), r
    assert r.motivo.startswith(rf.MOTIVO_CONFLITO)


@pytest.mark.parametrize("ordem", [1, -1])
@pytest.mark.parametrize("invalido", ["NaN", "abc"])
def test_vazio_e_invalido_sao_conflito_nas_duas_ordens(invalido, ordem):
    # Revisão do F2B-57: o vazio vale zero (ficha 1.3), o inválido abstém; os dois na mesma
    # versão não podem ser decididos pela ordem das linhas.
    registros = _registros()
    vazio = {**registros[5], "Percentual_Amortizacao_Cotas_Mes": ""}
    ruim = {**registros[5], "Percentual_Amortizacao_Cotas_Mes": invalido}
    r = _avaliar([*registros[:5], *[vazio, ruim][::ordem], *registros[6:]])
    assert isinstance(r, rf.Abstencao) and r.motivo.startswith(rf.MOTIVO_CONFLITO), r
    tijolo = _composicao()[0]
    r = _avaliar(
        composicoes=[{**tijolo, "CRI": ""}, {**tijolo, "CRI": invalido}][::ordem]
    )
    assert isinstance(r, rf.Abstencao) and r.motivo.startswith(rf.MOTIVO_CONFLITO), r


def test_composicoes_identicas_da_mesma_versao_calculam():
    tijolo = _composicao()[0]
    assert not isinstance(_avaliar(composicoes=[tijolo, dict(tijolo)]), rf.Abstencao)
