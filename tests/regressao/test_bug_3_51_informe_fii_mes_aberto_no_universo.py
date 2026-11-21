"""BUG-3-51 (Gemini A4): Informe de mês aberto ou futuro não entra no universo FII em D.

O universo em D lê o geral do Informe entregue antes de D (`universo._informe_em` e
`universo._fiis_com_informe`), mas não exigia o mês de referência encerrado antes de D, como
a leitura e a remontagem exigem (`leitura._mes_encerrado`). Uma linha com `Data_Referencia`
do mês de D, ou futura, entregue antes de D, avançava o "informe mais novo do arquivo" e
deslocava o corte de seis meses (`montagem.informe_mais_recente`) para todos os fundos.

Informe oficial de 2023 de um FII (fixture do F3-5) e um segundo fundo sintético no mesmo
leiaute, gravado na tabela real; índice, universo e montagem são os de produção.
"""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

import pytest
from test_universo_pit import CADASTRO, _negocio, _precos, _pregoes

from sentinela.data.pit import carga_cvm
from sentinela.data.referencia import universo
from sentinela.data.store import migracoes

FIXTURES = Path(__file__).parents[1] / "fixtures" / "pit_cvm"
FUNDO = (
    "00.332.266/0001-31"  # o FII da fixture: último mês 2023-12, entregue em 15/01/2024
)
OUTRO = "22.222.222/0001-22"
ISIN_OUTRO = "BROUTRCTF000"


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(":memory:")) as banco:
        migracoes.aplicar(banco)
        carga_cvm.carregar(
            banco,
            FIXTURES / "inf_mensal_fii_2023.zip",
            tipo="FII_INFORME",
            fonte="cvm",
            coleta="c",
        )
        yield banco


def _outro_fundo(conn: sqlite3.Connection, referencia: str, entrega: str) -> None:
    """Linha do geral de outro fundo, copiada do leiaute da fixture."""
    (texto,) = conn.execute(
        "SELECT linha_json FROM fii_informe_linhas WHERE parte = 'geral' "
        "ORDER BY dt_refer DESC LIMIT 1"
    ).fetchone()
    linha = json.loads(texto)
    chave_cnpj = "CNPJ_Fundo_Classe" if "CNPJ_Fundo_Classe" in linha else "CNPJ_Fundo"
    linha.update(
        {
            chave_cnpj: OUTRO,
            "Codigo_ISIN": ISIN_OUTRO,
            "Data_Referencia": referencia,
            "Data_Entrega": entrega,
            "Versao": "1",
        }
    )
    novo = json.dumps(linha, ensure_ascii=False, sort_keys=True)
    sha = hashlib.sha256(novo.encode()).hexdigest()
    conn.execute(
        "INSERT INTO fii_informe_linhas (cnpj, dt_refer, versao, parte, data_entrega, "
        "linha_sha256, linha_json, fonte, coleta, hash_sha256) "
        "VALUES (?, ?, '1', 'geral', ?, ?, ?, 'teste', 'c', ?)",
        (OUTRO, referencia, entrega, sha, novo, sha),
    )


def _cnpjs_fii(conn: sqlite3.Connection, dia: date) -> set[str]:
    return {
        r.cnpj
        for r in universo.indice_em(conn, dia, CADASTRO).registros.values()
        if r.classe == "FII"
    }


def test_mes_aberto_de_outro_fundo_nao_tira_o_fundo_regular_do_indice(conn):
    dia = date(2024, 7, 10)
    assert FUNDO in _cnpjs_fii(conn, dia)  # controle: corte pelo 2023-12 da fixture
    _outro_fundo(conn, "2024-07-01", "2024-07-05")  # mês de D, ainda aberto
    assert FUNDO in _cnpjs_fii(conn, dia)
    assert OUTRO not in _cnpjs_fii(conn, dia)


def test_referencia_futura_entregue_antes_de_d_nao_desloca_o_corte(conn):
    dia = date(2024, 2, 1)
    _outro_fundo(conn, "2024-09-01", "2024-01-20")  # erro material: referência futura
    assert FUNDO in _cnpjs_fii(conn, dia)
    assert OUTRO not in _cnpjs_fii(conn, dia)


def test_mes_encerrado_de_outro_fundo_desloca_o_corte_como_antes(conn):
    """Controle: o mês já encerrado em D segue valendo para o corte de seis meses."""
    _outro_fundo(conn, "2024-07-01", "2024-08-05")
    dia = date(2024, 8, 10)
    cnpjs = _cnpjs_fii(conn, dia)
    assert OUTRO in cnpjs and FUNDO not in cnpjs


def test_fundo_so_com_mes_aberto_nao_entra_nos_tickers(conn, tmp_path):
    dias = _pregoes(date(2024, 7, 1), 5)
    _precos(conn, tmp_path, [_negocio(d, "OUTR11", ISIN_OUTRO) for d in dias])
    dia = dias[-1] + timedelta(days=1)
    _outro_fundo(conn, "2024-07-01", "2024-07-03")
    assert {t["ticker"] for t in universo.tickers_em(conn, dia)} == set()
