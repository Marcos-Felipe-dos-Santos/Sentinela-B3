import logging
import math
from datetime import date

from config import MACRO, _normalizar_dy, get_selic_atual
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import MethodInputs, MethodResult
from sentinela.methods.fii_nav import (
    FAIXA_DESCONTO,
    FAIXA_PREMIO_ALTO,
    FAIXA_PREMIO_MODERADO,
    FiiNav,
    FiiNavParams,
)
from sentinela.methods.fii_yield import FiiYield, FiiYieldParams

logger = logging.getLogger("FII")

_FII_YIELD = FiiYield()
_FII_NAV = FiiNav()
# pontos de score por faixa de P/VP; a faixa neutra não pontua
_PONTOS_PVP = {FAIXA_PREMIO_ALTO: -15, FAIXA_PREMIO_MODERADO: -7, FAIXA_DESCONTO: 10}


class FIIEngine:
    def _calcular_rendimento(self, p, dy, vacancia, selic):
        """Monta MethodInputs uma única vez e delega o preço justo ao método.

        Devolve None quando algum valor não é finito: o método não é calculado.
        """
        valores = (p, dy, selic) if vacancia is None else (p, dy, selic, vacancia)
        if not all(math.isfinite(v) for v in valores):
            return None
        inputs = MethodInputs(
            as_of=date.today(),
            preco=BRL(p),
            dy=Ratio(dy),
            selic=RateNominal(selic),
            vacancia=None if vacancia is None else Ratio(vacancia),
        )
        return _FII_YIELD.calcular(inputs, FiiYieldParams(fator_ir=MACRO.FII_FATOR_IR))

    def _faixa_pvp(self, pvp):
        """Lente de P/VP; None quando o P/VP não é finito (a lente não é calculada)."""
        if not math.isfinite(pvp):
            return None
        return _FII_NAV.calcular(
            MethodInputs(as_of=date.today(), pvp=Ratio(pvp)),
            FiiNavParams(
                premio_alto=MACRO.FII_PVP_PREMIO_ALTO,
                premio_moderado=MACRO.FII_PVP_PREMIO_MODERADO,
                desconto=MACRO.FII_PVP_DESCONTO,
            ),
        )

    def analisar(self, dados: dict) -> dict:
        if not dados:
            return None

        p = float(dados.get("preco_atual", 0) or 0)
        if p <= 0 or not math.isfinite(p):
            # F2A-24 e F2B-20: preço não finito ou negativo, como preço zero, não é analisado.
            return None

        ticker = dados.get("ticker", "")

        # ── INVARIANTE DO DY ──────────────────────────────────────────────────
        # O DY chega em razão; a conversão é da fronteira do provedor (F2A-4).
        dy_raw = float(dados.get("dy", 0) or 0)
        dy, dy_confiavel = _normalizar_dy(dy_raw)
        if not dy_confiavel:
            logger.warning(
                f"[FII {ticker}] DY={dy_raw:.4f} fora de 0 a 25% "
                "— dado suspeito. Desconsiderado."
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

        # P/VP: o oficial da CVM chega pela cascata (F2A-11). Sem P/VP positivo e finito
        # (ausente, zero, negativo, NaN ou infinito; F2A-42), a lente não é calculada, não
        # pontua e a saída traz `pvp` nulo.
        pvp = float(dados.get("pvp") or 0)
        if pvp <= 0 or not math.isfinite(pvp):
            pvp = None

        # Vacância: sem fonte oficial (o Informe Mensal não a traz), o método recebe None
        # (F2A-23, F2A-13).
        # ── Bazin adaptado para FIIs (yield vs taxa livre de risco) ──────────
        # Fórmula, DY efetivo (ajustado por vacância) e Selic líquida em
        # sentinela/methods/fii_yield.py.
        selic = get_selic_atual()
        rendimento = self._calcular_rendimento(p, dy, None, selic)
        if isinstance(rendimento, MethodResult):
            preco_justo = rendimento.valor.valor
            dy_efetivo = rendimento.obter("dy_efetivo").valor
            selic_liquida = rendimento.obter("selic_liquida").valor
        else:
            # F2A-24: método não calculado (Selic zero ou não finita, vacância não finita).
            # A V1 propagava NaN até a saída; agora é o resultado do DY inválido, com o motivo.
            motivo = (
                rendimento.motivo
                if rendimento is not None
                else "valor não finito na entrada (Selic ou vacância)"
            )
            return {
                "fair_value":     round(p, 2),
                "upside":         0.0,
                "score_final":    50,
                "recomendacao":   "NEUTRO",
                "perfil":         "FII",
                "metodos_usados": f"Dados insuficientes ({_FII_YIELD.nome}: {motivo})",
            }
        upside = (preco_justo / p) - 1

        # ── Score ─────────────────────────────────────────────────────────────
        score = 50
        if dy_efetivo > selic_liquida:
            score += 20
        elif dy_efetivo < (selic_liquida * MACRO.FII_DY_SELIC_RATIO_MIN):
            score -= 20

        # Faixa de P/VP em sentinela/methods/fii_nav.py; os pontos ficam aqui.
        lente_pvp = self._faixa_pvp(pvp) if pvp is not None else None
        if isinstance(lente_pvp, MethodResult):
            score += sum(_PONTOS_PVP.get(faixa, 0) for faixa in lente_pvp.alertas)

        score = max(0, min(100, score))

        tipo = str(dados.get("tipo") or "TIPO INDISPONÍVEL")

        rec = "NEUTRO"
        if upside > MACRO.FII_UPSIDE_COMPRA:
            rec = "COMPRA"
        if upside < MACRO.FII_UPSIDE_VENDA:
            rec = "VENDA"

        return {
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
