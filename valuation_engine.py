import logging
import math
import statistics
from config import get_selic_atual, DISTRESSED_TICKERS, MACRO, _normalizar_dy

logger = logging.getLogger("Valuation")

class ValuationEngine:
    def processar(self, dados):
        if not dados or not dados.get('preco_atual'):
            return None

        ticker = str(dados.get('ticker', '')).upper()
        p   = float(dados['preco_atual'])

        # ── GUARD: DISTRESSED TICKERS ────────────────────────────────────────
        # Empresas em recuperação judicial ou situação especial não devem
        # receber COMPRA ou COMPRA FORTE — valuation baseado em múltiplos
        # não reflete o risco real (dívida, diluição, governança).
        if ticker in DISTRESSED_TICKERS:
            logger.warning(
                f"[{ticker}] DISTRESSED — bloqueando recomendação positiva"
            )
            return {
                'fair_value':    round(p, 2),
                'upside':        0.0,
                'score_final':   30,
                'recomendacao':  'ALTO RISCO — EVITAR',
                'metodos_usados': '',
                'perfil':        'DISTRESSED',
                'pl_confiavel':  False,
                'dy_confiavel':  False,
                'confianca':     0,
                'riscos':        ['Empresa em situação especial/distressed'],
            }
        roe = float(dados.get('roe', 0) or 0)
        pl  = float(dados.get('pl',  0) or 0)
        pvp = float(dados.get('pvp', 0) or 0)

        # ── NORMALIZAÇÃO DO DY ────────────────────────────────────────────────
        # Yahoo Finance retorna dividendYield de formas inconsistentes entre tickers BR:
        #   Ex: PETR4 → 12.47  (percentagem bruta)  → dividir por 100 → 0.1247
        #   Ex: WEGE3 → 3.02   (percentagem bruta)  → dividir por 100 → 0.0302
        #   Ex: ITUB4 → 0.45   (dado suspeito)       → 45% DY impossível → cap
        dy_raw = float(dados.get('dy', 0) or 0)
        dy, dy_confiavel = _normalizar_dy(dy_raw)
        if dy_raw > MACRO.DY_PERCENTUAL_THRESHOLD:
            logger.info(f"[{dados.get('ticker','?')}] DY normalizado: {dy_raw:.4f}% → {dy:.4f} decimal")
        elif not dy_confiavel:
            logger.warning(
                f"[{dados.get('ticker','?')}] DY={dy_raw:.4f} ({dy_raw*100:.1f}%) improvável para B3 "
                f"— dado suspeito (Yahoo bug?). Desconsiderado."
            )

        lpa = (p / pl)  if pl  > 0 else 0
        vpa = (p / pvp) if pvp > 0 else 0

        selic = get_selic_atual()

        confianca = 100
        riscos = []

        if dados.get("erro_scraper"):
            confianca -= 30
            riscos.append("Dados fundamentais indisponíveis (scraper)")

        # pl_confiavel: False quando Yahoo retornou PL negativo (prejuízo) ou > 80 (TTM atípico)
        # Definido em market_engine.py; padrão True para dados do Fundamentus (mais confiáveis)
        pl_confiavel = bool(dados.get('pl_confiavel', True))

        # ── DETECÇÃO DE PERFIL ────────────────────────────────────────────────
        # CRESCIMENTO: ROE alto + dividendos baixos (empresa reinveste lucros)
        # ATENÇÃO: se DY foi zerado por falta de confiabilidade, NÃO classificar como
        # crescimento só porque dy=0 — manter RENDA/VALOR por precaução.
        if dy_confiavel:
            is_growth = roe > MACRO.ROE_CRESCIMENTO_MIN and dy < MACRO.DY_CRESCIMENTO_MAX
        else:
            is_growth = False  # sem DY confiável, evitar Lynch (pode inflar valuation)
            logger.info(f"[{dados.get('ticker','?')}] DY não confiável → is_growth=False (conservador)")

        metodos = {}

        # ── 1. GRAHAM ─────────────────────────────────────────────────────────
        # Limite P/L aumentado de 20→25 para acomodar cíclicos em pico de lucro
        limite_pvp = MACRO.GRAHAM_PVP_LIMITE_CRESCIMENTO if is_growth else MACRO.GRAHAM_PVP_LIMITE_RENDA
        limite_pl  = MACRO.GRAHAM_PL_LIMITE
        pl_graham  = max(pl, MACRO.GRAHAM_PL_FLOOR)   # floor para evitar FV absurdo com PL baixo

        # Se PL veio do Yahoo com flag de baixa confiabilidade (PL negativo ou >80),
        # Graham é ignorado mesmo dentro do limite — melhor não aplicar com dado suspeito
        if not pl_confiavel:
            logger.info(f"[{dados.get('ticker','?')}] Graham IGNORADO — pl_confiavel=False (PL via Yahoo suspeito)")
        elif pl > 0 and pvp > 0 and pl <= limite_pl and pvp <= limite_pvp:
            lpa_adj = p / pl_graham
            metodos['Graham'] = (22.5 * lpa_adj * vpa) ** 0.5

        # ── 2. BAZIN ─────────────────────────────────────────────────────────
        # Só para RENDA com DY confiável; usa taxa mínima = max(selic, 5%)
        # Bazin foi criado para pagadoras de dividendos consistentes.
        # Gate de 5% evita avaliar pelo modelo de renda empresas com DY
        # simbólico (0-4%), que produziria fair value incorretamente baixo.
        if not is_growth and dy >= MACRO.BAZIN_DY_MIN and dy_confiavel:
            if dy > MACRO.BAZIN_DY_ARMADILHA:
                riscos.append("DY muito alto (possível armadilha)")
                confianca -= 10
            taxa_minima = max(selic, MACRO.BAZIN_TAXA_MIN)
            metodos['Bazin'] = (dy * p) / taxa_minima

        # ── 3. PETER LYNCH ───────────────────────────────────────────────────
        # Só para CRESCIMENTO com DY confiável e lpa > 0 e roe > 0
        if is_growth and pl > 0 and dy_confiavel and lpa > 0 and roe > 0:
            payout_ratio = min((dy * p) / lpa, MACRO.LYNCH_PAYOUT_MAX)
            retencao = 1 - payout_ratio
            g = roe * retencao
            g = min(g, MACRO.LYNCH_G_MAX)
            pl_justo = MACRO.LYNCH_PL_MULTIPLICADOR * (g * 100)
            pl_justo = min(pl_justo, MACRO.LYNCH_PL_MAX)
            metodos['Lynch'] = lpa * pl_justo

        # ── 4. GORDON ─────────────────────────────────────────────────────────
        # Modelo de dividendos; exige DY confiável e real (>4%) e ROE sólido
        if dy_confiavel and dy > MACRO.GORDON_DY_MIN and roe > MACRO.GORDON_ROE_MIN:
            payout_ratio_g = min((dy * p) / lpa, MACRO.GORDON_PAYOUT_MAX) if lpa > 0 else 0.5
            retencao_g = 1 - payout_ratio_g
            g = roe * retencao_g
            g = min(g, MACRO.GORDON_G_MAX)
            k = selic + MACRO.GORDON_PREMIO_RISCO
            if k > g:
                div_prox = (dy * p) * (1 + g)
                metodos['Gordon'] = div_prox / (k - g)

        # ── CÁLCULO FINAL ─────────────────────────────────────────────────────
        valores_validos = list(metodos.values())

        if not valores_validos:
            fair_value = p
            upside     = 0.0
        else:
            # Mediana em vez de média: Graham (patrimonial), Bazin (renda) e
            # Gordon (DCF) respondem perguntas diferentes. Quando divergem >2x,
            # a média aritmética produz um valor sem significado econômico.
            # statistics.median: 1 valor → o valor; 2 → média; 3+ → mediana.
            fair_value = statistics.median(valores_validos)
            upside     = (fair_value / p) - 1

            if len(valores_validos) >= 2:
                if max(valores_validos) / max(min(valores_validos), 0.01) > MACRO.METODOS_DIVERGENCIA_RATIO:
                    riscos.append("Métodos divergentes")
                    confianca -= 10

        if pl <= 0 or pvp <= 0:
            riscos.append("Dados incompletos")
            confianca -= 10

        # ── SCORE (Sigmoid) ───────────────────────────────────────────────────
        score = 50 + MACRO.SCORE_SIGMOID_AMPLITUDE * (2 / (1 + math.exp(-upside * MACRO.SCORE_SIGMOID_INCLINACAO)) - 1)
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
        if divida_liq_ebitda > MACRO.DIVIDA_EBITDA_LIMITE:
            score -= 15
            riscos.append("Dívida elevada")
            confianca -= 15

        if roe > MACRO.ROE_BONUS_MIN:    score += 10
        if roe < MACRO.ROE_PENALIDADE_MAX: score -= 15

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

        if upside > MACRO.REC_UPSIDE_COMPRA and score >= MACRO.REC_SCORE_COMPRA and confianca >= MACRO.REC_CONFIANCA_COMPRA:
            rec = "COMPRA"
            if score >= MACRO.REC_SCORE_FORTE and confianca >= MACRO.REC_CONFIANCA_FORTE:
                rec = "COMPRA FORTE"
        elif score >= MACRO.REC_SCORE_FORTE and upside <= 0:
            rec = "QUALIDADE — AGUARDAR"
        elif upside < MACRO.REC_UPSIDE_VENDA:
            rec = "VENDA"
        else:
            rec = "NEUTRO"

        if rec == "COMPRA FORTE" and riscos:
            rec = "COMPRA"

        # ── GUARD: Scraper falhou → não recomendar compra ─────────────────────
        # Dados fundamentais incompletos não significam que o ativo é ruim,
        # apenas que não há confiança suficiente para sugerir compra.
        # Preserva valores calculados para transparência.
        # Não sobrescreve VENDA nem ALTO RISCO — EVITAR.
        if rec in ("COMPRA", "COMPRA FORTE") and dados.get('erro_scraper'):
            rec = "DADOS INSUFICIENTES — AGUARDAR"
            riscos.append("Dados fundamentais insuficientes para análise precisa")
            confianca = min(confianca, 50)
            logger.warning(
                f"[{ticker}] Downgrade → DADOS INSUFICIENTES: "
                f"erro_scraper=True, rec original seria COMPRA/FORTE"
            )

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
            'dy_confiavel':  dy_confiavel,
            'confianca':     max(0, confianca),
            'riscos':        riscos,
        }
