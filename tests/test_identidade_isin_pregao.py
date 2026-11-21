"""F3-8d-fix (decisão 43, DD-74): a decisão 33 refeita na leitura com o ISIN do pregão.

Respostas oficiais da B3 da Lojas Renner (contrato D18): relação com 93 registros ON e
6 PN, GetDetail só com BRLRENACNOR1, complemento com 4 proventos em dinheiro do ISIN ON.
"""

import dataclasses
import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime

import pytest
from test_cotahist import _linha
from test_eventos_societarios import COLETA, _obter

from sentinela.data.providers import b3_cotahist, b3_proventos
from sentinela.data.store import migracoes

DIA = date(2026, 11, 2)
MOTIVO_PN = (
    "identidade do emissor não comprovada na coleta: identidade do emissor não "
    "comprovada: espécie PN da relação sem ISIN da companhia no GetDetail"
)


@pytest.fixture
def relacao():
    return b3_proventos.coletar(8133, COLETA, _obter())


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _pregao(conn, tmp_path, codigo, isin, dia="20261030"):
    caminho = tmp_path / f"COTAHIST_{codigo}_{dia}.ZIP"
    with zipfile.ZipFile(caminho, "w") as zf:
        linha = _linha(DATA=dia, CODNEG=codigo, ESPECI="PN", CODISI=isin)
        zf.writestr("COTAHIST.TXT", linha.encode("latin-1"))
    b3_cotahist.carregar(conn, caminho, fonte="b3", coleta=COLETA.isoformat())


def _ler(conn, ticker="LREN4"):
    return b3_proventos.proventos_ate(
        conn, "LREN", DIA, por_publicacao=True, ticker=ticker
    )


def test_complemento_gravado_com_a_fonte_da_coleta(conn, relacao):
    b3_proventos.gravar_proventos(conn, relacao, 8133)
    emissor, coleta, texto, fonte, hash_ = conn.execute(
        "SELECT * FROM proventos_complemento"
    ).fetchone()
    assert (emissor, coleta) == ("LREN", relacao.coleta)
    assert json.loads(texto) == list(relacao.dinheiro_complemento)
    assert len(json.loads(texto)) == 4
    assert "GetListedSupplementCompany" in fonte
    assert hash_ == relacao.fontes[-1]["sha256"]


def test_complemento_so_de_insercao(conn, relacao):
    b3_proventos.gravar_proventos(conn, relacao, 8133)
    for sql in (
        "UPDATE proventos_complemento SET dinheiro_json = '[]'",
        "DELETE FROM proventos_complemento",
        "INSERT INTO proventos_complemento SELECT * FROM proventos_complemento",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="só de inserção"):
            conn.execute(sql)


def test_ultima_fonte_que_nao_e_o_complemento_recusa_sem_gravar(conn, relacao):
    torta = dataclasses.replace(relacao, fontes=relacao.fontes[:-1])
    with pytest.raises(
        ValueError, match="^a última fonte da coleta não é o complemento"
    ):
        b3_proventos.gravar_proventos(conn, torta, 8133)
    assert conn.execute("SELECT COUNT(*) FROM proventos_coletas").fetchone() == (0,)


def test_sem_ticker_ou_sem_pregao_fica_o_motivo_da_coleta(conn, relacao, tmp_path):
    b3_proventos.gravar_proventos(conn, relacao, 8133)
    assert _ler(conn, ticker=None) == {"abstencao": MOTIVO_PN}
    assert _ler(conn) == {"abstencao": MOTIVO_PN}  # LREN4 sem pregão guardado
    _pregao(conn, tmp_path, "LREN4", "BRLRENACNPR8", dia="20261102")
    assert _ler(conn) == {"abstencao": MOTIVO_PN}  # pregão no próprio dia não vale


def test_codigo_do_emissor_diferente_nao_soma(conn, relacao, tmp_path):
    b3_proventos.gravar_proventos(conn, relacao, 8133)
    _pregao(conn, tmp_path, "LREN4", "BRLAMEACNPR6")  # PN de outra raiz
    assert _ler(conn) == {"abstencao": MOTIVO_PN}


