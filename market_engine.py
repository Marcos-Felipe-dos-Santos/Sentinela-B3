import logging
from typing import Any, Dict, Optional

import yfinance as yf

from fundamentus_scraper import FundamentusScraper
from brapi_provider import BrapiProvider

logger = logging.getLogger("MarketEngine")


class MarketEngine:
    def __init__(self) -> None:
        self.scraper = FundamentusScraper()
        self.brapi = BrapiProvider()

    # ── Método principal ─────────────────────────────────────────────────────
    def buscar_dados_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Busca dados de mercado com fallback multi-fonte.

        Fluxo de prioridade:
            1. yfinance — preço, histórico, fundamentalista básico
            2. Fundamentus scraper — fundamentalista detalhado
            3. Brapi (opcional) — complementar se token configurado
            4. Fallback: mantém dados parciais com flags de qualidade

        Args:
            ticker: Código do ativo B3 (ex: "PETR4").

        Returns:
            Dict com dados consolidados e flags de qualidade, ou None.
        """
        ticker = ticker.upper().replace(".SA", "")

        # Inicializar dict resultado com flags de qualidade
        dados: Dict[str, Any] = {
            'ticker': ticker,
            'fonte_preco': None,
            'fonte_fundamentos': None,
            'erro_scraper': False,
            'dados_parciais': False,
        }

        # ── 1. yfinance: preço + histórico + fundamentalista básico ──────
        yf_ok = self._buscar_yfinance(ticker, dados)

        # ── 2. Fundamentus: fundamentalista detalhado (sobrescreve yfinance)
        fund_ok = self._buscar_fundamentus(ticker, dados)

        # ── 3. Brapi: complementar opcional ──────────────────────────────
        if not fund_ok and self.brapi.disponivel:
            self._buscar_brapi(ticker, dados)

        # ── 4. Definir flags finais de qualidade ─────────────────────────
        if not dados.get('fonte_preco'):
            # Sem preço de nenhuma fonte → dados inúteis
            return None

        if not dados.get('fonte_fundamentos'):
            dados['dados_parciais'] = True

        # Garantia final: ticker sempre presente no dict retornado
        dados.setdefault('ticker', ticker)

        return dados

    # ── Fonte 1: yfinance ────────────────────────────────────────────────────
    def _buscar_yfinance(self, ticker: str, dados: Dict[str, Any]) -> bool:
        """Busca dados via yfinance. Retorna True se obteve dados válidos."""
        try:
            tk = yf.Ticker(f"{ticker}.SA")

            # Histórico (1 ano)
            hist = tk.history(period="1y", timeout=10)
            if not hist.empty:
                dados['historico'] = hist
                dados['preco_atual'] = hist['Close'].iloc[-1]
                dados['fonte_preco'] = 'yfinance'

            # Fundamentalista básico via .info
            info = tk.info
            if info:
                # Yahoo Finance retorna dividendYield como percentagem bruta
                # (ex: 12.47 = 12,47%) enquanto o sistema usa decimal (0.1247).
                dy_raw = info.get('dividendYield')
                if dy_raw is not None and dy_raw > 1:
                    dy_raw = dy_raw / 100

                # ── P/L sanity ───────────────────────────────────────────
                # Yahoo trailingPE para cíclicos (VALE3, PETR4) pode oscilar
                # muito entre trimestres — registrar confiabilidade.
                pl_raw = info.get('trailingPE')
                pl_confiavel = True
                if pl_raw is not None:
                    if pl_raw < 0:
                        pl_raw = None   # PL negativo → sem lucro → ausente
                        pl_confiavel = False
                        logger.warning(f"[{ticker}] PL negativo (prejuízo) — descartado")
                    elif pl_raw > 80:
                        pl_confiavel = False
                        logger.warning(
                            f"[{ticker}] PL={pl_raw:.1f} via Yahoo muito alto (>80) "
                            f"— possível TTM atípico. Graham pode ser descartado."
                        )

                dados.update({
                    'pl':          pl_raw,
                    'pvp':         info.get('priceToBook'),
                    'dy':          dy_raw,
                    'roe':         info.get('returnOnEquity'),
                    'preco_atual': dados.get('preco_atual') or info.get('currentPrice'),
                    'pl_confiavel': pl_confiavel,
                    # quoteType distingue FII real (MUTUALFUND) de unit/ação (EQUITY)
                    'quote_type':  info.get('quoteType', ''),
                })

                if not dados.get('fonte_preco') and info.get('currentPrice'):
                    dados['fonte_preco'] = 'yfinance'

                # yfinance fornece fundamentalista parcial por padrão
                if any(dados.get(k) is not None for k in ('pl', 'pvp', 'dy', 'roe')):
                    dados['fonte_fundamentos'] = 'yfinance_partial'

            return bool(dados.get('fonte_preco'))

        except Exception as e:
            logger.warning(f"Yahoo error {ticker}: {e}")
            return False

    # ── Fonte 2: Fundamentus scraper ─────────────────────────────────────────
    def _buscar_fundamentus(self, ticker: str, dados: Dict[str, Any]) -> bool:
        """Busca dados via Fundamentus. Retorna True se obteve dados completos."""
        scraper_dados = self.scraper.buscar_dados(ticker)

        # Scraper retornou None ou {"erro_scraper": True}
        if not scraper_dados or scraper_dados.get('erro_scraper'):
            dados['erro_scraper'] = True
            logger.info(
                f"[{ticker}] Fundamentus indisponível — "
                f"mantendo dados yfinance (fonte_fundamentos={dados.get('fonte_fundamentos')})"
            )
            return False

        # Fundamentus com dados válidos — sobrescreve yfinance nos campos
        # fundamentalistas, mas NÃO descarta preço/histórico do yfinance.
        for chave in ('pl', 'pvp', 'dy', 'roe', 'roic', 'div_liq_patrimonio',
                       'margem_liquida', 'margem_bruta', 'patrimonio_liquido',
                       'receita_liquida', 'lucro_liquido', 'ativo_total',
                       'ativo_circulante'):
            if chave in scraper_dados and scraper_dados[chave] is not None:
                dados[chave] = scraper_dados[chave]

        # Preço do Fundamentus como fallback se yfinance não obteve
        if not dados.get('preco_atual') and scraper_dados.get('preco_atual'):
            dados['preco_atual'] = scraper_dados['preco_atual']
            dados['fonte_preco'] = 'fundamentus'

        dados['fonte_fundamentos'] = 'fundamentus'
        dados['erro_scraper'] = False
        dados['dados_parciais'] = False

        logger.info(f"[{ticker}] Fundamentus ✓ — dados completos")
        return True

    # ── Fonte 3: Brapi (opcional) ────────────────────────────────────────────
    def _buscar_brapi(self, ticker: str, dados: Dict[str, Any]) -> bool:
        """Tenta complementar via Brapi. Retorna True se obteve dados."""
        if not self.brapi.disponivel:
            return False

        try:
            brapi_data = self.brapi.get_fundamentals(ticker)
            if not brapi_data:
                return False

            # Preenche apenas campos que estão ausentes
            campo_mapa = {
                'priceEarnings': 'pl',
                'priceToBookRatio': 'pvp',
                'dividendYield': 'dy',
                'returnOnEquity': 'roe',
            }
            preenchidos = 0
            for brapi_key, nosso_key in campo_mapa.items():
                if not dados.get(nosso_key) and brapi_data.get(brapi_key) is not None:
                    dados[nosso_key] = brapi_data[brapi_key]
                    preenchidos += 1

            if preenchidos > 0:
                dados['fonte_fundamentos'] = 'brapi_supplemental'
                logger.info(f"[{ticker}] Brapi complementou {preenchidos} campos")
                return True

        except Exception as e:
            logger.warning(f"[{ticker}] Brapi error: {e}")

        return False

    # ── Notícias ─────────────────────────────────────────────────────────────
    def buscar_noticias(self, ticker: str):
        """Busca últimas notícias via yfinance."""
        try:
            tk = yf.Ticker(f"{ticker}.SA")
            news = tk.news
            # CORREÇÃO CRÍTICA v9.1: Extração Segura com .get() aninhado
            # yfinance v0.2.40+ mudou estrutura para content.title em alguns casos
            safe_news = []
            for n in (news or [])[:3]:
                titulo = n.get('title', n.get('content', {}).get('title', 'Sem título'))
                link = n.get('link', n.get('url', '#'))
                safe_news.append({'titulo': titulo, 'link': link})
            return safe_news
        except Exception as e:
            logger.warning(f"News error {ticker}: {e}")
            return []

