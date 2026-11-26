import hashlib
import logging
import os
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import requests

from sentinela.data import proveniencia

logger = logging.getLogger(__name__)

_CACHE_TTL_DAYS = 7
_MAX_RETRIES = 3
_BACKOFF_FACTOR = 2

def is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(days=_CACHE_TTL_DAYS)

def _limpar_temporarios(tmp_path: Path, dest: Path) -> None:
    """Remove o temporário deste download e o de nome fixo deixado por versões anteriores."""
    for temporario in (tmp_path, dest.with_suffix('.tmp')):
        temporario.unlink(missing_ok=True)


def baixar_arquivo(url: str, dest: Path) -> Path:
    if is_fresh(dest):
        logger.debug("Cache válido: %s", dest)
        return proveniencia.caminho_da_execucao(dest)

    # BUG-4-16: temporário próprio deste download; outro download do mesmo destino não o toca.
    tmp_path = dest.with_name(f"{dest.name}.{uuid4().hex}.tmp")

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info("Baixando %s → %s (tentativa %d/%d)", url, dest, attempt, _MAX_RETRIES)
            with requests.get(url, timeout=60, stream=True) as resp:
                resp.raise_for_status()

                # Baixa em chunks para o arquivo temporário
                resumo = hashlib.sha256()
                with open(tmp_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            resumo.update(chunk)

            # Valida o ZIP
            with zipfile.ZipFile(tmp_path) as zf:
                bad_file = zf.testzip()
                if bad_file:
                    raise zipfile.BadZipFile(f"Arquivo corrompido no ZIP: {bad_file}")

            # Cópia privada dos bytes desta execução antes de publicar (BUG-4-24), depois a
            # substituição atômica; o consumidor lê a cópia, não o destino compartilhado.
            proveniencia.marcar_baixado(
                dest,
                resumo.hexdigest(),
                temporario=tmp_path,
                publicar=lambda: os.replace(tmp_path, dest),
            )
            return proveniencia.caminho_da_execucao(dest)

        except (requests.RequestException, ConnectionError) as e:
            logger.warning("Erro no download de %s: %s", url, e)
            if (
                isinstance(e, requests.HTTPError)
                and e.response is not None
                and e.response.status_code == 404
            ):
                # Ausência declarada pela fonte não se resolve repetindo a chamada.
                _limpar_temporarios(tmp_path, dest)
                raise
            if attempt < _MAX_RETRIES:
                sleep_time = _BACKOFF_FACTOR ** (attempt - 1)
                logger.info("Aguardando %ds antes da próxima tentativa...", sleep_time)
                time.sleep(sleep_time)
            else:
                logger.error("Falha final ao baixar %s após %d tentativas.", url, _MAX_RETRIES)
                # Remove o temp file antes de subir o erro se ainda existir
                _limpar_temporarios(tmp_path, dest)
                raise
        except Exception:
            # Para BadZipFile, apenas deleta o tmp e repassa
            _limpar_temporarios(tmp_path, dest)
            raise
