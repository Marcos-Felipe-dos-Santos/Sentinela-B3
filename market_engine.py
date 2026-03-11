import yfinance as yf
import pandas as pd
import logging
from fundamentus_scraper import FundamentusScraper

logger = logging.getLogger("MarketEngine")

class MarketEngine:
    def __init__(self):
        self.scraper = FundamentusScraper()

    def buscar_dados_ticker(self, ticker):
        ticker = ticker.upper().replace(".SA", "")
        
        # 1. Fundamentus
        dados = self.scraper.buscar_dados(ticker)
        
        # 2. Yahoo Fallback e Histórico
        try:
            tk = yf.Ticker(f"{ticker}.SA")
            
            # Histórico
            hist = tk.history(period="1y", timeout=10)
            if not hist.empty:
                dados = dados or {'ticker': ticker}
                dados['historico'] = hist
                if not dados.get('preco_atual'):
                    dados['preco_atual'] = hist['Close'].iloc[-1]
            
            # Fallback Fundamentalista
            if not dados or not dados.get('pl'):
                info = tk.info
                if info:
                    dados = dados or {'ticker': ticker}
                    # Yahoo Finance retorna dividendYield como percentagem bruta
                    # (ex: 12.47 = 12,47%) enquanto o resto do sistema usa decimal (0.1247).
                    # Normalizar: se dy > 1, assumir que está em % e dividir por 100.
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
                            pl_raw       = None   # PL negativo → sem lucro → tratar como ausente
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
                        'preco_atual': dados.get('preco_atual', info.get('currentPrice')),
                        'pl_confiavel': pl_confiavel,
                        # quoteType distingue FII real (MUTUALFUND) de unit/ação (EQUITY)
                        # Ex: HGLG11→MUTUALFUND, KLBN11→EQUITY, TAEE11→EQUITY
                        'quote_type':  info.get('quoteType', ''),
                    })
        except Exception as e:
            logger.warning(f"Yahoo error {ticker}: {e}")

        return dados

    def buscar_noticias(self, ticker):
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
        except:
            return []