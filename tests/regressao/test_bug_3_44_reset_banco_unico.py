"""BUG-3-44: o reset legado não pode destruir o armazenamento único (Gemini D1)."""

import ast
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from database import DatabaseManager
from sentinela.data.store import migracoes, resultados


def test_reset_preserva_banco_unico_e_resultados_imutaveis(tmp_path):
    caminho = tmp_path / "sentinela_store.db"
    with closing(sqlite3.connect(caminho)) as conn:
        migracoes.aplicar(conn)
        resultados.gravar(
            conn,
            ticker="TSTA3",
            as_of=date(2025, 6, 30),
            metodo="Graham",
            versao="2.1.0",
            execucao_id="sintetica",
            proveniencia={"fonte": "fixture"},
            resultado={"valor": 12.0},
        )
    banco = DatabaseManager(caminho)
    banco.salvar_analise({"ticker": "TSTA3", "lentes": {}})
    banco.adicionar_posicao("TSTA3", 2, 10.0)
    with closing(sqlite3.connect(caminho)) as conn:
        antes = conn.execute("SELECT * FROM resultados_analise").fetchall()
        esquema = conn.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()
        posicoes = conn.execute("SELECT * FROM carteira_real").fetchall()
        analises = conn.execute("SELECT * FROM analises").fetchall()
    erro = None
    try:
        banco.reset_db()
    except RuntimeError as exc:
        erro = str(exc)
    assert caminho.is_file()
    with closing(sqlite3.connect(caminho)) as conn:
        assert conn.execute("SELECT * FROM resultados_analise").fetchall() == antes
        assert (
            conn.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()
            == esquema
        )
        assert conn.execute("SELECT * FROM carteira_real").fetchall() == posicoes
        assert conn.execute("SELECT * FROM analises").fetchall() == analises
    assert erro == "Reset destrutivo desativado: o banco único deve ser preservado."


def test_config_nao_oferece_reset_destrutivo():
    arvore = ast.parse(Path("app.py").read_text())
    configuracoes = [
        no
        for no in ast.walk(arvore)
        if isinstance(no, ast.If) and ast.unparse(no.test) == "modo == 'Config'"
    ]
    assert len(configuracoes) == 1
    botoes = []
    st = SimpleNamespace(
        title=lambda *_: None,
        write=lambda *_: None,
        subheader=lambda *_: None,
        info=lambda *_: None,
        session_state={},
        button=lambda texto, **_: botoes.append(texto) or False,
    )
    trecho = ast.Module(body=configuracoes[0].body, type_ignores=[])
    exec(compile(trecho, "app.py", "exec"), {"st": st})  # noqa: S102
    assert not any("RESET" in b.upper() or "APAGAR" in b.upper() for b in botoes)
