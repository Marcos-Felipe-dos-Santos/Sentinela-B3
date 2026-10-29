"""Payout contextual usa a fonte comum, sem retenção nem truncamento."""

import math

import pytest

from sentinela.data.payout_lynch import contexto

FONTE = {"fonte": "relação de proventos da B3", "referencia": "2026-10-20"}


def test_exemplo_independente_e_proveniencia():
    r = contexto(0.02, 30, 2.0736, confiavel=True, fonte=FONTE)
    assert r == {
        "valor": pytest.approx(0.6 / 2.0736),
        "dy": 0.02,
        "preco_referencia": 30,
        "lpa_final": 2.0736,
        "fonte": FONTE,
    }
    assert r["fonte"] is FONTE


@pytest.mark.parametrize(
    "dy,preco,lpa,esperado",
    [
        (0, 30, 2, 0),
        (0.3, 30, 2, 4.5),
        (2, 30, 2, 30),
        (1e300, 1e300, 1e300, 1e300),
        (1e-300, 1e-300, 1e-300, 1e-300),
        (1e-300, 1e300, 1e-300, 1e300),
    ],
)
def test_dominio_sem_limites_de_perfil_ou_overflow_intermediario(
    dy, preco, lpa, esperado
):
    r = contexto(dy, preco, lpa, confiavel=True, fonte=FONTE)
    assert r["valor"] == pytest.approx(esperado, rel=1e-12, abs=0)
    assert math.isfinite(r["valor"])
    assert r["dy"] == dy
    assert r["preco_referencia"] == preco
    assert r["lpa_final"] == lpa


@pytest.mark.parametrize("campo", ["dy", "preco", "lpa"])
@pytest.mark.parametrize(
    "valor", [None, True, False, "2", float("nan"), float("inf"), -float("inf")]
)
def test_invalido_abstem_so_contexto_e_preserva_fonte(campo, valor):
    argumentos = {"dy": 0.02, "preco": 30, "lpa": 2.0736}
    argumentos[campo] = valor
    r = contexto(**argumentos, confiavel=True, fonte=FONTE)
    assert set(r) == {"abstencao", "fonte"}
    nome = {"dy": "DY", "preco": "preço de referência", "lpa": "LPA final"}[campo]
    motivo = "não finito" if isinstance(valor, float) else "ausente ou não numérico"
    assert r["abstencao"] == f"{nome} {motivo}"
    assert r["fonte"] is FONTE


@pytest.mark.parametrize(
    "dy,preco,lpa",
    [(-0.1, 30, 2), (0.02, 0, 2), (0.02, -30, 2), (0.02, 30, 0), (0.02, 30, -2)],
)
def test_dominio_negativo_ou_denominador_zero(dy, preco, lpa):
    r = contexto(dy, preco, lpa, confiavel=True, fonte=FONTE)
    assert set(r) == {"abstencao", "fonte"}
    nome = "DY" if dy < 0 else "preço de referência" if preco <= 0 else "LPA final"
    assert r["abstencao"] == f"{nome} fora do domínio"


def test_fonte_nao_confiavel_nao_e_zero():
    r = contexto(0, 30, 2, confiavel=False, fonte=FONTE)
    assert set(r) == {"abstencao", "fonte"}
    assert r["abstencao"] == "fonte comum de DY não confiável"


def test_overflow_final_abstem_com_motivo():
    r = contexto(1e300, 1e300, 1e-300, confiavel=True, fonte=FONTE)
    assert set(r) == {"abstencao", "fonte"}
    assert r["abstencao"] == "payout contextual não finito"


@pytest.mark.parametrize("confiavel", [None, 0, 1, "sim"])
def test_confiabilidade_exige_booleano_verdadeiro(confiavel):
    assert contexto(0.02, 30, 2, confiavel=confiavel, fonte=FONTE) == {
        "abstencao": "fonte comum de DY não confiável",
        "fonte": FONTE,
    }


def test_inteiro_fora_da_representacao_float_abstem():
    assert contexto(10**400, 30, 2, confiavel=True, fonte=FONTE) == {
        "abstencao": "payout contextual não finito",
        "fonte": FONTE,
    }
