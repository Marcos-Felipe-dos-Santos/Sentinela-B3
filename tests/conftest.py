import os
import socket
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Hermeticidade ──────────────────────────────────────────────────────────────
# CONTORNO, não correção (E-6): `config.MACRO = MacroContext()` chama o BCB no
# import. Enquanto o config.py não for corrigido, a Selic é semeada aqui.
# Escolha: stub de `requests.get` durante o import de `config`, em vez de mexer em
# `config.py` (intocável nesta fase). O import dos módulos de teste acontece na
# coleta, antes de qualquer fixture, então a semente precisa nascer no carregamento
# deste arquivo; a fixture `_selic_semeada` só confere que ela continua valendo.
# O valor 14.75 (% a.a.) é igual ao SELIC_FALLBACK, para não mudar nenhum resultado.
SELIC_SEMENTE_PCT = "14.75"
_BCB_SELIC_URL = "api.bcb.gov.br/dados/serie/bcdata.sgs.432/"


def _requests_get_so_bcb(url, *args, **kwargs):
    if _BCB_SELIC_URL not in url:
        raise RuntimeError(f"requests.get bloqueado na semeadura da Selic: {url}")
    resposta = mock.Mock()
    resposta.raise_for_status.return_value = None
    resposta.json.return_value = [{"valor": SELIC_SEMENTE_PCT}]
    return resposta


with mock.patch("requests.get", _requests_get_so_bcb):
    import config  # noqa: E402  (instancia MACRO com a Selic semeada)

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
