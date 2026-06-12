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
APP_VERSION = "v14"
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
    'VILG11', 'LVBI11', 'CXTL11', 'PATL11', 'RLOG11',
    # Híbridos/Outros
    'PVBI11', 'HGRU11', 'RBRY11', 'TRBL11', 'HGPO11', 'BTCI11', 'TGAR11',
}

# Units conhecidas (ações com sufixo 11, NÃO são FIIs)
UNITS_CONHECIDAS = {
    'KLBN11', 'TAEE11', 'SAPR11', 'CMIG11', 'CPLE11', 'ELET11',
    'BBSE11', 'SANB11', 'TRPL11', 'ALUP11', 'ENGI11', 'CPFE11',
}

# Empresas em situação especial (recuperação judicial, distressed)
# Valuation engine bloqueia COMPRA/COMPRA FORTE para estes tickers
DISTRESSED_TICKERS = {
    'AMER3',
    'OIBR3',
    'OIBR4',
    'CASH3',
    'MGLU3',
}

# Fallback manual para FIIs com cobertura fraca nas APIs.
# Estimativas mantidas manualmente; revisar periodicamente.
FII_MANUAL_FALLBACK = {
    "CVBI11": {"dy": 0.10, "pvp": 0.85, "vacancia": 0.25},
    "HGLG11": {"dy": 0.084, "pvp": 0.99, "vacancia": 0.08},
    "MXRF11": {"dy": 0.115, "pvp": 0.98, "vacancia": 0.05},
}

# ==========================================
# SELIC DINÂMICA (lazy load com cache)
# ==========================================
SELIC_FALLBACK = 0.1475
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


RISK_FREE_RATE_FALLBACK = SELIC_FALLBACK  # alias estático — preferir get_selic_atual()

# Fallbacks para indicadores macro dinâmicos
CDI_FALLBACK      = 0.143   # CDI ≈ Selic (BCB SGS série 12 anualizada)
IPCA_12M_FALLBACK = 0.055   # IPCA acumulado 12m estimado (BCB SGS série 433)
NTNB_LONGA_FALLBACK = 0.070 # Yield real NTN-B vencimento >= 2035 (Tesouro Direto)


# ── PARÂMETROS ECONÔMICOS CENTRALIZADOS ──────────────────────────────────────
# Todos os limiares usados pelos engines em um lugar nomeado.
# Altere aqui para tunar o comportamento sem caçar literais no código.

