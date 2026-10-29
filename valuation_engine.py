import logging
import math
import statistics
from dataclasses import replace
from datetime import UTC, date, datetime
from numbers import Real
from zoneinfo import ZoneInfo

from config import DISTRESSED_TICKERS, MACRO, _normalizar_dy
from sentinela.data import (
    gordon_cvm,
    janelas_fundamentais,
    liquidez,
    proventos_b3,
    qualidade_inputs,
)
from sentinela.domain.apresentacao import bloco
from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.bancos import Bancos, BancosParams
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.bazin import ALERTA_DY_ARMADILHA, Bazin, BazinParams
from sentinela.methods.gordon import Gordon, GordonParams
from sentinela.methods.graham import Graham, GrahamParams
from sentinela.methods.lynch import Lynch, LynchParams
from sentinela.methods.registry import QUADROS_DESCRITIVOS

logger = logging.getLogger("Valuation")

_GRAHAM = Graham()
_BAZIN = Bazin()
_LYNCH = Lynch()
_GORDON = Gordon()
_BANCOS = Bancos()


def _finito(valor):
    """Valor não finito vira None antes de entrar em MethodInputs."""
    return valor if math.isfinite(valor) else None


# F2A-29 (P7) e F2B-4: só STOCK e UNIT recebem os métodos de ação.
# F2B-4: classe oficial exigida; STOCK/UNIT exigem o modelo empresa pelo BPP consolidado.
MOTIVO_SEM_CLASSE = "classe do ativo não informada"
MOTIVO_SEM_MODELO = "modelo da demonstração não demonstrado no BPP consolidado"
MOTIVO_BPP_INDISPONIVEL = (
    "disponibilidade do BPP consolidado não demonstrada até o as_of"
)
# F2B-4 e F2B-32: empresa recebe os quatro métodos; banco, a lente de bancos.
MODELOS_COM_LENTE = (ModeloDemonstracao.EMPRESA.value, ModeloDemonstracao.BANCO.value)
INADIMPLENCIA_NAO_INFORMADA = "inadimplência IF.data não informada"
FUSO = ZoneInfo("America/Sao_Paulo")


def _abstencao_de_escopo(motivo, perfil):
    """Saída da abstenção de escopo (F2A-29): o motivo, sem número no lugar."""
    return {
        "abstencao": motivo,
        "metodos_usados": "",
        "perfil": perfil,
        "pl_confiavel": False,
        "dy_confiavel": False,
        "confianca": 0,
        "riscos": [motivo],
    }


def _texto_inadimplencia(dados, instante):
    """Inadimplência do IF.data só para leitura (F2B-32; ficha bancos 1.1, §3)."""
    ifdata = dados.get("ifdata")
    if not isinstance(ifdata, dict):
        return f"{INADIMPLENCIA_NAO_INFORMADA}: IF.data não consultado"
    registros = ifdata.get("proveniencia") or ()
    try:
        posterior = not registros or any(
            datetime.fromisoformat(str(r["data_coleta"])) > instante for r in registros
        )
    except (TypeError, KeyError, ValueError):
        posterior = True
    if posterior and dados.get("inadimplencia") is not None:
        return f"{INADIMPLENCIA_NAO_INFORMADA}: coleta não demonstrada até o as_of"
    valor = dados.get("inadimplencia")
    if valor is None:
        motivo = (ifdata.get("motivos") or {}).get("inadimplencia") or "valor ausente"
        return f"{INADIMPLENCIA_NAO_INFORMADA}: {motivo}"
    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not math.isfinite(valor)
        or not 0 <= valor <= 1
    ):
        return f"{INADIMPLENCIA_NAO_INFORMADA}: fora do domínio ({valor!r})"
    data_base = str(ifdata.get("data_base") or "")
    return (
        "inadimplência IF.data (carteira ativa inadimplida arrastada ÷ Total Geral, "
        f"relatório 16, conglomerado {ifdata.get('codinst')}, "
        f"data-base {data_base[4:]}/{data_base[:4]}): "
        + f"{valor * 100:.2f}%".replace(".", ",")
    )


