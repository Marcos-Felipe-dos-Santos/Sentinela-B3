"""Permissão aditiva de20/10: contrato da ficha Gordon1.0, sem alterar campos antigos."""

from dataclasses import FrozenInstanceError, fields
from datetime import date

import pytest

from sentinela.domain import units
from sentinela.methods.base import MethodInputs


def _proventos(**kw):
    dados = {
        "dividendo_anual": units.BRL(0.7),
        "payout": units.Ratio(0.7),
        "inicio": date(2025, 1, 1),
        "fim": date(2025, 12, 31),
    }
    dados.update(kw)
    return units.ProventosControladores(**dados)


def test_campos_gordon_opcionais_e_tipados_sem_mudar_os_antigos():
    antigo = MethodInputs(as_of=date(2026, 10, 20))
    assert antigo.proventos_controladores is None
    assert antigo.teto_pib_real is None
    assert antigo.custo_capital_real is None and antigo.inflacao is None
    proventos = _proventos()
    novo = MethodInputs(
        as_of=date(2026, 10, 20),
        proventos_controladores=proventos,
        teto_pib_real=units.RateReal(0.02),
    )
    assert novo.proventos_controladores is proventos
    assert novo.teto_pib_real == units.RateReal(0.02)
    assert next(f for f in fields(MethodInputs) if f.name == "selic").default is None
    with pytest.raises(FrozenInstanceError):
        novo.teto_pib_real = units.RateReal(0.03)


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("teto_pib_real", 0.02),
        ("teto_pib_real", units.RateNominal(0.02)),
        ("proventos_controladores", {}),
        ("proventos_controladores", True),
    ],
)
def test_tipos_errados_rejeitados_no_contrato(campo, valor):
    with pytest.raises(TypeError, match=campo):
        MethodInputs(as_of=date(2026, 10, 20), **{campo: valor})


@pytest.mark.parametrize(
    "kw",
    [
        {"dividendo_anual": 0.7},
        {"payout": 0.7},
        {"inicio": "2025-01-01"},
        {"fim": None},
    ],
)
def test_proventos_exigem_unidades_e_datas(kw):
    with pytest.raises(TypeError):
        _proventos(**kw)
