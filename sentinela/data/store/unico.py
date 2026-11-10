"""Banco único: migração verificada dos dois bancos atuais (F3-2c, E-14, D29, pacote §3).

`migrar` copia `analises`, `carteira_real` e `fundamentals_cache` de `sentinela_v6.db`
(`DatabaseManager`) e `analysis_runs` de `sentinela.db` (`AnalysisRepository`) para um
banco novo criado pelas migrações numeradas (`migracoes`), tabela por tabela, com os
mesmos nomes e colunas (R1). Antes de abrir um banco antigo, exige o backup do F3-2a
verificado (`conferir_backup`); depois da cópia, confere cada tabela linha a linha contra
a origem. Qualquer falha apaga o banco novo que esta chamada criou; os antigos ficam no
disco, sem escrita (saída no F3-9, pela lista do Marcos). Nada é sobrescrito.

`caminho_padrao` é o banco das classes sem caminho explícito: o banco único, com as
migrações pendentes aplicadas; sem ele e com um banco antigo no disco, recusa (não nasce
um banco vazio ao lado dos dados); sem nenhum, cria pelo esquema das migrações.

Linha de comando: `python -m sentinela.data.store.unico <diretório dos backups>
<relatório.json>`, no diretório dos bancos; usa a execução de backup mais recente sem
erros e grava o relatório (contagens e hashes: use `outputs/`, fora do git).
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path

from sentinela.data.store import backup, migracoes

BANCO_UNICO = "sentinela_store.db"
TABELAS = {
    "sentinela_v6.db": ("analises", "carteira_real", "fundamentals_cache"),
    "sentinela.db": ("analysis_runs",),
}
_EXECUCAO = re.compile(r"^(\d{8}T\d{12}Z)(?:-(\d+))?$")


class BackupNaoVerificado(ValueError):
    """Sem backup verificado do estado atual do banco antigo."""


class MigracaoDivergente(RuntimeError):
    """Tabela do banco novo diferente da origem depois da cópia."""


def pasta_de_backup_valida(diretorio: Path | str) -> Path:
    """Execução de backup mais recente, que precisa ter `backup.json` e não ter `erros.json`.

    A ordem é pelo carimbo e pelo número do sufixo (`-10` depois de `-2`). Execução mais
    recente com erro é recusada, sem cair para uma mais antiga.
    """
    candidatas = []
    for pasta in Path(diretorio).iterdir():
        casado = _EXECUCAO.match(pasta.name)
        if casado and pasta.is_dir():
            candidatas.append((casado.group(1), int(casado.group(2) or 1), pasta))
    if not candidatas:
        raise BackupNaoVerificado(f"nenhuma execução de backup em {diretorio}")
    pasta = max(candidatas)[2]
    if not (pasta / backup.RELATORIO).is_file() or (pasta / backup.ERROS).exists():
        raise BackupNaoVerificado(f"execução de backup mais recente com erro: {pasta}")
    return pasta


def conferir_backup(pasta: Path | str, origens: Mapping[str, Path | str]) -> None:
    """Cada banco antigo presente tem cópia verificada do estado atual; ausente, ausência."""
    pasta = Path(pasta)
    registros = json.loads((pasta / backup.RELATORIO).read_text(encoding="utf-8"))
    por_nome = {Path(r["origem"]).name: r for r in registros}
    for nome, caminho in origens.items():
        caminho = Path(caminho)
        registro = por_nome.get(nome)
        if not caminho.is_file():
            if registro is None or registro.get("ausente") is not True:
                raise BackupNaoVerificado(f"{nome}: ausência não registrada no backup")
            continue
        if registro is None or registro.get("ausente"):
            raise BackupNaoVerificado(f"{nome}: sem cópia no backup")
        if (
            registro.get("iguais") is not True
            or registro.get("restauracao_iguais") is not True
        ):
            raise BackupNaoVerificado(f"{nome}: cópia não verificada no backup")
        copia = pasta / nome
        if not copia.is_file() or backup._sha256(copia) != registro.get("sha256"):
            raise BackupNaoVerificado(f"{nome}: hash da cópia diferente do backup")
        if backup.contagens(caminho) != registro.get("contagens_antes"):
            raise BackupNaoVerificado(f"{nome}: contagens atuais diferentes do backup")
        if _conteudo(copia) != _conteudo(caminho):
            raise BackupNaoVerificado(
                f"{nome}: conteúdo atual diferente da cópia do backup"
            )


def _conteudo(caminho: Path) -> dict[str, list[tuple]]:
    """Todas as linhas de todas as tabelas (fora as internas `sqlite_%`), ordenadas."""
    with closing(sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)) as conn:
        tabelas = [
            linha[0]
            for linha in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\' ORDER BY name"
            )
        ]
        return {
            tabela: _linhas(
                conn,
                "main",
                backup._identificador(tabela),
                [
                    c[1]
                    for c in conn.execute(
                        f"PRAGMA table_info({backup._identificador(tabela)})"
                    )
                ],
            )
            for tabela in tabelas
        }


def _colunas(conn: sqlite3.Connection, tabela: str) -> list[str]:
    return [linha[1] for linha in conn.execute(f"PRAGMA main.table_info({tabela})")]


def _linhas(
    conn: sqlite3.Connection, esquema: str, tabela: str, colunas: list[str]
) -> list[tuple]:
    lista = ", ".join(backup._identificador(c) for c in colunas)
    return conn.execute(
        f"SELECT {lista} FROM {esquema}.{tabela} ORDER BY {lista}"
    ).fetchall()


def _sequencia(conn: sqlite3.Connection, tabela: str) -> None:
    """Mantém o contador do AUTOINCREMENT da origem: id apagado não é reaproveitado."""
    tem = conn.execute(
        "SELECT 1 FROM origem.sqlite_master WHERE name = 'sqlite_sequence'"
    ).fetchone()
    if tem is None:
        return
    origem = conn.execute(
        "SELECT seq FROM origem.sqlite_sequence WHERE name = ?", (tabela,)
    ).fetchone()
    if origem is None:
        return
    atual = conn.execute(
        "SELECT seq FROM main.sqlite_sequence WHERE name = ?", (tabela,)
    ).fetchone()
    if atual is None:
        conn.execute(
            "INSERT INTO main.sqlite_sequence (name, seq) VALUES (?, ?)",
            (tabela, origem[0]),
        )
    elif atual[0] < origem[0]:
        conn.execute(
            "UPDATE main.sqlite_sequence SET seq = ? WHERE name = ?",
            (origem[0], tabela),
        )


def _estrutura_igual(
    conn: sqlite3.Connection, caminho: Path, tabelas: tuple[str, ...]
) -> None:
    """Tabela ou coluna da origem fora do banco novo não some em silêncio."""
    da_origem = {
        linha[0]
        for linha in conn.execute(
            "SELECT name FROM origem.sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\'"
        )
    }
    if da_origem != set(tabelas):
        raise MigracaoDivergente(
            f"{caminho.name}: tabelas {sorted(da_origem)} diferentes de {sorted(tabelas)}"
        )
    for tabela in tabelas:
        colunas = [
            linha[1] for linha in conn.execute(f"PRAGMA origem.table_info({tabela})")
        ]
        if colunas != _colunas(conn, tabela):
            raise MigracaoDivergente(f"{caminho.name}: colunas de {tabela} diferentes")


def _copiar(conn: sqlite3.Connection, caminho: Path, tabelas: tuple[str, ...]) -> dict:
    conn.execute("ATTACH DATABASE ? AS origem", (str(caminho),))
    try:
        _estrutura_igual(conn, caminho, tabelas)
        conn.execute("BEGIN")
        try:
            for tabela in tabelas:
                lista = ", ".join(
                    backup._identificador(c) for c in _colunas(conn, tabela)
                )
                conn.execute(
                    f"INSERT INTO main.{tabela} ({lista}) SELECT {lista} FROM origem.{tabela}"
                )
                _sequencia(conn, tabela)
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        resultado = {}
        for tabela in tabelas:
            colunas = _colunas(conn, tabela)
            origem = _linhas(conn, "origem", tabela, colunas)
            if _linhas(conn, "main", tabela, colunas) != origem:
                raise MigracaoDivergente(
                    f"{caminho.name}: {tabela} diferente da origem"
                )
            texto = json.dumps(origem, ensure_ascii=False, default=repr)
            resultado[tabela] = {
                "linhas": len(origem),
                "sha256": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
            }
        return resultado
    finally:
        conn.execute("DETACH DATABASE origem")


def _apagar(destino: Path) -> None:
    for sufixo in ("", "-wal", "-shm", "-journal"):
        Path(f"{destino}{sufixo}").unlink(missing_ok=True)


def migrar(
    origens: Mapping[str, Path | str], destino: Path | str, pasta_backup: Path | str
) -> dict:
    """Migra os bancos antigos para `destino` (novo) e devolve linhas e hashes por tabela.

    O banco é montado em `<destino>.migrando` e só recebe o nome final depois de conferido:
    uma interrupção no meio não deixa um banco parcial no lugar do único.
    """
    destino = Path(destino)
    parcial = destino.with_name(destino.name + ".migrando")
    for caminho in (destino, parcial):
        if caminho.exists():
            raise FileExistsError(f"destino já existe: {caminho}")
    conferir_backup(pasta_backup, origens)
    try:
        with closing(sqlite3.connect(parcial)) as conn:
            migracoes.aplicar(conn)
            conn.isolation_level = None
            relatorio = {}
            for nome, tabelas in TABELAS.items():
                caminho = Path(origens[nome])
                if not caminho.is_file():
                    relatorio[nome] = {"ausente": True}
                    continue
                relatorio[nome] = _copiar(conn, caminho, tabelas)
        if destino.exists():
            raise FileExistsError(f"destino já existe: {destino}")
        parcial.rename(destino)
        return relatorio
    except BaseException:
        _apagar(parcial)
        raise


def caminho_padrao(diretorio: Path | str = ".") -> str:
    """Banco das classes sem caminho explícito (ver o docstring do módulo)."""
    base = Path(diretorio)
    unico = base / BANCO_UNICO
    if not unico.is_file():
        antigos = [nome for nome in TABELAS if (base / nome).is_file()]
        if antigos:
            raise RuntimeError(
                f"banco único {BANCO_UNICO} ausente com bancos antigos no disco "
                f"({', '.join(antigos)}): faça o backup e rode "
                "python -m sentinela.data.store.unico antes"
            )
    with closing(sqlite3.connect(unico)) as conn:
        migracoes.aplicar(conn)
    return str(unico)


def main(argv: list[str] | None = None) -> int:
    """Migra os bancos do diretório corrente; 1 se o backup ou a migração falharem."""
    argumentos = sys.argv[1:] if argv is None else argv
    if len(argumentos) != 2:
        print(
            "uso: python -m sentinela.data.store.unico <diretório dos backups> <relatório.json>"
        )
        return 2
    backups, saida = Path(argumentos[0]), Path(argumentos[1])
    if saida.exists():
        print(f"migração não feita: relatório já existe: {saida}")
        return 1
    try:
        pasta = pasta_de_backup_valida(backups)
        bancos = migrar({nome: Path(nome) for nome in TABELAS}, BANCO_UNICO, pasta)
        backup._gravar(
            saida,
            {
                "destino": BANCO_UNICO,
                "backup": str(pasta),
                "sem_perda": True,
                "bancos": bancos,
            },
        )
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as erro:
        print(f"migração não feita: {erro}")
        return 1
    print(f"banco único {BANCO_UNICO} criado; relatório em {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
