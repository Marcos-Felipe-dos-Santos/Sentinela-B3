"""Migrações numeradas do banco SQLite, com `schema_version` (F3-2b, E-14, PLANO §5).

Cada migração é um arquivo `NNN_descricao.sql` em `migrations/` (três dígitos, descrição em
minúsculas, dígitos e `_`), numerado de 001 em diante, sem lacuna nem repetição. O
executor aplica em ordem as que ainda não estão em `schema_version`, cada uma numa
transação própria com o seu registro: migração que falha não deixa versão nem efeito
parcial. Uma migração já aplicada cujo arquivo mudou (SHA-256 diferente) é recusada. Sem
ORM; o SQL das migrações é estrutura, sem valor vindo de fora.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path

DIRETORIO = Path(__file__).parent / "migrations"
_NOME = re.compile(r"^(\d{3})_[a-z0-9]+(?:_[a-z0-9]+)*\.sql$")
_SCHEMA_VERSION = (
    "CREATE TABLE IF NOT EXISTS schema_version ("
    "versao INTEGER PRIMARY KEY, nome TEXT NOT NULL, sha256 TEXT NOT NULL)"
)


def listar(diretorio: Path = DIRETORIO) -> list[tuple[int, Path]]:
    """Migrações do diretório em ordem; `ValueError` para nome fora do padrão ou sequência."""
    migracoes = []
    for arquivo in Path(diretorio).iterdir():
        casado = _NOME.match(arquivo.name)
        if casado is None:
            raise ValueError(
                f"nome de migração fora do padrão NNN_descricao.sql: {arquivo.name}"
            )
        migracoes.append((int(casado.group(1)), arquivo))
    migracoes.sort()
    numeros = [numero for numero, _ in migracoes]
    if numeros != list(range(1, len(numeros) + 1)):
        raise ValueError(f"migrações fora da sequência 001, 002, …: {numeros}")
    return migracoes


def comandos(sql: str) -> list[str]:
    """Comandos completos do arquivo, divididos pelo próprio analisador do SQLite."""
    resultado, atual = [], ""
    for linha in sql.splitlines(keepends=True):
        atual += linha
        if sqlite3.complete_statement(atual):
            resultado.append(atual.strip())
            atual = ""
    resto = "\n".join(
        linha for linha in atual.splitlines() if not linha.strip().startswith("--")
    )
    if resto.strip():
        raise ValueError(f"comando incompleto no fim da migração: {resto.strip()[:60]}")
    return resultado


def aplicar(conn: sqlite3.Connection, diretorio: Path = DIRETORIO) -> list[int]:
    """Aplica as migrações pendentes e devolve os números aplicados agora."""
    if conn.in_transaction:
        raise ValueError(
            "conexão com transação aberta: as migrações precisam da própria"
        )
    nivel = conn.isolation_level
    conn.isolation_level = None
    try:
        conn.execute(_SCHEMA_VERSION)
        aplicadas = dict(conn.execute("SELECT versao, sha256 FROM schema_version"))
        novas = []
        for numero, arquivo in listar(diretorio):
            texto = arquivo.read_text(encoding="utf-8")
            digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
            if numero in aplicadas:
                if aplicadas[numero] != digest:
                    raise ValueError(
                        f"migração já aplicada foi alterada: {arquivo.name}"
                    )
                continue
            lista = comandos(texto)
            conn.execute("BEGIN")
            try:
                for comando in lista:
                    conn.execute(comando)
                conn.execute(
                    "INSERT INTO schema_version (versao, nome, sha256) VALUES (?, ?, ?)",
                    (numero, arquivo.name, digest),
                )
                conn.execute("COMMIT")
            except BaseException:
                if (
                    conn.in_transaction
                ):  # o SQLite pode já ter desfeito (disco cheio, E/S)
                    conn.execute("ROLLBACK")
                raise
            novas.append(numero)
        return novas
    finally:
        conn.isolation_level = nivel
