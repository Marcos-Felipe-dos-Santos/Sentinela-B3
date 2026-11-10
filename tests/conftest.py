import os
import socket
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Hermeticidade ──────────────────────────────────────────────────────────────
# F3-1a (E-6 corrigido): importar `config` não faz rede; a Selic é lida sob demanda por
# `get_selic_atual`, com cache de 24 h. A semente vai direto para esse cache, válido
# pela sessão inteira, e nenhuma chamada ao BCB acontece. Quebra autorizada F3-1: muda o
# mecanismo, não o valor. O valor 14.75 (% a.a.) é igual ao SELIC_FALLBACK, para não
# mudar nenhum resultado; a fixture `_selic_semeada` confere que ela continua valendo.
SELIC_SEMENTE_PCT = "14.75"

import config  # noqa: E402

config._selic_cache_value = float(SELIC_SEMENTE_PCT) / 100
config._selic_cache_time = float("inf")

# F2B-30: semente isolada, sem contingência equivalente em produção.
TAXA_REAL_SEMENTE = {
    "ntnb": 0.07,
    "custo_capital_real": 0.12,
    "premio": 0.05,
    "vertice": "NTN-B ≥2035, pesos iguais",
    "data_base": "2026-10-15",
    "fonte": "semente de teste",
    "inflacao": {"valor": 0.055},
    "pib": {"valor": 0.02, "ano": 2030},
    "proveniencia": {"fonte": "semente de teste"},
}
config._carregar_taxa_real = lambda instante, janela: dict(TAXA_REAL_SEMENTE)


@pytest.fixture(autouse=True, scope="session")
def _taxa_real_semeada():
    assert config.get_taxa_real()["ntnb"] == 0.07
    assert config.get_taxa_real()["inflacao"]["valor"] == 0.055
    yield


# ── Pasta de dados ─────────────────────────────────────────────────────────────
# F2A-20: o índice oficial e o classificador leem `SENTINELA_DADOS`. A suíte a aponta
# para uma pasta temporária vazia, para nunca ler o índice da máquina.
os.environ["SENTINELA_DADOS"] = tempfile.mkdtemp(prefix="sentinela_dados_")

# ── Guarda de rede ─────────────────────────────────────────────────────────────
# Qualquer connect de socket (exceto AF_UNIX) vira falha. Como o código de produção
# engole exceções genéricas, a tentativa também é registrada e derruba o teste
# (fixture `_sem_rede`) e a sessão (pytest_sessionfinish).
_TENTATIVAS_DE_REDE: list[str] = []
_connect_original = socket.socket.connect


def _connect_bloqueado(self, address):
    if self.family == getattr(socket, "AF_UNIX", None):
        return _connect_original(self, address)
    _TENTATIVAS_DE_REDE.append(repr(address))
    raise OSError(f"Rede bloqueada pela suíte: connect{address!r}")


socket.socket.connect = _connect_bloqueado


@pytest.fixture(autouse=True)
def _sem_rede():
    antes = len(_TENTATIVAS_DE_REDE)
    yield
    novas = _TENTATIVAS_DE_REDE[antes:]
    assert not novas, f"Teste tentou acessar a rede: {novas}"


@pytest.fixture(autouse=True, scope="session")
def _selic_semeada():
    assert config._selic_cache_value == float(SELIC_SEMENTE_PCT) / 100
    assert config.MACRO.selic == float(SELIC_SEMENTE_PCT) / 100
    yield


def pytest_sessionfinish(session, exitstatus):
    if _TENTATIVAS_DE_REDE and session.exitstatus == 0:
        session.exitstatus = 1


def pytest_configure(config):
    """Redirect tmp_path base on Windows when the default dir is inaccessible.

    pytest stores temporary files under ``%TEMP%/pytest-of-<user>``.  On
    Windows this directory sometimes ends up with broken NTFS permissions
    (e.g. owned by SYSTEM after an elevated process), causing every test
    that uses the ``tmp_path`` fixture to fail with ``PermissionError``.

    This hook detects the problem and sets ``basetemp`` to a fallback
    directory that the current user can write to.
    """
    if config.option.basetemp is not None:
        return  # user already specified --basetemp, respect it

    if os.name != "nt":
        return  # only needed on Windows

    default_base = Path(tempfile.gettempdir()) / f"pytest-of-{os.getlogin()}"
    if default_base.exists():
        try:
            # Quick writability probe
            probe = default_base / ".sentinela_probe"
            probe.touch()
            probe.unlink()
            return  # directory is fine, nothing to do
        except PermissionError:
            pass  # fall through to workaround

    # Fallback: use a sibling directory we can create ourselves
    fallback = Path(tempfile.gettempdir()) / "sentinela_pytest"
    fallback.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(fallback)


@pytest.fixture(autouse=True)
def _macro_fii_cenario_temporal(monkeypatch):
    """Mantém a injeção dos cenários antigos na nova fábrica, sem rede em testes.

    É semente de cenário, não histórico observado. Testes temporais de integração
    sobrescrevem a fábrica com MacroContext e provedor SGS reais.
    """
    import fii_engine

    def contexto(*, as_of):
        return config.MacroContext(selic=fii_engine.get_selic_atual(), as_of=as_of)

    monkeypatch.setattr(fii_engine, "MacroContext", contexto)
