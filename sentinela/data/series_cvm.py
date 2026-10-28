"""Série de cinco exercícios da DFP e últimos doze meses pelo ITR (F2A-7; F-24, F-8).

Funções puras: sem rede, sem relógio, sem `config`. A data e o exercício de referência são
parâmetros. Só disponibilizam dados: os métodos passam a usá-los no F2C-1.

Especificação externa: os metadados da DFP e do ITR publicados pela CVM
(`meta_dfp_cia_aberta.txt` e `meta_itr_cia_aberta.txt`, em dados.cvm.gov.br). Cada linha
traz `DT_INI_EXERC` e `DT_FIM_EXERC`; no ITR, a DRE do 2º e do 3º trimestre tem o acumulado
do exercício (início no primeiro dia do exercício) e o trimestre, e a DVA só o acumulado.

- **Série.** Até cinco exercícios, do exercício de referência para trás. Exercício sem DFP
  fica de fora: nenhum outro ocupa o lugar dele, e o mais antigo nunca vira o corrente.
- **Números por ação de cada exercício.** As regras do F2A-3, revistas pela D19 do ADR-0003
  (F2A-36), aplicadas ao próprio documento: LPA divulgado da classe quando coerente, senão o
  recalculado; VPA e ações pela Composição do Capital do mesmo documento.
- **Proventos.** Dividendos e JCP declarados na DVA (7.08.04.02 e 7.08.04.01 no modelo de
  empresa), por **competência**: o exercício a que se referem, não a data-ex.
- **TTM.** Soma dos quatro últimos trimestres. Cada trimestre é a diferença entre dois
  acumulados consecutivos do mesmo exercício; o quarto é a DFP menos o acumulado de nove
  meses do ITR. De cada documento vale a maior `VERSAO`.
"""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import pairwise

from sentinela.data import acoes_cvm
from sentinela.data.contas_cvm import MOTIVO_LINHA_AUSENTE

MAX_EXERCICIOS = 5
COMPETENCIA = (
    "competência: proventos declarados na DVA para o exercício a que se referem, "
    "não pela data-ex"
)
CAMPOS_TTM = (
    "lucro_liquido",
    "lucro_controladores",
    "receita_liquida",
    "dividendos",
    "jcp",
)
MOTIVO_MENOS_DE_QUATRO = (
    "menos de quatro trimestres disponíveis até a data de referência"
)
MOTIVO_NAO_CONTIGUOS = "os quatro últimos trimestres não são contíguos"
MOTIVO_CAMPO_AUSENTE = (
    "campo ausente em ao menos um dos documentos dos quatro trimestres"
)


@dataclass(frozen=True)
class Abstencao:
    motivo: str


@dataclass(frozen=True)
class Acumulado:
    """Valores acumulados de um documento, do início do exercício até `fim`."""

    documento: str
    dt_refer: str
    versao: int
    inicio: date
    fim: date
    valores: Mapping[str, float | None] = field(default_factory=dict)
    # F2B-37: o motivo de cada campo abstido no documento (por exemplo, a decisão 7.2).
    motivos: Mapping[str, str] = field(default_factory=dict)
    proveniencia: Mapping[str, dict] = field(default_factory=dict)

    def origem(self) -> dict:
        return {
            "documento": self.documento,
            "dt_refer": self.dt_refer,
            "versao": self.versao,
        }


@dataclass(frozen=True)
class Trimestre:
    inicio: date
    fim: date
    valores: Mapping[str, float | None]
    documentos: tuple[Acumulado, ...]
    motivos: Mapping[str, str] = field(default_factory=dict)


MOTIVO_PERIMETROS = "comparabilidade dos perímetros não demonstrada para o TTM"


def _comparaveis(documentos: Iterable[Acumulado], campo: str) -> bool:
    """Exige perímetro e evidência explícitos por campo; igualdade de modelo não basta."""
    perimetros = set()
    for documento in documentos:
        fonte = documento.proveniencia.get(campo, {})
        perimetro = fonte.get("perimetro")
        evidencia = fonte.get("evidencia_comparabilidade")
        if not isinstance(perimetro, str) or not perimetro.strip():
            return False
        if not isinstance(evidencia, str) or not evidencia.strip():
            return False
        perimetros.add(perimetro)
    return len(perimetros) == 1