def _bpp_disponivel(proveniencia, instante):
    """Entrega do BPP antes do dia do as_of e coleta até o instante (D16/D17)."""
    try:
        entrega = date.fromisoformat(str(proveniencia["data_entrega"]))
        coleta = datetime.fromisoformat(str(proveniencia["data_coleta"]))
        return entrega < instante.astimezone(FUSO).date() and coleta <= instante
    except (TypeError, KeyError, ValueError):
        return False


class ValuationEngine:
    def _montar_inputs(
        self,
        p,
        pl,
        pvp,
        is_growth,
        pl_confiavel,
        dy=None,
        dy_confiavel=True,
        roe=None,
        lpa=None,
        *,
        classe,
        modelo,
    ):
        """Converte os dados já normalizados da V1 em MethodInputs (uma única vez)."""
        p, pl, pvp = _finito(p), _finito(pl), _finito(pvp)
        dy = None if dy is None else _finito(dy)
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
            perfil=Perfil.CRESCIMENTO if is_growth else Perfil.RENDA,
            pl_confiavel=pl_confiavel,
            dy_confiavel=dy_confiavel,
            classe_ativo=classe,
            modelo=modelo,
        )

    def _avaliar_metodos(
        self,
        inputs,
        inputs_gordon=None,
        inputs_bazin=None,
        inputs_bancos=None,
        inputs_graham=None,
        inputs_lynch=None,
    ):
        """Resultado de cada método extraído, na ordem da V1, e a lente de bancos (F2B-32)."""
        return {
            "Graham": _GRAHAM.calcular(
                inputs if inputs_graham is None else inputs_graham,
                GrahamParams(),
            ),
            "Bazin": _BAZIN.calcular(
                inputs if inputs_bazin is None else inputs_bazin,
                BazinParams(
                    dy_min=MACRO.BAZIN_DY_MIN,
                    dy_armadilha=MACRO.BAZIN_DY_ARMADILHA,
                ),
            ),
            "Lynch": _LYNCH.calcular(
                inputs if inputs_lynch is None else inputs_lynch,
                LynchParams(),
            ),
            "Gordon": _GORDON.calcular(
                inputs if inputs_gordon is None else inputs_gordon, GordonParams()
            ),
            "Bancos": _BANCOS.calcular(
                inputs if inputs_bancos is None else inputs_bancos, BancosParams()
            ),
        }

    def processar(self, dados, *, as_of: datetime | None = None):
        """Acrescenta o quadro independente sem tocar em saídas do valuation."""
        instante = as_of if as_of is not None else datetime.now(UTC)
        resultado = self._processar_valuation(dados, as_of=instante)
        if isinstance(resultado, dict):
            classe = dados.get("classe_ativo")
            modelo = dados.get("modelo_bpp")
            resultado["qualidade"] = QUADROS_DESCRITIVOS[0].calcular(
                qualidade_inputs.entradas(dados, instante),
                as_of=instante,
                classe=str(getattr(classe, "value", classe) or "").strip().upper(),
                modelo=str(getattr(modelo, "value", modelo) or "").strip().lower(),
            )
            if "lentes" not in resultado:
                motivo = (
                    resultado.get("abstencao")
                    or "; ".join(resultado.get("riscos", []))
                    or "lentes não calculadas"
                )
                resultado["lentes"] = {
                    m.nome: bloco(
                        m,
                        Abstention(m.nome, m.version, motivo),
                        dados.get("preco_atual"),
                        {},
                    )
                    for m in (_GRAHAM, _BAZIN, _LYNCH, _GORDON, _BANCOS)
                }
        return resultado

    def _processar_valuation(self, dados, *, as_of: datetime | None = None):
        if not dados or not dados.get("preco_atual"):
            return None
        dados.pop("perfil_fonte", None)  # F2B-52: só o da análise corrente

        ticker = str(dados.get("ticker", "")).upper()
        p = float(dados["preco_atual"])
        if not math.isfinite(p) or p <= 0:
            # F2A-24 e F2B-20: preço não finito ou negativo, como preço zero, não é analisado.
            return None

        instante = as_of if as_of is not None else datetime.now(UTC)
        if instante.utcoffset() is None:
            return _abstencao_de_escopo("as_of exige fuso horário", "INSTANTE SEM FUSO")

        # ── GUARD: CLASSE FORA DO ESCOPO (F2A-29, P7) ─────────────────────────
        # Só STOCK e UNIT recebem os métodos de ação; ETF, BDR, UNKNOWN e a ausência de
        # classe (F2B-4) se abstêm antes de qualquer método, sem número no lugar.
        classe = dados.get("classe_ativo")
        if classe is None:
            return _abstencao_de_escopo(MOTIVO_SEM_CLASSE, "SEM CLASSE")
        # F2B-4 (BUG-2B-39): espaços nas pontas não contornam a guarda; a classe normalizada
        # volta para `dados`, para os métodos lerem a mesma.
        classe = str(getattr(classe, "value", classe)).strip().upper()
        dados["classe_ativo"] = classe
        if not classe:
            return _abstencao_de_escopo(MOTIVO_SEM_CLASSE, "SEM CLASSE")
        if classe not in (AssetType.STOCK.value, AssetType.UNIT.value):
            logger.info(
                f"[{ticker}] Classe {classe} fora do escopo dos métodos de ação"
            )
            return _abstencao_de_escopo(
                f"Classe {classe} fora do escopo dos métodos de ação", classe
            )

        # ── GUARD: MODELO DO BPP CONSOLIDADO (F2B-4) ──────────────────────────
        # Banco e seguradora não recebem os métodos de empresa; sem modelo demonstrado,
        # abstenção (não há padrão empresa). A evidência, quando gravada, vale até o as_of.
        modelo = dados.get("modelo_bpp")
        modelo = str(getattr(modelo, "value", modelo) or "").strip().lower()
        dados["modelo_bpp"] = modelo
        if modelo not in MODELOS_COM_LENTE:
            motivo = (
                f"modelo {modelo} fora do escopo dos métodos de empresa"
                if modelo
                else MOTIVO_SEM_MODELO
            )
            return _abstencao_de_escopo(motivo, classe)
        if "modelo_bpp_proveniencia" in dados and not _bpp_disponivel(
            dados["modelo_bpp_proveniencia"], instante
        ):
            return _abstencao_de_escopo(MOTIVO_BPP_INDISPONIVEL, classe)

        # F2A-10: classe já verificada; dado não medido produz aviso, não zero.
        gate_liquidez = (
            liquidez.avaliar(
                dados.get("liquidez"),
                janela=MACRO.LIQUIDEZ_JANELA,
                presenca_min=MACRO.LIQUIDEZ_PRESENCA_MIN,
                volume_min=MACRO.LIQUIDEZ_VOLUME_ACOES_MIN,
            )
            if "liquidez" in dados
            else None
        )
        # F2B-45 (auditoria D30 do Claude): o aviso de liquidez não medida fica num campo
        # próprio, fora de `riscos`, como o `perfil_fonte`; não muda a classificação.
        aviso_liquidez = {}
        if gate_liquidez:
            if "abstencao" in gate_liquidez:
                return {
                    "abstencao": gate_liquidez["abstencao"],
                    "metodos_usados": "",
                    "perfil": "LIQUIDEZ INSUFICIENTE",
                    "pl_confiavel": False,
                    "dy_confiavel": False,
                    "confianca": 0,
                    "riscos": [gate_liquidez["abstencao"]],
                }
            aviso_liquidez = {"aviso_liquidez": gate_liquidez["aviso"]}

        # ── GUARD: DISTRESSED TICKERS ────────────────────────────────────────
        # Empresas em recuperação judicial ou situação especial não devem
        # receber valores calculados — valuation baseado em múltiplos
        # não reflete o risco real (dívida, diluição, governança).
        if ticker in DISTRESSED_TICKERS:
            logger.warning(f"[{ticker}] DISTRESSED — métodos não calculados")
            return {
                "fair_value": round(p, 2),
                "upside": 0.0,
                "metodos_usados": "",
                "perfil": "DISTRESSED",
                "pl_confiavel": False,
                "dy_confiavel": False,
                "confianca": 0,
                "riscos": ["Empresa em situação especial/distressed"],
                **aviso_liquidez,
            }
        roe = float(dados.get("roe", 0) or 0)
        pl = float(dados.get("pl", 0) or 0)
        pvp = float(dados.get("pvp", 0) or 0)

        # ── INVARIANTE DO DY ──────────────────────────────────────────────────
        # O DY chega em razão: a conversão de percentual é da fronteira de cada
        # provedor (F2A-4, `sentinela.data.normalizacao`). Aqui só o invariante.
        observado_dy = dados.get("dy")
        dy_raw = (
            float(observado_dy)
            if isinstance(observado_dy, Real) and not isinstance(observado_dy, bool)
            else math.nan
        )
        dy, dy_confiavel = _normalizar_dy(dy_raw)
        if not dy_confiavel:
            logger.warning(
                f"[{dados.get('ticker', '?')}] DY={dy_raw:.4f} fora de 0 a 25% "
                f"— dado suspeito. Desconsiderado."
            )

        lpa = dados.get("lpa")
        lpa = (
            lpa
            if isinstance(lpa, (int, float))
            and not isinstance(lpa, bool)
            and math.isfinite(lpa)
            else None
        )

        riscos = []

        if dados.get("fundamentos_incompletos"):
            riscos.append("Dados fundamentais obrigatórios ausentes")

        # pl_confiavel: False quando Yahoo retornou PL negativo (prejuízo) ou > 80 (TTM atípico)
        # Definido em market_engine.py; padrão True para dados do Fundamentus (mais confiáveis)
        pl_confiavel = bool(dados.get("pl_confiavel", True))

        # ── DETECÇÃO DE PERFIL ────────────────────────────────────────────────
        # CRESCIMENTO: ROE alto + dividendos baixos (empresa reinveste lucros)
        # ATENÇÃO: DY não confiável (da B3 ou da cascata) não vira crescimento — manter
        # RENDA/VALOR por precaução. O DY = 0 confiável da série B3 completa (F2B-53) pode.
        # F2B-52 (decisão do Marcos de 20/10/2026): um perfil só por ativo, para todos os
        # métodos, pelo DY bruto de 12 meses da relação B3 (ficha Bazin 1.2) quando a série é
        # válida; sem ela, pelo DY da cascata, com o aviso e o motivo da B3.
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
                "avisos": [
                    *entradas_bazin["avisos"],
                    proventos_b3.AVISO_EXTRAORDINARIA,
                ],
            }
        if dy_perfil_confiavel:
            is_growth = (
                roe > MACRO.ROE_CRESCIMENTO_MIN and dy_perfil < MACRO.DY_CRESCIMENTO_MAX
            )
        else:
            is_growth = False  # sem DY confiável, evitar Lynch (pode inflar valuation)
            logger.info(
                f"[{dados.get('ticker', '?')}] DY do perfil ({dados['perfil_fonte']['fonte']}) "
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
            dy_confiavel=dy_confiavel,
            roe=roe,
            lpa=lpa,
            classe=AssetType(classe),
            modelo=ModeloDemonstracao(modelo),
        )
        if instante.tzinfo is None or instante.utcoffset() is None:
            entradas_gordon = gordon_cvm.Abstencao("as_of exige fuso horário")
            dia_gordon = inputs.as_of
        else:
            dia_gordon = instante.astimezone(FUSO).date()
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
        # F2B-32: banco recebe a lente de bancos pela mesma fronteira documental do Gordon;
        # os métodos de empresa se abstêm pelo modelo no contrato.
        inputs_bancos = inputs
        if modelo == ModeloDemonstracao.BANCO.value:
            entradas_bancos = (
                gordon_cvm.entradas(dados, instante, modelo=modelo)
                if instante.utcoffset() is not None
                else gordon_cvm.Abstencao("as_of exige fuso horário")
            )
            if isinstance(entradas_bancos, gordon_cvm.Abstencao):
                dados["bancos_diagnostico"] = entradas_bancos.motivo
            else:
                dados.pop("bancos_diagnostico", None)
                inputs_bancos = replace(inputs, as_of=dia_gordon, **entradas_bancos)
        janelas = janelas_fundamentais.entradas(dados, instante)
        dados["janelas_fundamentais"] = janelas
        graham_janela, lynch_janela = janelas["graham"], janelas["lynch"]
        if not dy_perfil_confiavel and "abstencao" not in lynch_janela:
            lynch_janela["abstencao"] = (
                "perfil não demonstrado: DY comum ausente ou não confiável"
            )
        inputs_graham = replace(inputs, lpa=None, vpa=None)
        inputs_lynch = replace(inputs, lpa=None, crescimento_lpa=None)
        if "abstencao" not in graham_janela:
            inputs_graham = replace(
                inputs, lpa=BRL(graham_janela["lpa"]), vpa=BRL(graham_janela["vpa"])
            )
        if "abstencao" not in lynch_janela:
            preco_payout = (
                p
                if isinstance(entradas_bazin, proventos_b3.Abstencao)
                else entradas_bazin["preco_referencia"]
            )
            inputs_lynch = replace(
                inputs,
                lpa=BRL(lynch_janela["lpa"]),
                crescimento_lpa=RateNominal(lynch_janela["crescimento_lpa"]),
                dy=Ratio(dy_perfil) if dy_perfil_confiavel else None,
                dy_confiavel=dy_perfil_confiavel,
                preco=BRL(preco_payout),
            )
        resultados = self._avaliar_metodos(
            inputs,
            inputs_gordon,
            inputs_bazin,
            inputs_bancos,
            inputs_graham,
            inputs_lynch,
        )
        metadados = {
            "Graham": graham_janela,
            "Lynch": lynch_janela,
            "Bazin": dados.get("bazin_proventos") or {},
            "Gordon": dados.get("gordon_cvm") or {},
            "Bancos": dados.get("gordon_cvm") or {},
        }
        lentes = {}
        for metodo in (_GRAHAM, _BAZIN, _LYNCH, _GORDON, _BANCOS):
            resultado_metodo = resultados[metodo.nome]
            causa = dados.get(
                {
                    "Gordon": "gordon_diagnostico",
                    "Bazin": "bazin_diagnostico",
                    "Bancos": "bancos_diagnostico",
                }.get(metodo.nome, "")
            )
            if not causa and metodo.nome in ("Graham", "Lynch"):
                causa = metadados[metodo.nome].get("abstencao")
            if (
                isinstance(resultado_metodo, Abstention)
                and resultado_metodo.motivo.startswith("insumo ausente:")
                and causa
            ):
                resultado_metodo = Abstention(metodo.nome, metodo.version, causa)
            lentes[metodo.nome] = bloco(
                metodo, resultado_metodo, p, metadados[metodo.nome]
            )

        bancos = resultados["Bancos"]
        if modelo == ModeloDemonstracao.BANCO.value and not isinstance(
            bancos, MethodResult
        ):
            # Decisão provisória do F2B-32: sem a lente, o banco não tem método; abstenção
            # sem número, em vez do preço como valor da regra V1 de "nenhum método".
            dados.setdefault("bancos_diagnostico", bancos.motivo)
            return {
                **_abstencao_de_escopo(
                    f"lente de bancos abstida: {dados['bancos_diagnostico']}", classe
                ),
                "lentes": lentes,
                "inadimplencia_ifdata": _texto_inadimplencia(dados, instante),
                **aviso_liquidez,
            }
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
            metodos["Bazin"] = bazin.valor.valor
            for aviso in (*avisos_bazin, *bazin.alertas):
                if aviso != ALERTA_DY_ARMADILHA and aviso not in riscos:
                    riscos.append(aviso)

        # ── 3. PETER LYNCH ───────────────────────────────────────────────────
        # Fórmula e condições em sentinela/methods/lynch.py.
        lynch = resultados["Lynch"]
        if isinstance(lynch, MethodResult):
            from sentinela.data.payout_lynch import contexto

            lynch_janela["payout_contextual"] = contexto(
                dy_perfil,
                inputs_lynch.preco.valor,
                lynch_janela["lpa"],
                confiavel=dy_perfil_confiavel,
                fonte=dados["perfil_fonte"],
            )
            if not isinstance(entradas_bazin, proventos_b3.Abstencao):
                lynch_janela["payout_contextual"]["intervalo_dy"] = {
                    "inicio_exclusivo": entradas_bazin["serie"]["inicio_exclusivo"],
                    "fim": entradas_bazin["serie"]["referencia"],
                }
            metodos["Lynch"] = lynch.valor.valor

        # ── 4. GORDON ─────────────────────────────────────────────────────────
        # Fluxo da DVA e desconto real, na ficha Gordon1.0 (F2B-1).
        for aviso in (dados.get("gordon_cvm") or {}).get("avisos", ()):
            if aviso not in riscos:
                riscos.append(aviso)
        gordon = resultados["Gordon"]
        if isinstance(gordon, MethodResult):
            metodos["Gordon"] = gordon.valor.valor
            riscos.extend(a for a in gordon.alertas if a not in riscos)

        # ── 5. BANCOS (F2B-32) ────────────────────────────────────────────────
        # P/VP justificado da ficha bancos 1.1; só o modelo banco chega aqui com insumos.
        if isinstance(bancos, MethodResult):
            dados.pop("bancos_diagnostico", None)
            metodos["Bancos"] = bancos.valor.valor
            riscos.extend(a for a in bancos.alertas if a not in riscos)

        # ── CÁLCULO FINAL ─────────────────────────────────────────────────────
        valores_validos = list(metodos.values())

        if not valores_validos:
            fair_value = p
            upside = 0.0
        else:
            # Mediana em vez de média: Graham (patrimonial), Bazin (renda) e
            # Gordon (DCF) respondem perguntas diferentes. Quando divergem >2x,
            # a média aritmética produz um valor sem significado econômico.
            # statistics.median: 1 valor → o valor; 2 → média; 3+ → mediana.
            fair_value = statistics.median(valores_validos)
            upside = (fair_value / p) - 1

            if len(valores_validos) >= 2:
                if (
                    max(valores_validos) / max(min(valores_validos), 0.01)
                    > MACRO.METODOS_DIVERGENCIA_RATIO
                ):
                    riscos.append("Métodos divergentes")

        # Avisos de dados e contexto não são penalidades no valuation.
        aviso_alavancagem = None
        divida = dados.get("divida_liq_ebitda")
        if (
            not isinstance(divida, Real)
            or isinstance(divida, bool)
            or not math.isfinite(divida)
        ):
            motivos = dados.get("alavancagem_motivos") or {}
            causa = (
                motivos.get("divida_liq_ebitda") if isinstance(motivos, dict) else None
            )
            causa = causa.strip() if isinstance(causa, str) and causa.strip() else None
            aviso_alavancagem = f"alavancagem não avaliada: dívida líquida/EBITDA {causa or ('ausente' if divida is None else 'em texto' if isinstance(divida, str) else 'não numérica ou não finita')}"
        elif divida > MACRO.DIVIDA_EBITDA_LIMITE:
            riscos.append("Dívida elevada")
        if not dy_confiavel:
            riscos.append("DY suspeito")
        if not pl_confiavel:
            riscos.append("PL não confiável")
        # Um único indicador legado de completude; prejuízo/juros não o penalizam.
        confianca = 70 if dados.get("fundamentos_incompletos") else 100
        detalhes = ", ".join([f"{k}: R${v:.2f}" for k, v in metodos.items()])

        extra = (
            {"inadimplencia_ifdata": _texto_inadimplencia(dados, instante)}
            if modelo == ModeloDemonstracao.BANCO.value
            else {}
        )
        if aviso_alavancagem:
            extra["aviso_alavancagem"] = aviso_alavancagem
        extra.update(aviso_liquidez)
        return {
            "fair_value": round(fair_value, 2),
            "upside": round(upside * 100, 1),
            "lentes": lentes,
            "metodos_usados": detalhes,
            "perfil": "CRESCIMENTO" if is_growth else "RENDA/VALOR",
            "pl_confiavel": pl_confiavel,
            "dy_confiavel": dy_confiavel,
            "confianca": max(0, confianca),
            "riscos": riscos,
            **extra,
        }
