"""Migrações numeradas do banco SQLite com `schema_version` (F3-2b, E-14, PLANO §5)."""

import sqlite3
from contextlib import closing

import pytest

from database import DatabaseManager
from sentinela.data.store import migracoes
from sentinela.repositories.analysis_repository import AnalysisRepository


def _aplicar(caminho, diretorio=None):
    with closing(sqlite3.connect(caminho)) as conn:
        if diretorio is None:
            return migracoes.aplicar(conn)
        return migracoes.aplicar(conn, diretorio)


def _versoes(caminho):
    with closing(sqlite3.connect(caminho)) as conn:
        return conn.execute(
            "SELECT versao, nome FROM schema_version ORDER BY versao"
        ).fetchall()


def _estrutura(caminho, tabelas):
    """Nomes do sqlite_master e PRAGMA de cada tabela e índice, sem a `schema_version`."""
    with closing(sqlite3.connect(caminho)) as conn:
        objetos = sorted(
            (tipo, nome, tabela)
            for tipo, nome, tabela in conn.execute(
                "SELECT type, name, tbl_name FROM sqlite_master WHERE tbl_name IN "
                f"({','.join('?' * len(tabelas))})",
                tabelas,
            )
        )
        colunas = {
            t: conn.execute(f"PRAGMA table_info({t})").fetchall() for t in tabelas
        }
        indices = {
            t: sorted(
                (
                    nome,
                    unico,
                    origem,
                    conn.execute(f"PRAGMA index_info({nome})").fetchall(),
                )
                for _, nome, unico, origem, _ in conn.execute(f"PRAGMA index_list({t})")
            )
            for t in tabelas
        }
    return objetos, colunas, indices


V6 = ["analises", "carteira_real", "fundamentals_cache"]
REPOSITORIO = ["analysis_runs"]


def _diretorio(tmp_path, arquivos):
    pasta = tmp_path / "migrations"
    pasta.mkdir()
    for nome, sql in arquivos.items():
        (pasta / nome).write_text(sql, encoding="utf-8")
    return pasta


def test_001_reproduz_as_tabelas_do_banco_v6(tmp_path):
    DatabaseManager(db_path=str(tmp_path / "v6.db"))
    _aplicar(tmp_path / "novo.db")
    assert _estrutura(tmp_path / "novo.db", V6) == _estrutura(tmp_path / "v6.db", V6)


def test_001_reproduz_as_tabelas_do_repositorio(tmp_path):
    AnalysisRepository(db_path=str(tmp_path / "s.db"))
    _aplicar(tmp_path / "novo.db")
    estrutura = _estrutura(tmp_path / "novo.db", REPOSITORIO)
    assert estrutura == _estrutura(tmp_path / "s.db", REPOSITORIO)
    assert {nome for _, nome, _ in estrutura[0]} == {
        "analysis_runs",
        "idx_analysis_runs_ticker",
        "idx_analysis_runs_created_at",
        "idx_analysis_runs_ticker_created_at",
    }


def test_001_cria_so_as_tabelas_dos_dois_bancos(tmp_path):
    _aplicar(tmp_path / "novo.db")
    with closing(sqlite3.connect(tmp_path / "novo.db")) as conn:
        tabelas = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert tabelas == {*V6, *REPOSITORIO, "schema_version"}


def test_registra_versao_e_e_idempotente(tmp_path):
    banco = tmp_path / "novo.db"
    assert _aplicar(banco) == [1]
    assert _aplicar(banco) == []
    assert _versoes(banco) == [(1, "001_esquema_inicial.sql")]


