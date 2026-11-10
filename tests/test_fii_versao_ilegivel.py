"""Versão explicitamente ilegível do Informe não demonstra identidade (F3-P08, BUG-2C-27).

Levantamento da 2C (`docs/decisoes/fii-bordas-pendentes-2c.md`): ilegível nos dois lados,
só em um lado e controles de versões válidas; ausência legada fica no escopo ratificado.
"""

import pytest

from sentinela.data import rendimento_fii as rf
from tests.test_fii_rendimento_elegivel import _avaliar, _composicao, _registros


def _final(registros):
    return max(registros, key=lambda r: r["Data_Referencia"])


def test_ilegivel_nos_dois_lados_abstem_com_motivo():
    registros, composicoes = _registros(), _composicao()
    for linha in [*registros, *composicoes]:
        linha["Versao"] = "ilegivel"
    resultado = _avaliar(registros, composicoes)
    assert resultado == rf.Abstencao(f"{rf.MOTIVO_VERSAO_ILEGIVEL}: 2026-09")


def test_so_o_mes_final_ilegivel_nos_dois_lados_abstem():
    registros, composicoes = _registros(), _composicao()
    _final(registros)["Versao"] = "v?"
    composicoes[0]["Versao"] = "v?"
    resultado = _avaliar(registros, composicoes)
    assert resultado == rf.Abstencao(f"{rf.MOTIVO_VERSAO_ILEGIVEL}: 2026-09")


@pytest.mark.parametrize("lado", ["complemento", "composicao"])
def test_ilegivel_so_em_um_lado_abstem(lado):
    registros, composicoes = _registros(), _composicao()
    alvo = _final(registros) if lado == "complemento" else composicoes[0]
    alvo["Versao"] = "ilegivel"
    assert isinstance(_avaliar(registros, composicoes), rf.Abstencao)


def test_versoes_validas_produzem_rendimento():
    assert not isinstance(_avaliar(), rf.Abstencao)


def test_coexistencia_valida_e_ilegivel_usa_a_valida():
    registros, composicoes = _registros(), _composicao()
    ilegivel = {**_final(registros), "Versao": "ilegivel"}
    assert not isinstance(_avaliar([*registros, ilegivel], composicoes), rf.Abstencao)


@pytest.mark.parametrize("ausente", [None, "", "  ", float("nan"), "remover"])
def test_ausencia_legada_segue_o_escopo_ratificado(ausente):
    registros, composicoes = _registros(), _composicao()
    for linha in [*registros, *composicoes]:
        if ausente == "remover":
            del linha["Versao"]
        else:
            linha["Versao"] = ausente
    assert not isinstance(_avaliar(registros, composicoes), rf.Abstencao)


@pytest.mark.parametrize(
    ("bruto", "ilegivel"),
    [
        ("ilegivel", True),
        ("1a", True),
        ("NaN", True),
        ("inf", True),
        ("1", False),
        ("2,0", False),
        (3, False),
        (None, False),
        ("", False),
        (float("nan"), False),
    ],
)
def test_versao_explicitamente_ilegivel(bruto, ilegivel):
    assert rf.versao_ilegivel({"Versao": bruto}) is ilegivel
    assert rf.versao_ilegivel({}) is False


def test_composicao_ilegivel_nao_casa_com_complemento_legado():
    registros, composicoes = _registros(), _composicao()
    for linha in registros:
        del linha["Versao"]
    composicoes[0]["Versao"] = "ilegivel"
    assert _avaliar(registros, composicoes) == rf.Abstencao(rf.MOTIVO_SEM_COMPOSICAO)
