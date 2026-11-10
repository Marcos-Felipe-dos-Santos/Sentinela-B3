import logging
import os
import time
from datetime import UTC, date, datetime
from types import MappingProxyType
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from sentinela.data import taxas as _taxas

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


# Taxa real da ficha 1.1: carregamento separado, sem rede nova no import.
_TAXA_REAL_TTL = 86400
_taxa_real_cache: dict = {}


def _carregar_taxa_real(
    instante: datetime, janela: tuple[date, date] | None
) -> dict | None:
    from sentinela.data.providers.macro import MacroProvider

    return MacroProvider().registro(instante, janela)


def get_taxa_real(
    *, as_of: datetime | None = None, janela: tuple[date, date] | None = None
) -> dict | None:
    """Registro observado até as_of; ausência não usa contingência numérica."""
    instante = as_of if as_of is not None else datetime.now(UTC)
    if instante.tzinfo is None or instante.utcoffset() is None:
        return None
    chave = (janela, instante.astimezone(ZoneInfo("America/Sao_Paulo")).date())
    anterior = _taxa_real_cache.get(chave)
    if anterior is not None:
        coleta, registro = anterior
        idade = (instante - coleta).total_seconds()
        proxima = (registro.get("pib") or {}).get("proxima_publicacao")
        edicao_devida = proxima is not None and datetime.fromisoformat(proxima) <= instante
        if 0 <= idade < _TAXA_REAL_TTL and not edicao_devida:
            return registro
    registro = _carregar_taxa_real(instante, janela)
    # F2B-51: a abstenção não fica no cache; a próxima análise consulta de novo.
    if registro is not None and "abstencao" not in registro:
        _taxa_real_cache[chave] = (instante, registro)
    return registro


# Fallbacks para indicadores macro dinâmicos
CDI_FALLBACK      = 0.143   # CDI ≈ Selic (BCB SGS série 12 anualizada)
IPCA_12M_FALLBACK = 0.055   # IPCA acumulado 12m estimado (BCB SGS série 433)


# ── PARÂMETROS ECONÔMICOS CENTRALIZADOS ──────────────────────────────────────
# Todos os limiares usados pelos engines em um lugar nomeado.
# Altere aqui para tunar o comportamento sem caçar literais no código.

