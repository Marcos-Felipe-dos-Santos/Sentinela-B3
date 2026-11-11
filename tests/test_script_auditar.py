"""Testes de `scripts/auditar.py` (F3-0e): roteamento por autoria e montagem do prompt.

Repositório git temporário com commits dos dois executores intercalados; nenhum CLI de
auditoria é chamado.
"""

import hashlib
import importlib.util
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).parents[1]
SCRIPT = RAIZ / "scripts" / "auditar.py"


def _carregar():
    spec = importlib.util.spec_from_file_location("auditar_script", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


auditar = _carregar()

AMBIENTE_GIT = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def _git(repo, *args):
    ambiente = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    ambiente.update(AMBIENTE_GIT)
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=ambiente,
    ).stdout.strip()


def _commit(repo, mensagem):
    _git(repo, "commit", "-q", "--allow-empty", "-m", mensagem)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q")
    base = _commit(tmp_path, "chore: base\n\nExecutor: codex")
    hashes = {"base": base, "claude": [], "codex": [], "sem": [], "dois": []}
    sequencia = [
        ("claude", "feat: a\n\nExecutor: claude-code"),
        ("codex", "fix: b\n\nExecutor: codex"),
        ("sem", "docs: sem executor"),
        ("claude", "fix: c\n\ncorpo\nExecutor: claude-code\n\nCo-Authored-By: x"),
        ("codex", "feat: d\n\nExecutor: codex"),
        ("dois", "fix: e\n\nExecutor: codex\nExecutor: claude-code"),
        ("sem", "docs: menciona Executor: codex no meio da linha"),
        ("sem", "docs: Executor: claude-code-bot\n\nExecutor: claude-code-bot"),
    ]
    for chave, mensagem in sequencia:
        hashes[chave].append(_commit(tmp_path, mensagem))
    monkeypatch.chdir(tmp_path)
    return hashes


def test_selecao_por_autoria_no_intervalo(repo):
    selecao = auditar.commits_por_executor(repo["base"])
    assert set(selecao["claude"]) == set(repo["claude"] + repo["dois"])
    assert set(selecao["codex"]) == set(repo["codex"] + repo["dois"])
    assert set(selecao["sem"]) == set(repo["sem"])
    assert repo["base"] not in {h for v in selecao.values() for h in v}
    # ordem do git log, do mais novo ao mais antigo
    todos = _git(Path.cwd(), "log", "--format=%H", f"{repo['base']}..HEAD").split()
    assert selecao["sem"] == [h for h in todos if h in repo["sem"]]


def test_prompt_do_codex_traz_exatamente_os_hashes_claude(repo):
    selecao = auditar.commits_por_executor(repo["base"])
    bloco = auditar.bloco_autoria("codex", selecao)
    listados = [linha[2:] for linha in bloco.splitlines() if linha.startswith("- ")]
    alvo = selecao["claude"]
    assert listados[: len(alvo)] == alvo
    assert set(alvo) == set(repo["claude"] + repo["dois"])
    assert "`Executor: claude-code` no intervalo (3):" in bloco
    assert not set(repo["codex"]) & set(listados)


def test_prompt_do_claude_traz_exatamente_os_hashes_codex(repo):
    selecao = auditar.commits_por_executor(repo["base"])
    bloco = auditar.bloco_autoria("claude", selecao)
    listados = [linha[2:] for linha in bloco.splitlines() if linha.startswith("- ")]
    alvo = selecao["codex"]
    assert listados[: len(alvo)] == alvo
    assert set(alvo) == set(repo["codex"] + repo["dois"])
    assert "`Executor: codex` no intervalo (3):" in bloco
    assert not set(repo["claude"]) & set(listados)


def test_commit_sem_executor_sai_a_parte(repo):
    selecao = auditar.commits_por_executor(repo["base"])
    bloco = auditar.bloco_autoria("claude", selecao)
    parte = bloco.split("Commits sem linha `Executor:`")[1]
    assert "liste-os à parte no relatório, sem auditar (3):" in parte
    assert [
        linha[2:] for linha in parte.splitlines() if linha.startswith("- ")
    ] == selecao["sem"]


