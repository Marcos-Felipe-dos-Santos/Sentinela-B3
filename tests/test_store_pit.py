"""F3-3a: tabelas ponto-no-tempo das demonstrações (migração 004, PLANO §5).

`entregas` (data de entrega por documento e versão), `demonstracoes` (contas com escala) e
`composicao_capital` (ações por documento), com proveniência por linha, só de inserção e
aplicadas sobre o banco do F3-2c sem perda.
"""

import shutil
import sqlite3
from contextlib import closing

import pytest

from sentinela.data.store import migracoes

CHAVES = {
    "entregas": ["cnpj", "documento", "dt_refer", "versao"],
    "demonstracoes": [
        "cnpj", "documento", "dt_refer", "versao", "demonstracao", "ordem_exerc",
        "dt_ini_exerc", "dt_fim_exerc", "coluna_df", "conta",
    ],
    "composicao_capital": ["cnpj", "documento", "dt_refer", "versao"],
}  # fmt: skip
CNPJ = "00.000.000/0001-91"
PROVENIENCIA = ("cvm", "2026-11-11T00:00:00+00:00", "h")


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _chave(conn, tabela):
    colunas = conn.execute(f'PRAGMA table_info("{tabela}")').fetchall()
    return [c[1] for c in sorted((c for c in colunas if c[5]), key=lambda c: c[5])]


def _colunas(conn, tabela):
    return {c[1] for c in conn.execute(f'PRAGMA table_info("{tabela}")')}


def _contar(conn, tabela):
    return conn.execute(f'SELECT COUNT(*) FROM "{tabela}"').fetchone()[0]


def _entrega(conn, versao=1, documento="DFP", dt_receb="2024-03-01", na_fonte=1):
    conn.execute(
        "INSERT INTO entregas (cnpj, documento, dt_refer, versao, dt_receb, valores_na_fonte, "
        "fonte, coleta, hash_sha256) VALUES (?, ?, '2023-12-31', ?, ?, ?, ?, ?, ?)",
        (CNPJ, documento, versao, dt_receb, na_fonte, *PROVENIENCIA),
    )


def _conta(conn, versao=1, demonstracao="DRE_con", ordem="ÚLTIMO", conta="3.11", **kw):
    conn.execute(
        "INSERT INTO demonstracoes (cnpj, documento, dt_refer, versao, demonstracao, "
        "ordem_exerc, dt_ini_exerc, dt_fim_exerc, coluna_df, conta, valor, escala, fonte, "
        "coleta, hash_sha256) VALUES (?, ?, '2023-12-31', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            CNPJ,
            kw.get("documento", "DFP"),
            versao,
            demonstracao,
            ordem,
            kw.get("inicio", "2023-01-01"),
            kw.get("fim", "2023-12-31"),
            kw.get("coluna", ""),
            conta,
            kw.get("valor", -2.0),
            kw.get("escala", "MIL"),
            *PROVENIENCIA,
        ),
    )


def _composicao(conn, versao=1, documento="DFP"):
    conn.execute(
        "INSERT INTO composicao_capital (cnpj, documento, dt_refer, versao, acoes_ordinarias, "
        "fonte, coleta, hash_sha256) VALUES (?, ?, '2023-12-31', ?, 1000, ?, ?, ?)",
        (CNPJ, documento, versao, *PROVENIENCIA),
    )


def test_tabelas_com_as_chaves_e_a_proveniencia(conn):
    for tabela, chave in CHAVES.items():
        assert _chave(conn, tabela) == chave
    proveniencia = {"fonte", "coleta", "hash_sha256"}
    assert {"escala", "valor", "descricao", "moeda"} | proveniencia <= _colunas(
        conn, "demonstracoes"
    )
    assert {"dt_receb", "valores_na_fonte"} | proveniencia <= _colunas(conn, "entregas")
    composicao = _colunas(conn, "composicao_capital")
    assert {
        "acoes_ordinarias",
        "acoes_preferenciais",
        "tesouraria_total",
    } | proveniencia <= composicao
    assert (
        "escala_inferida" not in composicao
    )  # valor derivado: inferido na leitura (F3-3c)


def test_mesma_conta_no_consolidado_no_individual_e_nos_dois_exercicios(conn):
    _conta(conn)
    _conta(conn, demonstracao="DRE_ind")
    _conta(conn, ordem="PENÚLTIMO", inicio="2022-01-01", fim="2022-12-31")
    assert _contar(conn, "demonstracoes") == 3


def test_itr_trimestre_isolado_e_acumulado_da_mesma_conta(conn):
    """ITR do 2º trimestre: a DRE traz o trimestre e o acumulado como ÚLTIMO (DT_INI difere)."""
    _conta(conn, inicio="2023-04-01", fim="2023-06-30")
    _conta(conn, inicio="2023-01-01", fim="2023-06-30", valor=-5.0)
    _conta(conn, ordem="PENÚLTIMO", inicio="2022-04-01", fim="2022-06-30")
    _conta(conn, ordem="PENÚLTIMO", inicio="2022-01-01", fim="2022-06-30")
    assert _contar(conn, "demonstracoes") == 4


def test_gatilho_separa_ordem_e_fim_do_exercicio(conn):
    """A mesma conta com outra ordem, ou com outro fim, não é sobrescrita: é outra linha."""
    _conta(conn, ordem="ÚLTIMO", fim="2023-12-31")
    _conta(conn, ordem="PENÚLTIMO", fim="2023-12-31")
    _conta(conn, ordem="ÚLTIMO", fim="2023-06-30")
    assert _contar(conn, "demonstracoes") == 3


