"""Matriz da ficha: valor extraordinário ilegível não equivale a zero."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from tests import test_gordon_documento as fonte_documental

documento = fonte_documental.documento


def _ler_com_evento(documento, monkeypatch, valor):
    p, ind = documento
    original = p._read_raw

    def com_evento(caminho, tipo):
        df = original(caminho, tipo)
        if tipo == "DVA_con":
            extra = (
                df[
                    (df["CD_CVM"].astype(float) == 23264)
                    & (df["ORDEM_EXERC"] == "ÚLTIMO")
                ]
                .iloc[[0]]
                .copy()
            )
            extra["CD_CONTA"] = "7.99.99"
            extra["DS_CONTA"] = "Distribuição extraordinária identificada"
            extra["VL_CONTA"] = valor
            df = pd.concat([df, extra], ignore_index=True)
        return df

    monkeypatch.setattr(p, "_read_raw", com_evento)
    return p.gordon_do_documento(23264, ind, datetime(2026, 10, 20, 18, tzinfo=UTC))


@pytest.mark.parametrize("valor", [None, "ilegível", "inf"])
def test_evento_extraordinario_com_valor_invalido_abstem(documento, monkeypatch, valor):
    assert _ler_com_evento(documento, monkeypatch, valor) == {
        "abstencao": "distribuição extraordinária com valor inválido"
    }


def test_zero_informado_nao_e_evento_extraordinario(documento, monkeypatch):
    r = _ler_com_evento(documento, monkeypatch, "0")
    assert r["hipotese_dva_anual"] is True
    assert r["distribuicao_extraordinaria_identificada"] is False
    assert r["proventos_controladores"] == 10903280000.0
