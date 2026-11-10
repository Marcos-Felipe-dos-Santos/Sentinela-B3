"""BUG-3-09: restaurar uma cópia que não existe certifica um banco vazio como válido.

`restaurar` chama `_backup` sem conferir a cópia; `sqlite3.connect` cria o arquivo da cópia
ausente, a restauração copia um banco vazio, e `conferir` vê esquema e contagens vazios
iguais. Auditoria FASE do Codex, 10/11/2026; destino F3-2a-fix.
"""

import pytest

from sentinela.data.store import backup


def test_restaurar_copia_ausente_recusa_sem_criar_arquivo(tmp_path):
    copia = tmp_path / "nao_existe.db"
    destino = tmp_path / "restaurado.db"
    with pytest.raises(FileNotFoundError):
        backup.restaurar(copia, destino)
    assert not copia.exists()
    assert not destino.exists()
