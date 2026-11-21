"""BUG-3-14: o gate compara o golden da cópia de trabalho, não o que vai ao commit.

Auditoria cruzada da 3-a (Codex, 11/11/2026): golden alterado e posto no stage, com a cópia
de trabalho restaurada ao `HEAD`, passa no `scripts/gate.py` sem `--golden-autorizado`.
Corrige: F3-A-F1.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "gate.py"


def _carregar():
    spec = importlib.util.spec_from_file_location("gate_bug_3_14", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


gate = _carregar()


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
    ).stdout


def _rodar_em(repo):
    def rodar(comando):
        ambiente = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        feito = subprocess.run(
            list(comando),
            capture_output=True,
            text=True,
            check=False,
            cwd=repo,
            env=ambiente,
        )
        return gate.Execucao(feito.returncode, feito.stdout + feito.stderr)

    return rodar


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    golden = tmp_path / gate.GOLDEN
    golden.parent.mkdir(parents=True)
    golden.write_text('{"a": 1}\n', encoding="utf-8")
    _git(tmp_path, "add", gate.GOLDEN)
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def test_golden_inalterado_passa(repo):
    assert gate.golden(_rodar_em(repo), repo, autorizado=False).ok


def test_golden_alterado_so_no_stage_reprova(repo):
    golden = repo / gate.GOLDEN
    golden.write_text('{"a": 2}\n', encoding="utf-8")
    _git(repo, "add", gate.GOLDEN)
    golden.write_text(
        '{"a": 1}\n', encoding="utf-8"
    )  # cópia de trabalho de volta ao HEAD
    assert _git(repo, "diff", "--staged", "--name-only").strip() == gate.GOLDEN
    assert not gate.golden(_rodar_em(repo), repo, autorizado=False).ok
