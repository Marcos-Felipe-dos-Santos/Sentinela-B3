"""Contrato de pureza dos métodos de valuation (F1-10, D11).

`sentinela/methods/` e os módulos de `sentinela/domain/` que ele importa não
importam rede, banco, relógio, arquivo, log, motores da V1, provedores nem o
`config` (que faz rede no import), e não chamam relógio nem `open`.
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PROIBIDOS = (
    "sentinela.news",
    "sentinela.data",
    "sentinela.services",
    "sentinela.repositories",
    "sentinela.reports",
    "technical_engine",
    "config",
    "market_engine",
    "valuation_engine",
    "fii_engine",
    "database",
    "brapi_provider",
    "cvm_provider",
    "cvm_fii_provider",
    "cvm_ticker_map",
    "cvm_fii_map",
    "fundamentus_scraper",
    "ai_core",
    "requests",
    "urllib",
    "http",
    "socket",
    "sqlite3",
    "yfinance",
    "logging",
    "os",
    "pathlib",
    "time",
)
CHAMADAS_PROIBIDAS_ATRIBUTO = {"now", "today", "utcnow"}
CHAMADAS_PROIBIDAS_NOME = {"open"}


def _proibido(nome: str) -> bool:
    return any(nome == p or nome.startswith(p + ".") for p in PROIBIDOS)


def modulos_importados(fonte: str, pacote: str = "") -> set[str]:
    """Nomes pontuados importados por um módulo; resolve import relativo contra `pacote`."""
    achados: set[str] = set()
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Import):
            achados.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom):
            base = no.module or ""
            if no.level:
                partes = pacote.split(".")[: len(pacote.split(".")) - no.level + 1]
                base = ".".join([*partes, base] if base else partes)
            achados.add(base)
            achados.update(f"{base}.{alias.name}" for alias in no.names)
    return achados


def chamadas_proibidas(fonte: str) -> list[str]:
    achados = []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Call):
            continue
        f = no.func
        if isinstance(f, ast.Name) and f.id in CHAMADAS_PROIBIDAS_NOME:
            achados.append(f.id)
        elif isinstance(f, ast.Attribute) and f.attr in CHAMADAS_PROIBIDAS_ATRIBUTO:
            achados.append(f.attr)
    return achados


def _nome_do_modulo(arquivo: Path) -> str:
    partes = list(arquivo.relative_to(RAIZ).with_suffix("").parts)
    if partes[-1] == "__init__":
        partes.pop()
    return ".".join(partes)


def _arquivo_do_modulo(nome: str) -> Path | None:
    base = RAIZ / Path(*nome.split("."))
    if (base / "__init__.py").exists():
        return base / "__init__.py"
    if base.with_suffix(".py").exists():
        return base.with_suffix(".py")
    return None


def _com_pacotes_pai(nome: str) -> list[Path]:
    """O módulo e os `__init__` dos pacotes pai (importar `a.b.c` executa `a` e `a.b`)."""
    partes = nome.split(".")
    arquivos = (
        _arquivo_do_modulo(".".join(partes[: i + 1])) for i in range(len(partes))
    )
    return [a for a in arquivos if a is not None]


def arquivos_sob_contrato(raiz_metodos: Path | None = None) -> list[Path]:
    """Arquivos de `sentinela/methods/` e o fecho dos módulos de `sentinela.domain` que eles importam."""
    metodos = sorted((raiz_metodos or RAIZ / "sentinela" / "methods").rglob("*.py"))
    vistos: dict[Path, None] = {}
    fila = list(metodos)
    while fila:
        arquivo = fila.pop()
        if arquivo in vistos:
            continue
        vistos[arquivo] = None
        pacote = (
            _nome_do_modulo(arquivo)
            if arquivo.name == "__init__.py"
            else _nome_do_modulo(arquivo).rpartition(".")[0]
        )
        for nome in modulos_importados(arquivo.read_text(encoding="utf-8"), pacote):
            if nome == "sentinela.domain" or nome.startswith("sentinela.domain."):
                fila.extend(_com_pacotes_pai(nome))
    return sorted(vistos)


ARQUIVOS = arquivos_sob_contrato()


def test_a_grade_de_arquivos_cobre_metodos_e_dominio():
    nomes = {_nome_do_modulo(a) for a in ARQUIVOS}
    assert {"sentinela.methods", "sentinela.methods.base"} <= nomes
    assert {
        "sentinela.domain",
        "sentinela.domain.enums",
        "sentinela.domain.units",
    } <= nomes


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=_nome_do_modulo)
def test_metodos_nao_importam_modulos_proibidos(arquivo):
    pacote = (
        _nome_do_modulo(arquivo)
        if arquivo.name == "__init__.py"
        else _nome_do_modulo(arquivo).rpartition(".")[0]
    )
    ruins = sorted(
        n
        for n in modulos_importados(arquivo.read_text(encoding="utf-8"), pacote)
        if _proibido(n)
    )
    assert ruins == []


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=_nome_do_modulo)
def test_metodos_nao_leem_relogio_nem_arquivo(arquivo):
    assert chamadas_proibidas(arquivo.read_text(encoding="utf-8")) == []


_SONDA = """
import json, socket, sys
def _bloqueado(*a, **k):
    raise OSError("rede bloqueada")
