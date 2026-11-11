"""Testes de `scripts/fechar_fase.py` (F3-0f): repositório git temporário, sem rede."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "fechar_fase.py"


def _carregar():
    spec = importlib.util.spec_from_file_location("fechar_fase_script", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


fechar_fase = _carregar()

AGENTS_ABERTA = "# Agentes\n\n## Fase atual\n\nFase 9 ativa no branch `v2/fase-9`.\n\n## Outra\n\n`v2/fase-9` citado fora da seção.\n"
AGENTS_FECHADA = "# Agentes\n\n## Fase atual\n\nFase 9 fechada; próxima em proposta.\n\n## Outra\n\n`v2/fase-9` citado fora da seção.\n"


def _git(repo, *args):
    ambiente = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    ambiente.update(
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@t",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@t",
    )
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=ambiente,
    ).stdout.strip()


def _commit(repo, arquivo, texto, mensagem):
    (repo / arquivo).write_text(texto, encoding="utf-8")
    _git(repo, "add", arquivo)
    _git(repo, "commit", "-q", "-m", mensagem)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _commit(tmp_path, "AGENTS.md", AGENTS_ABERTA, "base")
    _git(tmp_path, "checkout", "-q", "-b", "v2/fase-9")
    _commit(tmp_path, "a.txt", "a", "feat: a")
    _git(tmp_path, "checkout", "-q", "main")
    _git(tmp_path, "merge", "-q", "--no-ff", "-m", "Merge pull request #9", "v2/fase-9")
    _git(tmp_path, "tag", "v2-fase-9")
    _commit(tmp_path, "AGENTS.md", AGENTS_FECHADA, "docs: close phase 9")
    return tmp_path


def _branches(repo):
    return _git(repo, "branch", "--format=%(refname:short)").splitlines()


def _fechar(repo, aplicar=False):
    return fechar_fase.fechar("9", raiz=repo, aplicar=aplicar)


def test_simulacao_confere_tudo_e_nao_apaga(repo):
    codigo, linhas = _fechar(repo)
    assert codigo == 0
    assert linhas[0] == "árvore limpa"
    assert linhas[1].startswith("merge ") and linhas[1].endswith(" na main")
    assert linhas[2].startswith("tag v2-fase-9 no merge ")
    assert linhas[3:] == [
        "Fase atual sem a fase fechada",
        "v2/fase-9 mesclado na main",
        "simulação: apagaria o branch v2/fase-9 (use --aplicar)",
    ]
    assert "v2/fase-9" in _branches(repo)


def test_aplicar_apaga_o_branch(repo):
    codigo, linhas = _fechar(repo, aplicar=True)
    assert codigo == 0
    assert linhas[-1] == "branch v2/fase-9 apagado"
    assert "v2/fase-9" not in _branches(repo)


def _interrompe(repo, motivo):
    codigo, linhas = _fechar(repo, aplicar=True)
    assert codigo == 1
    assert linhas[-1] == f"INTERROMPIDO: {motivo}; nada foi apagado"
    assert "v2/fase-9" in _branches(repo)


def test_arvore_suja_interrompe(repo):
    (repo / "solto.txt").write_text("x")
    _interrompe(repo, "árvore com alteração pendente")


def test_sem_merge_commit_interrompe(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _commit(tmp_path, "AGENTS.md", AGENTS_FECHADA, "base")
    _git(tmp_path, "checkout", "-q", "-b", "v2/fase-9")
    _commit(tmp_path, "a.txt", "a", "feat: a")
    _git(tmp_path, "checkout", "-q", "main")
    _git(tmp_path, "merge", "-q", "--ff-only", "v2/fase-9")  # sem merge commit
    _git(tmp_path, "tag", "v2-fase-9")
    _interrompe(
        tmp_path, "nenhum merge commit da main tem o topo de v2/fase-9 como segundo pai"
    )


def test_branch_inexistente_interrompe(repo):
    codigo, linhas = fechar_fase.fechar("8", raiz=repo, aplicar=True)
    assert codigo == 1
    assert linhas[-1] == "INTERROMPIDO: branch v2/fase-8 não existe; nada foi apagado"


def test_commit_depois_do_merge_no_branch_interrompe(repo):
    _git(repo, "checkout", "-q", "v2/fase-9")
    _commit(repo, "b.txt", "b", "feat: b depois do merge")
    _git(repo, "checkout", "-q", "main")
    _interrompe(
        repo, "nenhum merge commit da main tem o topo de v2/fase-9 como segundo pai"
    )


def test_sem_tag_interrompe(repo):
    _git(repo, "tag", "-d", "v2-fase-9")
    _interrompe(repo, "tag v2-fase-9 não existe")


def test_tag_fora_do_merge_interrompe(repo):
    _git(repo, "tag", "-f", "v2-fase-9", "HEAD")
    codigo, linhas = _fechar(repo, aplicar=True)
    assert codigo == 1
    assert linhas[-1].startswith("INTERROMPIDO: tag v2-fase-9 não aponta para o merge ")
    assert "v2/fase-9" in _branches(repo)


def test_fase_atual_ainda_aberta_interrompe(repo):
    _commit(repo, "AGENTS.md", AGENTS_ABERTA, "docs: reabre")
    _interrompe(repo, "Fase atual do AGENTS.md ainda cita v2/fase-9")


def test_agents_sem_secao_interrompe(repo):
    _commit(repo, "AGENTS.md", "# Agentes\n", "docs: sem seção")
    _interrompe(repo, "AGENTS.md sem a seção Fase atual")


def test_agents_ausente_interrompe(repo):
    _git(repo, "rm", "-q", "AGENTS.md")
    _git(repo, "commit", "-q", "-m", "sem agents")
    _interrompe(repo, "AGENTS.md ausente na main")


def test_nao_mesclado_interrompe(repo):
    real = fechar_fase.git_real(repo)

    def _git_falso(args):
        if args[:2] == ["branch", "--merged"]:
            return fechar_fase.Execucao(0, "main\n")
        return real(args)

    codigo, linhas = fechar_fase.fechar("9", raiz=repo, aplicar=True, git=_git_falso)
    assert codigo == 1
    assert (
        linhas[-1]
        == "INTERROMPIDO: v2/fase-9 não está em git branch --merged main; nada foi apagado"
    )
    assert "v2/fase-9" in _branches(repo)


def test_falha_do_git_ao_apagar_e_relatada(repo):
    real = fechar_fase.git_real(repo)

    def _git_falso(args):
        if args[:2] == ["branch", "-d"]:
            return fechar_fase.Execucao(1, "error: cannot delete branch")
        return real(args)

    codigo, linhas = fechar_fase.fechar("9", raiz=repo, aplicar=True, git=_git_falso)
    assert codigo == 1
    assert linhas[-1] == "git branch -d v2/fase-9 falhou: error: cannot delete branch"
    assert "v2/fase-9" in _branches(repo)


def test_main_simula_por_padrao(repo, monkeypatch, capsys):
    monkeypatch.chdir(repo)
    assert fechar_fase.main(["9"]) == 0
    assert capsys.readouterr().out.splitlines()[-1].startswith("simulação:")
    assert "v2/fase-9" in _branches(repo)
    assert fechar_fase.main([]) == 2


def _com_falha(repo, prefixo):
    real = fechar_fase.git_real(repo)

    def _git(args):
        if list(args[: len(prefixo)]) == prefixo:
            return fechar_fase.Execucao(128, "")
        return real(args)

    return _git


@pytest.mark.parametrize(
    ("prefixo", "motivo"),
    [
        (["status"], "git status falhou"),
        (["log"], "main não existe"),
        (["branch", "--merged"], "git branch --merged main falhou"),
    ],
)
def test_falha_do_git_em_cada_verificacao_interrompe(repo, prefixo, motivo):
    codigo, linhas = fechar_fase.fechar(
        "9", raiz=repo, aplicar=True, git=_com_falha(repo, prefixo)
    )
    assert codigo == 1
    assert linhas[-1] == f"INTERROMPIDO: {motivo}; nada foi apagado"
    assert "v2/fase-9" in _branches(repo)


def test_sem_main_interrompe(repo):
    _git(repo, "branch", "-m", "main", "principal")
    _interrompe(repo, "main não existe")


def test_agents_da_main_vale_mesmo_com_outro_checkout(repo):
    _git(repo, "checkout", "-q", "v2/fase-9")  # AGENTS.md do branch ainda aberto
    codigo, linhas = _fechar(repo)
    assert codigo == 0
    assert "Fase atual sem a fase fechada" in linhas


def test_erro_real_do_git_aparece_na_mensagem(repo):
    _git(repo, "checkout", "-q", "v2/fase-9")
    codigo, linhas = _fechar(repo, aplicar=True)
    assert codigo == 1
    assert linhas[-1].startswith("git branch -d v2/fase-9 falhou: ")
    assert len(linhas[-1]) > len("git branch -d v2/fase-9 falhou: ")


def test_merge_feito_fora_da_main_nao_vale(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _commit(tmp_path, "AGENTS.md", AGENTS_FECHADA, "base")
    _git(tmp_path, "checkout", "-q", "-b", "v2/fase-9")
    _commit(tmp_path, "a.txt", "a", "feat: a")
    _git(tmp_path, "checkout", "-q", "-b", "integracao", "main")
    _git(tmp_path, "merge", "-q", "--no-ff", "-m", "merge na integração", "v2/fase-9")
    _git(tmp_path, "checkout", "-q", "main")
    _git(tmp_path, "merge", "-q", "--no-ff", "-m", "merge da integração", "integracao")
    _git(tmp_path, "tag", "v2-fase-9")
    _interrompe(
        tmp_path, "nenhum merge commit da main tem o topo de v2/fase-9 como segundo pai"
    )


@pytest.mark.parametrize("fase", ["9^", "../x", "", "3 4", "2B"])
def test_fase_invalida_sai_com_2(repo, fase):
    codigo, linhas = fechar_fase.fechar(fase, raiz=repo, aplicar=True)
    assert codigo == 2
    assert linhas[0].startswith("fase inválida")
    assert "v2/fase-9" in _branches(repo)