def _linha_ausente(motivo: str | None) -> bool:
    return isinstance(motivo, str) and (
        motivo == MOTIVO_LINHA_AUSENTE or motivo.startswith(MOTIVO_LINHA_AUSENTE + " ")
    )


def _valor_acumulado(documento: Acumulado, campo: str) -> float | None:
    valor = documento.valores.get(campo)
    if (
        campo in ("dividendos", "jcp")
        and valor is None
        and _linha_ausente(documento.motivos.get(campo))
    ):
        return 0.0
    return valor


def proventos(
    dividendos: float | None,
    jcp: float | None,
    *,
    motivos: Mapping[str, str] | None = None,
) -> float | None:
    """Soma as rubricas informadas; motivo de falha difere de rubrica que não ocorre."""
    if dividendos is None and jcp is None:
        return None
    for campo, valor in (("dividendos", dividendos), ("jcp", jcp)):
        motivo = (motivos or {}).get(campo)
        if valor is None and not _linha_ausente(motivo):
            return None
    return (dividendos if dividendos is not None else 0.0) + (
        jcp if jcp is not None else 0.0
    )


def _por_acao(
    ind: Mapping,
    *,
    especie: str | None,
    classe: str | None,
    classes_preferenciais: list[str] | None,
    eh_unit: bool,
    acoes_por_unit: dict | None,
) -> dict:
    """LPA, VPA e ações do próprio documento (F2A-3 e D19), com os motivos das abstenções."""
    divulgados = acoes_cvm.divulgados_coerentes(
        ind.get("lpa_basico_por_classe") or {},
        ind.get("lucro_controladores"),
        ind.get("lucro_liquido"),
    )
    resultado = acoes_cvm.derivar_por_acao(
        lucro_controladores=ind.get("lucro_controladores"),
        pl_controladores=ind.get("pl_controladores"),
        composicao=ind.get("composicao_capital"),
        motivo_composicao=ind.get("composicao_motivo"),
        lpa_divulgado=acoes_cvm.divulgado_da_escala(divulgados),
        preco=None,
        eh_unit=eh_unit,
        acoes_por_unit=acoes_por_unit,
    )
    por_acao = resultado if isinstance(resultado, acoes_cvm.PorAcao) else None
    fator = (
        sum(acoes_por_unit.values())
        if eh_unit and acoes_cvm._unit_valida(acoes_por_unit)
        else 1
    )
    recalculado = (
        por_acao.lpa / fator if por_acao and por_acao.lpa is not None else None
    )
    lpa = acoes_cvm.lpa_dos_metodos(
        especie=especie,
        classe=classe,
        classes_preferenciais=classes_preferenciais,
        eh_unit=eh_unit,
        acoes_por_unit=acoes_por_unit,
        divulgados=divulgados,
        recalculado=recalculado,
    )
    saida: dict = {
        "acoes": None,
        "lpa": None,
        "lpa_origem": None,
        "vpa": None,
        "motivos": {},
    }
    if isinstance(lpa, acoes_cvm.Abstencao):
        saida["motivos"]["lpa"] = lpa.motivo
    else:
        saida["lpa"], saida["lpa_origem"] = lpa
    if por_acao is None:
        saida["motivos"]["acoes"] = resultado.motivo
        saida["motivos"]["vpa"] = resultado.motivo
        return saida
    saida["acoes"] = por_acao.acoes.valor
    saida["vpa"] = por_acao.vpa
    if por_acao.vpa is None:
        saida["motivos"]["vpa"] = acoes_cvm.MOTIVO_ROE_SEM_PL
    return saida


