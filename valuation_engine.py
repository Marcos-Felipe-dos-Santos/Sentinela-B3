import logging
import math
from config import get_selic_atual

logger = logging.getLogger("Valuation")

class ValuationEngine:
    def processar(self, dados):
        if not dados or not dados.get('preco_atual'):
            return None

        p   = float(dados['preco_atual'])
        roe = float(dados.get('roe', 0) or 0)
        pl  = float(dados.get('pl',  0) or 0)
        pvp = float(dados.get('pvp', 0) or 0)

        # ── NORMALIZAÇÃO DO DY ────────────────────────────────────────────────
        # Yahoo Finance retorna dividendYield de formas inconsistentes entre tickers BR:
        #   Ex: PETR4 → 12.47  (percentagem bruta)  → dividir por 100 → 0.1247
        #   Ex: WEGE3 → 3.02   (percentagem bruta)  → dividir por 100 → 0.0302
        #   Ex: ITUB4 → 0.45   (dado suspeito)       → 45% DY impossível → cap
        #
        # Regra 1: se dy > 1   → Yahoo retornou como % → dividir por 100
        # Regra 2: se dy > 0.25 → 25% DY é fisicamente impossível para B3 → dado inválido → 0
        dy_raw = float(dados.get('dy', 0) or 0)
        dy_confiavel = True   # flag: sabemos o DY com confiança?

        if dy_raw > 1:
            dy = dy_raw / 100
            logger.info(f"[{dados.get('ticker','?')}] DY normalizado: {dy_raw:.4f}% → {dy:.4f} decimal")
        elif dy_raw > 0.25:
            logger.warning(
                f"[{dados.get('ticker','?')}] DY={dy_raw:.4f} ({dy_raw*100:.1f}%) improvável para B3 "
                f"— dado suspeito (Yahoo bug?). Desconsiderado."
            )
            dy = 0.0
            dy_confiavel = False
        else:
            dy = dy_raw

        lpa = (p / pl)  if pl  > 0 else 0
        vpa = (p / pvp) if pvp > 0 else 0

        selic = get_selic_atual()

        confianca = 100
        riscos = []

        # pl_confiavel: False quando Yahoo retornou PL negativo (prejuízo) ou > 80 (TTM atípico)
        # Definido em market_engine.py; padrão True para dados do Fundamentus (mais confiáveis)
        pl_confiavel = bool(dados.get('pl_confiavel', True))

        # ── DETECÇÃO DE PERFIL ────────────────────────────────────────────────
        # CRESCIMENTO: ROE alto + dividendos baixos (empresa reinveste lucros)
        # ATENÇÃO: se DY foi zerado por falta de confiabilidade, NÃO classificar como
        # crescimento só porque dy=0 — manter RENDA/VALOR por precaução.
        if dy_confiavel:
            is_growth = roe > 0.20 and dy < 0.04
        else:
            is_growth = False  # sem DY confiável, evitar Lynch (pode inflar valuation)
            logger.info(f"[{dados.get('ticker','?')}] DY não confiável → is_growth=False (conservador)")

        metodos = {}

        # ── 1. GRAHAM ─────────────────────────────────────────────────────────
        # Limite P/L aumentado de 20→25 para acomodar cíclicos em pico de lucro
        limite_pvp = 3.0 if is_growth else 2.5
        limite_pl  = 25.0  # mesmo para ambos os perfis (era 20 para RENDA/VALOR)
        pl_graham  = max(pl, 7.0)   # floor de 7x para evitar FV absurdo com PL baixo

        # Se PL veio do Yahoo com flag de baixa confiabilidade (PL negativo ou >80),
        # Graham é ignorado mesmo dentro do limite — melhor não aplicar com dado suspeito
        if not pl_confiavel:
            logger.info(f"[{dados.get('ticker','?')}] Graham IGNORADO — pl_confiavel=False (PL via Yahoo suspeito)")
        elif pl > 0 and pvp > 0 and pl <= limite_pl and pvp <= limite_pvp:
            lpa_adj = p / pl_graham
            metodos['Graham'] = (22.5 * lpa_adj * vpa) ** 0.5

        # ── 2. BAZIN ─────────────────────────────────────────────────────────
        # Só para RENDA com DY confiável; usa taxa mínima = max(selic, 5%)
        if not is_growth and dy > 0 and dy_confiavel:
            if dy > 0.15:
                riscos.append("DY muito alto (possível armadilha)")
                confianca -= 10
            taxa_minima = max(selic, 0.05)
            metodos['Bazin'] = (dy * p) / taxa_minima

        # ── 3. PETER LYNCH ───────────────────────────────────────────────────
        # Só para CRESCIMENTO com DY confiável e lpa > 0 e roe > 0
        if is_growth and pl > 0 and dy_confiavel and lpa > 0 and roe > 0:
            payout_ratio = min((dy * p) / lpa, 0.95)
            retencao = 1 - payout_ratio
            g = roe * retencao
            g = min(g, 0.25)
            pl_justo = 1.5 * (g * 100)
            pl_justo = min(pl_justo, 35)
            metodos['Lynch'] = lpa * pl_justo

        # ── 4. GORDON ─────────────────────────────────────────────────────────
        # Modelo de dividendos; exige DY confiável e real (>4%) e ROE sólido
        if dy_confiavel and dy > 0.04 and roe > 0.10:
            payout_ratio_g = min((dy * p) / lpa, 0.95) if lpa > 0 else 0.5
            retencao_g = 1 - payout_ratio_g
            g = roe * retencao_g
            g = min(g, 0.08)
            k = selic + 0.04
            if k > g:
                div_prox = (dy * p) * (1 + g)
                metodos['Gordon'] = div_prox / (k - g)

        # ── CÁLCULO FINAL ─────────────────────────────────────────────────────
        valores_validos = list(metodos.values())

        if not valores_validos:
            fair_value = p
            upside     = 0.0
        else:
            fair_value = sum(valores_validos) / len(valores_validos)
            upside     = (fair_value / p) - 1
            
            if len(valores_validos) >= 2:
                if max(valores_validos) / max(min(valores_validos), 0.01) > 2.0:
                    riscos.append("Métodos divergentes")
                    confianca -= 10

        if pl <= 0 or pvp <= 0:
            riscos.append("Dados incompletos")
            confianca -= 10

        # ── SCORE (Sigmoid) ───────────────────────────────────────────────────
        score = 50 + 48 * (2 / (1 + math.exp(-upside * 3)) - 1)
        score = max(0, min(100, score))

        # Ajustes de qualidade (aplicados independente do valuation)
        try:
            divida_texto = str(dados.get('divida_liq_ebitda') or 0).strip()
            if ',' in divida_texto and '.' in divida_texto:
                if divida_texto.rfind(',') > divida_texto.rfind('.'):
                    divida_texto = divida_texto.replace('.', '').replace(',', '.')
                else:
                    divida_texto = divida_texto.replace(',', '')
            else:
                divida_texto = divida_texto.replace(',', '.')
            divida_liq_ebitda = float(divida_texto)
            if not math.isfinite(divida_liq_ebitda):
                divida_liq_ebitda = 0.0
        except (TypeError, ValueError):
            divida_liq_ebitda = 0.0
        if divida_liq_ebitda > 3.0: 
            score -= 15
            riscos.append("Dívida elevada")
            confianca -= 15
            
        if roe > 0.20:  score += 10
        if roe < 0.05:  score -= 15
        
        if not dy_confiavel: 
            score -= 5
            riscos.append("DY suspeito")
            confianca -= 20
            
        if not pl_confiavel: 
            score -= 5
            riscos.append("PL não confiável")
            confianca -= 20
            
        score = max(0, min(100, score))

        # ── RECOMENDAÇÃO ──────────────────────────────────────────────────────
        rec = "NEUTRO"
        tecnico_negativo = dados.get('tecnico_negativo', False)
        if tecnico_negativo:
            riscos.append("Técnico negativo")
            confianca -= 10

        if upside > 0.15 and score >= 60 and confianca >= 50:
            rec = "COMPRA"
            if score >= 75 and confianca >= 70:
                rec = "COMPRA FORTE"
        elif score >= 75 and upside <= 0:
            rec = "QUALIDADE — AGUARDAR"
        elif upside < -0.15 and tecnico_negativo:
            rec = "VENDA"
        else:
            rec = "NEUTRO"

        detalhes = ", ".join([f"{k}: R${v:.2f}" for k, v in metodos.items()])

        logger.info(
            f"[{dados.get('ticker','?')}] "
            f"dy={dy:.4f}(conf={dy_confiavel}) pl={pl:.1f}(conf={pl_confiavel}) "
            f"is_growth={is_growth} "
            f"FV={fair_value:.2f} upside={upside*100:.1f}% score={int(score)} rec={rec}"
        )

        return {
            'fair_value':    round(fair_value, 2),
            'upside':        round(upside * 100, 1),
            'score_final':   int(score),
            'recomendacao':  rec,
            'metodos_usados': detalhes,
            'perfil':        'CRESCIMENTO' if is_growth else 'RENDA/VALOR',
            'pl_confiavel':  pl_confiavel,
            'confianca':     max(0, confianca),
            'riscos':        riscos,
        }
