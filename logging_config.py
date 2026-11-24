"""Configuração do log da aplicação."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configurar_logging() -> None:
    """Instala os handlers da aplicação quando o logger raiz está livre."""
    if logging.getLogger().handlers:
        return

    diretorio_configurado = os.environ.get("SENTINELA_LOG_DIR")
    pasta = (
        Path(diretorio_configurado).expanduser()
        if diretorio_configurado
        else Path.home() / ".local" / "state" / "sentinela-b3"
    )
    arquivo = (pasta / "sentinela.log").resolve()
    if arquivo.is_relative_to(Path(__file__).resolve().parent):
        raise ValueError("SENTINELA_LOG_DIR deve apontar para fora do repositório")

    arquivo.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                arquivo,
                maxBytes=10 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
                delay=True,
            ),
            logging.StreamHandler(),
        ],
    )
