"""Ponte documental: o motor não presume compatibilidade de direitos e ações."""

from datetime import UTC, datetime

import pytest

from tests.test_market_engine_acoes_cvm import CNPJ, _ind, _motor


class Instante(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 20, 18, tzinfo=UTC).astimezone(tz)


@pytest.mark.parametrize(
    "prova,mesmo_documento,compativel",
    [(False, True, False), (True, True, True), (True, False, False)],
)
def test_base_oficial_explicita_e_documento_da_escala(
    monkeypatch, prova, mesmo_documento, compativel
):
    monkeypatch.setattr("market_engine.datetime", Instante)
    motor = _motor(monkeypatch, _ind())
    motor.cvm.gordon_do_documento = lambda cd, ind, instante: {
        "cnpj": CNPJ,
        "versao": "1" if mesmo_documento else "2",
        "inicio": "2025-01-01",
        "fim": "2025-12-31",
        "lucro_controladores": 2000.0,
        "pl_inicial_controladores": 9000.0,
        "proventos_controladores": 100.0,
        "hipotese_dva_anual": True,
    }
    dados = {"cd_cvm": 1, "preco_atual": 20.0, "especie": "ON", "classe_ativo": "STOCK"}
    if prova:
        motor.cvm.composicao_mais_recente = lambda cnpj, instante, ano: {
            "composicao": _ind()[2025]["composicao_capital"],
            "proveniencia": {"fonte": "ITR sintético", "data_entrega": "2026-08-10"},
        }
    assert motor._buscar_cvm("TSTA3", dados)
    fato = dados["gordon_cvm"]
    assert fato["base_acionaria_compativel"] is compativel
    assert fato["acoes_base"] == (1000.0 if mesmo_documento else None)
    assert fato["lpa"] == 2.1
    assert (
        "evento posterior ao último documento entregue não é detectado"
        in fato["avisos"]
    )