def test_sem_commit_sem_executor_nao_ha_bloco_a_parte():
    selecao = {"claude": ["a"], "codex": ["b"], "sem": []}
    assert auditar.bloco_autoria("claude", selecao) == (
        "\nSELEÇÃO POR AUTORIA (decisão 23), que restringe o ESCOPO acima: audite todos "
        "estes commits, e só eles, marcados `Executor: codex` no intervalo (1):\n- b\n"
    )


def _args(modo="fase", desde=None):
    return SimpleNamespace(
        modo=modo, fase="3", arquivo=None, desde=desde, foco=None, saida=None
    )


@pytest.fixture
def prompts(repo, monkeypatch, tmp_path_factory):
    # pasta temporária do sistema fora do repositório (evidências de saída dentro dele)
    monkeypatch.setattr(
        auditar.tempfile, "tempdir", str(tmp_path_factory.mktemp("sis"))
    )
    _git(Path.cwd(), "tag", "v2-fase-2c", repo["base"])  # base da fase anterior
    pasta = Path.cwd() / "docs" / "loop" / "prompts"
    pasta.mkdir(parents=True)
    (pasta / "fase.md").write_text("Fase {FASE}.\n{ACESSO}\n", encoding="utf-8")
    (pasta / "fechamento.md").write_text(
        "Fechamento {FASE}.\n{ACESSO}\n", encoding="utf-8"
    )
    monkeypatch.setattr(auditar, "PROMPTS", pasta)
    return repo


@pytest.mark.parametrize(("para", "outra"), [("claude", "codex"), ("codex", "claude")])
def test_montar_prompt_da_fase_com_desde_acrescenta_a_outra_familia(
    prompts, para, outra
):
    texto, v = auditar.montar_prompt(_args(desde=prompts["base"]), para)
    assert texto.startswith("Fase 3.\n" + auditar.preencher(auditar.ACESSO[para], v))
    assert "{EVIDENCIAS}" not in texto
    selecao = auditar.commits_por_executor(prompts["base"])
    assert texto.endswith(auditar.bloco_autoria(para, selecao))


def test_montar_prompt_sem_desde_ou_outro_modo_nao_seleciona(prompts):
    assert "SELEÇÃO POR AUTORIA" not in auditar.montar_prompt(_args(), "claude")[0]
    texto, _ = auditar.montar_prompt(_args("fechamento", prompts["base"]), "codex")
    assert "SELEÇÃO POR AUTORIA" not in texto
    gemini, _ = auditar.montar_prompt(_args(desde=prompts["base"]), "gemini")
    assert "SELEÇÃO POR AUTORIA" not in gemini