def test_gatilho_separa_a_conta(conn):
    _conta(conn, conta="3.11")
    _conta(conn, conta="3.01")
    assert _contar(conn, "demonstracoes") == 2


def test_balanco_sem_inicio_e_dmpl_por_coluna(conn):
    _conta(conn, demonstracao="BPA_con", conta="1", inicio="")
    _conta(
        conn,
        demonstracao="DMPL_con",
        conta="5.04",
        coluna="Capital Social Integralizado",
    )
    _conta(
        conn,
        demonstracao="DMPL_con",
        conta="5.04",
        coluna="Lucros ou Prejuízos Acumulados",
    )
    assert _contar(conn, "demonstracoes") == 3
    inicio = conn.execute(
        "SELECT dt_ini_exerc FROM demonstracoes WHERE demonstracao = 'BPA_con'"
    ).fetchone()
    assert inicio == ("",)


def test_composicao_de_dfp_e_itr_com_a_mesma_data(conn):
    _composicao(conn, documento="DFP")
    _composicao(conn, documento="ITR")
    assert _contar(conn, "composicao_capital") == 2


def test_versao_nova_entra_como_linha_nova(conn):
    _entrega(conn, na_fonte=0)
    _entrega(conn, versao=2, dt_receb="2024-06-30")
    _conta(conn)
    _conta(conn, versao=2, valor=-3.0)
    _composicao(conn)
    _composicao(conn, versao=2)
    linhas = conn.execute(
        "SELECT versao, dt_receb, valores_na_fonte FROM entregas ORDER BY versao"
    ).fetchall()
    assert linhas == [(1, "2024-03-01", 0), (2, "2024-06-30", 1)]
    contas = conn.execute(
        "SELECT versao, valor FROM demonstracoes ORDER BY versao"
    ).fetchall()
    assert contas == [(1, -2.0), (2, -3.0)]
    versoes = conn.execute(
        "SELECT versao FROM composicao_capital ORDER BY versao"
    ).fetchall()
    assert versoes == [(1,), (2,)]


@pytest.mark.parametrize(
    ("tabela", "inserir"),
    [
        ("entregas", _entrega),
        ("demonstracoes", _conta),
        ("composicao_capital", _composicao),
    ],
)
def test_so_insercao(conn, tabela, inserir):
    inserir(conn)
    antes = conn.execute(f'SELECT * FROM "{tabela}"').fetchall()
    for sql in (f'UPDATE "{tabela}" SET versao = 9', f'DELETE FROM "{tabela}"'):
        with pytest.raises(sqlite3.IntegrityError, match=f"{tabela} é só de inserção"):
            conn.execute(sql)
    with pytest.raises(sqlite3.IntegrityError, match=f"{tabela} é só de inserção"):
        inserir(conn)  # a mesma chave de novo
    assert conn.execute(f'SELECT * FROM "{tabela}"').fetchall() == antes


@pytest.mark.parametrize(
    "inserir",
    [
        lambda c: _entrega(c, documento="FRE"),
        lambda c: _conta(c, documento="FRE"),
        lambda c: _composicao(c, documento="FRE"),
        lambda c: _conta(c, ordem="ANTERIOR"),
        lambda c: _conta(c, escala="MILHAO"),
        lambda c: _conta(c, inicio=None),
        lambda c: _entrega(c, na_fonte=2),
    ],
)
def test_dominios_recusados(conn, inserir):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK|NOT NULL"):
        inserir(conn)


def test_aplicada_sobre_o_banco_do_f3_2c_sem_perda(tmp_path):
    """Banco com as migrações 001 a 003 e dados: a 004 não muda nenhuma tabela existente."""
    ate_003, ate_004 = tmp_path / "ate_003", tmp_path / "ate_004"
    ate_003.mkdir()
    ate_004.mkdir()
    for _, arquivo in migracoes.listar():
        if arquivo.name < "004":
            shutil.copy(arquivo, ate_003 / arquivo.name)
        if arquivo.name < "005":
            shutil.copy(arquivo, ate_004 / arquivo.name)
    banco = tmp_path / "f3_2c.db"
    with closing(sqlite3.connect(banco)) as c:
        assert migracoes.aplicar(c, ate_003) == [1, 2, 3]
        c.execute("INSERT INTO carteira_real VALUES ('TST3', 10, 9.5, '2026-01-02')")
        c.execute(
            "INSERT INTO analises (ticker, data_analise) VALUES ('TST3', '2026-01-02')"
        )
        c.execute(
            "INSERT INTO series_macro VALUES ('sgs_432', '2026-01-02', 15.0, NULL, '{}', 'f', "
            "'2026-01-03T00:00:00+00:00', 'h')"
        )
        c.commit()
        tabelas = [
            n for (n,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        antes = {
            t: c.execute(f'SELECT * FROM "{t}"').fetchall()
            for t in tabelas
            if t != "schema_version"
        }
    with closing(sqlite3.connect(banco)) as c:
        assert migracoes.aplicar(c, ate_004) == [4]
        depois = {t: c.execute(f'SELECT * FROM "{t}"').fetchall() for t in antes}
        versoes = [
            v for (v,) in c.execute("SELECT versao FROM schema_version ORDER BY versao")
        ]
    assert depois == antes
    assert versoes == [1, 2, 3, 4]