def test_isin_do_pregao_ja_conhecido_fica_o_motivo(conn, relacao, tmp_path):
    b3_proventos.gravar_proventos(conn, relacao, 8133)
    _pregao(conn, tmp_path, "LREN3", "BRLRENACNOR1")
    assert _ler(conn, ticker="LREN3") == {"abstencao": MOTIVO_PN}


def test_coleta_sem_complemento_guardado_abstem_com_motivo_proprio(
    conn, relacao, tmp_path
):
    # coleta anterior à migração 011: as três tabelas da 009, sem o complemento
    with closing(sqlite3.connect(":memory:")) as antiga:
        migracoes.aplicar(antiga)
        b3_proventos.gravar_proventos(antiga, relacao, 8133)
        for tabela in ("proventos_coletas", "proventos", "proventos_vistos"):
            linhas = antiga.execute(f"SELECT * FROM {tabela}").fetchall()
            marcas = ", ".join("?" * len(linhas[0]))
            conn.executemany(f"INSERT INTO {tabela} VALUES ({marcas})", linhas)
    _pregao(conn, tmp_path, "LREN4", "BRLRENACNPR8")
    assert _ler(conn) == {
        "abstencao": "identidade do emissor não comprovada na coleta: complemento da "
        "coleta não guardado para conferir o ISIN do ticker no pregão"
    }


def test_parte_b_continua_valendo_com_o_isin_do_pregao(conn, relacao, tmp_path):
    estranho = dict(relacao.dinheiro_complemento[0], rate="9,99000000000")
    alterada = dataclasses.replace(
        relacao, dinheiro_complemento=(*relacao.dinheiro_complemento, estranho)
    )
    b3_proventos.gravar_proventos(conn, alterada, 8133)
    _pregao(conn, tmp_path, "LREN4", "BRLRENACNPR8")
    motivo = _ler(conn)["abstencao"]
    assert motivo.endswith(
        f"provento do complemento JRS CAP PROPRIO {estranho['lastDatePrior']} "
        "ausente da relação"
    )


def test_ultimo_pregao_antes_do_dia_decide(conn, relacao, tmp_path):
    b3_proventos.gravar_proventos(conn, relacao, 8133)
    _pregao(conn, tmp_path, "LREN4", "BRLAMEACNPR6", dia="20261029")
    _pregao(conn, tmp_path, "LREN4", "BRLRENACNPR8", dia="20261030")
    assert b3_proventos.isin_no_pregao(conn, "LREN4", DIA) == "BRLRENACNPR8"
    assert "abstencao" not in _ler(conn)
    assert b3_proventos.isin_no_pregao(conn, "LREN4", date(2026, 10, 30)) == (
        "BRLAMEACNPR6"
    )
    assert b3_proventos.isin_no_pregao(conn, "LREN9", DIA) is None


def test_motor_historico_le_os_proventos_com_o_isin_do_pregao(conn, relacao, tmp_path):
    """[e2e] produtor real: coleta oficial gravada, COTAHIST carregado, motor em D."""
    import pandas as pd

    from sentinela.services import historico

    b3_proventos.gravar_proventos(conn, relacao, 8133)
    _pregao(conn, tmp_path, "LREN4", "BRLRENACNPR8")
    as_of = datetime(2026, 11, 2, 15, tzinfo=UTC)
    motor = historico.MotorHistorico(conn, as_of, tmp_path / "pit", pd.DataFrame())
    dados = {"classe_ativo": "STOCK", "modelo_bpp": "empresa"}
    assert motor._buscar_yfinance("LREN4", dados)  # o fechamento do COTAHIST (F3-8h)
    motor._buscar_proventos_b3("LREN4", dados)
    assert "abstencao" not in dados["proventos_b3"], dados["proventos_b3"]
    assert len(dados["proventos_b3"]["registros"]) == 99
    sem_pregao = {"classe_ativo": "STOCK", "modelo_bpp": "empresa"}
    sem_pregao |= {"fonte_preco": historico.FONTE_PRECO, "fechamentos_brutos": {"2026-10-30": 1.0}}
    motor._buscar_proventos_b3("LREN3", sem_pregao)  # ISIN ON já conhecido
    assert sem_pregao["proventos_b3"] == {"abstencao": MOTIVO_PN}
