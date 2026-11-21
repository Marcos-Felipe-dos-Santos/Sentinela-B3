"""Testes de `scripts/gate.py` (F3-0d): verificações injetadas, sem rodar a suíte real."""

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "gate.py"

FILA = """# Fila de teste

- [ ] **T-1** · feat · `feat: one` — Arquivos: `scripts/x.py`, `tests/test_x.py`, `sentinela/data/pit/`.
- [ ] **T-2** · docs · `docs: two` — Arquivos: `docs/a.md`.
"""


def _carregar():
    spec = importlib.util.spec_from_file_location("gate_script", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo  # as dataclasses do script procuram o módulo aqui
    spec.loader.exec_module(modulo)
    return modulo


gate = _carregar()


class _Repo:
    """Respostas por comando; o que não estiver aqui responde verde."""

    def __init__(self, tmp_path, **respostas):
        self.raiz = tmp_path
        self.chamadas = []
        golden = tmp_path / gate.GOLDEN
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text('{"a": 1}\n', encoding="utf-8")
        self.respostas = {
            "pytest": gate.Execucao(0, "....\n= 10 passed, 1 skipped in 1.0s =\n"),
            "ruff_ci": gate.Execucao(0, "All checks passed!\n"),
            "ruff": gate.Execucao(0, "All checks passed!\n"),
            "check": gate.Execucao(0, ""),
            "rev-parse": gate.Execucao(0, "abc\n"),
            "hash-object": gate.Execucao(0, "abc\n"),
            "name-only": gate.Execucao(0, "scripts/x.py\ntests/test_x.py\n"),
        }
        self.respostas.update(respostas)

    def __call__(self, comando):
        self.chamadas.append(list(comando))
        if "pytest" in comando:
            return self.respostas["pytest"]
        if comando[:2] == ["ruff", "check"]:
            return self.respostas["ruff_ci" if "--select" in comando else "ruff"]
        if "--check" in comando:
            return self.respostas["check"]
        if "--name-only" in comando:
            return self.respostas["name-only"]
        if comando[:2] == ["git", "rev-parse"] and comando[2].startswith(":"):
            return self.respostas.get("indice", self.respostas["rev-parse"])
        return self.respostas[comando[1]]


def _rodar(tmp_path, repo, ident="T-1", **kw):
    fila = tmp_path / "fila.md"
    fila.write_text(FILA, encoding="utf-8")
    return gate.rodar_gate(ident, fila_md=fila, raiz=tmp_path, rodar=repo, **kw)


def test_tudo_verde_sai_com_zero_e_uma_linha_por_verificacao(tmp_path):
    (tmp_path / "sentinela" / "data").mkdir(parents=True)
    repo = _Repo(tmp_path)
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 0
    assert linhas == [
        "[OK] suíte: = 10 passed, 1 skipped in 1.0s =",
        "[OK] Ruff CI: All checks passed!",
        "[OK] Ruff completo (sentinela/data): All checks passed!",
        "[OK] git diff --staged --check: limpo",
        "[OK] golden: igual ao HEAD (SHA256 "
        + hashlib.sha256(b'{"a": 1}\n').hexdigest()[:16]
        + "…)",
        "[OK] arquivos proibidos no stage: nenhum",
        "[OK] fora da linha do item: nenhum",
    ]
    assert ["ruff", "check", "--select", "E9,F63,F7,F82", "."] in repo.chamadas
    assert ["ruff", "check", "sentinela/data"] in repo.chamadas
    assert ["git", "diff", "--staged", "--check"] in repo.chamadas
    assert ["git", "rev-parse", f"HEAD:{gate.GOLDEN}"] in repo.chamadas
    assert ["git", "hash-object", gate.GOLDEN] in repo.chamadas


def test_nao_roda_mutacao_nem_comando_que_escreve(tmp_path):
    repo = _Repo(tmp_path)
    _rodar(tmp_path, repo)
    texto = " ".join(" ".join(c) for c in repo.chamadas)
    for proibido in ("mutmut", "format", "--fix", "add", "commit", "stash", "checkout"):
        assert proibido not in texto.split()


def test_suite_vermelha_lista_os_testes_que_falharam(tmp_path):
    saida = (
        "..F.E\n"
        "FAILED tests/test_a.py::test_um - AssertionError: x\n"
        "ERROR tests/test_b.py::test_dois - RuntimeError\n"
        "= 1 failed, 3 passed, 1 error in 1s =\n"
    )
    codigo, linhas = _rodar(tmp_path, _Repo(tmp_path, pytest=gate.Execucao(1, saida)))
    assert codigo == 1
    assert linhas[:3] == [
        "[FALHA] suíte: = 1 failed, 3 passed, 1 error in 1s =",
        "[FALHA] falhou: tests/test_a.py::test_um",
        "[FALHA] falhou: tests/test_b.py::test_dois",
    ]


def test_resumo_nunca_passa_de_20_linhas(tmp_path):
    saida = (
        "".join(f"FAILED tests/t.py::test_{n} - x\n" for n in range(40))
        + "= 40 failed =\n"
    )
    codigo, linhas = _rodar(tmp_path, _Repo(tmp_path, pytest=gate.Execucao(1, saida)))
    assert codigo == 1
    assert len(linhas) == gate.LIMITE_LINHAS == 20
    assert "[FALHA] falhou: mais 28 testes" in linhas


@pytest.mark.parametrize(
    ("chave", "nome"),
    [
        ("ruff_ci", "[FALHA] Ruff CI: Found 1 error."),
        ("ruff", "[FALHA] Ruff completo (sentinela/data): Found 1 error."),
    ],
)
def test_ruff_vermelho_reprova(tmp_path, chave, nome):
    (tmp_path / "sentinela" / "data").mkdir(parents=True)
    repo = _Repo(
        tmp_path, **{chave: gate.Execucao(1, "x.py:1:1 F821\nFound 1 error.\n")}
    )
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 1
    assert nome in linhas


def test_ruff_completo_so_nos_diretorios_que_existem(tmp_path):
    for d in ("sentinela/data", "sentinela/methods", "sentinela/data/store"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    repo = _Repo(tmp_path)
    _rodar(tmp_path, repo)
    assert ["ruff", "check", *gate.DIRETORIOS_RUFF] in repo.chamadas


def test_sem_diretorio_do_protocolo_nao_roda_ruff_completo(tmp_path):
    repo = _Repo(tmp_path)
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 0
    assert "[OK] Ruff completo: nenhum diretório do protocolo existe" in linhas
    assert not [
        c for c in repo.chamadas if c[:2] == ["ruff", "check"] and "--select" not in c
    ]


def test_diff_check_vermelho_reprova(tmp_path):
    repo = _Repo(
        tmp_path, check=gate.Execucao(2, "a.py:3: trailing whitespace.\n+x \n")
    )
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 1
    assert "[FALHA] git diff --staged --check: +x" in linhas


def test_golden_diferente_reprova_e_autorizado_vira_aviso(tmp_path):
    repo = _Repo(tmp_path, **{"hash-object": gate.Execucao(0, "outro\n")})
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 1
    assert any(
        linha.startswith("[FALHA] golden: diferente do HEAD") for linha in linhas
    )
    codigo, linhas = _rodar(tmp_path, repo, golden_autorizado=True)
    assert codigo == 0
    assert "[AVISO] golden: diferente do HEAD, autorizado" in linhas


def test_golden_ausente_ou_fora_do_head_reprova(tmp_path):
    repo = _Repo(tmp_path, **{"rev-parse": gate.Execucao(128, "fatal\n")})
    assert (
        "[FALHA] golden: sem tests/fixtures/golden_motores.jsonl no HEAD"
        in _rodar(tmp_path, repo)[1]
    )
    (tmp_path / gate.GOLDEN).unlink()
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 1
    assert "[FALHA] golden: tests/fixtures/golden_motores.jsonl ausente" in linhas


@pytest.mark.parametrize(
    "arquivo",
    [
        ".env",
        ".env.local",
        "dados/x.db",
        "sentinela_store.db",
        "outputs/a.txt",
        "mutants/x.py",
        "sentinela/__pycache__/a.pyc",
    ],
)
def test_arquivo_proibido_no_stage_reprova(tmp_path, arquivo):
    repo = _Repo(
        tmp_path, **{"name-only": gate.Execucao(0, f"scripts/x.py\n{arquivo}\n")}
    )
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 1
    assert f"[FALHA] arquivos proibidos no stage: {arquivo}" in linhas


def test_arquivo_fora_da_linha_e_so_aviso(tmp_path):
    nomes = "scripts/x.py\nsentinela/data/pit/leitor.py\ndocs/loop/diario.md\nmarket_engine.py\nREADME.md\n"
    repo = _Repo(tmp_path, **{"name-only": gate.Execucao(0, nomes)})
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 0
    assert "[AVISO] fora da linha do item: market_engine.py, README.md" in linhas


def test_item_inexistente_sai_com_2(tmp_path):
    codigo, linhas = _rodar(tmp_path, _Repo(tmp_path), ident="T-9")
    assert codigo == 2
    assert linhas == ["[FALHA] item: item T-9 não encontrado na fila"]


def test_main_imprime_o_resumo_e_devolve_o_codigo(tmp_path, monkeypatch, capsys):
    repo = _Repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "fila.md").write_text(FILA, encoding="utf-8")
    monkeypatch.setattr(gate, "executar", repo)
    assert gate.main(["--item", "T-2", "--fila", "fila.md"]) == 0
    saida = capsys.readouterr().out.splitlines()
    assert saida[0] == "[OK] suíte: = 10 passed, 1 skipped in 1.0s ="
    assert saida[-1] == "[AVISO] fora da linha do item: scripts/x.py, tests/test_x.py"


def test_main_sem_item_sai_com_2(capsys):
    assert gate.main([]) == 2


def test_execucao_real_junta_saida_e_erro():
    feito = gate.executar(
        [
            sys.executable,
            "-c",
            "import sys; print('a'); print('b', file=sys.stderr); sys.exit(3)",
        ]
    )
    assert feito.codigo == 3
    assert feito.saida == "a\nb\n"


def test_env_example_nao_e_proibido(tmp_path):
    repo = _Repo(
        tmp_path, **{"name-only": gate.Execucao(0, "scripts/x.py\n.env.example\n")}
    )
    assert "[OK] arquivos proibidos no stage: nenhum" in _rodar(tmp_path, repo)[1]


def test_falha_do_git_no_stage_reprova_em_vez_de_stage_vazio(tmp_path):
    repo = _Repo(
        tmp_path, **{"name-only": gate.Execucao(128, "fatal: not a git repository\n")}
    )
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 1
    assert linhas[-1] == "[FALHA] stage: git diff --staged --name-only falhou"
    assert not [linha for linha in linhas if "proibidos" in linha]


def test_execucao_roda_na_raiz_do_repositorio(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    feito = gate.executar([sys.executable, "-c", "import os; print(os.getcwd())"])
    assert feito.saida.strip() == str(gate.RAIZ)
    assert (gate.RAIZ / "scripts" / "gate.py").is_file()


def test_golden_do_indice_e_conferido(tmp_path):
    """BUG-3-14: o blob que vai ao commit (índice) também precisa ser o do HEAD."""
    repo = _Repo(tmp_path)
    _rodar(tmp_path, repo)
    assert ["git", "rev-parse", f":{gate.GOLDEN}"] in repo.chamadas


def test_golden_diferente_no_indice_reprova_e_autorizado_vira_aviso(tmp_path):
    repo = _Repo(tmp_path, indice=gate.Execucao(0, "outro\n"))
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 1
    assert any(
        linha.startswith("[FALHA] golden: diferente do HEAD no índice")
        for linha in linhas
    )
    codigo, linhas = _rodar(tmp_path, repo, golden_autorizado=True)
    assert codigo == 0
    assert "[AVISO] golden: diferente do HEAD no índice, autorizado" in linhas


def test_golden_fora_do_indice_reprova(tmp_path):
    repo = _Repo(tmp_path, indice=gate.Execucao(128, "fatal\n"))
    codigo, linhas = _rodar(tmp_path, repo)
    assert codigo == 1
    assert f"[FALHA] golden: sem {gate.GOLDEN} no índice" in linhas
