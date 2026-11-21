"""BUG-3-01 (E-6): importar `config` chamava o BCB, porque `MACRO = MacroContext()` buscava a Selic."""

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Em subprocesso, para importar `config` do zero, sem a semente do conftest.
_SONDA = """
import socket, sys
import requests

tentativas = []

def _connect(self, endereco):
    tentativas.append("socket " + repr(endereco))
    raise OSError("rede bloqueada pela sonda")

def _get(url, *args, **kwargs):
    tentativas.append("requests.get " + url)
    raise OSError("rede bloqueada pela sonda")

socket.socket.connect = _connect
requests.get = _get
sys.path.insert(0, sys.argv[1])
import config  # noqa: F401
print(len(tentativas))
for tentativa in tentativas:
    print(tentativa)
"""


def test_importar_config_nao_acessa_a_rede(tmp_path):
    resultado = subprocess.run(
        [sys.executable, "-c", _SONDA, str(RAIZ)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"PATH": "", "SENTINELA_DADOS": str(tmp_path)},
        check=True,
        timeout=60,
    )
    linhas = resultado.stdout.splitlines()
    assert linhas[0] == "0", linhas[1:]
