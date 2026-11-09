"""Leitura da fila do loop por trecho (F3-0a, pacote de processo F3-0, P1 a P3).

Subcomandos sobre `docs/loop/fila.md`, sem abrir o arquivo inteiro no contexto do agente:

    python scripts/fila.py status
    python scripts/fila.py proximo              # 3 se a próxima linha aberta for [DECISÃO]; 1 se nada aberto
    python scripts/fila.py item <ID>
    python scripts/fila.py marcar <ID> x|!
    python scripts/fila.py independentes <ID>
    python scripts/fila.py diario <arquivo>     # anexa ao diário sem imprimi-lo
    python scripts/fila.py pendencia <ID> "<texto>"

Saída 2: ID inexistente ou duplicado, ou entrada do diário ausente; o arquivo fica intacto.
Só biblioteca padrão. Sem rede, banco nem `.env`; o relógio só é lido para datar a pendência.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

FILA_PADRAO = Path("docs/loop/fila.md")
DIARIO_PADRAO = Path("docs/loop/diario.md")
PENDENCIAS_PADRAO = Path("docs/loop/pendencias.md")

CABECALHO_PENDENCIAS = "# Pendências do loop\n\nUma linha por decisão provisória ou `[!]` (pacote F3-0, P3).\n\n"

_ITEM = re.compile(r"^- \[(?P<estado>[ x!])\] \*\*(?P<rotulo>[^*]+)\*\*")
_DECISAO = "[DECISÃO]"
_CRASES = re.compile(r"`([^`]+)`")
_CAMINHO = re.compile(r"^[\w.*-]+(?:/[\w.*-]*)*$")
_EXTENSOES = (
    ".py",
    ".md",
    ".json",
    ".jsonl",
    ".csv",
    ".toml",
    ".ini",
    ".sql",
    ".txt",
    ".yml",
    ".yaml",
)
_IGNORADOS = ("tests/", "docs/")

LIMITE_DECISAO = 120

SAIDA_OK = 0
SAIDA_VAZIA = 1
SAIDA_ERRO = 2
SAIDA_DECISAO = 3


class ErroFila(Exception):
    """Falha de uso: ID inexistente, duplicado ou arquivo ausente."""


def _hoje() -> date:
    """Data local de hoje; só a pendência a lê."""
    return datetime.now(UTC).astimezone().date()


def _branch() -> str:
    try:
        resultado = subprocess.run(
            ["git", "--no-pager", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "desconhecido"
    nome = resultado.stdout.strip()
    return nome if resultado.returncode == 0 and nome else "desconhecido"


def _ler(caminho: Path) -> str:
    """Lê sem converter fim de linha, para regravar o arquivo como estava."""
    try:
        with caminho.open(encoding="utf-8", newline="") as arquivo:
            return arquivo.read()
    except FileNotFoundError as erro:
        raise ErroFila(f"arquivo não encontrado: {caminho}") from erro


def _gravar(caminho: Path, texto: str) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        arquivo.write(texto)


def _linhas(fila: Path) -> list[str]:
    return _ler(fila).splitlines()


def _item(linha: str) -> tuple[str, str] | None:
    """Devolve (estado, rótulo) de uma linha de item, ou None."""
    casamento = _ITEM.match(linha)
    if casamento is None:
        return None
    return casamento.group("estado"), casamento.group("rotulo").strip()


def _e_decisao(rotulo: str) -> bool:
    return rotulo.startswith(_DECISAO)


def _ate_decisao(linhas: list[str]) -> tuple[list[tuple[int, str, str]], str | None]:
    """Itens antes do primeiro [DECISÃO] aberto, e a linha desse [DECISÃO]."""
    itens: list[tuple[int, str, str]] = []
    for indice, linha in enumerate(linhas):
        dados = _item(linha)
        if dados is None:
            continue
        estado, rotulo = dados
        if _e_decisao(rotulo):
            if estado == " ":
                return itens, linha
            continue
        itens.append((indice, estado, rotulo))
    return itens, None


def _localizar(linhas: list[str], ident: str) -> int:
    achados = [
        indice
        for indice, linha in enumerate(linhas)
        if (dados := _item(linha)) is not None and dados[1] == ident
    ]
    if not achados:
        raise ErroFila(f"item {ident} não encontrado na fila")
    if len(achados) > 1:
        raise ErroFila(f"item {ident} aparece {len(achados)} vezes na fila")
    return achados[0]


def _caminhos(linha: str) -> set[str]:
    """Caminhos citados entre crases, fora de `tests/` e `docs/`."""
    caminhos: set[str] = set()
    for trecho in _CRASES.findall(linha):
        for parte in trecho.split():
            parte = parte.strip(",;:()")
            if not _CAMINHO.match(parte):
                continue
            if "/" not in parte and not parte.endswith(_EXTENSOES):
                continue
            if parte.startswith(_IGNORADOS):
                continue
            caminhos.add(parte)
    return caminhos


def _compartilham(a: set[str], b: set[str]) -> bool:
    return any(
        x == y or x.startswith(y.rstrip("/") + "/") or y.startswith(x.rstrip("/") + "/")
        for x in a
        for y in b
    )


def _cita(linha: str, ident: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(ident)}(?![\w-])", linha) is not None


def status(fila: Path) -> list[str]:
    linhas = _linhas(fila)
    itens, decisao = _ate_decisao(linhas)
    contagem = {estado: sum(1 for _, e, _ in itens if e == estado) for estado in "x !"}
    proximo = next((rotulo for _, estado, rotulo in itens if estado == " "), "nenhum")
    return [
        f"branch: {_branch()}",
        f"[x]: {contagem['x']}",
        f"[ ]: {contagem[' ']}",
        f"[!]: {contagem['!']}",
        f"próximo: {proximo}",
        f"[DECISÃO]: {decisao[:LIMITE_DECISAO] if decisao else 'nenhum'}",
    ]


def proximo(fila: Path) -> tuple[int, str | None]:
    for linha in _linhas(fila):
        dados = _item(linha)
        if dados is None or dados[0] != " ":
            continue
        return (SAIDA_DECISAO if _e_decisao(dados[1]) else SAIDA_OK), linha
    return SAIDA_VAZIA, None


def item(fila: Path, ident: str) -> str:
    linhas = _linhas(fila)
    return linhas[_localizar(linhas, ident)]


def marcar(fila: Path, ident: str, estado: str) -> None:
    linhas = _ler(fila).splitlines(keepends=True)
    indice = _localizar([linha.rstrip("\r\n") for linha in linhas], ident)
    linhas[indice] = re.sub(r"^- \[[ x!]\]", f"- [{estado}]", linhas[indice], count=1)
    _gravar(fila, "".join(linhas))


def independentes(fila: Path, ident: str) -> list[str]:
    linhas = _linhas(fila)
    alvo = linhas[_localizar(linhas, ident)]
    caminhos_alvo = _caminhos(alvo)
    itens, _ = _ate_decisao(linhas)
    resultado = []
    for indice, estado, rotulo in itens:
        if estado != " " or rotulo == ident:
            continue
        linha = linhas[indice]
        if _cita(linha, ident) or _compartilham(_caminhos(linha), caminhos_alvo):
            continue
        resultado.append(rotulo)
    return resultado


def _anexar(destino: Path, conteudo: str, separador: str) -> None:
    """Acrescenta ao fim, no fim de linha que o destino já usa (LF quando novo)."""
    atual = _ler(destino) if destino.exists() else ""
    quebra = "\r\n" if "\r\n" in atual else "\n"
    if atual and not atual.endswith("\n"):
        atual += quebra
    if atual:
        atual += separador.replace("\n", quebra)
    conteudo = conteudo.replace("\r\n", "\n")
    if not conteudo.endswith("\n"):
        conteudo += "\n"
    _gravar(destino, atual + conteudo.replace("\n", quebra))


def diario(destino: Path, entrada: Path) -> None:
    if not entrada.is_file():
        raise ErroFila(f"entrada do diário não encontrada: {entrada}")
    _anexar(destino, _ler(entrada), "\n")


def pendencia(destino: Path, ident: str, texto: str) -> None:
    linha = f"- {_hoje().isoformat()} · {ident} · {' '.join(texto.split())}"
    if not destino.exists():
        _gravar(destino, CABECALHO_PENDENCIAS)
    _anexar(destino, linha, "")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Leitura da fila do loop por trecho.")
    parser.add_argument("--fila", type=Path, default=FILA_PADRAO)
    parser.add_argument("--diario", type=Path, default=DIARIO_PADRAO)
    parser.add_argument("--pendencias", type=Path, default=PENDENCIAS_PADRAO)
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("status")
    sub.add_parser("proximo")
    sub.add_parser("item").add_argument("id")
    marcacao = sub.add_parser("marcar")
    marcacao.add_argument("id")
    marcacao.add_argument("estado", choices=["x", "!"])
    sub.add_parser("independentes").add_argument("id")
    sub.add_parser("diario").add_argument("arquivo", type=Path)
    pend = sub.add_parser("pendencia")
    pend.add_argument("id")
    pend.add_argument("texto")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.comando == "status":
            print("\n".join(status(args.fila)))
        elif args.comando == "proximo":
            codigo, linha = proximo(args.fila)
            if linha is None:
                print("nenhum item aberto na fila", file=sys.stderr)
            else:
                print(linha)
            return codigo
        elif args.comando == "item":
            print(item(args.fila, args.id))
        elif args.comando == "marcar":
            marcar(args.fila, args.id, args.estado)
        elif args.comando == "independentes":
            for rotulo in independentes(args.fila, args.id):
                print(rotulo)
        elif args.comando == "diario":
            diario(args.diario, args.arquivo)
        elif args.comando == "pendencia":
            pendencia(args.pendencias, args.id, args.texto)
    except ErroFila as erro:
        print(str(erro), file=sys.stderr)
        return SAIDA_ERRO
    return SAIDA_OK


if __name__ == "__main__":
    sys.exit(main())
