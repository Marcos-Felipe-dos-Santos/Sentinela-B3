import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("Peers")

class PeersEngine:
    def __init__(self, market_engine):
        self.market = market_engine

        self.peers_map = {
            'bancos':     ['ITUB4', 'BBDC4', 'BBAS3', 'SANB11', 'BPAC11'],
            'petroleo':   ['PETR4', 'PRIO3', 'BRAV3', 'RECV3',  'CSAN3'],
            'energia':    ['ELET3', 'CMIG4', 'CPLE6', 'EGIE3',  'TAEE11'],
            'varejo':     ['MGLU3', 'LREN3', 'AZZA3', 'PETZ3',  'CEAB3'],
            'siderurgia': ['VALE3', 'GGBR4', 'CSNA3', 'USIM5',  'CMIN3'],
            'construcao': ['CYRE3', 'EZTC3', 'MRVE3', 'TEND3'],
            'saude':      ['HAPV3', 'RDOR3', 'FLRY3', 'RADL3'],
            'seguros':    ['BBSE3', 'CXSE3', 'PSSA3'],
            'telecom':    ['VIVT3', 'TIMS3'],
            'shopping':   ['ALSO3', 'IGTI11', 'MULT3'],
        }

        # índice reverso: ticker → setor
        self.ticker_to_sector = {
            t: setor
            for setor, tickers in self.peers_map.items()
            for t in tickers
        }

    def comparar(self, ticker: str, setor: str = None) -> dict:
        ticker = ticker.upper()
        if not setor:
            setor = self.ticker_to_sector.get(ticker)

        target_peers = []
        if setor and setor in self.peers_map:
            target_peers = [t for t in self.peers_map[setor] if t != ticker]

        if not target_peers:
            return {"erro": "Setor não identificado ou sem peers cadastrados."}

        dados_peers = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.market.buscar_dados_ticker, p): p
                       for p in target_peers}

            # CORRIGIDO: timeout em as_completed e future.result() evita hang infinito.
            # Antes: um peer com DNS timeout travava o loop para sempre.
            try:
                for future in as_completed(futures, timeout=10):
                    try:
                        d = future.result(timeout=2)
                        if d and d.get('preco_atual'):
                            dados_peers.append(d)
                    except Exception as e:
                        logger.warning(f"Peer {futures[future]} ignorado: {e}")
            except TimeoutError:
                logger.warning("Timeout global na busca de peers (10s).")

        if not dados_peers:
            return {"erro": "Não foi possível coletar dados dos peers."}

        def media(campo):
            vals = [d[campo] for d in dados_peers if d.get(campo) is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        return {
            'Setor':            setor,
            'PL_Media_Peers':   media('pl'),
            'PVP_Media_Peers':  media('pvp'),
            'DY_Media_Peers':   media('dy'),
            'Peers_Utilizados': [d['ticker'] for d in dados_peers],
        }