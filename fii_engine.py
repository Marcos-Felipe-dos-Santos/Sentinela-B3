import logging
import math
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from config import MACRO, _normalizar_dy, get_selic_atual
from sentinela.data import rendimento_fii
from sentinela.domain.units import BRL, RateReal, Ratio
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
    def _calcular_rendimento(self, dados, p, instante):
        """Lente de rendimento (F2B-2): Informe e B3 pela cascata, NTN-B real e spread datado.

        Grava `dados['rendimento_fii_cvm']` (o rendimento elegível ou a abstenção) e devolve o
        resultado do método, ou a abstenção das entradas. A Selic não entra.
        """
        entradas = rendimento_fii.entradas(dados, instante)
        if isinstance(entradas, rendimento_fii.Abstencao):
            dados["rendimento_fii_cvm"] = {"abstencao": entradas.motivo}
            return entradas
        dados["rendimento_fii_cvm"] = entradas
        taxa = dados.get("taxa_real")
        ntnb = taxa.get("ntnb") if isinstance(taxa, dict) else None
        ntnb_valida = (
            isinstance(ntnb, (int, float))
            and not isinstance(ntnb, bool)
            and math.isfinite(ntnb)
        )
        inputs = MethodInputs(
            as_of=instante.astimezone(ZoneInfo("America/Sao_Paulo")).date(),
            preco=BRL(p),
            dy=Ratio(entradas["dy"]),
            ntnb_real=RateReal(ntnb) if ntnb_valida else None,
        )
        return _FII_YIELD.calcular(
            inputs, FiiYieldParams(spread=getattr(MACRO, "FII_SPREAD_TIJOLO", None))
        )

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

    def analisar(self, dados: dict, as_of: datetime | None = None) -> dict:
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

        # ── Rendimento do FII (F2B-2; ficha FII 1.1) ─────────────────────────
        # Preço justo = rendimento de 12 meses do Informe ÷ (NTN-B real + spread), em
        # sentinela/methods/fii_yield.py. A Selic líquida fica como contexto e no score, que
        # não muda na 2B (decisão de 19/10/2026). Vacância: sem fonte oficial (F2A-23); o DY
        # efetivo do score é o próprio DY.
        instante = as_of if as_of is not None else datetime.now(UTC)
        rendimento = self._calcular_rendimento(dados, p, instante)
        if isinstance(rendimento, MethodResult):
            preco_justo = rendimento.valor.valor
        else:
            # Lente não calculada (fora do escopo, sem Informe elegível, sem NTN-B ou spread,
            # resultado não finito): o resultado do DY inválido, com o motivo.
            motivo = rendimento.motivo
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
        selic = get_selic_atual()
        dy_efetivo = dy
        # Selic não finita fica sem a comparação, em vez de levar NaN à saída (F2A-24).
        selic_liquida = (
            selic * MACRO.FII_FATOR_IR
            if isinstance(selic, (int, float)) and math.isfinite(selic)
            else None
        )
        score = 50
        if selic_liquida is None:
            pass
        elif dy_efetivo > selic_liquida:
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
            "metodos_usados": f"{_FII_YIELD.nome}: R${preco_justo:.2f}",
            "dy":             dy,
            "dy_efetivo":     dy_efetivo,
            "pvp":            pvp,
            "selic_liquida":  selic_liquida,
            "avisos_rendimento": list(dados["rendimento_fii_cvm"].get("avisos", ())),
        }
