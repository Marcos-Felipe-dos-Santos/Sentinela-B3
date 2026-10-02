import logging
import math
import statistics
from datetime import date

from config import DISTRESSED_TICKERS, MACRO, _normalizar_dy, get_selic_atual
from sentinela.domain.enums import Perfil
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import MethodInputs, MethodResult
from sentinela.methods.bazin import ALERTA_DY_ARMADILHA, Bazin, BazinParams
from sentinela.methods.gordon import Gordon, GordonParams
from sentinela.methods.graham import Graham, GrahamParams
from sentinela.methods.lynch import Lynch, LynchParams

logger = logging.getLogger("Valuation")

_GRAHAM = Graham()
_BAZIN = Bazin()
_LYNCH = Lynch()
_GORDON = Gordon()


def _finito(valor):
    """Valor não finito vira None antes de entrar em MethodInputs."""
    return valor if math.isfinite(valor) else None


class ValuationEngine:
    def _montar_inputs(
        self,
        p,
        pl,
        pvp,
        is_growth,
        pl_confiavel,
        dy=None,
        selic=None,
        dy_confiavel=True,
        roe=None,
        lpa=None,
    ):
        """Converte os dados já normalizados da V1 em MethodInputs (uma única vez)."""
        p, pl, pvp = _finito(p), _finito(pl), _finito(pvp)
        dy = None if dy is None else _finito(dy)
        selic = None if selic is None else _finito(selic)
        roe = None if roe is None else _finito(roe)
        lpa = None if lpa is None else _finito(lpa)
        vpa = None
        if p is not None and pvp is not None:
            vpa = _finito(p / pvp) if pvp > 0 else 0.0
        return MethodInputs(
            as_of=date.today(),
            preco=None if p is None else BRL(p),
            pl=None if pl is None else Ratio(pl),
            pvp=None if pvp is None else Ratio(pvp),
            vpa=None if vpa is None else BRL(vpa),
            lpa=None if lpa is None else BRL(lpa),
            roe=None if roe is None else Ratio(roe),
            dy=None if dy is None else Ratio(dy),
            selic=None if selic is None else RateNominal(selic),
            perfil=Perfil.CRESCIMENTO if is_growth else Perfil.RENDA,
            pl_confiavel=pl_confiavel,
            dy_confiavel=dy_confiavel,
        )

    def _avaliar_metodos(self, inputs):
        """Resultado de cada método extraído, na ordem da V1."""
        return {
            "Graham": _GRAHAM.calcular(
                inputs,
                GrahamParams(
                    pl_limite=MACRO.GRAHAM_PL_LIMITE,
                    pl_piso=MACRO.GRAHAM_PL_FLOOR,
                    pvp_limite_renda=MACRO.GRAHAM_PVP_LIMITE_RENDA,
                    pvp_limite_crescimento=MACRO.GRAHAM_PVP_LIMITE_CRESCIMENTO,
                ),
            ),
            "Bazin": _BAZIN.calcular(
                inputs,
                BazinParams(
                    dy_min=MACRO.BAZIN_DY_MIN,
                    dy_armadilha=MACRO.BAZIN_DY_ARMADILHA,
                    taxa_min=MACRO.BAZIN_TAXA_MIN,
                ),
            ),
            "Lynch": _LYNCH.calcular(
                inputs,
                LynchParams(
                    payout_max=MACRO.LYNCH_PAYOUT_MAX,
                    g_max=MACRO.LYNCH_G_MAX,
                    pl_multiplicador=MACRO.LYNCH_PL_MULTIPLICADOR,
                    pl_max=MACRO.LYNCH_PL_MAX,
                ),
            ),
            "Gordon": _GORDON.calcular(
                inputs,
                GordonParams(
                    dy_min=MACRO.GORDON_DY_MIN,
                    roe_min=MACRO.GORDON_ROE_MIN,
                    g_max=MACRO.GORDON_G_MAX,
                    premio_risco=MACRO.GORDON_PREMIO_RISCO,
                    payout_max=MACRO.GORDON_PAYOUT_MAX,
                ),
            ),
        }

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
        # Fórmula e condições em sentinela/methods/graham.py.
        # Se PL veio do Yahoo com flag de baixa confiabilidade (PL negativo ou >80),
        # Graham é ignorado mesmo dentro do limite — melhor não aplicar com dado suspeito
        resultados = self._avaliar_metodos(
            self._montar_inputs(
                p,
                pl,
                pvp,
                is_growth,
                pl_confiavel,
                dy=dy,
                selic=selic,
                dy_confiavel=dy_confiavel,
                roe=roe,
                lpa=lpa,
            )
        )
        graham = resultados["Graham"]
        if isinstance(graham, MethodResult):
            metodos['Graham'] = graham.valor.valor
        elif not pl_confiavel:
            logger.info(f"[{dados.get('ticker','?')}] Graham IGNORADO — pl_confiavel=False (PL via Yahoo suspeito)")

        # ── 2. BAZIN ─────────────────────────────────────────────────────────
        # Fórmula e condições em sentinela/methods/bazin.py.
        # O alerta de DY acima de 15% volta como alerta do resultado; o motor mantém
        # o risco e o desconto de confiança no mesmo ponto de `riscos`.
        bazin = resultados["Bazin"]
        if isinstance(bazin, MethodResult):
            if ALERTA_DY_ARMADILHA in bazin.alertas:
                riscos.append("DY muito alto (possível armadilha)")
                confianca -= 10
            metodos['Bazin'] = bazin.valor.valor

        # ── 3. PETER LYNCH ───────────────────────────────────────────────────
        # Fórmula e condições em sentinela/methods/lynch.py.
        lynch = resultados["Lynch"]
        if isinstance(lynch, MethodResult):
            metodos['Lynch'] = lynch.valor.valor

        # ── 4. GORDON ─────────────────────────────────────────────────────────
        # Fórmula e condições em sentinela/methods/gordon.py (regime nominal; a troca
        # por taxa real é o F2B-1).
        gordon = resultados["Gordon"]
        if isinstance(gordon, MethodResult):
            metodos['Gordon'] = gordon.valor.valor

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
