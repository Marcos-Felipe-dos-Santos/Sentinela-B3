"""Gate mecânico de um item da fila (F3-0d, P5; decisão 22).

Uso: `python scripts/gate.py --item <ID> [--golden-autorizado] [--fila <arquivo>]`

Roda as verificações do gate G que não exigem julgamento e imprime uma linha por
verificação (no máximo 20 linhas), com saída 1 se alguma falhar:
suíte (`python -m pytest -q`: linha final e nomes dos testes que falharam), Ruff CI,
Ruff completo nos diretórios do protocolo que existirem, `git diff --staged --check`,
SHA-256 do golden igual ao do `HEAD` (salvo `--golden-autorizado`), arquivos proibidos no
stage e, só como aviso, arquivos do stage que a linha do item não cita entre crases.
Não roda mutação e não altera arquivo. Saída 2: uso errado ou item inexistente.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import importlib.util
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

GOLDEN = "tests/fixtures/golden_motores.jsonl"
DIRETORIOS_RUFF = ("sentinela/data", "sentinela/methods", "sentinela/data/store")
PROIBIDOS = (".env", ".env.*", "*.db", "outputs/*", "mutants/*", "*__pycache__*")
# Modelo sem segredo que o CLAUDE.md espera versionado.
PERMITIDOS = (".env.example",)
RAIZ = Path(__file__).resolve().parents[1]
LIMITE_LINHAS = 20
MAX_FALHAS = LIMITE_LINHAS - 8  # linha da suíte, a de "mais N" e as outras seis
SAIDA_OK, SAIDA_FALHA, SAIDA_USO = 0, 1, 2


@dataclass(frozen=True)
class Execucao:
    codigo: int
    saida: str


Executar = Callable[[Sequence[str]], Execucao]


@dataclass(frozen=True)
class Resultado:
    nome: str
    ok: bool
    detalhe: str
    aviso: bool = False

    def linha(self) -> str:
        estado = "AVISO" if self.aviso else ("OK" if self.ok else "FALHA")
        return f"[{estado}] {self.nome}: {self.detalhe}"


def executar(comando: Sequence[str]) -> Execucao:
    """Roda o comando na raiz do repositório e junta stdout e stderr."""
    feito = subprocess.run(
        list(comando), capture_output=True, text=True, check=False, cwd=RAIZ
    )
    return Execucao(feito.returncode, feito.stdout + feito.stderr)


def _fila():
    caminho = Path(__file__).with_name("fila.py")
    spec = importlib.util.spec_from_file_location("fila_para_gate", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _ultima_linha(texto: str) -> str:
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    return linhas[-1] if linhas else "(sem saída)"


def suite(rodar: Executar) -> list[Resultado]:
    feito = rodar([sys.executable, "-m", "pytest", "-q"])
    falhas = [
        linha.split(" - ")[0].removeprefix("FAILED ").removeprefix("ERROR ")
        for linha in feito.saida.splitlines()
        if linha.startswith(("FAILED ", "ERROR "))
    ]
    resultados = [Resultado("suíte", feito.codigo == 0, _ultima_linha(feito.saida))]
    mostradas = falhas[:MAX_FALHAS]
    resultados += [Resultado("falhou", False, nome) for nome in mostradas]
    if len(falhas) > len(mostradas):
        resultados.append(
            Resultado("falhou", False, f"mais {len(falhas) - len(mostradas)} testes")
        )
    return resultados


def ruff_ci(rodar: Executar) -> Resultado:
    feito = rodar(["ruff", "check", "--select", "E9,F63,F7,F82", "."])
    return Resultado("Ruff CI", feito.codigo == 0, _ultima_linha(feito.saida))


def ruff_completo(rodar: Executar, raiz: Path) -> Resultado:
    diretorios = [d for d in DIRETORIOS_RUFF if (raiz / d).is_dir()]
    if not diretorios:
        return Resultado("Ruff completo", True, "nenhum diretório do protocolo existe")
    feito = rodar(["ruff", "check", *diretorios])
    return Resultado(
        f"Ruff completo ({', '.join(diretorios)})",
        feito.codigo == 0,
        _ultima_linha(feito.saida),
    )


def diff_check(rodar: Executar) -> Resultado:
    feito = rodar(["git", "diff", "--staged", "--check"])
    detalhe = "limpo" if feito.codigo == 0 else _ultima_linha(feito.saida)
    return Resultado("git diff --staged --check", feito.codigo == 0, detalhe)


def golden(rodar: Executar, raiz: Path, autorizado: bool) -> Resultado:
    """Mesmo blob do `HEAD` no índice e na cópia de trabalho (BUG-3-14), sem decodificar.

    `git rev-parse :<golden>` dá o blob que vai ao commit; `git hash-object` o da cópia de
    trabalho. Os dois precisam ser o do `HEAD`, salvo `--golden-autorizado`.
    """
    atual = raiz / GOLDEN
    if not atual.is_file():
        return Resultado("golden", False, f"{GOLDEN} ausente")
    sha_atual = hashlib.sha256(atual.read_bytes()).hexdigest()
    no_head = rodar(["git", "rev-parse", f"HEAD:{GOLDEN}"])
    if no_head.codigo != 0:
        return Resultado("golden", False, f"sem {GOLDEN} no HEAD")
    no_indice = rodar(["git", "rev-parse", f":{GOLDEN}"])
    if no_indice.codigo != 0:
        return Resultado("golden", False, f"sem {GOLDEN} no índice")
    agora = rodar(["git", "hash-object", GOLDEN])
    blob = no_head.saida.strip()
    if (
        agora.codigo == 0
        and agora.saida.strip() == blob
        and no_indice.saida.strip() == blob
    ):
        return Resultado("golden", True, f"igual ao HEAD (SHA256 {sha_atual[:16]}…)")
    onde = " no índice" if no_indice.saida.strip() != blob else ""
    if autorizado:
        return Resultado(
            "golden", True, f"diferente do HEAD{onde}, autorizado", aviso=True
        )
    return Resultado(
        "golden", False, f"diferente do HEAD{onde} (SHA256 {sha_atual[:16]}…)"
    )


def stage(rodar: Executar) -> list[str] | None:
    """Arquivos do stage; `None` se o git falhar (não vira stage vazio)."""
    feito = rodar(["git", "diff", "--staged", "--name-only"])
    if feito.codigo != 0:
        return None
    return [linha.strip() for linha in feito.saida.splitlines() if linha.strip()]


def _proibido(caminho: str) -> bool:
    nome = Path(caminho).name
    if nome in PERMITIDOS:
        return False
    return any(
        fnmatch.fnmatch(caminho, padrao) or fnmatch.fnmatch(nome, padrao)
        for padrao in PROIBIDOS
    )


def proibidos(arquivos: Sequence[str]) -> Resultado:
    achados = [a for a in arquivos if _proibido(a)]
    if achados:
        return Resultado("arquivos proibidos no stage", False, ", ".join(achados))
    return Resultado("arquivos proibidos no stage", True, "nenhum")


def fora_da_linha(arquivos: Sequence[str], linha_item: str, fila) -> Resultado:
    citados = fila._caminhos(linha_item) | set(fila._DO_LOOP)
    fora = [a for a in arquivos if not any(fila._casam(a, c) for c in citados)]
    if fora:
        return Resultado("fora da linha do item", True, ", ".join(fora), aviso=True)
    return Resultado("fora da linha do item", True, "nenhum")


def rodar_gate(
    ident: str,
    *,
    fila_md: Path,
    raiz: Path,
    golden_autorizado: bool = False,
    rodar: Executar | None = None,
) -> tuple[int, list[str]]:
    """Código de saída e as linhas do resumo (no máximo `LIMITE_LINHAS`)."""
    rodar = executar if rodar is None else rodar
    fila = _fila()
    try:
        linha_item = fila.item(fila_md, ident)
    except fila.ErroFila as erro:
        return SAIDA_USO, [f"[FALHA] item: {erro}"]
    arquivos = stage(rodar)
    if arquivos is None:
        do_stage = [Resultado("stage", False, "git diff --staged --name-only falhou")]
    else:
        do_stage = [proibidos(arquivos), fora_da_linha(arquivos, linha_item, fila)]
    resultados = [
        *suite(rodar),
        ruff_ci(rodar),
        ruff_completo(rodar, raiz),
        diff_check(rodar),
        golden(rodar, raiz, golden_autorizado),
        *do_stage,
    ]
    # suíte: 1 + MAX_FALHAS + 1 linhas; demais verificações: 6 linhas.
    linhas = [r.linha() for r in resultados]
    return (SAIDA_OK if all(r.ok for r in resultados) else SAIDA_FALHA), linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--item", required=True)
    parser.add_argument("--golden-autorizado", action="store_true")
    parser.add_argument("--fila", default=str(RAIZ / "docs/loop/fila.md"))
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return SAIDA_USO
    codigo, linhas = rodar_gate(
        args.item,
        fila_md=Path(args.fila),
        raiz=RAIZ,
        golden_autorizado=args.golden_autorizado,
    )
    print("\n".join(linhas))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
