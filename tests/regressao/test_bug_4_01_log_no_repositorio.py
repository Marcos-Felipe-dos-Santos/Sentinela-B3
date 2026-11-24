"""BUG-4-01: o import de config instalava um log sem rotação no diretório atual."""

import json
import logging
import os
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

_SONDA = """
import json
import logging
import sys
from logging.handlers import RotatingFileHandler

sys.path.insert(0, sys.argv[1])
import config

handlers = logging.getLogger().handlers
arquivo = next(handler for handler in handlers if isinstance(handler, logging.FileHandler))
logging.getLogger("sonda").info("Mensagem de teste")
print(json.dumps({
    "arquivo": arquivo.baseFilename,
    "rotativo": isinstance(arquivo, RotatingFileHandler),
    "limite": getattr(arquivo, "maxBytes", None),
    "backups": getattr(arquivo, "backupCount", None),
}))
"""


def test_config_instala_log_rotativo_fora_do_diretorio_atual(tmp_path):
    pasta_log = tmp_path / "estado" / "logs"
    resultado = subprocess.run(
        [sys.executable, "-c", _SONDA, str(RAIZ)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={
            **os.environ,
            "PYTHON_DOTENV_DISABLED": "1",
            "SENTINELA_LOG_DIR": str(pasta_log),
        },
        check=True,
        timeout=60,
    )

    assert json.loads(resultado.stdout) == {
        "arquivo": str(pasta_log / "sentinela.log"),
        "rotativo": True,
        "limite": 10 * 1024 * 1024,
        "backups": 3,
    }
    assert (pasta_log / "sentinela.log").is_file()


@pytest.mark.parametrize("personalizado", [False, True])
def test_configurar_logging_preserva_handlers_e_formato(
    tmp_path, monkeypatch, personalizado
):
    from logging_config import configurar_logging

    raiz = logging.RootLogger(logging.WARNING)
    monkeypatch.setattr(logging, "root", raiz)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SENTINELA_LOG_DIR", raising=False)
    pasta = tmp_path / ".local" / "state" / "sentinela-b3"
    if personalizado:
        pasta = tmp_path / "outro" / "logs"
        monkeypatch.setenv("SENTINELA_LOG_DIR", str(pasta))

    try:
        configurar_logging()
        arquivo, console = raiz.handlers
        configurar_logging()
        assert raiz.handlers == [arquivo, console]

        assert isinstance(arquivo, RotatingFileHandler)
        assert type(console) is logging.StreamHandler
        assert raiz.level == logging.INFO
        assert arquivo.baseFilename == str(pasta / "sentinela.log")
        assert arquivo.encoding == "utf-8"
        assert arquivo.maxBytes == 10 * 1024 * 1024
        assert arquivo.backupCount == 3
        assert pasta.is_dir()
        assert not Path(arquivo.baseFilename).exists()
        raiz.info("Mensagem de teste")
        assert " - root - INFO - Mensagem de teste" in Path(
            arquivo.baseFilename
        ).read_text(encoding="utf-8")
    finally:
        for handler in raiz.handlers:
            handler.close()


def test_configurar_logging_recusa_pasta_dentro_do_repositorio(monkeypatch):
    from logging_config import configurar_logging

    raiz = logging.RootLogger(logging.WARNING)
    monkeypatch.setattr(logging, "root", raiz)
    monkeypatch.setenv("SENTINELA_LOG_DIR", str(RAIZ))

    with pytest.raises(
        ValueError, match="SENTINELA_LOG_DIR deve apontar para fora do repositório"
    ):
        configurar_logging()

    assert raiz.handlers == []
