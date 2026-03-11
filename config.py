import os
import logging
from dotenv import load_dotenv
import requests

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
_selic_cache = None

def get_selic_atual():
    """Busca a Selic atual no BCB. Usa fallback 10.75% se indisponível."""
    global _selic_cache
    if _selic_cache:
        return _selic_cache
    try:
        # CORRIGIDO: série 432 = Meta Selic anual definida pelo Copom (ex: 13.25)
        # Série 11 era a taxa DIÁRIA (ex: 0.0476 % ao dia) → /100 dava 0.05% a.a. ERRADO
        r = requests.get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json",
            timeout=3
        )
        if r.status_code == 200:
            _selic_cache = float(r.json()[0]['valor']) / 100
            logger.info(f"Selic BCB: {_selic_cache*100:.2f}% a.a.")
            return _selic_cache
    except Exception as e:
        # CORRIGIDO: logar falha em vez de silenciar (era except: pass)
        logger.warning(f"BCB API indisponível: {e}. Usando fallback 10.75%.")
    return 0.1075

RISK_FREE_RATE = 0.1075  # fallback estático, use get_selic_atual() nos engines