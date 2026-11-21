"""Resultados imutáveis por ticker, as_of, método e versão (F3-2d, decisão 16)."""

import ast
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from sentinela.data.store import migracoes, resultados

PROV = {"fonte": "teste", "hash": "0" * 64}


@pytest.fixture
def conn(tmp_path):
    with closing(sqlite3.connect(tmp_path / "unico.db")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _gravar(conn, **kw):
    base = {
        "ticker": "TSTA3",
        "as_of": date(2026, 6, 30),
        "metodo": "graham",
        "versao": "2.1.0",
        "execucao_id": "e1",
        "proveniencia": PROV,
    }
    base.update(kw)
    if "resultado" not in base and "motivo_abstencao" not in base:
        base["resultado"] = {"valor": 10.5}
    return resultados.gravar(conn, **base)


def test_recupera_duas_datas_duas_versoes_e_um_recalculo(conn):
    a = _gravar(conn, as_of=date(2026, 6, 30), execucao_id="e1")
    b = _gravar(
        conn, as_of=date(2026, 7, 31), execucao_id="e1", resultado={"valor": 11.0}
    )
    c = _gravar(conn, versao="2.2.0", execucao_id="e1", resultado={"valor": 9.0})
    d = _gravar(conn, execucao_id="e2", resultado={"valor": 10.75})
    assert [r.tipo for r in (a, b, c, d)] == [
        "original",
        "original",
        "original",
        "recalculo",
    ]
    junho = resultados.buscar(conn, "TSTA3", as_of=date(2026, 6, 30), versao="2.1.0")
    assert [(r.execucao_id, r.tipo, r.resultado) for r in junho] == [
        ("e1", "original", {"valor": 10.5}),
        ("e2", "recalculo", {"valor": 10.75}),
    ]
    assert [
        r.resultado for r in resultados.buscar(conn, "tsta3", as_of=date(2026, 7, 31))
    ] == [{"valor": 11.0}]
    assert [r.versao for r in resultados.buscar(conn, "TSTA3", versao="2.2.0")] == [
        "2.2.0"
    ]
    assert [r.id for r in resultados.buscar(conn, "TSTA3", tipo="original")] == [
        a.id,
        b.id,
        c.id,
    ]
    assert resultados.buscar(conn, "TSTA3", metodo="bazin") == []
    assert resultados.buscar(conn, "TSTA3") == [a, b, c, d]


def test_abstencao_com_motivo_e_gravada(conn):
    r = _gravar(conn, metodo="bazin", versao="2.0.0", motivo_abstencao="insumo ausente")
    (lido,) = resultados.buscar(conn, "TSTA3", metodo="bazin")
    assert lido == r
    assert (lido.resultado, lido.motivo_abstencao) == (None, "insumo ausente")
    assert lido.hash_resultado == resultados.hash_resultado(None, "insumo ausente")


def test_hash_e_proveniencia(conn):
    r = _gravar(conn, resultado={"b": 1, "a": "ação"})
    assert r.hash_resultado == resultados.hash_resultado({"a": "ação", "b": 1}, None)
    assert r.hash_resultado != resultados.hash_resultado({"a": "ação", "b": 2}, None)
    assert len(r.hash_resultado) == 64
    assert resultados.buscar(conn, "TSTA3")[0].proveniencia == PROV


_COLUNAS_INSERCAO = (
    " INTO resultados_analise (ticker, as_of, metodo, versao, execucao_id, tipo, "
    "resultado_json, hash_resultado, proveniencia_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _parametros_insercao(as_of, execucao, tipo):
    return ("TSTA3", as_of, "graham", "2.1.0", execucao, tipo, "{}", "x", "{}")


@pytest.mark.parametrize(
    ("sql", "parametros"),
    [
        ("UPDATE resultados_analise SET resultado_json = ?", ("{}",)),
        ("DELETE FROM resultados_analise", ()),
        (
            "INSERT OR REPLACE INTO resultados_analise SELECT * FROM resultados_analise",
            (),
        ),
        (
            "REPLACE" + _COLUNAS_INSERCAO,
            _parametros_insercao("2026-06-30", "e1", "recalculo"),
        ),
        (
            "INSERT" + _COLUNAS_INSERCAO,
            _parametros_insercao("2026-06-30", "e9", "original"),
        ),
        (
            "INSERT" + _COLUNAS_INSERCAO,
            _parametros_insercao("2026-01-01", "e9", "recalculo"),
        ),
    ],
)
def test_sobrescrever_ou_apagar_falha(conn, sql, parametros):
    _gravar(conn)
    antes = conn.execute("SELECT * FROM resultados_analise").fetchall()
    with pytest.raises(sqlite3.IntegrityError, match="resultados_analise"):
        conn.execute(sql, parametros)
    conn.rollback()
    assert conn.execute("SELECT * FROM resultados_analise").fetchall() == antes


def test_mesma_execucao_nao_grava_de_novo(conn):
    _gravar(conn)
    with pytest.raises(sqlite3.IntegrityError, match="só de inserção"):
        _gravar(conn, resultado={"valor": 99.0})
    assert [r.resultado for r in resultados.buscar(conn, "TSTA3")] == [{"valor": 10.5}]
    assert not conn.in_transaction


def test_modulo_so_insere_e_le():
    arvore = ast.parse(Path(resultados.__file__).read_text(encoding="utf-8"))
    textos = [
        n.value.upper()
        for n in ast.walk(arvore)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    assert not [t for t in textos if "UPDATE" in t or "DELETE" in t or "REPLACE" in t]
    assert any(t.startswith("INSERT INTO RESULTADOS_ANALISE") for t in textos)


@pytest.mark.parametrize(
    ("kw", "erro"),
    [
        ({"resultado": None, "motivo_abstencao": None}, ValueError),
        ({"resultado": {"v": 1}, "motivo_abstencao": "x"}, ValueError),
        ({"motivo_abstencao": " "}, ValueError),
        ({"resultado": [1]}, TypeError),
        ({"proveniencia": None}, TypeError),
        ({"ticker": ""}, ValueError),
        ({"metodo": None}, ValueError),
        ({"versao": ""}, ValueError),
        ({"execucao_id": ""}, ValueError),
        ({"as_of": datetime(2026, 6, 30, 12)}, ValueError),  # noqa: DTZ001
        ({"as_of": "2026-06-30"}, TypeError),
        ({"resultado": {"v": float("nan")}}, ValueError),
    ],
)
def test_entrada_invalida_nao_grava(conn, kw, erro):
    with pytest.raises(erro):
        _gravar(conn, **kw)
    assert conn.execute("SELECT COUNT(*) FROM resultados_analise").fetchone() == (0,)


def test_as_of_datetime_com_fuso(conn):
    r = _gravar(conn, as_of=datetime(2026, 6, 30, 18, tzinfo=UTC))
    assert r.as_of == "2026-06-30T18:00:00+00:00"
    assert resultados.buscar(
        conn, "TSTA3", as_of=datetime(2026, 6, 30, 18, tzinfo=UTC)
    ) == [r]


def test_conexao_com_transacao_aberta_e_recusada(conn):
    conn.execute("BEGIN")
    with pytest.raises(ValueError, match="transação aberta"):
        _gravar(conn)
    conn.rollback()


def test_nivel_de_isolamento_volta(conn):
    conn.isolation_level = "DEFERRED"
    _gravar(conn)
    assert conn.isolation_level == "DEFERRED"


def test_ticker_normalizado(conn):
    r = _gravar(conn, ticker=" tsta3 ")
    assert r.ticker == "TSTA3"
    assert resultados.buscar(conn, " tsta3") == [r]


def test_hash_confere_com_bytes_persistidos(conn):
    """O hash identifica o conteúdo gravado, sem depender do helper que o produz."""
    _gravar(conn, resultado={"b": 2, "a": "ação"})
    bruto, motivo, digest = conn.execute(
        "SELECT resultado_json, motivo_abstencao, hash_resultado FROM resultados_analise"
    ).fetchone()
    envelope = json.dumps(
        {"resultado": json.loads(bruto), "motivo_abstencao": motivo},
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    )
    assert digest == hashlib.sha256(envelope.encode("utf-8")).hexdigest()


def test_hash_independe_da_ordem_das_chaves():
    assert resultados.hash_resultado(
        {"b": 2, "a": 1}, None
    ) == resultados.hash_resultado({"a": 1, "b": 2}, None)


def test_resultado_persiste_em_outra_conexao(tmp_path):
    caminho = tmp_path / "persistente.db"
    with closing(sqlite3.connect(caminho)) as conn:
        migracoes.aplicar(conn)
        registro = _gravar(conn)
    with closing(sqlite3.connect(caminho)) as outra:
        assert resultados.buscar(outra, "TSTA3") == [registro]
