"""Fechamento de uma fase depois do merge (F3-0f, P9; decisão 25).

Uso, na raiz do repositório: `python scripts/fechar_fase.py N [--aplicar]`

Simula por padrão; com `--aplicar`, apaga o branch local `v2/fase-N` só depois de todas as
verificações, nesta ordem:
1. árvore limpa (`git status --porcelain` vazio);
2. PR mesclado com merge commit na `main`: um commit de merge da própria `main`
   (`--first-parent`) tem o topo do branch como segundo pai;
3. tag `v2-fase-N` apontando para esse commit de merge;
4. seção "Fase atual" do `AGENTS.md` da `main` sem `v2/fase-N` (o Marcos já a trocou);
5. `git branch --merged main` lista o branch.
Qualquer verificação que falhe interrompe sem apagar nada (saída 1). O script é do
Marcos: o loop não o roda. Não faz push nem rede.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

SAIDA_OK, SAIDA_FALHA, SAIDA_USO = 0, 1, 2
FASE = re.compile(r"\d+[a-z]?")


@dataclass(frozen=True)
class Execucao:
    codigo: int
    saida: str


Git = Callable[[Sequence[str]], Execucao]


def git_real(raiz: Path) -> Git:
    def rodar(args: Sequence[str]) -> Execucao:
        feito = subprocess.run(
            ["git", "-C", str(raiz), *args], capture_output=True, text=True, check=False
        )
        return Execucao(feito.returncode, (feito.stdout + feito.stderr).strip())

    return rodar


class Interrompido(Exception):
    """Verificação que falhou; nada foi apagado."""


def _exigir(condicao: bool, motivo: str) -> None:
    if not condicao:
        raise Interrompido(motivo)


def arvore_limpa(git: Git) -> str:
    feito = git(["status", "--porcelain"])
    _exigir(feito.codigo == 0, "git status falhou")
    _exigir(feito.saida == "", "árvore com alteração pendente")
    return "árvore limpa"


def merge_na_main(git: Git, branch: str) -> str:
    topo = git(["rev-parse", "--verify", "-q", f"refs/heads/{branch}"])
    _exigir(topo.codigo == 0 and topo.saida, f"branch {branch} não existe")
    merges = git(
        ["log", "refs/heads/main", "--first-parent", "--merges", "--format=%H %P"]
    )
    _exigir(merges.codigo == 0, "main não existe")
    for linha in merges.saida.splitlines():
        partes = linha.split()
        if len(partes) >= 3 and partes[2] == topo.saida:
            return partes[0]
    raise Interrompido(
        f"nenhum merge commit da main tem o topo de {branch} como segundo pai"
    )


def tag_no_merge(git: Git, fase: str, merge: str) -> str:
    tag = f"v2-fase-{fase}"
    feito = git(["rev-parse", "--verify", "-q", f"refs/tags/{tag}^{{commit}}"])
    _exigir(feito.codigo == 0 and feito.saida, f"tag {tag} não existe")
    _exigir(feito.saida == merge, f"tag {tag} não aponta para o merge {merge[:7]}")
    return f"tag {tag} no merge {merge[:7]}"


def fase_atual_sem(git: Git, branch: str) -> str:
    """A seção "Fase atual" do `AGENTS.md` da `main` não cita o branch da fase."""
    feito = git(["show", "refs/heads/main:AGENTS.md"])
    _exigir(feito.codigo == 0, "AGENTS.md ausente na main")
    casado = re.search(
        r"^## Fase atual\s*$(.*?)(?=^## |\Z)", feito.saida, re.MULTILINE | re.DOTALL
    )
    _exigir(casado is not None, "AGENTS.md sem a seção Fase atual")
    _exigir(
        branch not in casado.group(1), f"Fase atual do AGENTS.md ainda cita {branch}"
    )
    return "Fase atual sem a fase fechada"


def mesclado(git: Git, branch: str) -> str:
    feito = git(["branch", "--merged", "refs/heads/main", "--format=%(refname:short)"])
    _exigir(feito.codigo == 0, "git branch --merged main falhou")
    _exigir(
        branch in feito.saida.splitlines(),
        f"{branch} não está em git branch --merged main",
    )
    return f"{branch} mesclado na main"


def fechar(
    fase: str, *, raiz: Path, aplicar: bool, git: Git | None = None
) -> tuple[int, list[str]]:
    if not FASE.fullmatch(fase):
        return SAIDA_USO, [
            f"fase inválida: {fase!r} (número e letra opcional, como 3 ou 2b)"
        ]
    git = git_real(raiz) if git is None else git
    branch = f"v2/fase-{fase}"
    linhas = []
    try:
        linhas.append(arvore_limpa(git))
        merge = merge_na_main(git, branch)
        linhas.append(f"merge {merge[:7]} na main")
        linhas.append(tag_no_merge(git, fase, merge))
        linhas.append(fase_atual_sem(git, branch))
        linhas.append(mesclado(git, branch))
    except Interrompido as erro:
        return SAIDA_FALHA, [*linhas, f"INTERROMPIDO: {erro}; nada foi apagado"]
    if not aplicar:
        return SAIDA_OK, [
            *linhas,
            f"simulação: apagaria o branch {branch} (use --aplicar)",
        ]
    feito = git(["branch", "-d", branch])
    if feito.codigo != 0:
        return SAIDA_FALHA, [*linhas, f"git branch -d {branch} falhou: {feito.saida}"]
    return SAIDA_OK, [*linhas, f"branch {branch} apagado"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fase", help="fase fechada: 3, 4...")
    parser.add_argument("--aplicar", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return SAIDA_USO
    codigo, linhas = fechar(args.fase, raiz=Path("."), aplicar=args.aplicar)
    print("\n".join(linhas))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
