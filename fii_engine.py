import logging
from config import get_selic_atual, MACRO, _normalizar_dy

logger = logging.getLogger("FII")

VACANCIA_CONHECIDA = {
    # Estimativas manuais; revisar periodicamente.
    "CVBI11": 0.25,
    "MALL11": 0.18,
    "HGLG11": 0.08,
    "RBRP11": 0.00,
    "MXRF11": 0.05,
}

class FIIEngine:
    def analisar(self, dados: dict) -> dict:
        if not dados:
            return None

        p   = float(dados.get('preco_atual', 0) or 0)
        pvp = float(dados.get('pvp', 1.0) or 1.0)

        if p == 0:
            return None

        # ── NORMALIZAÇÃO DO DY ────────────────────────────────────────────────
        # Yahoo Finance retorna dividendYield inconsistente para FIIs também:
        #   Ex: alguns FIIs → 8.50 (percentagem bruta) → dividir por 100 → 0.085
        #   Ex: outros FIIs → 0.45 (dado suspeito) → 45% DY impossível → cap
        dy_raw = float(dados.get('dy', 0) or 0)
        dy, dy_confiavel = _normalizar_dy(dy_raw)
        if dy_raw > MACRO.DY_PERCENTUAL_THRESHOLD:
            logger.info(f"[FII {dados.get('ticker','?')}] DY normalizado: {dy_raw:.4f}% → {dy:.4f} decimal")
        elif not dy_confiavel:
            logger.warning(
                f"[FII {dados.get('ticker','?')}] DY={dy_raw:.4f} ({dy_raw*100:.1f}%) improvável "
                f"— dado suspeito (Yahoo bug?). Desconsiderado."
            )

        # ── FALLBACK: sem DY confiável não podemos calcular valuation ─────────
        if dy == 0 or not dy_confiavel:
            return {
                'fair_value':    round(p, 2),
                'upside':        0.0,
                'score_final':   50,
                'recomendacao':  'NEUTRO',
                'perfil':        'FII',
                'metodos_usados': 'Dados insuficientes (DY ausente ou inválido)',
            }

        ticker = dados.get('ticker', '')
        vacancia = None
        if ticker in VACANCIA_CONHECIDA:
            vacancia = VACANCIA_CONHECIDA[ticker]
            dy_efetivo = dy * (1 - vacancia)
        else:
            dy_efetivo = dy

        selic = get_selic_atual()
        selic_liquida = selic * MACRO.FII_FATOR_IR

        # Bazin adaptado para FIIs (yield vs taxa livre de risco)
        preco_justo = (p * dy_efetivo) / selic_liquida
        upside      = (preco_justo / p) - 1

        # Score
        score = 50
        if dy_efetivo > selic_liquida:
            score += 20
        elif dy_efetivo < (selic_liquida * MACRO.FII_DY_SELIC_RATIO_MIN):
            score -= 20
        pvp = float(dados.get('pvp', 1.0) or 1.0)
        if pvp > MACRO.FII_PVP_PREMIO_ALTO:
            score -= 15  # pagando prêmio excessivo sobre o patrimônio
        elif pvp > MACRO.FII_PVP_PREMIO_MODERADO:
            score -= 7   # prêmio moderado
        elif pvp < MACRO.FII_PVP_DESCONTO:
            score += 10  # desconto relevante = margem de segurança

        if vacancia is not None:
            if vacancia > 0.15:
                score -= int(100 * vacancia)

        score = max(0, min(100, score))

        # Heurística removida: não é possível determinar o tipo pelo P/VP
        tipo = str(dados.get('tipo') or "TIPO INDISPONÍVEL")

        rec = "NEUTRO"
        if upside > MACRO.FII_UPSIDE_COMPRA:
            rec = "COMPRA"
        if upside < MACRO.FII_UPSIDE_VENDA:
            rec = "VENDA"

        return {
            'fair_value':    round(preco_justo, 2),
            'upside':        round(upside * 100, 1),
            'score_final':   int(score),
            'recomendacao':  rec,
            'tipo':          tipo,
            'perfil':        'FII',
            'metodos_usados': f'Bazin FII: R${preco_justo:.2f}',
            'dy':            dy,
            'dy_efetivo':    dy_efetivo,
        }
