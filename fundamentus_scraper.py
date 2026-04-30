import logging
import threading
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("Scraper")

# ── Tentativa de usar cloudscraper (bypassa Cloudflare/bot detection) ─────────
# Instalar com: pip install cloudscraper
# Se indisponível, cai automaticamente em requests.Session (comportamento anterior)
try:
    import cloudscraper
except ImportError:
    cloudscraper = None


def _criar_session():
    if cloudscraper is not None:
        logger.info("[Scraper] cloudscraper disponível — usando para bypass Cloudflare")
        session = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        session.headers.update({
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
        })
        return session, True

    logger.warning("[Scraper] cloudscraper NÃO instalado — usando requests.Session")
    logger.warning("[Scraper]   → Instalar com: pip install cloudscraper")
    session = requests.Session()
    session.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': (
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        ),
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return session, False


class FundamentusScraper:
    def __init__(self):
        self.session, self._usando_cs = _criar_session()
        self._ultimo_req   = 0.0      # timestamp do último request
        self._lock         = threading.Lock()  # ADICIONADO: proteção contra race condition

    def __del__(self):
        try:
            self.session.close()
        except Exception:
            pass

    def _limpar_valor(self, texto):
        if not texto or texto.strip() in ['-', 'N/A', '']:
            return None

        v = texto.strip().replace('%', '').replace(' ', '')
        try:
            if ',' in v and '.' in v:
                # 1.234,56 -> 1234.56
                v = v.replace('.', '').replace(',', '.')
            elif ',' in v:
                # 15,2 -> 15.2
                v = v.replace(',', '.')
            elif '.' in v:
                partes = v.split('.')
                if len(partes) > 2:
                    # 12.345.678 -> 12345678
                    v = v.replace('.', '')
                elif len(partes) == 2 and len(partes[1]) == 3 and len(partes[0]) >= 1:
                    # 1.500 -> 1500
                    v = v.replace('.', '')
                # senão mantém como decimal US (3.5)
            return float(v)
        except ValueError:
            return None

    def buscar_dados(self, ticker):
        # Rate-limit: mínimo 2.5s entre requests (cloudscraper é mais lento por design)
        espera = 2.5 if self._usando_cs else 2.0
        
        # CORRIGIDO: lock para evitar race condition em ambiente multithread
        # (peers_engine usa ThreadPoolExecutor com 4 threads simultâneas)
        with self._lock:
            elapsed = time.time() - self._ultimo_req
            if elapsed < espera:
                time.sleep(espera - elapsed)
            self._ultimo_req = time.time()

        url       = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker}"
        tentativas = 3 if self._usando_cs else 2

        for tentativa in range(1, tentativas + 1):
            try:
                r = self.session.get(url, timeout=15)

                if r.status_code == 403:
                    detalhe_403 = (
                        "— cloudscraper falhou também, site pode ter mudado"
                        if self._usando_cs
                        else "— instale cloudscraper"
                    )
                    logger.warning(
                        f"[Fundamentus] 403 para {ticker} (tentativa {tentativa}) "
                        f"{detalhe_403}"
                    )
                    time.sleep(6 if tentativa == 1 else 10)
                    continue

                if r.status_code != 200:
                    logger.warning(f"[Fundamentus] HTTP {r.status_code} para {ticker}")
                    return None

                soup = BeautifulSoup(r.content, 'html.parser')
                dados = {}

                mapa = {
                    'P/L':              'pl',
                    'P/VP':             'pvp',
                    'Div. Yield':       'dy',
                    'ROE':              'roe',
                    'ROIC':             'roic',
                    'Dív.Líq/ Patrim.': 'div_liq_patrimonio',
                    'Dív.Líq/EBITDA':   'divida_liq_ebitda',
                    'Marg. Líquida':    'margem_liquida',
                    'Margem Bruta':     'margem_bruta',
                    'Patrim. Líq':      'patrimonio_liquido',
                    'Receita Líquida':  'receita_liquida',
                    'Lucro Líquido':    'lucro_liquido',
                    'Ativo':            'ativo_total',
                    'Ativo Circulante': 'ativo_circulante',
                }

                for row in soup.find_all('tr'):
                    cols = row.find_all('td')
                    for i in range(0, len(cols), 2):
                        if i + 1 < len(cols):
                            chave = cols[i].text.strip()
                            valor = cols[i+1].text.strip()
                            if chave in mapa:
                                dados[mapa[chave]] = self._limpar_valor(valor)

                campos_ok = [k for k, v in dados.items() if v is not None]
                if len(campos_ok) == 0:
                    return {
                        "erro_scraper": True,
                        "ticker": ticker,
                    }
                if len(campos_ok) < 3:
                    motivo = (
                        "cloudscraper ativo mas ainda bloqueado"
                        if self._usando_cs
                        else "instale cloudscraper"
                    )
                    logger.warning(
                        f"[Fundamentus] {len(campos_ok)} campo(s) para {ticker} "
                        f"(tentativa {tentativa}) — possível bloqueio ({motivo}). "
                        f"Campos: {campos_ok or 'NENHUM'}"
                    )
                    if tentativa < tentativas:
                        time.sleep(8)
                    continue

                # Converter percentuais de % para decimal
                for campo in ['dy', 'roe', 'roic', 'margem_liquida', 'margem_bruta']:
                    if campo in dados and dados[campo] is not None:
                        dados[campo] = dados[campo] / 100

                dados['ticker'] = ticker

                preco_elem = soup.find('td', class_='data destaque w3')
                if preco_elem:
                    dados['preco_atual'] = self._limpar_valor(preco_elem.text)

                fonte = 'cloudscraper' if self._usando_cs else 'requests'
                logger.info(
                    f"[Fundamentus] ✓ {ticker}: {len(campos_ok)} campos | "
                    f"fonte: {fonte}"
                )
                return dados

            except Exception as e:
                logger.error(f"[Fundamentus] Erro {ticker} tentativa {tentativa}: {e}")
                if tentativa < tentativas:
                    time.sleep(4)

        return None