socket.socket.connect = _bloqueado
antes = set(sys.modules)
import importlib
importlib.import_module(sys.argv[1])
print(json.dumps(sorted(set(sys.modules) - antes)))
"""


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=_nome_do_modulo)
def test_import_isolado_nao_carrega_modulos_proibidos(arquivo):
    saida = subprocess.run(
        [sys.executable, "-c", _SONDA, _nome_do_modulo(arquivo)],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout
    carregados = json.loads(saida)
    assert [m for m in carregados if _proibido(m)] == []


# ── o detector detecta ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "fonte",
    [
        "import config",
        "import requests",
        "import os.path",
        "from config import MACRO",
        "from sentinela.data import x",
        "from sentinela import news",
        "from sentinela.news.coletor import y",
        "import logging as log",
        "from pathlib import Path",
        "from time import sleep",
    ],
)
def test_detector_pega_import_proibido(fonte):
    assert any(_proibido(n) for n in modulos_importados(fonte, "sentinela.methods"))


@pytest.mark.parametrize(
    "fonte",
    [
        "import math",
        "from dataclasses import dataclass",
        "from sentinela.domain.units import BRL",
        "from sentinela.methods.base import MethodInputs",
        "import datetime",
        "from .base import MethodInputs",
        "import configparser",
        "import timeit",
    ],
)
def test_detector_nao_acusa_import_permitido(fonte):
    assert not any(_proibido(n) for n in modulos_importados(fonte, "sentinela.methods"))


def test_import_relativo_resolve_contra_o_pacote():
    assert "sentinela.methods.base" in modulos_importados(
        "from .base import X", "sentinela.methods"
    )
    assert "sentinela.domain.units" in modulos_importados(
        "from ..domain import units", "sentinela.methods"
    )
    assert "sentinela.methods" in modulos_importados(
        "from . import base", "sentinela.methods"
    )


@pytest.mark.parametrize(
    ("fonte", "esperado"),
    [
        ("datetime.now()", ["now"]),
        ("date.today()", ["today"]),
        ("datetime.utcnow()", ["utcnow"]),
        ("open('x')", ["open"]),
        ("x = open('a'); y = date.today()", ["open", "today"]),
        ("math.sqrt(2)", []),
        ("reabrir(1)", []),
        ("agora = 1", []),
    ],
)
def test_detector_pega_chamada_proibida(fonte, esperado):
    assert sorted(chamadas_proibidas(fonte)) == sorted(esperado)
