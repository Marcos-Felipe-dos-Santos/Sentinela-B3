"""Contrato com recorte literal da DFP do exemplo público da ficha Gordon."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

import cvm_provider
from cvm_provider import CVMProvider


@pytest.fixture
def documento(tmp_path, monkeypatch):
    fixture = json.loads(
        (
            Path(__file__).parent / "fixtures/contratos/dfp_2025_ambev_gordon.json"
        ).read_text()
    )
    zip_path = tmp_path / "dfp_cia_aberta_2025.zip"
    with ZipFile(zip_path, "w") as z:
        for nome, texto in fixture["membros"].items():
            z.writestr(nome, texto.encode("latin-1"))
    instante = datetime.fromisoformat(fixture["data_coleta"]).timestamp()
    os.utime(zip_path, (instante, instante))
    p = CVMProvider(tmp_path / "cache")
    monkeypatch.setattr(p, "baixar_dfp", lambda ano: zip_path)
    ind = {
        "cvm_dt_refer": "2025-12-31",
        "cvm_versao": "1",
        "cnpj": "07.526.557/0001-00",
        "lucro_controladores": 15503400000.0,
    }
    return p, ind


def test_dva_ambev_e_pl_inicial_comparativo_mesma_dfp(documento):
    p, ind = documento
    r = p.gordon_do_documento(23264, ind, datetime(2026, 10, 20, 18, tzinfo=UTC))
    assert "abstencao" not in r, r
    assert r["pl_inicial_controladores"] == 98642139000.0
    assert r["proventos_controladores"] == 10903280000.0
    assert r["inicio"] == "2025-01-01" and r["fim"] == "2025-12-31"
    assert r["data_entrega"] == "2026-02-12"
    assert r["modelo"] == "empresa" and r["documento"] == "DFP"


def test_documento_entregue_no_dia_do_asof_ainda_nao_entra(documento):
    p, ind = documento
    r = p.gordon_do_documento(23264, ind, datetime(2026, 2, 12, 18, tzinfo=UTC))
    assert r == {"abstencao": "disponibilidade histórica da DFP não demonstrada"}


@pytest.mark.parametrize(
    "tipo,coluna,valor,motivo",
    [
        ("DVA_con", "DT_INI_EXERC", "2025-04-01", "janelas incompatíveis"),
        ("DRE_con", "ESCALA_MOEDA", "DESCONHECIDA", "escala monetária"),
        ("BPP_con", "DT_FIM_EXERC", "2023-12-31", "PL inicial ausente"),
    ],
)
def test_documento_incompativel_nao_e_reserva(
    documento, monkeypatch, tipo, coluna, valor, motivo
):
    p, ind = documento
    original = p._read_raw

    def alterar(caminho, demonstrativo):
        df = original(caminho, demonstrativo).copy()
        if demonstrativo == tipo:
            mascara = df["CD_CVM"].astype(float) == 23264
            if tipo == "BPP_con":
                mascara &= df["ORDEM_EXERC"] == "PENÚLTIMO"
            df.loc[mascara, coluna] = valor
        return df

    monkeypatch.setattr(p, "_read_raw", alterar)
    r = p.gordon_do_documento(23264, ind, datetime(2026, 10, 20, 18, tzinfo=UTC))
    assert motivo in r["abstencao"]


def test_sem_fuso_nao_consulta_documento(documento):
    p, ind = documento
    assert p.gordon_do_documento(
        23264, ind, datetime(2026, 10, 20, tzinfo=UTC).replace(tzinfo=None)
    ) == {"abstencao": "as_of exige fuso horário"}


def test_dva_extraordinaria_identificada_nao_vira_fluxo_projetavel(
    documento, monkeypatch
):
    import pandas as pd

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
            extra["VL_CONTA"] = "1"
            df = pd.concat([df, extra], ignore_index=True)
        return df

    monkeypatch.setattr(p, "_read_raw", com_evento)
    r = p.gordon_do_documento(23264, ind, datetime(2026, 10, 20, 18, tzinfo=UTC))
    assert r["distribuicao_extraordinaria_identificada"] is True
    assert r["hipotese_dva_anual"] is True


def test_mudanca_estrutural_identificada_exige_reconciliacao(documento):
    p, ind = documento
    ind["mudanca_estrutural_sem_reconciliacao"] = True
    r = p.gordon_do_documento(23264, ind, datetime(2026, 10, 20, 18, tzinfo=UTC))
    assert r["hipotese_dva_anual"] is True
    assert (
        r["fundamento_fluxo"]
        == "hipótese de DVA anual como aproximação do fluxo recorrente (ficha Gordon1.1, §1)"
    )


def _como_banco(original, *, manter_pl_de_empresa=False):
    """O recorte da Ambev no leiaute de banco (PL em 2.08, DVA em 7.09.04), mesmos valores."""

    def ler(caminho, demonstrativo):
        df = original(caminho, demonstrativo).copy()
        if demonstrativo == "BPP_con":
            novo = df[df["CD_CONTA"].astype(str).str.startswith("2.03")].copy()
            novo["CD_CONTA"] = novo["CD_CONTA"].str.replace("2.03", "2.08", n=1)
            if not manter_pl_de_empresa:
                df = df[~df["CD_CONTA"].astype(str).str.startswith("2.03")]
            df = pd.concat([df, novo])
        if demonstrativo == "DVA_con":
            df["CD_CONTA"] = df["CD_CONTA"].str.replace("7.08.04", "7.09.04", n=1)
        if demonstrativo == "DRE_con":
            df.loc[df["CD_CONTA"] == "3.11.02", "DS_CONTA"] = (
                "Atribuído aos Sócios Não Controladores"
            )
        return df

    return ler


def test_banco_le_as_contas_do_proprio_modelo(documento, monkeypatch):
    # F2B-32: os mesmos valores, lidos pelos pares do modelo banco da tabela de contas.
    p, ind = documento
    monkeypatch.setattr(p, "_read_raw", _como_banco(p._read_raw))
    r = p.gordon_do_documento(23264, ind, datetime(2026, 10, 20, 18, tzinfo=UTC))
    assert "abstencao" not in r, r
    assert r["modelo"] == "banco"
    assert r["pl_inicial_controladores"] == 98642139000.0
    assert r["proventos_controladores"] == 10903280000.0


def test_pl_de_empresa_e_de_banco_no_mesmo_bpp_abstem(documento, monkeypatch):
    p, ind = documento
    monkeypatch.setattr(
        p, "_read_raw", _como_banco(p._read_raw, manter_pl_de_empresa=True)
    )
    r = p.gordon_do_documento(23264, ind, datetime(2026, 10, 20, 18, tzinfo=UTC))
    assert r == {"abstencao": cvm_provider.MOTIVO_MODELO_DO_BPP}
