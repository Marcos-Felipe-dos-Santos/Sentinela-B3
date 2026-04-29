import logging
from config import get_selic_atual

logger = logging.getLogger("FII")

VACANCIA_CONHECIDA = {
    # examples only if already relevant in tests
}

class FIIEngine:
    def analisar(self, dados: dict) -> dict:
        if not dados:
            return None

        p   = float(dados.get('preco_atual', 0) or 0)
        pvp = float(dados.get('pvp', 1.0) or 1.0)

        if p == 0:
            return None

        # ── NORMALIZAÇÃO DO DY (idêntico ao valuation_engine) ────────────────
        # Yahoo Finance retorna dividendYield inconsistente para FIIs também:
        #   Ex: alguns FIIs → 8.50 (percentagem bruta) → dividir por 100 → 0.085
        #   Ex: outros FIIs → 0.45 (dado suspeito) → 45% DY impossível → cap
        #
        # Regra 1: se dy > 1   → Yahoo retornou como % → dividir por 100
        # Regra 2: se dy > 0.25 → 25% DY é impossível para qualquer ativo B3 → inválido
        dy_raw = float(dados.get('dy', 0) or 0)
        dy_confiavel = True

        if dy_raw > 1:
            dy = dy_raw / 100
            logger.info(f"[FII {dados.get('ticker','?')}] DY normalizado: {dy_raw:.4f}% → {dy:.4f} decimal")
        elif dy_raw > 0.25:
            logger.warning(
                f"[FII {dados.get('ticker','?')}] DY={dy_raw:.4f} ({dy_raw*100:.1f}%) improvável "
                f"— dado suspeito (Yahoo bug?). Desconsiderado."
            )
            dy = 0.0
            dy_confiavel = False
        else:
            dy = dy_raw

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

        # Bazin adaptado para FIIs (yield vs taxa livre de risco)
        preco_justo = (p * dy_efetivo) / selic
        upside      = (preco_justo / p) - 1

        # Score
        score = 50
        if dy_efetivo > selic:
            score += 20
        elif dy_efetivo < (selic * 0.7):
            score -= 20
        pvp = float(dados.get('pvp', 1.0) or 1.0)
        if pvp > 1.15:
            score -= 15  # pagando prêmio excessivo sobre o patrimônio
        elif pvp > 1.05:
            score -= 7  # prêmio moderado
        elif pvp < 0.85:
            score += 10  # desconto relevante = margem de segurança
            
        if vacancia is not None:
            if vacancia > 0.15:
                score -= int(100 * vacancia)
                
        score = max(0, min(100, score))

        # Heurística removida: não é possível determinar o tipo pelo P/VP
        tipo = str(dados.get('tipo') or "TIPO INDISPONÍVEL")

        rec = "NEUTRO"
        if upside > 0.10:
            rec = "COMPRA"
        if upside < -0.10:
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