class MacroContext:
    # F2A-10: regra do Marcos de 18/10/2026, em pregões, razão e BRL/dia.
    LIQUIDEZ_JANELA = 63
    LIQUIDEZ_PRESENCA_MIN = 0.80
    LIQUIDEZ_VOLUME_ACOES_MIN = 500_000.0
    LIQUIDEZ_VOLUME_FII_MIN = 100_000.0

    PREMIO_ACOES_REAL = _taxas.PREMIO_ACOES_REAL

    # DY normalização (Yahoo Finance)
    DY_PERCENTUAL_THRESHOLD = 1.0      # DY > 1 → Yahoo retornou como %
    DY_SANIDADE_MAX         = 0.25     # DY > 25% → dado inválido

    # Classificação de perfil
    ROE_CRESCIMENTO_MIN     = 0.20     # ROE > 20% → perfil CRESCIMENTO
    DY_CRESCIMENTO_MAX      = 0.04     # DY < 4% → perfil CRESCIMENTO

    # Cenários históricos de Graham (scripts/grade protegida, não o motor atual)
    GRAHAM_PVP_LIMITE_CRESCIMENTO = 3.0
    GRAHAM_PVP_LIMITE_RENDA       = 2.5
    GRAHAM_PL_LIMITE              = 25.0
    GRAHAM_PL_FLOOR               = 7.0    # piso para cíclicos

    # Bazin
    BAZIN_DY_MIN            = 0.05     # gate: pagadoras consistentes
    BAZIN_DY_ARMADILHA      = 0.15     # DY > 15% → possível armadilha

    # Cenários históricos de Lynch (scripts, não o motor atual)
    LYNCH_PAYOUT_MAX        = 0.95
    LYNCH_G_MAX             = 0.25
    LYNCH_PL_MULTIPLICADOR  = 1.5
    LYNCH_PL_MAX            = 35.0

    # Divergência entre métodos
    METODOS_DIVERGENCIA_RATIO = 2.0

    # Qualidade financeira
    DIVIDA_EBITDA_LIMITE    = 3.0
    # Grade histórica protegida; não pontua análises atuais.
    ROE_PENALIDADE_MAX      = 0.05

    # Compatibilidade de teste, sem leitor de classificação no motor atual
    REC_UPSIDE_COMPRA       = 0.15

    # FII
    FII_FATOR_IR            = 0.85     # alíquota 15% renda fixa longo prazo
    FII_PVP_PREMIO_ALTO     = 1.15
    FII_PVP_PREMIO_MODERADO = 1.05
    FII_PVP_DESCONTO        = 0.85
    # F2B-2 (ficha FII 1.1, §6; plano final da 2B, seção 3): spread dos FIIs de tijolo sobre
    # a NTN-B real, calibrado por `scripts/calibrar_spread_fii.py` em 21/10/2026. Constante
    # datada, sem recalibração em execução: nova calibração é item novo da fila. Mantida por
    # decisão de 25/10/2026; a recalibração posterior com cotas fracionárias (ficha 1.2,
    # F2B-55: 3,5124% contra 3,5058%, diferença de 0,0066 pp) confirma que a diferença é
    # imaterial (ficha FII, §3b e §6a).
    FII_SPREAD_TIJOLO       = 0.03505842448151178
    FII_SPREAD_CALIBRACAO   = MappingProxyType({
        "data": "2026-10-21",
        "janela": ("2021-10", "2026-09"),
        "fundos_por_mes": {"minimo": 30, "mediana": 36, "maximo": 41},
        "p25": 0.03170004418948333,
        "p75": 0.03773431291227301,
        "registro": "docs/metodologia/fii.md, seção 6a",
    })

    # ── Indicadores dinâmicos ──────────────────────────────────────────────────

    def __init__(
        self,
        selic: float | None = None,
        as_of: date | None = None,
        provedor=None,
        instante: datetime | None = None,
    ):
        # selic explícito: útil em testes (evita chamada BCB). Sem arg, a Selic é lida sob
        # demanda por get_selic_atual(), com o cache de 24 h e o fallback dela (E-6, F3-1a).
        # Com as_of (F3-1b), Selic, CDI e IPCA vêm da série completa do SGS vigente naquela
        # data; ausência com as_of passado abstém (None), sem fallback fixo.
        if isinstance(as_of, datetime):
            raise TypeError("as_of do MacroContext é date (dia de Brasília), não datetime")
        if instante is not None and instante.utcoffset() is None:
            raise ValueError("instante da coleta exige fuso horário")
        self._selic: float | None = selic
        self._cdi:      float | None = None
        self._ipca_12m: float | None = None
        self.as_of = as_of
        self._provedor = provedor
        self._instante = instante
        self._por_data: dict[str, dict] = {}

    @property
    def selic(self) -> float | None:
        if self._selic is not None:
            return self._selic
        if self.as_of is not None:
            return self._valor_por_data("selic", SELIC_FALLBACK)
        return get_selic_atual()

    @property
    def selic_liquida(self) -> float | None:
        """Selic líquida de IR para FIIs: Selic × 0.85."""
        selic = self.selic
        return None if selic is None else selic * self.FII_FATOR_IR

    @property
    def cdi(self) -> float | None:
        """CDI anualizado base 252 (BCB SGS série 12). Fallback: CDI_FALLBACK."""
        if self.as_of is not None:
            return self._valor_por_data("cdi", CDI_FALLBACK)
        if self._cdi is None:
            d = self._fetch_bcb(12)        # CDI diário % a.d. como decimal
            if d is not None:
                self._cdi = (1 + d) ** 252 - 1
            else:
                self._cdi = CDI_FALLBACK
        return self._cdi

    @property
    def ipca_12m(self) -> float | None:
        """IPCA acumulado últimos 12 meses (BCB SGS série 433). Fallback: IPCA_12M_FALLBACK."""
        if self.as_of is not None:
            return self._valor_por_data("ipca_12m", IPCA_12M_FALLBACK)
        if self._ipca_12m is None:
            self._ipca_12m = self._fetch_ipca_acumulado()
        return self._ipca_12m

    # ── Por data (F3-1b) ───────────────────────────────────────────────────────

    def _instante_coleta(self) -> datetime:
        if self._instante is None:
            self._instante = datetime.now(UTC)
        return self._instante

    def _hoje(self) -> date:
        return self._instante_coleta().astimezone(ZoneInfo("America/Sao_Paulo")).date()

    @staticmethod
    def _hoje_no_relogio() -> date:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    def registro_por_data(self, nome: str) -> dict:
        """Valor e data da observação vigente em as_of, ou `{"abstencao": motivo}`."""
        if nome not in self._por_data:
            from sentinela.data import macro_por_data
            from sentinela.data.providers.macro import MacroProvider

            serie = {
                "selic": macro_por_data.SELIC_META,
                "cdi": macro_por_data.CDI,
                "ipca_12m": macro_por_data.IPCA,
            }[nome]
            hoje = self._hoje()
            if self.as_of > hoje:
                registro = {"abstencao": "as_of posterior à data da coleta"}
            else:
                provedor = self._provedor if self._provedor is not None else MacroProvider()
                dados = provedor.serie_sgs(serie, hoje, self._instante_coleta())
                if "abstencao" in dados:
                    registro = dados
                elif nome == "ipca_12m":
                    registro = macro_por_data.ipca_12m(
                        dados["observacoes"], self.as_of, dados["coleta"]
                    )
                else:
                    calculo = getattr(macro_por_data, nome)
                    registro = calculo(dados["observacoes"], self.as_of)
            self._por_data[nome] = registro
        return self._por_data[nome]

    def _valor_por_data(self, nome: str, fallback: float) -> float | None:
        registro = self.registro_por_data(nome)
        if "valor" in registro:
            return registro["valor"]
        # Fallback existente só para as_of = hoje, no relógio e na coleta; data passada
        # abstém (F3-1b), mesmo com instante de coleta injetado no passado.
        if self.as_of == self._hoje() == self._hoje_no_relogio():
            return fallback
        return None

    def motivo(self, nome: str) -> str | None:
        """Motivo da abstenção por data de `selic`, `cdi` ou `ipca_12m`; None sem as_of."""
        if self.as_of is None:
            return None
        return self.registro_por_data(nome).get("abstencao")

    def cost_of_equity_real(self) -> float | None:
        """Custo real do F2B-30, sem contingência nem prêmio duplicado."""
        registro = get_taxa_real()
        return (
            None
            if registro is None or "abstencao" in registro
            else registro['custo_capital_real']
        )

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


# Instância global — engines importam MACRO em vez de literais; o import não faz rede.
MACRO = MacroContext()


def _normalizar_dy(dy_raw: float) -> tuple[float, bool]:
    """Invariante do DY nos motores (F2A-4). Retorna (dy, dy_confiavel).

    O DY já chega em razão: a conversão de percentual é da fronteira de cada provedor
    (`sentinela.data.normalizacao`). Fora de 0 ≤ DY ≤ `DY_SANIDADE_MAX`, ou não finito,
    vira (0.0, False).
    """
    # NaN e infinito falham a comparação e caem aqui.
    if not 0 <= dy_raw <= MACRO.DY_SANIDADE_MAX:
        return 0.0, False
    return dy_raw, True
