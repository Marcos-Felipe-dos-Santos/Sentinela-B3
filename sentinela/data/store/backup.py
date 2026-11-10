"""Cópia verificada e restauração dos bancos SQLite atuais (F3-2a, D29, pacote §3).

A cópia usa a API de backup do SQLite, que lê um instantâneo consistente, inclusive o que
ainda está no `-wal`. Cada cópia traz o SHA-256 do arquivo copiado e a contagem de linhas
por tabela antes (origem) e depois (cópia); a restauração copia de volta para um banco novo
e confere tabelas, índices e contagens. Banco ausente é registro de ausência: nada é
criado. Nenhum destino existente é sobrescrito.

Linha de comando: `python -m sentinela.data.store.backup <diretório> [bancos...]`, sem
bancos lê os dois atuais (`BANCOS`); grava as cópias e `backup.json` no diretório (use um
diretório em `outputs/`, fora do git: as contagens são da carteira real). A restauração de
teste é feita num diretório temporário. Erro num banco (destino existente, arquivo que não
é SQLite, falha de disco) entra no relatório, e os seguintes continuam.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path

# `database.py` (DatabaseManager) e `AnalysisRepository`, caminhos padrão.
BANCOS = ("sentinela_v6.db", "sentinela.db")
RELATORIO = "backup.json"


@dataclass(frozen=True)
class Ausente:
    origem: str


@dataclass(frozen=True)
class Copia:
    origem: str
    destino: str
    sha256: str
    contagens_antes: dict[str, int]
    contagens_depois: dict[str, int]

    @property
    def iguais(self) -> bool:
        return self.contagens_antes == self.contagens_depois


@dataclass(frozen=True)
class Conferencia:
    esquema_igual: bool
    contagens: dict[str, int]
    contagens_referencia: dict[str, int]

    @property
    def iguais(self) -> bool:
        return self.esquema_igual and self.contagens == self.contagens_referencia


def _identificador(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def _contar(conn: sqlite3.Connection) -> dict[str, int]:
    tabelas = [
        linha[0]
        for linha in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\' ORDER BY name"
        )
    ]
    # Nome de tabela não aceita `?`: vem do próprio sqlite_master, entre aspas escapadas.
    return {
        nome: conn.execute(f"SELECT COUNT(*) FROM {_identificador(nome)}").fetchone()[0]
        for nome in tabelas
    }


def contagens(caminho: Path | str) -> dict[str, int]:
    """Linhas por tabela do banco (tabelas internas `sqlite_%` de fora)."""
    with closing(sqlite3.connect(caminho)) as conn:
        return _contar(conn)


def _esquema(caminho: Path | str) -> list[tuple]:
    with closing(sqlite3.connect(caminho)) as conn:
        return conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite\\_%' ESCAPE '\\' ORDER BY type, name"
        ).fetchall()


def _sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _backup(origem: Path, destino: Path) -> dict[str, int]:
    """Copia e devolve as contagens da origem lidas na mesma transação de leitura.

    Falha no meio apaga o destino que esta chamada criou, para não bloquear outra cópia.
    """
    if destino.exists():
        raise FileExistsError(f"destino já existe: {destino}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        with (
            closing(sqlite3.connect(origem, isolation_level=None)) as fonte,
            closing(sqlite3.connect(destino)) as alvo,
        ):
            fonte.execute("BEGIN")
            antes = _contar(fonte)
            fonte.backup(alvo)
            fonte.execute("COMMIT")
    except BaseException:
        destino.unlink(missing_ok=True)
        raise
    return antes


def copiar(origem: Path | str, destino: Path | str) -> Copia | Ausente:
    """Cópia consistente de `origem` em `destino`, com hash e contagens antes e depois."""
    origem, destino = Path(origem), Path(destino)
    if not origem.is_file():
        return Ausente(str(origem))
    antes = _backup(origem, destino)
    return Copia(str(origem), str(destino), _sha256(destino), antes, contagens(destino))


def conferir(referencia: Path | str, restaurado: Path | str) -> Conferencia:
    """Mesmo esquema (tabelas e índices) e mesmas contagens de `referencia`."""
    return Conferencia(
        esquema_igual=_esquema(referencia) == _esquema(restaurado),
        contagens=contagens(restaurado),
        contagens_referencia=contagens(referencia),
    )


def restaurar(copia: Path | str, destino: Path | str) -> Conferencia:
    """Restaura a cópia num banco novo (`destino` não pode existir) e confere."""
    copia, destino = Path(copia), Path(destino)
    _backup(copia, destino)
    return conferir(copia, destino)


def main(argv: list[str] | None = None) -> int:
    """Copia e restaura em teste cada banco; 1 se alguma contagem ou esquema divergir."""
    argumentos = sys.argv[1:] if argv is None else argv
    if not argumentos:
        print("uso: python -m sentinela.data.store.backup <diretório> [bancos...]")
        return 2
    diretorio = Path(argumentos[0])
    relatorio, ok = [], True
    for banco in argumentos[1:] or BANCOS:
        origem = Path(banco)
        try:
            copia = copiar(origem, diretorio / origem.name)
            if isinstance(copia, Ausente):
                relatorio.append({"origem": copia.origem, "ausente": True})
                continue
            # Restauração de teste num banco temporário, apagado ao fim.
            with tempfile.TemporaryDirectory() as temporario:
                teste = restaurar(copia.destino, Path(temporario) / origem.name)
        except (OSError, sqlite3.Error) as erro:
            relatorio.append({"origem": str(origem), "erro": str(erro)})
            ok = False
            continue
        ok = ok and copia.iguais and teste.iguais
        relatorio.append(
            {
                **asdict(copia),
                "iguais": copia.iguais,
                "restauracao_iguais": teste.iguais,
            }
        )
    diretorio.mkdir(parents=True, exist_ok=True)
    (diretorio / RELATORIO).write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
