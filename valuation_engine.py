import logging
import math
import statistics
from dataclasses import replace
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from config import DISTRESSED_TICKERS, MACRO, _normalizar_dy, get_selic_atual
from sentinela.data import gordon_cvm, liquidez, proventos_b3
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


# F2A-29 (P7): classes sem os métodos de ação; o `applies_to` dos métodos é do F2B-4.
CLASSES_FORA_DO_ESCOPO = frozenset({"ETF", "BDR", "UNKNOWN"})
ROTULO_FORA_DO_ESCOPO = "FORA DO ESCOPO DOS MÉTODOS"


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

    def _avaliar_metodos(self, inputs, inputs_gordon=None, inputs_bazin=None):
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
                inputs if inputs_bazin is None else inputs_bazin,
                BazinParams(
                    dy_min=MACRO.BAZIN_DY_MIN,
                    dy_armadilha=MACRO.BAZIN_DY_ARMADILHA,
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
                inputs if inputs_gordon is None else inputs_gordon, GordonParams()
            ),
        }

    def processar(self, dados, *, as_of: datetime | None = None):
        if not dados or not dados.get('preco_atual'):
            return None
        dados.pop("perfil_fonte", None)  # F2B-52: só o da análise corrente

        ticker = str(dados.get('ticker', '')).upper()
        p   = float(dados['preco_atual'])
        if not math.isfinite(p) or p <= 0:
            # F2A-24 e F2B-20: preço não finito ou negativo, como preço zero, não é analisado.
            return None

        # ── GUARD: CLASSE FORA DO ESCOPO (F2A-29, P7) ─────────────────────────
        # ETF, BDR e classe desconhecida não recebem os métodos de ação: abstenção
        # antes de qualquer método, sem número no lugar. Sem a chave, nada muda.
        classe = dados.get('classe_ativo')
        if classe is not None:
            classe = str(getattr(classe, 'value', classe)).upper()
            if classe in CLASSES_FORA_DO_ESCOPO:
                logger.info(f"[{ticker}] Classe {classe} fora do escopo dos métodos de ação")
                return {
                    'recomendacao':   ROTULO_FORA_DO_ESCOPO,
                    'metodos_usados': '',
                    'perfil':         classe,
                    'pl_confiavel':   False,
                    'dy_confiavel':   False,
                    'confianca':      0,
                    'riscos':         [f"Classe {classe} fora do escopo dos métodos de ação"],
                }

        # F2A-10: classe já verificada; dado não medido produz aviso, não zero.
        gate_liquidez = liquidez.avaliar(
            dados.get("liquidez"), janela=MACRO.LIQUIDEZ_JANELA,
            presenca_min=MACRO.LIQUIDEZ_PRESENCA_MIN,
            volume_min=MACRO.LIQUIDEZ_VOLUME_ACOES_MIN,
        ) if "liquidez" in dados else None
        avisos_liquidez = []
        if gate_liquidez:
            if "abstencao" in gate_liquidez:
                return {
                    'recomendacao': ROTULO_FORA_DO_ESCOPO,
                    'metodos_usados': '', 'perfil': 'LIQUIDEZ INSUFICIENTE',
                    'pl_confiavel': False, 'dy_confiavel': False, 'confianca': 0,
                    'riscos': [gate_liquidez["abstencao"]],
                }
            avisos_liquidez.append(gate_liquidez["aviso"])

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
                'riscos':        ['Empresa em situação especial/distressed', *avisos_liquidez],
            }
        roe = float(dados.get('roe', 0) or 0)
        pl  = float(dados.get('pl',  0) or 0)
        pvp = float(dados.get('pvp', 0) or 0)

        # ── INVARIANTE DO DY ──────────────────────────────────────────────────
        # O DY chega em razão: a conversão de percentual é da fronteira de cada
        # provedor (F2A-4, `sentinela.data.normalizacao`). Aqui só o invariante.
        dy_raw = float(dados.get('dy', 0) or 0)
        dy, dy_confiavel = _normalizar_dy(dy_raw)
        if not dy_confiavel:
            logger.warning(
                f"[{dados.get('ticker','?')}] DY={dy_raw:.4f} fora de 0 a 25% "
                f"— dado suspeito. Desconsiderado."
            )

        lpa = (p / pl)  if pl  > 0 else 0

        selic = get_selic_atual()

        confianca = 100
        riscos = list(avisos_liquidez)

        if dados.get("fundamentos_incompletos"):
            confianca -= 30
            riscos.append("Dados fundamentais obrigatórios ausentes")

        # pl_confiavel: False quando Yahoo retornou PL negativo (prejuízo) ou > 80 (TTM atípico)
        # Definido em market_engine.py; padrão True para dados do Fundamentus (mais confiáveis)
        pl_confiavel = bool(dados.get('pl_confiavel', True))

        # ── DETECÇÃO DE PERFIL ────────────────────────────────────────────────
        # CRESCIMENTO: ROE alto + dividendos baixos (empresa reinveste lucros)
        # ATENÇÃO: DY não confiável (da B3 ou da cascata) não vira crescimento — manter
        # RENDA/VALOR por precaução. O DY = 0 confiável da série B3 completa (F2B-53) pode.
        # F2B-52 (decisão do Marcos de 20/10/2026): um perfil só por ativo, para todos os
        # métodos, pelo DY bruto de 12 meses da relação B3 (ficha Bazin 1.2) quando a série é
        # válida; sem ela, pelo DY da cascata, com o aviso e o motivo da B3.
        instante = as_of if as_of is not None else datetime.now(UTC)
        entradas_bazin = proventos_b3.entradas(dados, instante)
        if isinstance(entradas_bazin, proventos_b3.Abstencao):
            dy_perfil, dy_perfil_confiavel = dy, dy_confiavel
            # O aviso fica nos dados e no relatório, fora de `riscos`: lá ele rebaixaria a
            # classificação de todo ativo sem a relação B3, o que a decisão não pede.
            dados["perfil_fonte"] = {
                "fonte": "cascata",
                "aviso": f"perfil pelo DY da cascata: {entradas_bazin.motivo}",
            }
        else:
            dy_perfil, dy_perfil_confiavel = _normalizar_dy(entradas_bazin["dy"])
            # F2B-54, decisões (b) e (c): os avisos da série que decide o perfil, com o
            # aviso fixo da ficha 1.2, ficam aqui e no relatório, fora de `riscos`.
            dados["perfil_fonte"] = {
                "fonte": "relação de proventos da B3",
                "avisos": [*entradas_bazin["avisos"], proventos_b3.AVISO_EXTRAORDINARIA],
            }
        if dy_perfil_confiavel:
            is_growth = (
                roe > MACRO.ROE_CRESCIMENTO_MIN and dy_perfil < MACRO.DY_CRESCIMENTO_MAX
            )
        else:
            is_growth = False  # sem DY confiável, evitar Lynch (pode inflar valuation)
            logger.info(
                f"[{dados.get('ticker','?')}] DY do perfil ({dados['perfil_fonte']['fonte']}) "
                "não confiável → is_growth=False (conservador)"
            )

        metodos = {}

        # ── 1. GRAHAM ─────────────────────────────────────────────────────────
        # Fórmula e condições em sentinela/methods/graham.py.
        # Se PL veio do Yahoo com flag de baixa confiabilidade (PL negativo ou >80),
        # Graham é ignorado mesmo dentro do limite — melhor não aplicar com dado suspeito
        inputs = self._montar_inputs(
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
        if instante.tzinfo is None or instante.utcoffset() is None:
            entradas_gordon = gordon_cvm.Abstencao("as_of exige fuso horário")
            dia_gordon = inputs.as_of
        else:
            dia_gordon = instante.astimezone(ZoneInfo("America/Sao_Paulo")).date()
            entradas_gordon = gordon_cvm.entradas(dados, instante)
        if isinstance(entradas_gordon, gordon_cvm.Abstencao):
            dados["gordon_diagnostico"] = entradas_gordon.motivo
            inputs_gordon = inputs
        else:
            dados.pop("gordon_diagnostico", None)
            inputs_gordon = replace(inputs, as_of=dia_gordon, **entradas_gordon)
        # F2B-31 (ficha Bazin 1.2): o DY do Bazin é o bruto de 12 meses da relação B3; sem
        # ela, o Bazin se abstém, sem reserva no DY da cascata.
        avisos_bazin = ()
        if isinstance(entradas_bazin, proventos_b3.Abstencao):
            dados["bazin_diagnostico"] = entradas_bazin.motivo
            dados.pop("bazin_proventos", None)
            inputs_bazin = replace(inputs, as_of=dia_gordon, dy=None)
        else:
            dados.pop("bazin_diagnostico", None)
            dados["bazin_proventos"] = entradas_bazin["serie"]
            avisos_bazin = tuple(entradas_bazin["avisos"])
            dy_b3, dy_b3_confiavel = _normalizar_dy(entradas_bazin["dy"])
            lpa_cvm = dados.get("lpa")
            lpa_cvm = (
                lpa_cvm
                if isinstance(lpa_cvm, (int, float))
                and not isinstance(lpa_cvm, bool)
                and math.isfinite(lpa_cvm)
                else None
            )
            inputs_bazin = replace(
                inputs,
                as_of=dia_gordon,
                preco=BRL(entradas_bazin["preco_referencia"]),
                dy=Ratio(dy_b3),
                dy_confiavel=dy_b3_confiavel,
                lpa=None if lpa_cvm is None else BRL(lpa_cvm),
            )
        resultados = self._avaliar_metodos(inputs, inputs_gordon, inputs_bazin)
        graham = resultados["Graham"]
        if isinstance(graham, MethodResult):
            metodos["Graham"] = graham.valor.valor
        elif not pl_confiavel:
            logger.info(
                f"[{dados.get('ticker', '?')}] Graham IGNORADO — pl_confiavel=False (PL via Yahoo suspeito)"
            )

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
            for aviso in (*avisos_bazin, *bazin.alertas):
                if aviso != ALERTA_DY_ARMADILHA and aviso not in riscos:
                    riscos.append(aviso)

        # ── 3. PETER LYNCH ───────────────────────────────────────────────────
        # Fórmula e condições em sentinela/methods/lynch.py.
        lynch = resultados["Lynch"]
        if isinstance(lynch, MethodResult):
            metodos['Lynch'] = lynch.valor.valor

        # ── 4. GORDON ─────────────────────────────────────────────────────────
        # Fluxo da DVA e desconto real, na ficha Gordon1.0 (F2B-1).
        for aviso in (dados.get("gordon_cvm") or {}).get("avisos", ()):
            if aviso not in riscos:
                riscos.append(aviso)
        gordon = resultados["Gordon"]
        if isinstance(gordon, MethodResult):
            metodos['Gordon'] = gordon.valor.valor
            riscos.extend(a for a in gordon.alertas if a not in riscos)

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

        # ── GUARD: campo obrigatório ausente (F2A-22) → sem classificação positiva ──
        # Dados fundamentais incompletos não significam que o ativo é ruim,
        # apenas que não há confiança suficiente para uma classificação positiva.
        # Preserva valores calculados para transparência.
        # Não sobrescreve VENDA nem ALTO RISCO — EVITAR.
        if rec in ("COMPRA", "COMPRA FORTE") and dados.get('fundamentos_incompletos'):
            rec = "DADOS INSUFICIENTES — AGUARDAR"
            riscos.append("Dados fundamentais insuficientes para análise precisa")
            confianca = min(confianca, 50)
            logger.warning(
                f"[{ticker}] Downgrade → DADOS INSUFICIENTES: "
                f"fundamentos_incompletos=True, rec original seria COMPRA/FORTE"
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
