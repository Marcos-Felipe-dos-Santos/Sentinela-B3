"""Prompts e pacotes da auditoria externa do Sentinela B3 (docs/loop/ciclo-de-fase.md).

Uso, na raiz do repositório (WSL, venv ativa):
    python scripts/auditar.py codex MODO --fase 2b [--arquivo A] [--desde C] [--foco T]
    python scripts/auditar.py gemini MODO --fase 2b [--arquivo A] [--foco T]
    python scripts/auditar.py prompt MODO --fase 2b [--para gemini] [...]

MODO: documento | ficha | fase | fechamento (o fechamento é só no Codex).
- codex: roda o Codex em sandbox só de leitura e grava o log inteiro e o relatório final.
- gemini: grava o prompt e o pacote de texto (partes de até 350 KB, linhas numeradas) para
  anexar no app do Gemini, que não lê o repositório nem anexos maiores.
- prompt: só imprime o prompt preenchido.

Saída: /mnt/c/Users/marcos/Downloads, se existir; senão outputs/auditorias/ (fora do git).
Os modelos dos prompts ficam em docs/loop/prompts/. Nada é escrito no repositório fora de outputs/.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

FASES = ["0", "1", "2a", "2b", "2c", "3", "4", "5", "6", "7", "8"]
MODOS = ["documento", "ficha", "fase", "fechamento"]
PROMPTS = Path("docs/loop/prompts")
SAIDA_WINDOWS = Path("/mnt/c/Users/marcos/Downloads")
SAIDA_LOCAL = Path("outputs/auditorias")
# O app do Gemini cortou anexos de ~450 KB (teste de 14/10/2026).
MAX_CHARS_POR_PARTE = 350_000
# Arquivo maior fica fora do pacote, listado no 05-git.
MAX_BYTES_POR_ARQUIVO = 300_000

FOCO_PADRAO = {
    "documento": (
        "Achados das auditorias anteriores que o documento deveria tratar e não trata "
        "({HIST_ANT}auditoria-externa.md e tests/regressao/README.md)."
    ),
    "ficha": (
        "Refaça o exemplo numérico da ficha por conta própria, a partir da fórmula e da "
        "referência citadas, e compare. Não copie o número da ficha."
    ),
    "fase": (
        "Itens que mudam número na saída: os commits fix: e feat: de cálculo (o diário diz "
        "quais). Para cada alegação de número: confirmada, contradita ou não verificável, "
        "com evidência."
    ),
    "fechamento": (
        "Cada commit da fila de fechamento corrige o que {HIST}auditoria-externa.md mandou "
        "corrigir, e nada além."
    ),
}

ACESSO = {
    "codex": (
        "ACESSO: você está na raiz do repositório, num sandbox só de leitura. Leia os arquivos "
        "e use git (log, show, diff) à vontade. Pode rodar, sem escrever no repositório, "
        "python -m pytest -q -p no:cacheprovider e ruff check --select E9,F63,F7,F82 . "
        "Não regenere o golden, não rode mutmut e não use a rede."
    ),
    "gemini": (
        "ACESSO: você não tem o repositório nem um terminal. Tem anexos de texto gerados do "
        'branch {ATUAL} (HEAD {HEAD}). Cada arquivo começa com "===== ARQUIVO: caminho =====" '
        'e tem as linhas numeradas "N| "; cite sempre como caminho:linha. O último anexo, git.md, '
        "traz o índice do pacote, os commits desde {BASE} com os arquivos que cada um alterou "
        "(você não tem git diff) e a lista do que ficou fora. Onde este prompt mandar rodar um "
        "comando, use os "
        "anexos no lugar. Você não tem os CSV da CVM, o cache, o banco nem resultados de "
        'execução: o que depender deles vai para "Não verificado". Não invente valores. Se a '
        "resposta ficar longa demais para uma mensagem, pare no fim de uma seção com "
        '"CONTINUA"; quando eu escrever "continue", siga sem repetir.'
    ),
}

EXCLUIR = [
    "tests/fixtures/golden_motores.jsonl",
    "**.png",
    "**.jpg",
    "**.jpeg",
    "**.gif",
    "**.ico",
    "**.pdf",
    "**.zip",
    "**.gz",
    "**.db",
    "**.sqlite*",
    "**.parquet",
    "**.pkl",
    "**.xlsx",
]
CONTEXTO = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "pyproject.toml",
    "pytest.ini",
    "requirements*.txt",
    "docs/PLANO.md",
    "docs/adr/**",
    "docs/decisoes/**",
    "docs/metodologia/**",
    "docs/loop/*.md",
    "docs/auditoria/**",
    ".agents/skills/**",
    ".claude/skills/**",
    ".claude/commands/**",
    ".claude/agents/**",
    ".github/workflows/**",
    "tests/regressao/README.md",
]


def regex(padrao):
    """Glob simples: * não cruza "/", ** cruza."""
    r = (
        re.escape(padrao)
        .replace(r"\*\*", "\0")
        .replace(r"\*", "[^/]*")
        .replace("\0", ".*")
    )
    return re.compile(r + r"\Z")


def casa(caminho, padroes):
    return any(regex(p).match(caminho) for p in padroes)


def aviso(msg):
    print(f"Aviso: {msg}", file=sys.stderr)


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True, check=check)
    return r.stdout.strip()


def tem_tag(tag):
    return bool(git("tag", "--list", tag))


def contexto(a):
    """Valores dos marcadores {X} dos modelos de prompt."""
    i = FASES.index(a.fase)
    ant, prox = FASES[i - 1], FASES[min(i + 1, len(FASES) - 1)]
    base = f"v2-fase-{ant}"
    if not tem_tag(base):
        base = git("merge-base", "HEAD", "main")
        aviso(
            f"a tag v2-fase-{ant} não existe; base = merge-base com a main ({base[:7]})."
        )
    v = {
        "FASE": a.fase.upper(),
        "FASE_MIN": a.fase,
        "ANT": ant.upper(),
        "BRANCH": f"v2/fase-{a.fase}",
        "BASE": base,
        "HIST": f"docs/loop/historico/fase-{a.fase}/",
        "HIST_ANT": f"docs/loop/historico/fase-{ant}/",
        "PROPOSTA_PROX": f"docs/loop/fila-fase{prox}-proposta.md",
        "PREFIXO": f"F{a.fase.upper()}",
        "ARQUIVO": a.arquivo or "",
        "DESDE": a.desde or "",
        "ATUAL": git("branch", "--show-current") or "(HEAD destacado)",
        "HEAD": git("rev-parse", "--short", "HEAD"),
    }
    v["FOCO"] = preencher(a.foco or FOCO_PADRAO[a.modo], v)
    return v


def preencher(texto, valores):
    for k, val in valores.items():
        texto = texto.replace("{" + k + "}", val)
    return texto


def montar_prompt(a, para):
    v = contexto(a)
    v["ACESSO"] = preencher(ACESSO[para], v)
    texto = preencher((PROMPTS / f"{a.modo}.md").read_text(encoding="utf-8"), v)
    sobra = re.findall(r"\{[A-Z_]+\}", texto)
    if sobra:
        sys.exit(f"Marcadores sem valor no prompt: {sorted(set(sobra))}")
    return texto, v


def validar(a):
    if not Path("docs/loop/protocolo.md").exists():
        sys.exit("Rode na raiz do repositório.")
    if a.fase not in FASES[1:]:
        sys.exit(f"--fase deve ser uma de {FASES[1:]}.")
    if a.arquivo:
        a.arquivo = Path(a.arquivo).as_posix()
    if a.modo in ("documento", "ficha") and not (
        a.arquivo and Path(a.arquivo).is_file()
    ):
        sys.exit(f"O modo {a.modo} precisa de --arquivo com um arquivo que exista.")
    if a.modo == "fechamento":
        if not a.desde:
            sys.exit(
                "O modo fechamento precisa de --desde <commit anterior ao 1º item da fila de fechamento>."
            )
        if subprocess.run(
            ["git", "rev-parse", "--verify", "-q", a.desde + "^{commit}"],
            capture_output=True,
            check=False,
        ).returncode:
            sys.exit(f"--desde {a.desde}: commit não encontrado.")
    if a.modo in ("fase", "fechamento"):
        atual = git("branch", "--show-current")
        if atual != f"v2/fase-{a.fase}":
            aviso(f"você está em {atual or 'HEAD destacado'}, não em v2/fase-{a.fase}.")
        if git("status", "--short"):
            aviso(
                "há mudanças não commitadas; o auditor vê o diretório de trabalho, não só os commits."
            )


def pasta_saida(a):
    if a.saida:
        return Path(a.saida)
    return SAIDA_WINDOWS if SAIDA_WINDOWS.is_dir() else SAIDA_LOCAL


def rotulo(a):
    return Path(a.arquivo).stem if a.modo in ("documento", "ficha") else a.fase


def livre(pasta, nome, ext):
    """Primeiro nome que não sobrescreve uma rodada anterior: x.txt, x-2.txt, x-3.txt..."""
    n = 1
    while True:
        alvo = pasta / f"{nome}{'' if n == 1 else f'-{n}'}{ext}"
        if not alvo.exists():
            return alvo
        n += 1


def relatorio_do_log(log):
    """Fallback quando o Codex não grava --output-last-message: o texto depois do último "tokens used"."""
    linhas = log.splitlines()
    marcas = [i for i, linha in enumerate(linhas) if "tokens used" in linha.lower()]
    if not marcas:
        return log
    resto = linhas[marcas[-1] + 1 :]
    if resto and re.fullmatch(r"[\d.,\s]+", resto[0]):
        resto = resto[1:]
    return "\n".join(resto).strip()


def veredito(texto):
    """O texto depois da última menção a "veredito"; sem ela, a última expressão de veredito."""
    linhas = texto.splitlines()
    marcas = [i for i, ln in enumerate(linhas) if "veredito" in ln.lower()]
    if marcas:
        i = marcas[-1]
        resto = re.sub(
            r"^.*?veredito[\W_]*", "", linhas[i], flags=re.IGNORECASE
        ).strip()
        if not resto:
            resto = next((ln.strip() for ln in linhas[i + 1 :] if ln.strip()), "")
        if resto:
            return resto[:200]
    achados = re.findall(
        r"(não pode seguir|pode seguir com ressalvas|pode seguir)", texto, re.IGNORECASE
    )
    return achados[-1] if achados else "(não encontrado: leia o relatório)"


def cmd_prompt(a):
    texto, _ = montar_prompt(a, a.para)
    print(texto)


def cmd_codex(a):
    if not shutil.which("codex"):
        sys.exit("codex não encontrado no PATH.")
    texto, _ = montar_prompt(a, "codex")
    pasta = pasta_saida(a)
    pasta.mkdir(parents=True, exist_ok=True)
    log = livre(pasta, f"auditoria-{a.modo}-{rotulo(a)}-codex", ".txt")
    rel = log.with_name(log.stem + "-relatorio.md")
    print(
        f"Codex auditando ({a.modo}, fase {a.fase}). Log em {log}. Pode levar vários minutos."
    )
    with log.open("w", encoding="utf-8") as f:
        r = subprocess.run(
            [
                "codex",
                "exec",
                "--sandbox",
                "read-only",
                "--output-last-message",
                str(rel),
                texto,
            ],
            stdout=f,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if not rel.exists() or not rel.read_text(encoding="utf-8").strip():
        rel.write_text(
            relatorio_do_log(log.read_text(encoding="utf-8")) + "\n", encoding="utf-8"
        )
    corpo = rel.read_text(encoding="utf-8")
    print(
        f"Saída do codex: {r.returncode}. Relatório: {rel} ({len(corpo.splitlines())} linhas)"
    )
    print(f"Veredito: {veredito(corpo)}")
    if r.returncode:
        aviso(f"o Codex terminou com erro ({r.returncode}); leia o log.")
        if "output-last-message" in log.read_text(encoding="utf-8"):
            aviso("este Codex não aceita --output-last-message: atualize o Codex CLI.")
    print("Mande o relatório (e, se pedirem, o log) para o Claude no chat consolidar.")


def blocos(caminhos):
    saida, fora = [], []
    for c in caminhos:
        p = Path(c)
        if p.is_symlink() or not p.is_file():
            continue
        if p.stat().st_size > MAX_BYTES_POR_ARQUIVO:
            fora.append((c, f"{p.stat().st_size // 1000} KB, acima do limite"))
            continue
        try:
            linhas = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            fora.append((c, "binário"))
            continue
        larg = len(str(len(linhas)))
        corpo = "\n".join(f"{i:>{larg}}| {linha}" for i, linha in enumerate(linhas, 1))
        saida.append(
            (c, f"\n===== ARQUIVO: {c} ({len(linhas)} linhas) =====\n{corpo}\n")
        )
    return saida, fora


def dividir(itens):
    """Partes de até MAX_CHARS_POR_PARTE, na ordem dos itens, sem quebrar arquivo."""
    partes, atual, tam = [], [], 0
    for item in itens:
        if atual and tam + len(item[2]) > MAX_CHARS_POR_PARTE:
            partes.append(atual)
            atual, tam = [], 0
        atual.append(item)
        tam += len(item[2])
    if atual:
        partes.append(atual)
    return partes


def cmd_gemini(a):
    if a.modo == "fechamento":
        sys.exit("A auditoria rápida de fechamento é só no Codex.")
    texto, v = montar_prompt(a, "gemini")
    pasta = pasta_saida(a) / f"gemini-{a.modo}-{rotulo(a)}"
    pasta.mkdir(parents=True, exist_ok=True)
    for padrao in ("0*.md", "parte-*.md", "git.md"):
        for velho in pasta.glob(padrao):
            velho.unlink()
    (pasta / "00-prompt.md").write_text(texto, encoding="utf-8")

    historico = [
        "docs/loop/diario.md",
        v["HIST"] + "**",
        v["HIST_ANT"] + "auditoria-externa.md",
    ]
    grupos = {"contexto": [], "diário e histórico": [], "código": [], "testes": []}
    fora = []
    rastreados = git("ls-files").splitlines()
    if a.arquivo and a.arquivo not in rastreados:
        rastreados.append(a.arquivo)
    for c in rastreados:
        if casa(c, EXCLUIR):
            fora.append((c, "tipo excluído"))
        elif c == a.arquivo:
            grupos["contexto"].append(c)
        elif casa(c, historico):
            if a.modo == "ficha":
                fora.append((c, "diário e histórico ficam fora no modo ficha"))
            else:
                grupos["diário e histórico"].append(c)
        elif casa(c, CONTEXTO):
            grupos["contexto"].append(c)
        elif c.startswith("docs/"):
            fora.append((c, "documento fora do escopo"))
        elif a.modo == "fase":
            grupos["testes" if c.startswith("tests/") else "código"].append(c)
        else:
            fora.append((c, f"código e testes ficam fora no modo {a.modo}"))

    cab = (
        "# Sentinela B3 — pacote de contexto para auditoria\n"
        f"Branch: {v['ATUAL']} · HEAD: {v['HEAD']} · base: {v['BASE'][:12]}\n"
        "Formato: cada arquivo começa com '===== ARQUIVO: caminho ====='; linhas numeradas 'N| '.\n"
    )
    itens = []
    for grupo, caminhos in grupos.items():
        feitos, sem = blocos(caminhos)
        fora += sem
        itens += [(grupo, c, b) for c, b in feitos]
    partes = dividir(itens)
    indice = []
    for i, parte in enumerate(partes, 1):
        nomes = ", ".join(dict.fromkeys(g for g, _, _ in parte))
        corpo = (
            cab
            + f"Parte {i} de {len(partes)} · {nomes}\n"
            + "".join(b for *_, b in parte)
        )
        nome = f"parte-{i:02d}.md"
        (pasta / nome).write_text(corpo, encoding="utf-8")
        indice.append((nome, len(corpo), f"{nomes}: {parte[0][1]} … {parte[-1][1]}"))

    log = git(
        "log",
        "--stat",
        "--format=%n----- commit %h · %ad · %s%n%b",
        "--date=short",
        f"{v['BASE']}..HEAD",
    )
    git_txt = (
        cab
        + "\n## Índice do pacote\n"
        + "\n".join(f"- {nome}: {desc}" for nome, _, desc in indice)
        + "\n\n## Commits desde a base (mais recente primeiro), com arquivos alterados\n"
        + log
        + "\n\n## Arquivos rastreados\n"
        + git("ls-files")
        + "\n\n## Arquivos fora deste pacote\n"
        + "\n".join(f"- {c}: {m}" for c, m in fora)
        + "\n"
    )
    (pasta / "git.md").write_text(git_txt, encoding="utf-8")
    indice.append(("git.md", len(git_txt), "índice, commits e arquivos fora"))

    print(f"Pasta: {pasta}")
    for nome, tam, desc in indice:
        print(f"  {nome:<14} {tam / 1e3:5.0f} KB  {desc}")
    total = sum(r[1] for r in indice)
    print(
        f"  {'TOTAL':<14} {total / 1e3:5.0f} KB · {len(fora)} arquivos fora (lista no git.md)"
    )
    print(
        f"No app do Gemini: anexe os {len(indice)} arquivos (parte-01 a parte-{len(partes):02d} "
        "e git.md) e cole o texto do 00-prompt.md."
    )
    if len(indice) > 10:
        aviso(
            "mais de 10 anexos. Se o app recusar, mande em duas mensagens; na primeira, "
            'escreva só "Leia estes anexos; o pedido vem na próxima mensagem."'
        )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="acao", required=True)
    for nome in ("prompt", "codex", "gemini"):
        p = sub.add_parser(nome)
        p.add_argument("modo", choices=MODOS)
        p.add_argument(
            "--fase",
            required=True,
            help="fase auditada ou a que o documento propõe: 2b, 2c, 3...",
        )
        p.add_argument(
            "--arquivo", help="documento ou ficha auditada (modos documento e ficha)"
        )
        p.add_argument(
            "--desde",
            help="commit anterior ao 1º item da fila de fechamento (modo fechamento)",
        )
        p.add_argument("--foco", help="substitui a 1ª prioridade do prompt")
        p.add_argument(
            "--saida",
            help="pasta de saída (padrão: Downloads do Windows ou outputs/auditorias)",
        )
        if nome == "prompt":
            p.add_argument("--para", choices=["codex", "gemini"], default="codex")
    a = ap.parse_args()
    validar(a)
    {"prompt": cmd_prompt, "codex": cmd_codex, "gemini": cmd_gemini}[a.acao](a)


if __name__ == "__main__":
    main()