class MacroContext:
    # DY normalização (Yahoo Finance)
    DY_PERCENTUAL_THRESHOLD = 1.0      # DY > 1 → Yahoo retornou como %
    DY_SANIDADE_MAX         = 0.25     # DY > 25% → dado inválido

    # Classificação de perfil
    ROE_CRESCIMENTO_MIN     = 0.20     # ROE > 20% → perfil CRESCIMENTO
    DY_CRESCIMENTO_MAX      = 0.04     # DY < 4% → perfil CRESCIMENTO

    # Graham
    GRAHAM_PVP_LIMITE_CRESCIMENTO = 3.0
    GRAHAM_PVP_LIMITE_RENDA       = 2.5
    GRAHAM_PL_LIMITE              = 25.0
    GRAHAM_PL_FLOOR               = 7.0    # piso para cíclicos

    # Bazin
    BAZIN_DY_MIN            = 0.05     # gate: pagadoras consistentes
    BAZIN_DY_ARMADILHA      = 0.15     # DY > 15% → possível armadilha
    BAZIN_TAXA_MIN          = 0.05     # taxa mínima (floor da Selic)

    # Lynch
    LYNCH_PAYOUT_MAX        = 0.95
    LYNCH_G_MAX             = 0.25
    LYNCH_PL_MULTIPLICADOR  = 1.5
    LYNCH_PL_MAX            = 35.0

    # Gordon
    GORDON_DY_MIN           = 0.04
    GORDON_ROE_MIN          = 0.10
    GORDON_G_MAX            = 0.08
    GORDON_PREMIO_RISCO     = 0.07     # k = Selic + 7% (também reutilizado em cost_of_equity_real)
    GORDON_PAYOUT_MAX       = 0.95

    # Divergência entre métodos
    METODOS_DIVERGENCIA_RATIO = 2.0

    # Score sigmoid
    SCORE_SIGMOID_AMPLITUDE  = 48
    SCORE_SIGMOID_INCLINACAO = 3

    # Qualidade financeira
    DIVIDA_EBITDA_LIMITE    = 3.0
    ROE_BONUS_MIN           = 0.20
    ROE_PENALIDADE_MAX      = 0.05

    # Recomendação ações
    REC_UPSIDE_COMPRA       = 0.15
    REC_SCORE_COMPRA        = 60
    REC_CONFIANCA_COMPRA    = 50
    REC_SCORE_FORTE         = 75
    REC_CONFIANCA_FORTE     = 70
    REC_UPSIDE_VENDA        = -0.15

    # FII
    FII_FATOR_IR            = 0.85     # alíquota 15% renda fixa longo prazo
    FII_DY_SELIC_RATIO_MIN  = 0.70     # DY < 70% da Selic líquida → penalidade
    FII_PVP_PREMIO_ALTO     = 1.15
    FII_PVP_PREMIO_MODERADO = 1.05
    FII_PVP_DESCONTO        = 0.85
    FII_UPSIDE_COMPRA       = 0.10
    FII_UPSIDE_VENDA        = -0.10

    # ── Indicadores dinâmicos ──────────────────────────────────────────────────

    def __init__(self, selic: float | None = None):
        # selic explícito: útil em testes (evita chamada BCB). Sem arg: usa get_selic_atual().
        self._selic: float = selic if selic is not None else get_selic_atual()
        self._cdi:      float | None = None
        self._ipca_12m: float | None = None
        self._ntnb_longa: float | None = None

    @property
    def selic(self) -> float:
        return self._selic

    @property
    def selic_liquida(self) -> float:
        """Selic líquida de IR para FIIs: Selic × 0.85."""
        return self._selic * self.FII_FATOR_IR

    @property
    def cdi(self) -> float:
        """CDI anualizado base 252 (BCB SGS série 12). Fallback: CDI_FALLBACK."""
        if self._cdi is None:
            d = self._fetch_bcb(12)        # CDI diário % a.d. como decimal
            if d is not None:
                self._cdi = (1 + d) ** 252 - 1
            else:
                self._cdi = CDI_FALLBACK
        return self._cdi

    @property
    def ipca_12m(self) -> float:
        """IPCA acumulado últimos 12 meses (BCB SGS série 433). Fallback: IPCA_12M_FALLBACK."""
        if self._ipca_12m is None:
            self._ipca_12m = self._fetch_ipca_acumulado()
        return self._ipca_12m

    @property
    def ntnb_longa(self) -> float:
        """Yield real NTN-B vencimento >= 2035 (Tesouro Direto). Fallback: NTNB_LONGA_FALLBACK."""
        if self._ntnb_longa is None:
            self._ntnb_longa = self._fetch_ntnb()
        return self._ntnb_longa

    def cost_of_equity_real(self) -> float:
        """Custo de capital próprio real = yield NTN-B longa + prêmio de risco."""
        return self.ntnb_longa + self.GORDON_PREMIO_RISCO

    # ── Fetchers privados ──────────────────────────────────────────────────────

    def _fetch_bcb(self, serie: int) -> float | None:
        """Retorna último valor da série BCB SGS como decimal (÷100), ou None em falha."""
        try:
            url = (
                f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/"
                "dados/ultimos/1?formato=json"
            )
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            return float(resp.json()[0]["valor"]) / 100
        except Exception as exc:
            logger.warning("Falha BCB SGS série %d: %s", serie, exc)
            return None

    def _fetch_ipca_acumulado(self) -> float:
        """IPCA acumulado 12 meses via BCB SGS série 433. Retorna decimal."""
        try:
            url = (
                "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/"
                "dados/ultimos/12?formato=json"
            )
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            acumulado = 1.0
            for item in resp.json():
                acumulado *= 1 + float(item["valor"]) / 100
            return acumulado - 1.0
        except Exception as exc:
            logger.warning("Falha IPCA BCB série 433: %s. Usando fallback.", exc)
            return IPCA_12M_FALLBACK

    def _fetch_ntnb(self) -> float:
        """Yield real médio de NTN-B com vencimento >= 2035 via Tesouro Direto. Retorna decimal."""
        try:
            url = (
                "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/"
                "service/api/treasureList.json"
            )
            resp = requests.get(
                url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}
            )
            resp.raise_for_status()
            bonds = resp.json()["response"]["TrsrBdTradgList"]
            rates: list[float] = []
            for item in bonds:
                bd = item["TrsrBd"]
                nm   = str(bd.get("nm", ""))
                venc = str(bd.get("mtrtyDt", ""))
                ano  = int(venc[:4]) if len(venc) >= 4 and venc[:4].isdigit() else 0
                if "IPCA+" in nm and ano >= 2035:
                    # taxa pode estar em sellr.anulInvstmtRate ou no nível do TrsrBd
                    taxa = (
                        bd.get("sellr", {}).get("anulInvstmtRate")
                        or bd.get("anulInvstmtRate")
                    )
                    if taxa is not None:
                        rates.append(float(taxa))
            if rates:
                return sum(rates) / len(rates) / 100
        except Exception as exc:
            logger.warning("Falha NTN-B Tesouro Direto: %s. Usando fallback.", exc)
        return NTNB_LONGA_FALLBACK


# Instância global — engines importam MACRO em vez de literais
MACRO = MacroContext()


def _normalizar_dy(dy_raw: float) -> tuple[float, bool]:
    """Normaliza DY do Yahoo Finance. Retorna (dy_decimal, dy_confiavel)."""
    if dy_raw > MACRO.DY_PERCENTUAL_THRESHOLD:
        return dy_raw / 100, True
    if dy_raw > MACRO.DY_SANIDADE_MAX:
        return 0.0, False
    return dy_raw, True