def test_aplica_em_ordem_numerica(tmp_path):
    pasta = _diretorio(
        tmp_path,
        {
            "002_segunda.sql": "INSERT INTO t VALUES (2);",
            "001_primeira.sql": "CREATE TABLE t (x INTEGER);",
            "010_decima.sql": "INSERT INTO t VALUES (10);",
            "003_terceira.sql": "INSERT INTO t VALUES (3);",
        },
    )
    with pytest.raises(ValueError, match="sequência"):
        _aplicar(tmp_path / "b.db", pasta)
    (pasta / "010_decima.sql").rename(pasta / "004_quarta.sql")
    assert _aplicar(tmp_path / "b.db", pasta) == [1, 2, 3, 4]
    with closing(sqlite3.connect(tmp_path / "b.db")) as conn:
        assert [r[0] for r in conn.execute("SELECT x FROM t ORDER BY rowid")] == [
            2,
            3,
            10,
        ]


def test_so_aplica_as_novas(tmp_path):
    pasta = _diretorio(tmp_path, {"001_a.sql": "CREATE TABLE t (x INTEGER);"})
    banco = tmp_path / "b.db"
    assert _aplicar(banco, pasta) == [1]
    (pasta / "002_b.sql").write_text("INSERT INTO t VALUES (1);")
    assert _aplicar(banco, pasta) == [2]
    assert _aplicar(banco, pasta) == []
    with closing(sqlite3.connect(banco)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1


def test_migracao_que_falha_nao_deixa_versao_parcial(tmp_path):
    pasta = _diretorio(
        tmp_path,
        {
            "001_a.sql": "CREATE TABLE t (x INTEGER);",
            "002_b.sql": "CREATE TABLE u (y INTEGER);\nINSERT INTO t VALUES (1);\nINSERT INTO nao_existe VALUES (1);",
        },
    )
    banco = tmp_path / "b.db"
    with pytest.raises(sqlite3.OperationalError, match="nao_existe"):
        _aplicar(banco, pasta)
    assert _versoes(banco) == [(1, "001_a.sql")]
    with closing(sqlite3.connect(banco)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0
        nomes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert "u" not in nomes


def test_migracao_alterada_depois_de_aplicada_e_recusada(tmp_path):
    pasta = _diretorio(tmp_path, {"001_a.sql": "CREATE TABLE t (x INTEGER);"})
    banco = tmp_path / "b.db"
    _aplicar(banco, pasta)
    (pasta / "001_a.sql").write_text("CREATE TABLE t (x TEXT);")
    with pytest.raises(ValueError, match="001_a.sql"):
        _aplicar(banco, pasta)


@pytest.mark.parametrize(
    "nome", ["1_a.sql", "001-a.sql", "001_a.txt", "001_A.sql", "001_.sql", "0001_a.sql"]
)
def test_nome_fora_do_padrao_e_recusado(tmp_path, nome):
    pasta = _diretorio(tmp_path, {nome: "SELECT 1;"})
    with pytest.raises(ValueError, match="nome"):
        migracoes.listar(pasta)


def test_numero_repetido_e_recusado(tmp_path):
    pasta = _diretorio(tmp_path, {"001_a.sql": "SELECT 1;", "001_b.sql": "SELECT 1;"})
    with pytest.raises(ValueError, match="sequência"):
        migracoes.listar(pasta)


def test_divide_comandos_sem_quebrar_texto_com_ponto_e_virgula(tmp_path):
    pasta = _diretorio(
        tmp_path,
        {
            "001_a.sql": "CREATE TABLE t (x TEXT);\n-- comentário; sem efeito\n"
            "INSERT INTO t VALUES ('a;b');\nINSERT INTO t VALUES ('c');\n"
        },
    )
    _aplicar(tmp_path / "b.db", pasta)
    with closing(sqlite3.connect(tmp_path / "b.db")) as conn:
        assert [r[0] for r in conn.execute("SELECT x FROM t ORDER BY rowid")] == [
            "a;b",
            "c",
        ]


def test_comando_incompleto_no_fim_e_recusado(tmp_path):
    pasta = _diretorio(
        tmp_path, {"001_a.sql": "CREATE TABLE t (x TEXT);\nINSERT INTO t VALUES (1)"}
    )
    with pytest.raises(ValueError, match="incompleto"):
        _aplicar(tmp_path / "b.db", pasta)
    assert _versoes_ou_vazio(tmp_path / "b.db") == []


def _versoes_ou_vazio(caminho):
    with closing(sqlite3.connect(caminho)) as conn:
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'schema_version'"
        ).fetchone()
        return (
            conn.execute("SELECT versao FROM schema_version").fetchall()
            if existe
            else []
        )


def test_conexao_com_transacao_aberta_e_recusada(tmp_path):
    with closing(sqlite3.connect(tmp_path / "b.db")) as conn:
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        assert conn.in_transaction
        with pytest.raises(ValueError, match="transação"):
            migracoes.aplicar(conn)


def test_vocabulario_novo_nao_usa_termos_legados():
    texto = (migracoes.DIRETORIO / "001_esquema_inicial.sql").read_text(
        encoding="utf-8"
    )
    sql = "\n".join(
        linha for linha in texto.splitlines() if not linha.lstrip().startswith("--")
    )
    assert sql.lower().count("recomendacao") == 1  # coluna legada de `analises` (R1)
    assert (
        sql.lower().count("recommendation") == 1
    )  # coluna legada de `analysis_runs` (R1)
    assert "schema_version" not in sql  # criada pelo executor


def test_comentario_e_linhas_vazias_no_fim_sao_aceitos(tmp_path):
    pasta = _diretorio(
        tmp_path, {"001_a.sql": "CREATE TABLE t (x INTEGER);\n-- fim; nada aqui\n\n\n"}
    )
    assert _aplicar(tmp_path / "b.db", pasta) == [1]


@pytest.mark.parametrize("nivel", ["", "DEFERRED", "IMMEDIATE", None])
def test_nivel_de_isolamento_da_conexao_volta_ao_original(tmp_path, nivel):
    with closing(sqlite3.connect(tmp_path / "b.db", isolation_level=nivel)) as conn:
        migracoes.aplicar(conn)
        assert conn.isolation_level == nivel


def _sql_normalizado(caminho, tabelas):
    with closing(sqlite3.connect(caminho)) as conn:
        return sorted(
            (nome, " ".join(sql.replace("(", " ( ").replace(")", " ) ").split()))
            for nome, sql in conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL AND tbl_name IN "
                f"({','.join('?' * len(tabelas))})",
                tabelas,
            )
        )


