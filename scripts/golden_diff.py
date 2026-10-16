"""Compara o golden dos motores (HEAD ou `--base`) com o da árvore de trabalho (F2A-15).

Lista os casos alterados, incluídos e removidos, por (motor, id).
`--onde "<expressão>"` sai com 1 se algum caso alterado não a satisfizer; a expressão vê
`caso`, `entrada`, `saida_antiga` e `saida_nova`.
`--par "<antigo>=<novo>"` pareia removidos e incluídos cujo id só difere pelo trecho.
Não roda o gerador nem altera o golden.

Uso: python scripts/golden_diff.py [--base arquivo] [--onde EXPR] [--par ANTIGO=NOVO]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

GOLDEN = "tests/fixtures/golden_motores.jsonl"
RAIZ = Path(__file__).resolve().parents[1]
_FUNCOES = {
    "abs": abs,
    "all": all,
    "any": any,
    "isinstance": isinstance,
    "len": len,
    "max": max,
    "min": min,
    "round": round,
    "set": set,
    "str": str,
    "float": float,
    "int": int,
}


def _parse(texto: str) -> dict[tuple[str, str], dict]:
    casos = [json.loads(linha) for linha in texto.splitlines() if linha.strip()]
    return {(c["motor"], c["id"]): c for c in casos}


def _golden_do_head() -> str:
    resultado = subprocess.run(
        ["git", "show", f"HEAD:{GOLDEN}"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return resultado.stdout


def avaliar(expressao: str, caso: dict, antigo: dict, novo: dict) -> bool:
    escopo = {
        "__builtins__": _FUNCOES,
        "caso": caso,
        "entrada": caso["entrada"],
        "saida_antiga": antigo,
        "saida_nova": novo,
    }
    return bool(eval(expressao, escopo))


def _nome(chave: tuple[str, str]) -> str:
    return f"{chave[0]}/{chave[1]}"


def _diferencas(antiga: dict, nova: dict) -> list[str]:
    linhas = []
    for campo in list(antiga) + [k for k in nova if k not in antiga]:
        if antiga.get(campo) != nova.get(campo):
            linhas.append(f"    {campo}: {antiga.get(campo)!r} -> {nova.get(campo)!r}")
    return linhas


def _parear(removidos: list, incluidos: list, antigo: str, novo: str) -> list:
    livres = set(incluidos)
    pares = []
    for motor, id_ in removidos:
        alvo = (motor, id_.replace(antigo, novo))
        if antigo in id_ and alvo in livres:
            livres.discard(alvo)
            pares.append(((motor, id_), alvo))
    return pares


def _listar(titulo: str, chaves: list) -> None:
    print(f"{titulo}: {len(chaves)}")
    for chave in chaves:
        print(f"  {_nome(chave)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", help="arquivo no lugar do golden do HEAD")
    ap.add_argument("--novo", default=str(RAIZ / GOLDEN), help=argparse.SUPPRESS)
    ap.add_argument("--onde", help="predicado que todo caso alterado deve satisfazer")
    ap.add_argument("--par", help="ANTIGO=NOVO: pareia removidos e incluídos")
    args = ap.parse_args(argv)

    if args.base:
        base = _parse(Path(args.base).read_text(encoding="utf-8"))
    else:
        base = _parse(_golden_do_head())
    atual = _parse(Path(args.novo).read_text(encoding="utf-8"))

    alterados = [
        k for k in atual if k in base and atual[k]["saida"] != base[k]["saida"]
    ]
    incluidos = [k for k in atual if k not in base]
    removidos = [k for k in base if k not in atual]

    if args.par:
        antigo, _, novo = args.par.partition("=")
        pares = _parear(removidos, incluidos, antigo, novo)
        pareados_antigos = {a for a, _ in pares}
        pareados_novos = {n for _, n in pares}
        removidos = [k for k in removidos if k not in pareados_antigos]
        incluidos = [k for k in incluidos if k not in pareados_novos]
        print(f"pares: {len(pares)}")
        for a, n in pares:
            print(f"  {_nome(a)} -> {_nome(n)}")
            for linha in _diferencas(base[a]["saida"], atual[n]["saida"]):
                print(linha)

    _listar("alterados", alterados)
    _listar("incluídos", incluidos)
    _listar("removidos", removidos)

    if args.onde:
        fora = [
            k
            for k in alterados
            if not avaliar(args.onde, atual[k], base[k]["saida"], atual[k]["saida"])
        ]
        _listar("fora do predicado", fora)
        if fora:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
