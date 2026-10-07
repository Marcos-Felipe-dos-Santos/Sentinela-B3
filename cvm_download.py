import logging
import os
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_CACHE_TTL_DAYS = 7
_MAX_RETRIES = 3
_BACKOFF_FACTOR = 2

def is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(days=_CACHE_TTL_DAYS)

def baixar_arquivo(url: str, dest: Path) -> Path:
    if is_fresh(dest):
        logger.debug("Cache válido: %s", dest)
        return dest

    tmp_path = dest.with_suffix('.tmp')

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info("Baixando %s → %s (tentativa %d/%d)", url, dest, attempt, _MAX_RETRIES)
            with requests.get(url, timeout=60, stream=True) as resp:
                resp.raise_for_status()

                # Baixa em chunks para o arquivo temporário
                with open(tmp_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            # Valida o ZIP
            with zipfile.ZipFile(tmp_path) as zf:
                bad_file = zf.testzip()
                if bad_file:
                    raise zipfile.BadZipFile(f"Arquivo corrompido no ZIP: {bad_file}")

            # Substituição atômica
            os.replace(tmp_path, dest)
            return dest

        except (requests.RequestException, ConnectionError) as e:
            logger.warning("Erro no download de %s: %s", url, e)
            if attempt < _MAX_RETRIES:
                sleep_time = _BACKOFF_FACTOR ** (attempt - 1)
                logger.info("Aguardando %ds antes da próxima tentativa...", sleep_time)
                time.sleep(sleep_time)
            else:
                logger.error("Falha final ao baixar %s após %d tentativas.", url, _MAX_RETRIES)
                # Remove o temp file antes de subir o erro se ainda existir
                if tmp_path.exists():
                    tmp_path.unlink()
                raise
        except Exception:
            # Para BadZipFile, apenas deleta o tmp e repassa
            if tmp_path.exists():
                tmp_path.unlink()
            raise
