"""F3-3d (DD-62): ZIPs oficiais remontados do banco como existiam em D.

Ida e volta pelas fixtures oficiais (`tests/fixtures/pit_cvm/`): carregado o ZIP e remontado em
D = hoje, a cascata (`CVMProvider`) lê do remontado o mesmo que lê do original; num D anterior
à entrega de uma versão, ela some do índice e dos números.
"""

import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, datetime

import pandas as pd
import pytest
from test_carga_cvm import CIA, DFP, FII, ITR

import cvm_provider
from sentinela.data.pit import carga_cvm, leitura, remontagem
from sentinela.data.store import migracoes

HOJE = datetime(2026, 11, 12, 15, tzinfo=UTC)
DEMONSTRACOES = ["BPA_con", "BPP_con", "DRE_con", "DFC_MI_con", "DVA_con", "DMPL_con",
                 "BPA_ind", "DRE_ind"]  # fmt: skip


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _carregar(conn, arquivo, tipo):
    carga_cvm.carregar(
        conn, arquivo, tipo=tipo, fonte="cvm", coleta="2026-11-11T12:00:00+00:00"
    )


def _normalizar(frame):
    return frame.astype(str).sort_values(list(frame.columns)).reset_index(drop=True)


@pytest.mark.parametrize(
    ("original", "tipo", "ano"), [(ITR, "ITR", 2020), (DFP, "DFP", 2019)]
)
def test_cascata_le_do_remontado_o_mesmo_que_do_original(
    conn, tmp_path, original, tipo, ano
):
    _carregar(conn, original, tipo)
    remontado, motivos = remontagem.zip_cia_em(conn, tipo, ano, HOJE, tmp_path / "pit")
    assert remontado.name == original.name and motivos == {}
    provedor = cvm_provider.CVMProvider(cache_dir=str(tmp_path / "cache"))
    lidas = 0
    for demonstracao in DEMONSTRACOES:
        if not any(demonstracao in n for n in zipfile.ZipFile(original).namelist()):
            continue
        a, b = (
            provedor.parsear_demonstrativo(z, demonstracao, include_cd_cvm=True,
                                           include_versao=True, include_periodo=True)
            for z in (original, remontado)
        )  # fmt: skip
        lidas += len(a)
        pd.testing.assert_frame_equal(_normalizar(a), _normalizar(b))
    assert lidas > 100
    sem_link = [
        {k: v for k, v in e.items() if k != "LINK_DOC"}
        for e in provedor._entregas(original)
    ]
    assert [
        {k: v for k, v in e.items() if k != "LINK_DOC"}
        for e in provedor._entregas(remontado)
    ] == sem_link
    if tipo == "ITR":
        colunas = remontagem._COMPOSICAO_CSV
        a, b = (
            provedor._read_raw(z, "composicao_capital")[colunas]
            for z in (original, remontado)
        )
        pd.testing.assert_frame_equal(_normalizar(a), _normalizar(b))


def test_versao_entregue_depois_de_d_some_do_indice_e_dos_numeros(conn, tmp_path):
    _carregar(conn, DFP, "DFP")
    entre = datetime(2020, 2, 21, 15, tzinfo=UTC)  # só a versão 1 (20/02/2020) entregue
    remontado, motivos = remontagem.zip_cia_em(conn, "DFP", 2019, entre, tmp_path)
    provedor = cvm_provider.CVMProvider(cache_dir=str(tmp_path / "cache"))
    assert [e["VERSAO"] for e in provedor._entregas(remontado)] == ["1"]
    assert motivos == {(CIA, "2019-12-31"): leitura.MOTIVO_ENTREGA_POSTERIOR}
    assert provedor.parsear_demonstrativo(remontado, "DRE_con").empty
    antes = datetime(2020, 2, 20, 15, tzinfo=UTC)
    remontado, motivos = remontagem.zip_cia_em(conn, "DFP", 2019, antes, tmp_path / "b")
    assert provedor._entregas(remontado) == [] and motivos == {}


def test_ano_sem_documento_gera_o_leiaute_completo_sem_linhas(conn, tmp_path):
    _carregar(conn, DFP, "DFP")
    remontado, motivos = remontagem.zip_cia_em(conn, "DFP", 2018, HOJE, tmp_path)
    nomes = zipfile.ZipFile(remontado).namelist()
    assert len(nomes) == 17 and "dfp_cia_aberta_2018.csv" in nomes
    assert "dfp_cia_aberta_DFC_MD_ind_2018.csv" in nomes and motivos == {}
    provedor = cvm_provider.CVMProvider(cache_dir=str(tmp_path / "cache"))
    assert provedor.parsear_demonstrativo(remontado, "DRE_con").empty


def test_informe_remontado_so_com_o_geral_entregue_antes_de_d(conn, tmp_path):
    _carregar(conn, FII, "FII_INFORME")
    remontado = remontagem.zip_informe_em(conn, 2023, HOJE, tmp_path)
    with zipfile.ZipFile(FII) as original, zipfile.ZipFile(remontado) as novo:
        for nome in original.namelist():
            lidos = [
                pd.read_csv(z.open(nome), sep=";", encoding="latin-1", dtype=str,
                            keep_default_na=False)
                for z in (original, novo)
            ]  # fmt: skip
            pd.testing.assert_frame_equal(
                _normalizar(lidos[0]), _normalizar(lidos[1][lidos[0].columns])
            )
    cedo = datetime(2023, 3, 1, 15, tzinfo=UTC)
    parcial = zipfile.ZipFile(
        remontagem.zip_informe_em(conn, 2023, cedo, tmp_path / "c")
    )
    geral = pd.read_csv(parcial.open("inf_mensal_fii_geral_2023.csv"), sep=";",
                        encoding="latin-1", dtype=str)  # fmt: skip
    assert (geral["Data_Entrega"] < "2023-03-01").all() and len(geral) < 12
