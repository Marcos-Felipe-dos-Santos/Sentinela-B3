import logging
from typing import Optional

from config import get_selic_atual, MACRO, _normalizar_dy
from cvm_fii_map import get_cnpj_fii
from cvm_fii_provider import CVMFIIProvider

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
    def __init__(self, cvm_provider: Optional[CVMFIIProvider] = None):
        # None = CVM desabilitado (sem chamadas de rede); útil em testes.
        self._cvm_provider = cvm_provider

    def _obter_cvm_dados(self, ticker: str) -> Optional[dict]:
        provider = getattr(self, "_cvm_provider", None)
        if provider is None:
            return None
        cnpj = get_cnpj_fii(ticker)
        if cnpj is None:
            return None
        try:
            return provider.obter_dados_fii(cnpj)
        except Exception as exc:
            logger.warning("[FII %s] CVM error: %s", ticker, exc)
            return None

    def analisar(self, dados: dict) -> dict:
        if not dados:
            return None

        p = float(dados.get("preco_atual", 0) or 0)
        if p == 0:
            return None

        ticker = dados.get("ticker", "")

        # ── NORMALIZAÇÃO DO DY ────────────────────────────────────────────────
        dy_raw = float(dados.get("dy", 0) or 0)
        dy, dy_confiavel = _normalizar_dy(dy_raw)
        if dy_raw > MACRO.DY_PERCENTUAL_THRESHOLD:
            logger.info(
                f"[FII {ticker}] DY normalizado: {dy_raw:.4f}% → {dy:.4f} decimal"
            )
        elif not dy_confiavel:
            logger.warning(
                f"[FII {ticker}] DY={dy_raw:.4f} ({dy_raw*100:.1f}%) improvável "
                "— dado suspeito (Yahoo bug?). Desconsiderado."
            )

        # ── FALLBACK: sem DY confiável não podemos calcular valuation ─────────
        if dy == 0 or not dy_confiavel:
            return {
                "fair_value":     round(p, 2),
                "upside":         0.0,
                "score_final":    50,
                "recomendacao":   "NEUTRO",
                "perfil":         "FII",
                "metodos_usados": "Dados insuficientes (DY ausente ou inválido)",
            }

        # ── CVM: VPA oficial e vacância ───────────────────────────────────────
        cvm = self._obter_cvm_dados(ticker)

        # P/VP: prioriza VPA oficial da CVM (PL/cotas)
        vpa_cvm = cvm.get("valor_cota") if cvm else None
        if vpa_cvm and vpa_cvm > 0:
            pvp = p / vpa_cvm
        else:
            pvp = float(dados.get("pvp", 1.0) or 1.0)

        # Vacância: CVM (quando disponível) > VACANCIA_CONHECIDA (manual) > None
        vacancia: Optional[float] = None
        vacancia_fonte: Optional[str] = None

        if cvm:
            vac_cvm = cvm.get("vacancia_fisica")
            if vac_cvm is not None:
                vacancia = vac_cvm
                vacancia_fonte = "CVM"

        if vacancia is None and ticker in VACANCIA_CONHECIDA:
            vacancia = VACANCIA_CONHECIDA[ticker]
            vacancia_fonte = "manual"

        # ── DY efetivo (ajustado por vacância) ───────────────────────────────
        if vacancia is not None:
            dy_efetivo = dy * (1 - vacancia)
        else:
            dy_efetivo = dy

        selic = get_selic_atual()
        selic_liquida = selic * MACRO.FII_FATOR_IR

        # Bazin adaptado para FIIs (yield vs taxa livre de risco)
        preco_justo = (p * dy_efetivo) / selic_liquida
        upside = (preco_justo / p) - 1

        # ── Score ─────────────────────────────────────────────────────────────
        score = 50
        if dy_efetivo > selic_liquida:
            score += 20
        elif dy_efetivo < (selic_liquida * MACRO.FII_DY_SELIC_RATIO_MIN):
            score -= 20

        if pvp > MACRO.FII_PVP_PREMIO_ALTO:
            score -= 15  # pagando prêmio excessivo sobre o patrimônio
        elif pvp > MACRO.FII_PVP_PREMIO_MODERADO:
            score -= 7   # prêmio moderado
        elif pvp < MACRO.FII_PVP_DESCONTO:
            score += 10  # desconto relevante = margem de segurança

        if vacancia is not None and vacancia > 0.15:
            score -= int(100 * vacancia)

        score = max(0, min(100, score))

        tipo = str(dados.get("tipo") or "TIPO INDISPONÍVEL")

        rec = "NEUTRO"
        if upside > MACRO.FII_UPSIDE_COMPRA:
            rec = "COMPRA"
        if upside < MACRO.FII_UPSIDE_VENDA:
            rec = "VENDA"

        result: dict = {
            "fair_value":     round(preco_justo, 2),
            "upside":         round(upside * 100, 1),
            "score_final":    int(score),
            "recomendacao":   rec,
            "tipo":           tipo,
            "perfil":         "FII",
            "metodos_usados": f"Bazin FII: R${preco_justo:.2f}",
            "dy":             dy,
            "dy_efetivo":     dy_efetivo,
            "pvp":            pvp,
        }

        if vacancia_fonte is not None:
            result["vacancia_fonte"] = vacancia_fonte

        return result
