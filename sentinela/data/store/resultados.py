"""Resultados imutáveis da análise por ticker, as_of, método e versão (F3-2d, decisão 16).

Tabela `resultados_analise` (migração `002`), só de inserção: cada chamada de `gravar`
acrescenta uma linha com ticker, as_of, método, versão, `execucao_id`, tipo (`original` na
primeira execução de ticker/as_of/método/versão, `recalculo` nas seguintes), o resultado
ou a abstenção com motivo, o SHA-256 do resultado e a proveniência. Nada é alterado nem
apagado: os gatilhos da migração recusam alteração, remoção e a inserção que
sobrescreveria uma linha; este módulo só insere e lê. Sem relógio: o `as_of` e a `execucao_id` vêm de quem grava. O legado
(`analises` do `database.py` e `analysis_runs`) segue como está até o F3-9.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

ORIGINAL = "original"
RECALCULO = "recalculo"


@dataclass(frozen=True)
class Registro:
    id: int
    ticker: str
    as_of: str
    metodo: str
    versao: str
    execucao_id: str
    tipo: str
    resultado: dict | None
    motivo_abstencao: str | None
    hash_resultado: str
    proveniencia: dict


def _texto_as_of(as_of: date | datetime) -> str:
    if isinstance(as_of, datetime):
        if as_of.utcoffset() is None:
            raise ValueError("as_of datetime exige fuso horário")
        return as_of.isoformat()
    if isinstance(as_of, date):
        return as_of.isoformat()
    raise TypeError("as_of é date ou datetime com fuso")


def _json(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _obrigatorio(nome: str, valor: object) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{nome} é texto não vazio")
    return valor


def hash_resultado(resultado: Mapping | None, motivo_abstencao: str | None) -> str:
    """SHA-256 do JSON canônico do resultado ou da abstenção."""
    texto = _json({"resultado": resultado, "motivo_abstencao": motivo_abstencao})
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def gravar(
    conn: sqlite3.Connection,
    *,
    ticker: str,
    as_of: date | datetime,
    metodo: str,
    versao: str,
    execucao_id: str,
    proveniencia: Mapping,
    resultado: Mapping | None = None,
    motivo_abstencao: str | None = None,
) -> Registro:
    """Acrescenta o resultado (ou a abstenção com motivo) e devolve o registro gravado."""
    if (resultado is None) == (motivo_abstencao is None):
        raise ValueError("grave o resultado ou a abstenção com motivo, um dos dois")
    if motivo_abstencao is not None:
        _obrigatorio("motivo_abstencao", motivo_abstencao)
    if resultado is not None and not isinstance(resultado, Mapping):
        raise TypeError("resultado é um mapeamento")
    if not isinstance(proveniencia, Mapping):
        raise TypeError("proveniência é um mapeamento")
    campos = {
        "ticker": _obrigatorio("ticker", ticker).strip().upper(),
        "as_of": _texto_as_of(as_of),
        "metodo": _obrigatorio("metodo", metodo),
        "versao": _obrigatorio("versao", versao),
        "execucao_id": _obrigatorio("execucao_id", execucao_id),
    }
    resultado_json = None if resultado is None else _json(dict(resultado))
    proveniencia_json = _json(dict(proveniencia))
    digest = hash_resultado(
        None if resultado is None else json.loads(resultado_json), motivo_abstencao
    )
    if conn.in_transaction:
        raise ValueError("conexão com transação aberta: a gravação precisa da própria")
    nivel = conn.isolation_level
    conn.isolation_level = None
    try:
        # IMMEDIATE: o tipo é decidido e gravado sob o mesmo bloqueio de escrita.
        conn.execute("BEGIN IMMEDIATE")
        try:
            existe = conn.execute(
                "SELECT 1 FROM resultados_analise WHERE ticker = ? AND as_of = ? "
                "AND metodo = ? AND versao = ? AND tipo = ?",
                (
                    campos["ticker"],
                    campos["as_of"],
                    campos["metodo"],
                    campos["versao"],
                    ORIGINAL,
                ),
            ).fetchone()
            tipo = RECALCULO if existe else ORIGINAL
            cursor = conn.execute(
                "INSERT INTO resultados_analise (ticker, as_of, metodo, versao, "
                "execucao_id, tipo, resultado_json, motivo_abstencao, hash_resultado, "
                "proveniencia_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    campos["ticker"],
                    campos["as_of"],
                    campos["metodo"],
                    campos["versao"],
                    campos["execucao_id"],
                    tipo,
                    resultado_json,
                    motivo_abstencao,
                    digest,
                    proveniencia_json,
                ),
            )
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.isolation_level = nivel
    return Registro(
        id=cursor.lastrowid,
        tipo=tipo,
        resultado=None if resultado_json is None else json.loads(resultado_json),
        motivo_abstencao=motivo_abstencao,
        hash_resultado=digest,
        proveniencia=json.loads(proveniencia_json),
        **campos,
    )


def _registro(linha: tuple) -> Registro:
    (
        id_,
        ticker,
        as_of,
        metodo,
        versao,
        execucao_id,
        tipo,
        resultado_json,
        motivo,
        digest,
        proveniencia_json,
    ) = linha
    return Registro(
        id=id_,
        ticker=ticker,
        as_of=as_of,
        metodo=metodo,
        versao=versao,
        execucao_id=execucao_id,
        tipo=tipo,
        resultado=None if resultado_json is None else json.loads(resultado_json),
        motivo_abstencao=motivo,
        hash_resultado=digest,
        proveniencia=json.loads(proveniencia_json),
    )


def buscar(
    conn: sqlite3.Connection,
    ticker: str,
    *,
    as_of: date | datetime | None = None,
    metodo: str | None = None,
    versao: str | None = None,
    tipo: str | None = None,
) -> list[Registro]:
    """Registros do ticker na ordem de gravação, filtrados pelos campos dados."""
    ticker = _obrigatorio("ticker", ticker).strip().upper()
    data = None if as_of is None else _texto_as_of(as_of)
    linhas = conn.execute(
        "SELECT id, ticker, as_of, metodo, versao, execucao_id, tipo, resultado_json, "
        "motivo_abstencao, hash_resultado, proveniencia_json FROM resultados_analise "
        "WHERE ticker = ? AND (? IS NULL OR as_of = ?) "
        "AND (? IS NULL OR metodo = ?) AND (? IS NULL OR versao = ?) "
        "AND (? IS NULL OR tipo = ?) ORDER BY id",
        (ticker, data, data, metodo, metodo, versao, versao, tipo, tipo),
    ).fetchall()
    return [_registro(linha) for linha in linhas]
