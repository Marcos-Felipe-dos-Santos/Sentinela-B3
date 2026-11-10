"""BUG-3-10: rodar o backup de novo no mesmo diretório apaga o manifesto válido.

A linha de comando recusa destino existente, mas grava `backup.json` sem condição: a
segunda execução troca o relatório verificado (hashes e contagens) por um só com o erro.
Pendência do F3-2a; decisão 34 do Marcos (10/11/2026): cada execução em pasta própria com
carimbo, sem sobrescrever `backup.json` válido. Auditoria FASE do Codex; destino F3-2a-fix.
"""

import sqlite3
from contextlib import closing

from sentinela.data.store import backup


def _banco(caminho):
    with closing(sqlite3.connect(caminho)) as conn:
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()


def _arquivos(diretorio):
    return {
        p.relative_to(diretorio): p.read_bytes()
        for p in diretorio.rglob("*")
        if p.is_file()
    }


def test_segunda_execucao_preserva_manifesto_e_copias(tmp_path):
    banco = tmp_path / "origem.db"
    _banco(banco)
    saida = tmp_path / "saida"
    assert backup.main([str(saida), str(banco)]) == 0
    antes = _arquivos(saida)
    assert any(p.name == backup.RELATORIO for p in antes)
    backup.main([str(saida), str(banco)])
    depois = _arquivos(saida)
    assert {p: depois.get(p) for p in antes} == antes