@pytest.mark.parametrize(
    ("fabrica", "tabelas"),
    [(DatabaseManager, V6), (AnalysisRepository, REPOSITORIO)],
)
def test_001_tem_o_mesmo_sql_da_origem(tmp_path, fabrica, tabelas):
    """Pega o que os PRAGMAs não mostram, como o AUTOINCREMENT de `analysis_runs`."""
    fabrica(db_path=str(tmp_path / "origem.db"))
    _aplicar(tmp_path / "novo.db")
    origem = _sql_normalizado(tmp_path / "origem.db", tabelas)
    novo = _sql_normalizado(tmp_path / "novo.db", tabelas)
    assert [(nome, sql.replace("IF NOT EXISTS ", "")) for nome, sql in origem] == novo


def test_ids_de_analysis_runs_nao_sao_reaproveitados(tmp_path):
    banco = tmp_path / "novo.db"
    _aplicar(banco)
    with closing(sqlite3.connect(banco)) as conn:
        inserir = "INSERT INTO analysis_runs (ticker, created_at, payload_json) VALUES (?, ?, ?)"
        conn.execute(inserir, ("TST3", "2026-11-10", "{}"))
        conn.execute(inserir, ("TST4", "2026-11-10", "{}"))
        conn.execute("DELETE FROM analysis_runs WHERE id = 2")
        conn.execute(inserir, ("TST5", "2026-11-10", "{}"))
        assert conn.execute("SELECT MAX(id) FROM analysis_runs").fetchone()[0] == 3