def exercicio(
    ano: int,
    ind: Mapping,
    *,
    especie: str | None = None,
    classe: str | None = None,
    classes_preferenciais: list[str] | None = None,
    eh_unit: bool = False,
    acoes_por_unit: dict | None = None,
) -> dict:
    """Um exercício da série, a partir do `calcular_indicadores` daquele ano e da DVA."""
    dividendos, jcp = ind.get("dividendos"), ind.get("jcp")
    por_acao = _por_acao(
        ind,
        especie=especie,
        classe=classe,
        classes_preferenciais=classes_preferenciais,
        eh_unit=eh_unit,
        acoes_por_unit=acoes_por_unit,
    )
    por_acao["motivos"].update(ind.get("proventos_motivos") or {})
    return {
        "exercicio": ano,
        "dt_refer": ind.get("cvm_dt_refer"),
        "versao": ind.get("cvm_versao"),
        "lucro_liquido": ind.get("lucro_liquido"),
        "lucro_controladores": ind.get("lucro_controladores"),
        "patrimonio_liquido": ind.get("patrimonio_liquido"),
        "pl_controladores": ind.get("pl_controladores"),
        "receita_liquida": ind.get("receita_liquida"),
        "ebit": ind.get("ebit"),
        "inicio": ind.get("inicio"),
        "fim": ind.get("fim"),
        "proveniencia": ind.get("proveniencia"),
        "perimetro": ind.get("perimetro"),
        "evidencia_comparabilidade": ind.get("evidencia_comparabilidade"),
        "pl_inicial_controladores": ind.get("pl_inicial_controladores"),
        "divida_liquida": ind.get("divida_liquida"),
        "ebitda": ind.get("ebitda"),
        **por_acao,
        "dividendos": dividendos,
        "jcp": jcp,
        "proventos": proventos(dividendos, jcp, motivos=ind.get("proventos_motivos")),
        "proventos_base": COMPETENCIA,
    }


def serie_anual(
    indicadores: Mapping[int, Mapping], ano_final: int, **ticker
) -> list[dict]:
    """Até `MAX_EXERCICIOS` exercícios de `ano_final` para trás, do mais antigo ao mais recente.

    `indicadores`: {ano: saída do `calcular_indicadores`, com `dividendos` e `jcp`}. Ano fora
    da janela ou sem DFP fica de fora; `ticker` são os atributos do papel (espécie, classe…).
    """
    janela = range(ano_final - MAX_EXERCICIOS + 1, ano_final + 1)
    return [
        exercicio(ano, indicadores[ano], **ticker)
        for ano in janela
        if ano in indicadores
    ]


def mais_recentes(acumulados: Iterable[Acumulado]) -> list[Acumulado]:
    """Um acumulado por período (início, fim): o da maior `VERSAO`."""
    escolhidos: dict[tuple[date, date], Acumulado] = {}
    for acumulado in acumulados:
        chave = (acumulado.inicio, acumulado.fim)
        atual = escolhidos.get(chave)
        if atual is None or acumulado.versao > atual.versao:
            escolhidos[chave] = acumulado
    return sorted(escolhidos.values(), key=lambda a: (a.inicio, a.fim))


def _meses(inicio: date, fim: date) -> int:
    """Meses civis completos declarados; limites parciais não provam um trimestre."""
    if fim < inicio or inicio.day != 1 or fim.day != monthrange(fim.year, fim.month)[1]:
        return 0
    return (fim.year - inicio.year) * 12 + fim.month - inicio.month + 1


def _diferenca(atual: float | None, anterior: float | None) -> float | None:
    if atual is None or anterior is None:
        return None
    return atual - anterior


