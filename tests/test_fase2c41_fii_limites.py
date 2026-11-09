"""Limites da ficha FII 1.3 e apresentação vigente, sem alterar metodologia."""

from datetime import UTC, datetime

import pytest
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

from sentinela.data import rendimento_fii as rf
from tests.test_fii_rendimento_elegivel import _avaliar, _registros
from tests.test_rastreabilidade import _contexto, _fii


@pytest.mark.parametrize("indice", [0, 6])
@pytest.mark.parametrize("vp", [None, "", "0", "-1", "nan", "inf", "abc"])
def test_vp_invalido_inclusive_mes_intermediario_e_decimo_terceiro(indice, vp):
    registros = _registros()
    registros[indice]["Valor_Patrimonial_Cotas"] = vp
    mes = registros[indice]["Data_Referencia"][:7]
    assert _avaliar(registros) == rf.Abstencao(f"{rf.MOTIVO_VP}: {mes}")


@pytest.mark.parametrize("inverter", [False, True])
def test_duplicata_numericamente_igual_nao_cria_conflito(inverter):
    registros = _registros(vp="1500", dy="0.001")
    duplicata = {
        **registros[6],
        "Valor_Patrimonial_Cotas": "1500.0",
        "Cotas_Emitidas": "1000.0",
    }
    registros.insert(6 if inverter else 7, duplicata)
    resultado = _avaliar(registros)
    assert resultado["rendimento_12m"] == pytest.approx(18.0)
    assert resultado["dy"] == pytest.approx(0.18)


def test_proveniencia_nula_abstem_sem_excecao():
    dados = enriquecer_fii({"ticker": "TST11", "preco_atual": 100.0, "dy": 0.12})
    dados["informe_fii"]["proveniencia"] = None
    assert rf.entradas(dados, AS_OF_GORDON) == rf.Abstencao(rf.MOTIVO_COLETA_INFORME)


def test_taxa_mesmo_dia_utc_mas_dia_anterior_em_brasilia_abstem():
    taxa = {
        "as_of": "2026-10-20T02:00:00+00:00",
        "data_base": "2026-10-16",
        "dias_uteis": 1,
        "ntnb": 0.07,
    }
    instante = datetime(2026, 10, 20, 3, tzinfo=UTC)
    assert rf.ntnb_ate(taxa, instante) == rf.Abstencao(
        f"{rf.MOTIVO_TAXA_SEM_CORTE}: registro de outro dia"
    )
    # Datas UTC distintas podem representar o mesmo dia local.
    taxa["as_of"] = "2026-10-19T23:00:00+00:00"
    assert rf.ntnb_ate(taxa, datetime(2026, 10, 20, 2, tzinfo=UTC)) == 0.07


def test_sintese_preserva_aviso_de_liquidez_no_fii_abstido():
    dados = _fii()
    dados["informe_fii"] = {"abstencao": "sem arquivo"}
    dados["liquidez"] = {"abstencao": "coleta indisponível"}
    sintese = dict(_contexto(dados, eh_fii=True)["sintese"])
    assert (
        sintese["Aviso de liquidez (fora dos riscos)"]
        == "liquidez não medida: coleta indisponível"
    )
