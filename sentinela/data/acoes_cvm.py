"""Valores por ação a partir da Composição do Capital da CVM (F2A-3, E-1, armadilhas 3 e 10).

Funções puras: sem rede, sem banco, sem relógio.

- **Ações:** ON + PN − tesouraria, da Composição do Capital do **mesmo documento** do lucro e
  do PL (mesmo CNPJ, `DT_REFER` e `VERSAO`). São as ações do fim do período; o LPA divulgado
  usa a média ponderada do exercício.
- **Escala** (armadilha 10): o CSV não a traz. Vale a (unidade ou mil) que deixa
  (lucro ÷ ações) ÷ LPA básico divulgado mais perto de 1. Fora de `FAIXA_DA_ESCALA`, a escala
  fica indeterminada (o F2A-16 mediu 250 de 255 empresas dentro dessa faixa; as duas hipóteses
  só se confundem perto de 31,6, a raiz de 1.000).
- **Lucro e PL:** os atribuídos aos controladores (CPC 41).
- **Unit:** LPA recalculado e VPA multiplicados pelas ações por unit do índice oficial.
- **LPA dos métodos** (F2A-36, ADR-0003, D19; ficha `docs/metodologia/por-acao.md`): o LPA
  básico divulgado da classe do ticker, quando coerente; sem ele, o recalculado, com a marca
  do fim do período. Unit: soma dos LPAs das espécies, ponderada pela composição oficial.

Sem insumo, abstém-se com o motivo; nunca devolve número conservador.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from numbers import Real

from sentinela.domain.units import Escala, QuantidadeAcoes

FAIXA_DA_ESCALA = (0.1, 10.0)
# Ficha 1.1, 7.7: Q_CVM ÷ Q_yf, com as duas desigualdades estritas.
FAIXA_DA_CONFIRMACAO = (0.1, 10.0)

MOTIVO_SEM_COMPOSICAO = "sem Composição do Capital no documento do lucro"
MOTIVO_DOCUMENTO_DIFERENTE = (
    "Composição do Capital de documento diferente do lucro (outra data ou versão)"
)
MOTIVO_ESCALA = "escala das ações indeterminada"
MOTIVO_ESCALA_NAO_CONFIRMADA = "escala inferida pelo lucro consolidado sem a confirmação da quantidade do yfinance (7.7)"
MOTIVO_TOTAL = "total de ações da Composição do Capital ≤ 0"
MOTIVO_UNIT = "unit sem composição oficial (ações por unit)"
MOTIVO_COMPARACAO_CLASSES = (
    "comparação indisponível: quantidade oficial por classe preferencial ausente; "
    "total PN não corresponde à classe do ticker"
)
MOTIVO_ROE_PL = "PL dos controladores ≤ 0"
MOTIVO_ROE_SEM_PL = "PL dos controladores não identificado no documento"
MOTIVO_ROE_SEM_LUCRO = "lucro dos controladores não identificado no documento"
MOTIVO_SINAL_CONTROLADORES = "LPA divulgado com sinal oposto ao lucro dos controladores"
MOTIVO_SINAL_CONSOLIDADO = "LPA divulgado com sinal oposto ao lucro consolidado"
MOTIVO_LINHAS_CONFLITANTES = "LPA divulgado com linhas conflitantes para a espécie"
MOTIVO_LPA_INVALIDO = "LPA divulgado inválido para a espécie"
MOTIVO_LPA_ZERO = "LPA divulgado não informado: linha igual a zero"
MOTIVO_LUCRO_ZERO = "LPA divulgado diferente de zero com lucro zero no documento"
MOTIVO_SINAL_NAO_CONFERIVEL = (
    "sinal do LPA divulgado não conferível: lucro não identificado no documento"
)
MOTIVO_CLASSES_PREFERENCIAIS = "mais de uma classe preferencial com direitos distintos, sem LPA divulgado da classe"
MOTIVO_SEM_RECALCULADO = "sem LPA divulgado da espécie nem LPA recalculado"
MOTIVOS_DO_DIVULGADO = (
    MOTIVO_SINAL_CONTROLADORES,
    MOTIVO_SINAL_CONSOLIDADO,
    MOTIVO_LINHAS_CONFLITANTES,
    MOTIVO_LPA_INVALIDO,
    MOTIVO_LUCRO_ZERO,
    MOTIVO_SINAL_NAO_CONFERIVEL,
    MOTIVO_CLASSES_PREFERENCIAIS,
)
NOTA_SINAL_CONSOLIDADO = (
    "sinal conferido pelo lucro consolidado: lucro dos controladores indisponível"
)
NOTA_RECALCULADO = "ações do fim do período, não média ponderada"
NOTA_LINHA_AGREGADA = (
    "LPA da linha agregada (3.99.01 ou 3.99, conferida pelo recalculado): companhia de "
    "espécie única no FCA"
)
# Ficha 1.1, 7.8: a 3.99 só vale com o recalculado a até 10% dela (o limiar da 7.3).
LIMIAR_DA_LINHA_399 = 0.10
NOTA_ESCALA_PELO_CONSOLIDADO = (
    "escala inferida pelo lucro consolidado e confirmada pela quantidade do yfinance: lucro "
    "dos controladores indisponível (7.2)"
)
ORDEM_DA_ESCALA = ("ON", "PN")
NOTA_FIM_DO_PERIODO = (
    "ações do fim do período (Composição do Capital); o LPA divulgado usa a média "
    "ponderada do exercício"
)


@dataclass(frozen=True)
class Composicao:
    """Linha da Composição do Capital, na escala do documento (desconhecida)."""

    on: float
    pn: float
    tesouraria_on: float
    tesouraria_pn: float
    tesouraria_total: float
    dt_refer: str
    versao: str

    @property
    def total(self) -> float:
        return self.on + self.pn - self.tesouraria_total


@dataclass(frozen=True)
class PorAcao:
    acoes: QuantidadeAcoes
    escala: Escala
    razao_lpa: float | None
    lpa: float | None
    vpa: float | None
    pl: float | None
    pvp: float | None
    escala_pelo_consolidado: dict | None = None
    motivos: dict[str, str] = field(default_factory=dict)

    def detalhe(self, documento: dict) -> dict:
        return {
            "documento": documento,
            "escala": self.escala.name,
            "acoes": self.acoes.valor,
            "razao_lpa_calculado_sobre_divulgado": self.razao_lpa,
            "nota": NOTA_FIM_DO_PERIODO,
            **({"motivos": self.motivos} if self.motivos else {}),
        }


@dataclass(frozen=True)
class Abstencao:
    motivo: str
    escala_pelo_consolidado: dict | None = None


def inferir_escala(
    lucro: float | None, acoes: float, lpa_divulgado: float | None
) -> tuple[Escala, float] | None:
    """(escala, razão calculado ÷ divulgado) ou `None` se indeterminada.

    Lucro e LPA precisam de valor e do mesmo sinal (prejuízo com LPA negativo também serve).
    """
    if not lucro or not lpa_divulgado or acoes <= 0:
        return None
    if (lucro > 0) != (lpa_divulgado > 0):
        return None
    melhor = min(
        Escala,
        key=lambda e: abs(math.log(lucro / (acoes * e.fator) / lpa_divulgado)),
    )
    razao = lucro / (acoes * melhor.fator) / lpa_divulgado
    if not FAIXA_DA_ESCALA[0] <= razao <= FAIXA_DA_ESCALA[1]:
        return None
    return melhor, razao


def confirmar_escala(
    composicao: Composicao,
    escala: Escala,
    *,
    eh_unit: bool,
    acoes_por_unit: dict | None,
    shares_outstanding: float | None,
) -> dict:
    """Confirmação da escala inferida pelo consolidado (ficha 1.1, 7.7), para a proveniência.

    Q_CVM: ações em circulação da Composição do Capital na escala escolhida (para unit, ÷ ações
    por unit); Q_yf: `sharesOutstanding` do yfinance. Confirmada só com 0,1 < Q_CVM ÷ Q_yf < 10;
    Q_yf ausente, ≤ 0 ou não finito não confirma. O yfinance nunca entra no cálculo.
    """
    acoes = QuantidadeAcoes(composicao.total, escala).em_unidades().valor
    if eh_unit and acoes_por_unit:
        acoes /= sum(acoes_por_unit.values())
    valido = (
        shares_outstanding is not None
        and math.isfinite(shares_outstanding)
        and shares_outstanding > 0
    )
    razao = acoes / shares_outstanding if valido else None
    confirmada = (
        razao is not None and FAIXA_DA_CONFIRMACAO[0] < razao < FAIXA_DA_CONFIRMACAO[1]
    )
    return {
        # A nota da ficha só vale para a escala confirmada; sem confirmação, o motivo é outro.
        "nota": NOTA_ESCALA_PELO_CONSOLIDADO
        if confirmada
        else MOTIVO_ESCALA_NAO_CONFIRMADA,
        "escala": escala.name,
        "acoes_cvm": acoes,
        "acoes_yfinance": shares_outstanding if valido else None,
        "razao": razao,
        "confirmada": confirmada,
    }


@dataclass(frozen=True)
class LpaDivulgado:
    """LPA básico divulgado de uma classe, coerente com o sinal do lucro (ficha, 7.1 e 7.6)."""

    valor: float
    nota: str | None = None


def linhas_da_especie_unica(
    linhas: dict[str, list[float] | Abstencao],
    agregado: dict | None,
    especies: list[str] | None,
    *,
    lucro_controladores: float | None,
    acoes: float,
) -> tuple[dict[str, list[float] | Abstencao], dict | None]:
    """Linhas de LPA por classe, com a linha agregada na companhia de espécie única (7.8).

    Sem linha por espécie na DRE e com uma só espécie no FCA, a 3.99.01 é o LPA divulgado
    dessa espécie; zerada ou ausente, vale a 3.99, só com o recalculado (lucro dos
    controladores ÷ ações, na escala que a própria 3.99 escolhe) a até 10% dela. Devolve as
    linhas e o registro da linha usada (`None` se nenhuma). A coerência (7.5 e 7.6) é a de
    `divulgados_coerentes`, depois.
    """
    if linhas or not agregado or len(set(especies or ())) != 1:
        return linhas, None
    (especie,) = set(especies)
    base = agregado.get("3.99.01")
    if isinstance(base, Abstencao):
        return {especie: base}, None
    if base:
        return {especie: [base]}, {
            "conta": "3.99.01",
            "especie": especie,
            "nota": NOTA_LINHA_AGREGADA,
        }
    titulo = agregado.get("3.99")
    if isinstance(titulo, Abstencao):
        return {especie: titulo}, None
    if not titulo:
        return linhas, None
    inferida = inferir_escala(lucro_controladores, acoes, titulo)
    if inferida is None or abs(inferida[1] - 1) > LIMIAR_DA_LINHA_399:
        return linhas, None
    return {especie: [titulo]}, {
        "conta": "3.99",
        "especie": especie,
        "razao": inferida[1],
        "nota": NOTA_LINHA_AGREGADA,
    }


def divulgados_coerentes(
    linhas: dict[str, list[float] | Abstencao],
    lucro_controladores: float | None,
    lucro_consolidado: float | None,
) -> dict[str, LpaDivulgado | Abstencao]:
    """Classe → LPA divulgado coerente, ou a abstenção da classe (ficha, abstenções 8 e 9).

    `linhas`: os valores das linhas 3.99.01.xx por classe da descrição (ON, PN, PNA…).
    Zero é linha não informada (ficha 1.1, §4.11); não finito invalida a classe (§4.10).
    Linhas repetidas com o mesmo valor contam como uma; valores diferentes na mesma
    classe são conflito. O sinal é conferido contra o lucro dos controladores ou, quando ele se
    abstém, contra o lucro consolidado.
    """
    if lucro_controladores is not None:
        referencia, motivo_sinal, nota = (
            lucro_controladores,
            MOTIVO_SINAL_CONTROLADORES,
            None,
        )
    else:
        referencia, motivo_sinal, nota = (
            lucro_consolidado,
            MOTIVO_SINAL_CONSOLIDADO,
            NOTA_SINAL_CONSOLIDADO,
        )
    resultado: dict[str, LpaDivulgado | Abstencao] = {}
    for classe, valores in linhas.items():
        if isinstance(valores, Abstencao):
            resultado[classe] = valores
            continue
        if any(not _finito(valor) for valor in valores):
            resultado[classe] = Abstencao(MOTIVO_LPA_INVALIDO)
            continue
        distintos = {valor for valor in valores if valor != 0}
        if not distintos:
            resultado[classe] = Abstencao(MOTIVO_LPA_ZERO)
            continue
        if len(distintos) != 1:
            resultado[classe] = Abstencao(MOTIVO_LINHAS_CONFLITANTES)
            continue
        (valor,) = distintos
        if referencia is None or not math.isfinite(referencia):
            resultado[classe] = Abstencao(MOTIVO_SINAL_NAO_CONFERIVEL)
        elif referencia == 0:
            resultado[classe] = Abstencao(MOTIVO_LUCRO_ZERO)
        elif (referencia > 0) != (valor > 0):
            resultado[classe] = Abstencao(motivo_sinal)
        else:
            resultado[classe] = LpaDivulgado(valor, nota)
    return resultado


def divulgado_da_escala(
    divulgados: dict[str, LpaDivulgado | Abstencao],
) -> float | None:
    """O LPA divulgado coerente que fixa a escala: ON, depois PN, depois as classes em ordem.

    Só do mesmo documento (ficha, 7.4): nunca de outro documento.
    """
    ordem = [*ORDEM_DA_ESCALA, *sorted(set(divulgados) - set(ORDEM_DA_ESCALA))]
    for classe in ordem:
        achado = divulgados.get(classe)
        if isinstance(achado, LpaDivulgado):
            return achado.valor
    return None


def nota_linha_pn_unica(classe: str) -> str:
    """Marca do LPA da linha "PN" única atribuída a uma classe preferencial (ficha 1.1, 7.9)."""
    return f"LPA da linha PN única, aplicado à classe {classe}"


def especie_da_classe(classe: str | None) -> str | None:
    """Espécie de uma classe da composição ou do FCA: ON fica ON; PN, PNA, PNB… viram PN."""
    if classe is None:
        return None
    return "PN" if classe.startswith("PN") else classe


def _lpa_da_classe(
    classe: str | None,
    especie: str | None,
    divulgados: dict[str, LpaDivulgado | Abstencao],
    recalculado: float | None,
    varias_preferenciais: bool,
) -> tuple[float, dict] | Abstencao:
    """LPA de uma classe (D19, regras 1 a 3) e o detalhe da origem."""
    chaves = [classe] if varias_preferenciais else [classe, especie]
    for chave in chaves:
        if chave in divulgados:
            achado = divulgados[chave]
            if isinstance(achado, Abstencao):
                return achado
            nota = [achado.nota] if achado.nota else []
            return achado.valor, {"origem": "divulgado", "classe": chave, "notas": nota}
    preferencial = especie != "ON"
    if varias_preferenciais and preferencial and "PN" in divulgados:
        # F2B-12 (ficha 1.1, 7.9): sem a linha da classe, a linha "PN" única da DRE é
        # atribuída a ela; incoerente, a classe se abstém. O recalculado segue proibido.
        achado = divulgados["PN"]
        if isinstance(achado, Abstencao):
            return achado
        notas = [achado.nota] if achado.nota else []
        return achado.valor, {
            "origem": "divulgado",
            "classe": classe,
            "notas": [*notas, nota_linha_pn_unica(classe)],
        }
    if varias_preferenciais and preferencial:
        return Abstencao(MOTIVO_CLASSES_PREFERENCIAIS)
    if recalculado is None:
        return Abstencao(MOTIVO_SEM_RECALCULADO)
    return recalculado, {
        "origem": "recalculado",
        "classe": classe or especie,
        "notas": [NOTA_RECALCULADO],
    }


def lpa_dos_metodos(
    *,
    especie: str | None,
    classe: str | None,
    classes_preferenciais: list[str] | None,
    eh_unit: bool,
    acoes_por_unit: dict | None,
    divulgados: dict[str, LpaDivulgado | Abstencao],
    recalculado: float | None,
) -> tuple[float, dict] | Abstencao:
    """LPA que entra nos métodos (D19, regras 1 a 4) e o detalhe da origem, para a proveniência.

    `recalculado` é o LPA comum por ação (lucro dos controladores ÷ ações do fim do período),
    `None` quando a escala é indeterminada. `classes_preferenciais`: as siglas do FCA da
    companhia (PNA, PNB…); com mais de uma, o recalculado comum não vale para preferenciais.
    """
    # Zero tem a mesma ausência que a coleta já declara; inválido continua bloqueando reserva.
    divulgados = {
        classe: achado
        for classe, achado in divulgados.items()
        if not (isinstance(achado, Abstencao) and achado.motivo == MOTIVO_LPA_ZERO)
    }
    varias = len({c for c in classes_preferenciais or () if c.startswith("PN")}) > 1
    if not eh_unit:
        return _lpa_da_classe(
            classe or especie, especie, divulgados, recalculado, varias
        )
    if not _unit_valida(acoes_por_unit):
        return Abstencao(MOTIVO_UNIT)
    total, componentes, notas = 0.0, {}, []
    for componente, quantidade in acoes_por_unit.items():
        achado = _lpa_da_classe(
            componente, especie_da_classe(componente), divulgados, recalculado, varias
        )
        if isinstance(achado, Abstencao):
            return Abstencao(f"{achado.motivo} ({componente} da unit)")
        valor, detalhe = achado
        total += quantidade * valor
        componentes[componente] = {"quantidade": quantidade, "lpa": valor, **detalhe}
        notas += [n for n in detalhe["notas"] if n not in notas]
    return total, {"origem": "unit", "componentes": componentes, "notas": notas}


def _dividir(numerador: float | None, denominador: float | None) -> float | None:
    if numerador is None or not denominador:
        return None
    return numerador / denominador


def _finito(valor: object) -> bool:
    """Número real finito, sem aceitar booleano como quantidade ou dado contábil."""
    return (
        isinstance(valor, Real) and not isinstance(valor, bool) and math.isfinite(valor)
    )


def _unit_valida(acoes_por_unit: dict | None) -> bool:
    return bool(acoes_por_unit) and all(
        _finito(q) and q > 0 and q % 1 == 0 for q in acoes_por_unit.values()
    )


def derivar_por_acao(
    *,
    lucro_controladores: float | None,
    pl_controladores: float | None,
    composicao: Composicao | None,
    motivo_composicao: str | None,
    lpa_divulgado: float | None,
    preco: float | None,
    eh_unit: bool,
    acoes_por_unit: dict | None,
    lucro_consolidado: float | None = None,
    shares_outstanding: float | None = None,
) -> PorAcao | Abstencao:
    """LPA, VPA, P/L e P/VP da CVM; abstém-se só quando a própria CVM falha.

    Com o lucro dos controladores abstido (7.2) e `lucro_consolidado` informado, a escala é
    inferida pelo consolidado e só vale confirmada pela `sharesOutstanding` (ficha 1.1, 7.7). O
    consolidado serve só à escala: o LPA recalculado continua abstido. Só o documento mais
    recente passa o consolidado; a série de cinco anos não (D17).
    """
    if composicao is None:
        return Abstencao(motivo_composicao or MOTIVO_SEM_COMPOSICAO)
    if eh_unit and not _unit_valida(acoes_por_unit):
        return Abstencao(MOTIVO_UNIT)
    for nome, valor in (
        ("lucro dos controladores", lucro_controladores),
        ("LPA divulgado", lpa_divulgado),
        ("lucro consolidado", lucro_consolidado),
    ):
        if valor is not None and not _finito(valor):
            return Abstencao(f"insumo inválido: {nome}")
    if any(
        not _finito(q) or q < 0 or q % 1
        for q in (
            composicao.on,
            composicao.pn,
            composicao.tesouraria_on,
            composicao.tesouraria_pn,
            composicao.tesouraria_total,
        )
    ):
        return Abstencao("Composição do Capital com quantidade inválida")
    if composicao.total <= 0:
        return Abstencao(MOTIVO_TOTAL)
    if (
        composicao.tesouraria_on > composicao.on
        or composicao.tesouraria_pn > composicao.pn
    ):
        return Abstencao(
            "Composição do Capital inválida: tesouraria maior que a espécie"
        )
    confirmacao = None
    if lucro_controladores is None and lucro_consolidado is not None:
        inferida = inferir_escala(lucro_consolidado, composicao.total, lpa_divulgado)
        if inferida is None:
            return Abstencao(MOTIVO_ESCALA)
        confirmacao = confirmar_escala(
            composicao,
            inferida[0],
            eh_unit=eh_unit,
            acoes_por_unit=acoes_por_unit,
            shares_outstanding=shares_outstanding,
        )
        if not confirmacao["confirmada"]:
            return Abstencao(MOTIVO_ESCALA_NAO_CONFIRMADA, confirmacao)
    else:
        inferida = inferir_escala(lucro_controladores, composicao.total, lpa_divulgado)
    if inferida is None:
        return Abstencao(MOTIVO_ESCALA)
    escala, razao = inferida
    acoes = QuantidadeAcoes(composicao.total, escala).em_unidades()
    fator = sum(acoes_por_unit.values()) if eh_unit else 1
    lpa = _dividir(lucro_controladores, acoes.valor)
    motivos = {}
    pl_valido = pl_controladores
    if pl_controladores is not None and not _finito(pl_controladores):
        pl_valido = None
        motivos["vpa"] = "PL dos controladores inválido"
        motivos["pvp"] = motivos["vpa"]
    vpa = _dividir(pl_valido, acoes.valor)
    lpa = lpa * fator if lpa is not None else None
    vpa = vpa * fator if vpa is not None else None
    preco_valido = preco if _finito(preco) and preco > 0 else None
    if preco_valido is None:
        motivo = "preço ausente, não positivo ou inválido"
        motivos["pl"] = motivo
        motivos["pvp"] = motivo
    return PorAcao(
        acoes=acoes,
        escala=escala,
        razao_lpa=razao,
        lpa=lpa,
        vpa=vpa,
        pl=_dividir(preco_valido, lpa),
        pvp=_dividir(preco_valido, vpa),
        escala_pelo_consolidado=confirmacao,
        motivos=motivos,
    )


def divergencia_acoes(
    composicao: Composicao,
    escala: Escala,
    *,
    especie: str | None,
    eh_unit: bool,
    acoes_por_unit: dict | None,
    shares_outstanding: float | None,
    classes_preferenciais: list[str] | None = None,
) -> dict | None:
    """Ações da espécie do ticker na CVM × `sharesOutstanding` do yfinance (alerta, não abstenção).

    Ação ON: ON − tesouraria ON; ação PN: PN − tesouraria PN; unit: total ÷ ações por unit.
    `None` se falta a espécie ou o número do yfinance. Com várias classes PN, o total
    da espécie não é comparável à quantidade de uma classe: comparação indisponível.
    """
    if not shares_outstanding or shares_outstanding <= 0:
        return None
    if eh_unit:
        if not acoes_por_unit:
            return None
        bruto, rotulo = composicao.total / sum(acoes_por_unit.values()), "UNIT"
    elif especie == "ON":
        bruto, rotulo = composicao.on - composicao.tesouraria_on, "ON"
    elif especie == "PN":
        if len(set(classes_preferenciais or ())) > 1:
            return None
        bruto, rotulo = composicao.pn - composicao.tesouraria_pn, "PN"
    else:
        return None
    cvm = QuantidadeAcoes(bruto, escala).em_unidades().valor
    if cvm <= 0:
        return None
    return {
        "especie": rotulo,
        "acoes_cvm": cvm,
        "acoes_yfinance": float(shares_outstanding),
        "diferenca": shares_outstanding / cvm - 1,
    }


def roe_dos_controladores(
    lucro_controladores: float | None, pl_controladores: float | None
) -> tuple[float | None, str | None]:
    """(ROE, motivo da abstenção). Com PL ≤ 0, lucro negativo daria ROE positivo: abstém-se."""
    if lucro_controladores is None:
        return None, MOTIVO_ROE_SEM_LUCRO
    if pl_controladores is None:
        return None, MOTIVO_ROE_SEM_PL
    if not _finito(lucro_controladores) or not _finito(pl_controladores):
        return None, "ROE com insumo inválido"
    if pl_controladores <= 0:
        return None, MOTIVO_ROE_PL
    roe = lucro_controladores / pl_controladores
    if not math.isfinite(roe):
        return None, "ROE não finito"
    return roe, None