def test_cmd_claude_grava_log_e_relatorio_sem_chamar_o_cli(
    prompts, tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(auditar.shutil, "which", lambda nome: "/bin/" + nome)
    chamadas = []

    def _rodar(comando, **kw):
        chamadas.append(comando)
        return SimpleNamespace(
            returncode=0, stdout="Relatório.\nVeredito: pode seguir\n", stderr="aviso\n"
        )

    a = _args(desde=prompts["base"])
    a.saida = str(tmp_path / "saida")
    auditar.cmd_claude(a, rodar=_rodar)
    (comando,) = chamadas
    assert comando[:2] == ["claude", "-p"] and "SELEÇÃO POR AUTORIA" in comando[-1]
    log = tmp_path / "saida" / "auditoria-fase-3-claude.txt"
    assert (
        log.read_text(encoding="utf-8") == "Relatório.\nVeredito: pode seguir\naviso\n"
    )
    rel = tmp_path / "saida" / "auditoria-fase-3-claude-relatorio.md"
    assert rel.read_text(encoding="utf-8") == "Relatório.\nVeredito: pode seguir\n"
    assert "Veredito: pode seguir" in capsys.readouterr().out
    # segunda rodada não sobrescreve a primeira
    auditar.cmd_claude(a, rodar=_rodar)
    assert (tmp_path / "saida" / "auditoria-fase-3-claude-2.txt").is_file()


def test_cmd_claude_com_erro_avisa_sem_trocar_de_familia(
    prompts, tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(auditar.shutil, "which", lambda nome: "/bin/" + nome)
    chamadas = []

    def _rodar(comando, **kw):
        chamadas.append(comando[0])
        return SimpleNamespace(returncode=1, stdout="", stderr="limite de uso\n")

    a = _args(desde=prompts["base"])
    a.saida = str(tmp_path / "saida")
    auditar.cmd_claude(a, rodar=_rodar)
    assert chamadas == ["claude"]
    assert "Sem cota: registre e pare, sem trocar a família" in capsys.readouterr().err


def test_cmd_claude_sem_cli_sai(prompts, monkeypatch):
    monkeypatch.setattr(auditar.shutil, "which", lambda nome: None)
    with pytest.raises(SystemExit, match="claude não encontrado"):
        auditar.cmd_claude(_args(desde=prompts["base"]))


def test_lista_vazia_da_outra_familia_e_explicita(capsys):
    bloco = auditar.bloco_autoria("claude", {"claude": ["a"], "codex": [], "sem": []})
    assert "no intervalo (0):" in bloco
    assert (
        "- (nenhum: registre no relatório que não há commit dessa família no intervalo)"
        in bloco
    )


def test_montar_prompt_avisa_sem_commit_da_outra_familia(prompts, capsys):
    ultimo = _git(Path.cwd(), "rev-parse", "HEAD")
    texto, _ = auditar.montar_prompt(_args(desde=ultimo), "claude")
    assert "no intervalo (0):" in texto
    assert "nenhum commit `Executor: codex` no intervalo." in capsys.readouterr().err


def test_desde_invalido_no_modo_fase_sai_sem_traceback(prompts, monkeypatch):
    (Path.cwd() / "docs" / "loop" / "protocolo.md").write_text("x", encoding="utf-8")
    a = _args(desde="naoexiste")
    with pytest.raises(SystemExit, match="--desde naoexiste: commit não encontrado"):
        auditar.validar(a)


def test_acesso_do_claude_nao_roda_a_suite_e_aponta_as_evidencias():
    acesso = auditar.ACESSO["claude"]
    assert "A suíte não roda nesta auditoria" in acesso
    assert "pytest -q" not in acesso
    assert "sem terminal" in acesso and "{EVIDENCIAS}" in acesso


def test_cmd_claude_sem_relatorio_avisa(prompts, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(auditar.shutil, "which", lambda nome: "/bin/" + nome)
    a = _args(desde=prompts["base"])
    a.saida = str(tmp_path / "saida")
    auditar.cmd_claude(
        a,
        rodar=lambda comando, **kw: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    assert "o Claude terminou sem relatório" in capsys.readouterr().err


def _entre(comando, inicio, fim):
    return comando[comando.index(inicio) + 1 : comando.index(fim)]


def test_comando_do_claude_sem_bash_sem_escrita_e_sem_add_dir(tmp_path):
    comando = auditar.comando_claude("PROMPT", tmp_path)
    assert comando[:2] == ["claude", "-p"]
    assert comando[comando.index("--permission-mode") + 1] == "dontAsk"
    assert comando[comando.index("--setting-sources") + 1] == "project"
    assert "--strict-mcp-config" in comando and "--mcp-config" not in comando
    assert _entre(comando, "--tools", "--disallowedTools") == ["Read", "Grep", "Glob"]
    # sem liberação ampla: o dontAsk nega a leitura fora da pasta de trabalho (a cópia)
    assert "--allowedTools" not in comando
    negados = _entre(comando, "--disallowedTools", "--output-format")
    assert {"Edit", "Write", "NotebookEdit", "Bash"} <= set(negados)
    assert negados[-1] == f"Read(/{tmp_path.resolve()}/**)"  # repositório real negado
    assert not [c for c in comando[:-1] if c.startswith("Bash(")]
    assert "--add-dir" not in comando  # o repositório real não é passado ao auditor
    assert comando[-2:] == ["--", "PROMPT"]


def test_negacoes_de_leitura_ficam_como_segunda_camada(tmp_path):
    negados = _entre(
        auditar.comando_claude("P", tmp_path), "--disallowedTools", "--output-format"
    )
    for padrao in (
        "Read(**/.env)",
        "Read(**/.env.*)",
        "Read(**/*.db)",
        "Read(**/*.sqlite*)",
        "Read(./outputs/**)",
    ):
        assert padrao in negados
    # o CLI não aplica Grep(caminho) nem Glob(caminho); as regras Read valem para os três
    assert not [n for n in negados if n.startswith(("Grep(", "Glob("))]


@pytest.mark.parametrize(
    ("modo", "desde", "selecao"),
    [
        ("fase", None, None),
        ("fase", "d" * 40, ["a" * 40, "b" * 40]),
        ("fechamento", "d" * 40, None),
        ("documento", None, None),
        ("ficha", None, None),
    ],
)
def test_comandos_de_evidencia_so_entre_commits(modo, desde, selecao):
    a = _args(modo, desde)
    ini = auditar.inicio_do_intervalo(a, "e" * 40)
    comandos = auditar.comandos_de_evidencia(modo, ini, selecao, final="f" * 40)
    assert comandos[-1] == auditar.RUFF_CI
    assert auditar.RUFF_CI == [
        "ruff",
        "check",
        "--select",
        "E9,F63,F7,F82",
        "--no-cache",
        ".",
    ]
    assert ini == (desde if desde and modo in ("fase", "fechamento") else "e" * 40)
    assert comandos[0] == [
        "git",
        "--no-pager",
        "log",
        "--reverse",
        "--stat",
        "--format=fuller",
        f"{ini}..{'f' * 40}",
    ]
    for comando in comandos[:-1]:
        assert comando[:2] == ["git", "--no-pager"]
        assert comando[2] in ("log", "show", "diff")
    texto = " ".join(" ".join(c) for c in comandos)
    for proibido in (
        "--no-index",
        "--fix",
        "--add-noqa",
        "--output",
        "--cache-dir",
        "-o",
    ):
        assert proibido not in texto.split()
    mostrados = [c[-4] for c in comandos if c[2] == "show"]
    if selecao:
        assert mostrados == list(reversed(selecao))
    else:
        assert mostrados == []
    if modo in ("documento", "ficha"):
        assert [c[2] for c in comandos[:-1]] == ["log"]


@pytest.mark.parametrize(
    ("ini", "selecao"),
    [
        ("--output=/tmp/x", None),
        ("HEAD", None),
        ("e" * 40, ["--no-index"]),
        ("e" * 39, None),
    ],
)
def test_comandos_de_evidencia_recusam_o_que_nao_for_hash(ini, selecao):
    with pytest.raises(ValueError, match="hashes completos"):
        auditar.comandos_de_evidencia("fase", ini, selecao, final="f" * 40)


def test_commit_completo_resolve_e_recusa_opcao(prompts):
    assert auditar.commit_completo("HEAD") == _git(Path.cwd(), "rev-parse", "HEAD")
    with pytest.raises(SystemExit, match="commit não encontrado"):
        auditar.commit_completo("--output=x")


def test_commit_completo_passa_a_referencia_depois_de_end_of_options(monkeypatch):
    chamadas = []

    def _run(comando, **kw):
        chamadas.append(comando)
        return SimpleNamespace(returncode=0, stdout="e" * 40 + "\n")

    monkeypatch.setattr(auditar.subprocess, "run", _run)
    assert auditar.commit_completo("--all") == "e" * 40
    (comando,) = chamadas
    assert comando[-2:] == ["--end-of-options", "--all^{commit}"]


def test_patches_das_evidencias_excluem_o_golden():
    excluir = ["--", ".", ":(exclude)tests/fixtures/golden_motores.jsonl"]
    for selecao in (None, ["a" * 40]):
        comandos = auditar.comandos_de_evidencia(
            "fase", "e" * 40, selecao, final="f" * 40
        )
        patches = [
            c
            for c in comandos
            if c[2] == "show" or (c[2] == "diff" and "--stat" not in c)
        ]
        assert patches and all(c[-3:] == excluir for c in patches)


def _instantaneo(repo):
    status = _git(repo, "status", "--porcelain", "--ignored", "--untracked-files=all")
    rastreados = _git(repo, "ls-files").splitlines()
    hashes = {
        c: hashlib.sha256((repo / c).read_bytes()).hexdigest() for c in rastreados
    }
    return status, hashes


def _arquivos(pasta):
    return sorted(
        p.relative_to(pasta).as_posix() for p in pasta.rglob("*") if p.is_file()
    )


def _com_ignorados(repo):
    """Rastreados (um com erro de sintaxe) e, fora do git, .log, .db, .env e outputs/."""
    (repo / ".gitignore").write_text("*.log\n*.db\n.env\noutputs/\n", encoding="utf-8")
    (repo / "pkg").mkdir(exist_ok=True)
    (repo / "pkg" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "ruim.py").write_text("x = (\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "pkg/a.py", "ruim.py")
    final = _commit(repo, "fix: arquivos\n\nExecutor: codex")
    (repo / "sentinela.log").write_text("Posição removida: TSTE3\n", encoding="utf-8")
    (repo / "carteira.db").write_text("SONDA_DB\n", encoding="utf-8")
    (repo / ".env").write_text("CHAVE=SONDA_ENV\n", encoding="utf-8")
    (repo / "outputs").mkdir(exist_ok=True)
    (repo / "outputs" / "c.txt").write_text("SONDA_OUT\n", encoding="utf-8")
    (repo / "pkg" / "a.py").write_text("x = 2  # não commitado\n", encoding="utf-8")
    (repo / "solto.py").write_text("y = 1\n", encoding="utf-8")
    return final


def test_exportacao_traz_so_a_arvore_rastreada_do_commit(repo, tmp_path_factory):
    final = _com_ignorados(Path.cwd())
    destino = tmp_path_factory.mktemp("copia")
    auditar.exportar_arvore(final, destino)
    assert _arquivos(destino) == [".gitignore", "pkg/a.py", "ruim.py"]
    assert (destino / "pkg" / "a.py").read_text(encoding="utf-8") == "x = 1\n"


@pytest.mark.parametrize("commit", ["HEAD", "--output=x", "e" * 39])
def test_exportacao_recusa_o_que_nao_for_hash(commit, tmp_path):
    with pytest.raises(ValueError, match="hash completo"):
        auditar.exportar_arvore(commit, tmp_path)


def test_cmd_claude_roda_na_copia_e_o_repositorio_fica_identico(
    prompts, monkeypatch, tmp_path_factory, capsys
):
    repo = Path.cwd().resolve()
    _com_ignorados(repo)
    monkeypatch.setattr(auditar.shutil, "which", lambda nome: "/bin/" + nome)
    antes = _instantaneo(repo)
    saida = tmp_path_factory.mktemp("downloads")
    a = _args(desde=prompts["base"])
    a.saida = str(saida)
    vistos = {}

    def _rodar(comando, **kw):
        copia = Path(kw["cwd"]).resolve()
        vistos.update(
            comando=comando,
            stdin=kw["stdin"],
            copia=copia,
            arquivos=_arquivos(copia),
            evidencias=(copia / "evidencias.txt").read_text(encoding="utf-8"),
        )
        return SimpleNamespace(
            returncode=0, stdout="Veredito: pode seguir\n", stderr=""
        )

    auditar.cmd_claude(a, rodar=_rodar)
    assert _instantaneo(repo) == antes
    copia = vistos["copia"]
    assert repo not in copia.parents and copia != repo
    assert not copia.exists()  # removida pelo próprio script
    assert vistos["stdin"] is subprocess.DEVNULL
    assert vistos["arquivos"] == [".gitignore", "evidencias.txt", "pkg/a.py", "ruim.py"]
    comando = vistos["comando"]
    assert "--add-dir" not in comando
    assert str(repo) not in comando[-1]  # o prompt não cita o repositório real
    assert (
        comando[
            comando.index("--disallowedTools") + 1 : comando.index("--output-format")
        ][-1]
        == f"Read(/{repo}/**)"
    )
    assert "estão em evidencias.txt" in comando[-1]
    texto = vistos["evidencias"]
    final = _git(repo, "rev-parse", "HEAD")
    assert f"Commit exportado: {final}" in texto
    assert (
        "===== $ git --no-pager log --reverse --stat --format=fuller "
        f"{prompts['base']}..{final}" in texto
    )
    assert (
        "===== $ ruff check --select E9,F63,F7,F82 --no-cache . (saída 1) ====="
        in texto
    )
    assert "ruim.py" in texto.split("$ ruff check")[1]
    codex = auditar.commits_por_executor(prompts["base"])["codex"]
    mostrados = [
        linha.split()[8]
        for linha in texto.splitlines()
        if linha.startswith("===== $ git --no-pager show")
    ]
    assert mostrados == list(reversed(codex))
    assert _arquivos(saida) == [
        "auditoria-fase-3-claude-evidencias.txt",
        "auditoria-fase-3-claude-relatorio.md",
        "auditoria-fase-3-claude.txt",
    ]
    assert "SONDA" not in texto and "TSTE3" not in texto


def test_pasta_temporaria_e_removida_mesmo_com_erro(prompts, monkeypatch, tmp_path):
    monkeypatch.setattr(auditar.shutil, "which", lambda nome: "/bin/" + nome)
    vistos = []

    def _rodar(comando, **kw):
        vistos.append(Path(kw["cwd"]))
        raise RuntimeError("CLI caiu")

    a = _args(desde=prompts["base"])
    a.saida = str(tmp_path / "saida")
    with pytest.raises(RuntimeError, match="CLI caiu"):
        auditar.cmd_claude(a, rodar=_rodar)
    (copia,) = vistos
    assert not copia.exists()
    assert list(Path(auditar.tempfile.tempdir).iterdir()) == []


def test_tmpdir_dentro_do_repositorio_e_recusado(prompts, monkeypatch, tmp_path):
    monkeypatch.setattr(auditar.shutil, "which", lambda nome: "/bin/" + nome)
    dentro = Path.cwd() / "tmp-interno"
    dentro.mkdir()
    monkeypatch.setattr(auditar.tempfile, "tempdir", str(dentro))
    a = _args(desde=prompts["base"])
    a.saida = str(tmp_path / "saida")
    with pytest.raises(SystemExit, match="mude o TMPDIR"):
        auditar.cmd_claude(a, rodar=lambda *x, **k: pytest.fail("não chama o CLI"))
    assert list(dentro.iterdir()) == []


def test_documento_nao_rastreado_e_recusado(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("x", encoding="utf-8")
    auditar.documento_na_copia("docs/a.md", tmp_path)
    with pytest.raises(SystemExit, match="não está rastreado no commit final"):
        auditar.documento_na_copia("docs/novo.md", tmp_path)
    for fora in (str(tmp_path / "docs" / "a.md"), "docs/../docs/a.md"):
        with pytest.raises(SystemExit, match="caminho relativo à raiz"):
            auditar.documento_na_copia(fora, tmp_path)


def test_comandos_de_evidencia_recusam_final_que_nao_e_hash():
    with pytest.raises(ValueError, match="hashes completos"):
        auditar.comandos_de_evidencia("fase", "e" * 40, None, final="HEAD")


def test_comando_ausente_vira_saida_127():
    assert auditar.rodar_capturando(["comando-inexistente-sentinela"]) == (
        127,
        "comando não encontrado: comando-inexistente-sentinela\n",
    )


def test_validar_passa_o_desde_depois_de_end_of_options(prompts, monkeypatch):
    (Path.cwd() / "docs" / "loop" / "protocolo.md").write_text("x", encoding="utf-8")
    chamadas = []

    def _run(comando, **kw):
        chamadas.append(comando)
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(auditar.subprocess, "run", _run)
    with pytest.raises(SystemExit, match="commit não encontrado"):
        auditar.validar(_args(desde="--all"))
    assert chamadas[0][-2:] == ["--end-of-options", "--all^{commit}"]


def test_exportacao_de_arvore_vazia_da_pasta_vazia(repo, tmp_path_factory):
    destino = tmp_path_factory.mktemp("vazia")
    auditar.exportar_arvore(repo["base"], destino)
    assert list(destino.iterdir()) == []


def test_exportacao_recusa_tar_que_sai_da_pasta(monkeypatch, tmp_path):
    bruto = io.BytesIO()
    with tarfile.open(fileobj=bruto, mode="w") as tar:
        info = tarfile.TarInfo("../fora.txt")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"x"))
    monkeypatch.setattr(
        auditar.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=bruto.getvalue()),
    )
    destino = tmp_path / "copia"
    destino.mkdir()
    with pytest.raises(tarfile.OutsideDestinationError):
        auditar.exportar_arvore("e" * 40, destino)
    assert not (tmp_path / "fora.txt").exists()
