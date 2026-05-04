import logging
import math
from typing import Any, Dict, Optional

import yfinance as yf
import pandas as pd

from brapi_provider import BrapiProvider
from database import DatabaseManager
from fundamentus_scraper import FundamentusScraper

logger = logging.getLogger("MarketEngine")

REQUIRED_FUNDAMENTALS = ('pl', 'pvp', 'roe', 'dy')
REQUIRED_MARKET_DATA = ('preco_atual', 'historico')
FUNDAMENTAL_KEYS = (
    'pl', 'pvp', 'dy', 'roe', 'roic', 'divida_liq_ebitda',
    'div_liq_patrimonio', 'margem_liquida', 'margem_bruta',
    'patrimonio_liquido', 'receita_liquida', 'lucro_liquido',
    'ativo_total', 'ativo_circulante', 'quote_type',
)


def is_missing(value: Any) -> bool:
    """Return True for empty/null/non-finite values; numeric zero is field-specific."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.strip().upper() in {"N/A", "NA", "NONE", "NULL"}
    try:
        if isinstance(value, (int, float)) and not math.isfinite(float(value)):
            return True
    except (TypeError, ValueError):
        return False
    return False


def _as_float(value: Any) -> Optional[float]:
    if is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_field_missing(field: str, value: Any, dados: Optional[Dict[str, Any]] = None) -> bool:
    if is_missing(value):
        return True

    numero = _as_float(value)
    if field == 'preco_atual':
        return numero is None or numero <= 0
    if field == 'historico':
        return value is None or getattr(value, 'empty', True)
    if field in {'pl', 'pvp', 'roe'}:
        if dados and field == 'pl' and dados.get('pl_confiavel') is False:
            return True
        return numero is not None and numero <= 0

    # DY zero can be a valid "no dividends" signal.
    return False


def merge_if_valid(
    base: Dict[str, Any],
    supplemental: Dict[str, Any],
    *,
    overwrite: bool = False,
    allowed_keys: Optional[set[str]] = None,
) -> list[str]:
    """Merge supplemental values when valid, optionally overwriting fields."""
    preenchidos: list[str] = []
    if not supplemental:
        return preenchidos

    for chave, valor in supplemental.items():
        if chave in {
            'ticker', 'erro_scraper', 'dados_parciais', 'campos_faltantes',
            'dados_cache', 'fonte_preco', 'fonte_fundamentos', 'riscos_dados',
        }:
            continue
        if allowed_keys is not None and chave not in allowed_keys:
            continue
        if _is_field_missing(chave, valor):
            continue
        if overwrite or _is_field_missing(chave, base.get(chave), base):
            base[chave] = valor
            preenchidos.append(chave)
            if chave == 'pl':
                base['pl_confiavel'] = bool(supplemental.get('pl_confiavel', True))

    return preenchidos


def list_missing_required_fields(dados: Dict[str, Any]) -> list[str]:
    """List required fields still absent after source consolidation."""
    return [
        campo
        for campo in REQUIRED_FUNDAMENTALS
        if _is_field_missing(campo, dados.get(campo), dados)
    ]


def list_missing_market_fields(dados: Dict[str, Any]) -> list[str]:
    """List required price/history fields still absent."""
    return [
        campo
        for campo in REQUIRED_MARKET_DATA
        if _is_field_missing(campo, dados.get(campo), dados)
    ]


def _registrar_fonte_fundamentos(dados: Dict[str, Any], fonte: str) -> None:
    atual = dados.get('fonte_fundamentos')
    if not atual:
        dados['fonte_fundamentos'] = fonte
        return
    fontes = atual.split('+')
    if fonte not in fontes:
        dados['fonte_fundamentos'] = f"{atual}+{fonte}"


def _definir_fonte_fundamentos(dados: Dict[str, Any], fonte: str) -> None:
    dados['fonte_fundamentos'] = fonte


def _fundamentos_validos_para_cache(dados: Dict[str, Any]) -> bool:
    return not list_missing_required_fields(dados)


class MarketEngine:
    def __init__(self) -> None:
        self.scraper = FundamentusScraper()
        self.brapi = BrapiProvider()
        self.database = DatabaseManager()

    def buscar_dados_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Busca dados de mercado com fallback multi-fonte."""
        ticker = ticker.upper().replace(".SA", "").strip()

        dados: Dict[str, Any] = {
            'ticker': ticker,
            'historico': pd.DataFrame(),
            'fonte_preco': None,
            'fonte_fundamentos': None,
            'erro_scraper': False,
            'dados_parciais': False,
            'campos_faltantes': [],
            'dados_cache': False,
            'riscos_dados': [],
        }

        # 1. yfinance: always first for price, history and fallback basics.
        self._buscar_yfinance(ticker, dados)

        # 2. Brapi: preferred fundamentals source when available.
        brapi_ok = self._buscar_brapi(ticker, dados)

        # 3. Fundamentus: fallback only when Brapi is unavailable/incomplete.
        missing_after_brapi = list_missing_required_fields(dados)
        fundamentus_ok = False
        if not brapi_ok or missing_after_brapi:
            fundamentus_ok = self._buscar_fundamentus(ticker, dados)

        if not dados.get('fonte_preco'):
            return None

        missing_before_cache = list_missing_required_fields(dados)
        if missing_before_cache or (not brapi_ok and not fundamentus_ok):
            self._aplicar_cache_fundamentos(ticker, dados, overwrite=not (brapi_ok or fundamentus_ok))

        dados['campos_faltantes'] = (
            list_missing_required_fields(dados)
            + list_missing_market_fields(dados)
        )
        dados['dados_parciais'] = bool(dados['campos_faltantes'])
        self._salvar_cache_se_valido(ticker, dados)
        dados.setdefault('ticker', ticker)
        return dados

    def _buscar_yfinance(self, ticker: str, dados: Dict[str, Any]) -> bool:
        """Busca dados via yfinance. Retorna True se obteve preco valido."""
        try:
            tk = yf.Ticker(f"{ticker}.SA")

            hist = tk.history(period="1y", timeout=10)
            if hist is not None and not hist.empty:
                dados['historico'] = hist
                dados['preco_atual'] = hist['Close'].iloc[-1]
                dados['fonte_preco'] = 'yfinance'

            info = tk.info
            if info:
                dy_raw = _as_float(info.get('dividendYield'))
                if dy_raw is not None and dy_raw > 1:
                    dy_raw = dy_raw / 100

                pl_raw = _as_float(info.get('trailingPE'))
                pl_confiavel = True
                if pl_raw is not None:
                    if pl_raw < 0:
                        pl_raw = None
                        pl_confiavel = False
                        logger.warning(f"[{ticker}] PL negativo (prejuizo) - descartado")
                    elif pl_raw > 80:
                        pl_confiavel = False
                        logger.warning(
                            f"[{ticker}] PL={pl_raw:.1f} via Yahoo muito alto (>80) "
                            "Possivel TTM atipico; pode ser sobrescrito por fonte melhor."
                        )

                preco_info = _as_float(info.get('currentPrice'))
                if not dados.get('fonte_preco') and preco_info and preco_info > 0:
                    dados['preco_atual'] = preco_info
                    dados['fonte_preco'] = 'yfinance'

                payload = {
                    'pl': pl_raw,
                    'pvp': _as_float(info.get('priceToBook')),
                    'dy': dy_raw,
                    'roe': _as_float(info.get('returnOnEquity')),
                    'pl_confiavel': pl_confiavel,
                    'quote_type': info.get('quoteType', ''),
                }
                for chave, valor in payload.items():
                    if not is_missing(valor):
                        dados[chave] = valor

                if any(not _is_field_missing(k, dados.get(k), dados) for k in ('pl', 'pvp', 'dy', 'roe')):
                    _registrar_fonte_fundamentos(dados, 'yfinance_partial')

            return bool(dados.get('fonte_preco'))

        except Exception as e:
            logger.warning(f"Yahoo error {ticker}: {e}")
            return False

    def _buscar_brapi(self, ticker: str, dados: Dict[str, Any]) -> bool:
        """Busca fundamentos via Brapi, sobrescrevendo fundamentos do Yahoo."""
        if not self.brapi.disponivel:
            logger.warning(f"[{ticker}] Brapi indisponivel: BRAPI_TOKEN ausente")
            return False

        try:
            brapi_data = self.brapi.get_fundamentals(ticker)
            if not brapi_data:
                return False

            fundamentos = {
                chave: valor
                for chave, valor in brapi_data.items()
                if chave in FUNDAMENTAL_KEYS
            }
            preenchidos = merge_if_valid(
                dados,
                fundamentos,
                overwrite=True,
                allowed_keys=set(FUNDAMENTAL_KEYS),
            )

            if _is_field_missing('preco_atual', dados.get('preco_atual'), dados):
                merge_if_valid(dados, brapi_data, allowed_keys={'preco_atual'})

            if dados.get('preco_atual') and not dados.get('fonte_preco'):
                dados['fonte_preco'] = 'brapi'

            campos_fundamentalistas = [c for c in preenchidos if c in FUNDAMENTAL_KEYS and c != 'quote_type']
            if campos_fundamentalistas:
                _definir_fonte_fundamentos(dados, 'brapi')
                logger.info(f"[{ticker}] Brapi definiu {len(campos_fundamentalistas)} fundamentos")
                return True

        except Exception as e:
            logger.warning(f"[{ticker}] Brapi error: {e}")

        return False

    def _buscar_fundamentus(self, ticker: str, dados: Dict[str, Any]) -> bool:
        """Busca dados via Fundamentus como complemento."""
        try:
            scraper_dados = self.scraper.buscar_dados(ticker)
        except Exception as e:
            dados['erro_scraper'] = True
            logger.warning(f"[{ticker}] Fundamentus error: {e}")
            return False

        if not scraper_dados or scraper_dados.get('erro_scraper'):
            dados['erro_scraper'] = True
            logger.info(
                f"[{ticker}] Fundamentus indisponivel - preservando dados existentes "
                f"(fonte_fundamentos={dados.get('fonte_fundamentos')})"
            )
            return False

        campos = ('preco_atual',) + FUNDAMENTAL_KEYS
        supplemental = {
            chave: scraper_dados[chave]
            for chave in campos
            if chave in scraper_dados
        }
        preenchidos = merge_if_valid(dados, supplemental)

        if 'preco_atual' in preenchidos and not dados.get('fonte_preco'):
            dados['fonte_preco'] = 'fundamentus'

        campos_fundamentalistas = [c for c in preenchidos if c in FUNDAMENTAL_KEYS and c != 'quote_type']
        if campos_fundamentalistas:
            if dados.get('fonte_fundamentos') in (None, 'yfinance_partial'):
                _definir_fonte_fundamentos(dados, 'fundamentus')
            else:
                _registrar_fonte_fundamentos(dados, 'fundamentus')

        dados['erro_scraper'] = False
        logger.info(f"[{ticker}] Fundamentus OK - complementou {len(campos_fundamentalistas)} campos")
        return bool(campos_fundamentalistas)

    def _aplicar_cache_fundamentos(
        self,
        ticker: str,
        dados: Dict[str, Any],
        *,
        overwrite: bool,
    ) -> bool:
        database = getattr(self, 'database', None)
        if database is None:
            return False

        try:
            cache = database.buscar_fundamentos_cache(ticker)
        except Exception as e:
            logger.warning(f"[{ticker}] Cache fundamentos indisponivel: {e}")
            return False

        if not cache:
            return False

        preenchidos = merge_if_valid(
            dados,
            cache,
            overwrite=overwrite,
            allowed_keys=set(FUNDAMENTAL_KEYS),
        )
        if not preenchidos:
            return False

        dados['dados_cache'] = True
        _definir_fonte_fundamentos(dados, 'cache')
        dados.setdefault('riscos_dados', []).append(
            'usando últimos fundamentos válidos em cache'
        )
        logger.info(f"[{ticker}] Usando cache de fundamentos ({len(preenchidos)} campos)")
        return True

    def _salvar_cache_se_valido(self, ticker: str, dados: Dict[str, Any]) -> None:
        if dados.get('dados_cache') or not _fundamentos_validos_para_cache(dados):
            return

        fonte = dados.get('fonte_fundamentos')
        if not fonte or fonte == 'yfinance_partial':
            return

        payload = {
            chave: dados[chave]
            for chave in FUNDAMENTAL_KEYS
            if chave in dados and not _is_field_missing(chave, dados.get(chave), dados)
        }
        if not _fundamentos_validos_para_cache(payload):
            return

        database = getattr(self, 'database', None)
        if database is None:
            return

        try:
            database.salvar_fundamentos_cache(ticker, payload, fonte)
        except Exception as e:
            logger.warning(f"[{ticker}] Falha ao salvar cache de fundamentos: {e}")

    def buscar_noticias(self, ticker: str):
        """Busca ultimas noticias via yfinance."""
        try:
            tk = yf.Ticker(f"{ticker}.SA")
            news = tk.news
            safe_news = []
            for n in (news or [])[:3]:
                titulo = n.get('title', n.get('content', {}).get('title', 'Sem titulo'))
                link = n.get('link', n.get('url', '#'))
                safe_news.append({'titulo': titulo, 'link': link})
            return safe_news
        except Exception as e:
            logger.warning(f"News error {ticker}: {e}")
            return []
