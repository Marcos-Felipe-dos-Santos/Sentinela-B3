import logging
import math
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from config import MACRO, _normalizar_dy, get_selic_atual
from sentinela.data import liquidez, rendimento_fii
from sentinela.domain.apresentacao import bloco
from sentinela.domain.enums import AssetType
from sentinela.domain.units import BRL, RateReal, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.fii_nav import FiiNav, FiiNavParams
from sentinela.methods.fii_yield import FiiYield, FiiYieldParams

logger = logging.getLogger("FII")

_FII_YIELD = FiiYield()
_FII_NAV = FiiNav()


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
        # F2B-58 (BUG-2B-46): a NTN-B já vem conferida pelo corte temporal das entradas.
        inputs = MethodInputs(
            as_of=instante.astimezone(ZoneInfo("America/Sao_Paulo")).date(),
            preco=BRL(p),
            dy=Ratio(entradas["dy"]),
            ntnb_real=RateReal(entradas["ntnb_real"]),
            classe_ativo=AssetType.FII,  # F2B-4: motor de FII, classe oficial FII
        )
        return _FII_YIELD.calcular(
            inputs, FiiYieldParams(spread=getattr(MACRO, "FII_SPREAD_TIJOLO", None))
        )

    def _faixa_pvp(self, pvp):
        """Lente de P/VP; None quando o P/VP não é finito (a lente não é calculada)."""
        if not math.isfinite(pvp):
            return None
        return _FII_NAV.calcular(
            MethodInputs(
                as_of=date.today(), pvp=Ratio(pvp), classe_ativo=AssetType.FII
            ),
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

        gate_liquidez = (
            liquidez.avaliar(
                dados.get("liquidez"),
                janela=MACRO.LIQUIDEZ_JANELA,
                presenca_min=MACRO.LIQUIDEZ_PRESENCA_MIN,
                volume_min=MACRO.LIQUIDEZ_VOLUME_FII_MIN,
            )
            if "liquidez" in dados
            else None
        )
        if gate_liquidez and "abstencao" in gate_liquidez:
            return {
                "abstencao": gate_liquidez["abstencao"],
                "metodos_usados": "",
                "perfil": "LIQUIDEZ INSUFICIENTE",
                "pl_confiavel": False,
                "dy_confiavel": False,
                "confianca": 0,
                "riscos": [gate_liquidez["abstencao"]],
                "lentes": {
                    _FII_YIELD.nome: bloco(
                        _FII_YIELD,
                        Abstention(
                            _FII_YIELD.nome,
                            _FII_YIELD.version,
                            gate_liquidez["abstencao"],
                        ),
                        p,
                        {},
                    )
                },
            }

        rendimento = None

        def _com_aviso(resultado: dict) -> dict:
            # F2B-45 (auditoria D30 do Claude): o aviso fica num campo próprio, fora de
            # `riscos`, como o `perfil_fonte`; liquidez não medida não muda a classificação.
            if gate_liquidez and "aviso" in gate_liquidez:
                resultado["aviso_liquidez"] = gate_liquidez["aviso"]
            motivo = resultado.get("metodos_usados", "lente não calculada")
            resultado["lentes"] = {
                _FII_YIELD.nome: bloco(
                    _FII_YIELD,
                    rendimento
                    or Abstention(_FII_YIELD.nome, _FII_YIELD.version, motivo),
                    p,
                    (dados.get("rendimento_fii_cvm") or {})
                    if rendimento is not None
                    else {},
                )
            }
            return resultado

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
        # F2C-3: abstenção sem valor, distância ou score; motivo explícito na lente.
        if dy == 0 or not dy_confiavel:
            return _com_aviso(
                {
                    "perfil": "FII",
                    "metodos_usados": "Dados insuficientes (DY ausente ou inválido)",
                }
            )

        # P/VP: o oficial da CVM chega pela cascata (F2A-11). Sem P/VP positivo e finito
        # (ausente, zero, negativo, NaN ou infinito; F2A-42), a lente não é calculada, não
        # pontua e a saída traz `pvp` nulo.
        pvp = float(dados.get("pvp") or 0)
        if pvp <= 0 or not math.isfinite(pvp):
            pvp = None

        # ── Rendimento do FII (F2B-2; ficha FII 1.1) ─────────────────────────
        # Preço justo = rendimento de 12 meses do Informe ÷ (NTN-B real + spread), em
        # sentinela/methods/fii_yield.py. Selic líquida permanece contexto nominal,
        # sem pontuar. Vacância sem fonte oficial não altera o rendimento.
        instante = as_of if as_of is not None else datetime.now(UTC)
        rendimento = self._calcular_rendimento(dados, p, instante)
        if isinstance(rendimento, MethodResult):
            preco_justo = rendimento.valor.valor
        else:
            # Lente não calculada (fora do escopo, sem Informe elegível, sem NTN-B ou spread,
            # resultado não finito): o resultado do DY inválido, com o motivo.
            motivo = rendimento.motivo
            return _com_aviso(
                {
                    "perfil": "FII",
                    "metodos_usados": f"Dados insuficientes ({_FII_YIELD.nome}: {motivo})",
                }
            )
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
        # O patrimônio e a taxa nominal permanecem contexto, sem pontos ou sinais.
        if pvp is not None:
            self._faixa_pvp(pvp)
        tipo = str(dados.get("tipo") or "TIPO INDISPONÍVEL")

        return _com_aviso(
            {
                "fair_value": round(preco_justo, 2),
                "upside": round(upside * 100, 1),
                "tipo": tipo,
                "perfil": "FII",
                "metodos_usados": f"{_FII_YIELD.nome}: R${preco_justo:.2f}",
                "dy": dy,
                "dy_efetivo": dy_efetivo,
                "pvp": pvp,
                "selic_liquida": selic_liquida,
                "avisos_rendimento": list(
                    dados["rendimento_fii_cvm"].get("avisos", ())
                ),
            }
        )
