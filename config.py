import logging
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sentinela.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Config")

# ==========================================
# CHAVES & MODELOS
# ==========================================
GEMINI_MODEL = "gemini-2.0-flash"
GROQ_MODEL   = "llama-3.3-70b-versatile"
OLLAMA_URL   = "http://localhost:11434"
OLLAMA_MODEL = "llama3"

# ==========================================
# PARÂMETROS
# ==========================================
MAX_WORKERS = min(8, (os.cpu_count() or 1) + 4)
TIMEOUT_API = 15

# ==========================================
# FIIs CONHECIDOS (B3)
# ==========================================
# Lista dos principais FIIs negociados na B3
# Usada para distinguir FIIs reais de units com sufixo 11
FIIS_CONHECIDOS = {
    # Papel (CRI/CRA)
    'HGLG11', 'XPML11', 'VISC11', 'MXRF11', 'KNRI11', 'KNCR11', 'BTLG11',
    'RBRR11', 'VGIR11', 'RECT11', 'GGRC11', 'RBRF11', 'RZTR11', 'CVBI11',
    # Tijolo (Lajes/Galpões)
    'BCFF11', 'HGCR11', 'KNIP11', 'KNSC11', 'VCRI11', 'BRCR11', 'RBRP11',
    'TRXF11', 'ALZR11', 'DEVA11', 'SARE11', 'GTWR11', 'XPCI11', 'JSRE11',
    # Shopping
    'HSML11', 'HGBS11', 'VIUR11', 'SHPH11', 'MALL11', 'RBVA11', 'XPPR11',
    # Logística
    'HGLG11', 'VILG11', 'LVBI11', 'CXTL11', 'BTLG11', 'PATL11', 'RLOG11',
    # Híbridos/Outros
    'PVBI11', 'HGRU11', 'RBRY11', 'TRBL11', 'HGPO11', 'BTCI11', 'TGAR11',
}

# Units conhecidas (ações com sufixo 11, NÃO são FIIs)
UNITS_CONHECIDAS = {
    'KLBN11', 'TAEE11', 'SAPR11', 'CMIG11', 'CPLE11', 'ELET11',
    'BBSE11', 'SANB11', 'TRPL11', 'ALUP11', 'ENGI11', 'CPFE11',
}

# ==========================================
# SELIC DINÂMICA (lazy load com cache)
# ==========================================
SELIC_FALLBACK = 0.1075
SELIC_CACHE_TTL = 86400
_selic_cache_value = None
_selic_cache_time = 0.0


def get_selic_atual() -> float:
    """Busca a Selic atual via API do Banco Central do Brasil."""
    global _selic_cache_time, _selic_cache_value

    now = time.time()
    if (
        _selic_cache_value is not None
        and now - _selic_cache_time < SELIC_CACHE_TTL
    ):
        return _selic_cache_value

    try:
        url = (
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/"
            "dados/ultimos/1?formato=json"
        )
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        selic_anual = float(resp.json()[0]['valor']) / 100
        _selic_cache_value = selic_anual
        _selic_cache_time = now
        logger.info(
            f"Selic atual: {selic_anual:.4f} ({selic_anual*100:.2f}% a.a.)"
        )
        return selic_anual
    except Exception as e:
        logger.warning(
            f"Falha ao buscar Selic do BCB: {e}. Usando fallback hardcoded."
        )
        return SELIC_FALLBACK


RISK_FREE_RATE = SELIC_FALLBACK  # compatibilidade; use get_selic_atual() nos engines