def trimestres(acumulados: Iterable[Acumulado]) -> list[Trimestre]:
    """Trimestres pela diferença entre acumulados consecutivos do mesmo exercício.

    O primeiro acumulado do exercício é o 1º trimestre; o da DFP, menos o de nove meses, é o
    4º. Um intervalo que não tem três meses (trimestre faltando) não vira trimestre.
    """
    resultado: list[Trimestre] = []
    anterior: Acumulado | None = None
    for acumulado in mais_recentes(acumulados):
        motivos_trimestre: dict[str, str] = {}
        if anterior is None or anterior.inicio != acumulado.inicio:
            inicio, valores, documentos = (
                acumulado.inicio,
                {c: _valor_acumulado(acumulado, c) for c in acumulado.valores},
                (acumulado,),
            )
        else:
            inicio = anterior.fim + timedelta(days=1)
            valores = {
                campo: _diferenca(
                    _valor_acumulado(acumulado, campo),
                    _valor_acumulado(anterior, campo),
                )
                for campo in acumulado.valores
            }
            documentos = (anterior, acumulado)
            for campo, valor in valores.items():
                if valor is not None and not _comparaveis(documentos, campo):
                    valores[campo] = None
                    motivos_trimestre[campo] = MOTIVO_PERIMETROS
        if _meses(inicio, acumulado.fim) == 3:
            resultado.append(Trimestre(inicio, acumulado.fim, valores, documentos, motivos_trimestre))
        anterior = acumulado
    return resultado


def ttm(acumulados: Iterable[Acumulado], data_referencia: date) -> dict | Abstencao:
    """Lucro, receita e proventos dos quatro últimos trimestres encerrados até a data.

    Campo que falta em algum dos documentos fica `None`, com o motivo; os outros seguem.
    """
    encerrados = sorted(
        (t for t in trimestres(acumulados) if t.fim <= data_referencia),
        key=lambda t: t.fim,
    )
    if len(encerrados) < 4:
        return Abstencao(MOTIVO_MENOS_DE_QUATRO)
    ultimos = encerrados[-4:]
    for anterior, seguinte in pairwise(ultimos):
        if seguinte.inicio != anterior.fim + timedelta(days=1):
            return Abstencao(MOTIVO_NAO_CONTIGUOS)
    valores: dict[str, float | None] = {}
    motivos: dict[str, str] = {}
    for campo in CAMPOS_TTM:
        parcelas = [t.valores.get(campo) for t in ultimos]
        documentos_do_campo = [d for t in ultimos for d in t.documentos]
        if all(
            d.valores.get(campo) is None and _linha_ausente(d.motivos.get(campo))
            for d in documentos_do_campo
        ):
            valores[campo] = None
            motivos[campo] = MOTIVO_LINHA_AUSENTE
        elif any(p is None for p in parcelas):
            valores[campo] = None
            do_documento = [
                d.motivos[campo]
                for t in ultimos
                for d in t.documentos
                if campo in d.motivos and not _linha_ausente(d.motivos[campo])
            ]
            do_documento += [t.motivos[campo] for t in ultimos if campo in t.motivos]
            motivos[campo] = (
                f"{MOTIVO_CAMPO_AUSENTE}: {do_documento[0]}"
                if do_documento
                else MOTIVO_CAMPO_AUSENTE
            )
        else:
            if _comparaveis(documentos_do_campo, campo):
                valores[campo] = sum(parcelas)
            else:
                valores[campo] = None
                motivos[campo] = MOTIVO_PERIMETROS
    valores["proventos"] = proventos(
        valores["dividendos"], valores["jcp"], motivos=motivos
    )
    documentos: list[dict] = []
    for trimestre in ultimos:
        for documento in trimestre.documentos:
            if documento.origem() not in documentos:
                documentos.append(documento.origem())
    return {
        "inicio": ultimos[0].inicio.isoformat(),
        "fim": ultimos[-1].fim.isoformat(),
        "valores": valores,
        "motivos": motivos,
        "trimestres": [
            {
                "inicio": t.inicio.isoformat(),
                "fim": t.fim.isoformat(),
                "valores": dict(t.valores),
                "documentos": [d.origem() for d in t.documentos],
            }
            for t in ultimos
        ],
        "documentos": documentos,
        "proveniencia": {
            campo: [
                {
                    **d.origem(),
                    **d.proveniencia[campo],
                }
                for t in ultimos
                for d in t.documentos
                if campo in d.proveniencia
            ]
            for campo in CAMPOS_TTM
        },
        "proventos_base": COMPETENCIA,
    }
