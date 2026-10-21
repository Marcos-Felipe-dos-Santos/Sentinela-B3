"""Elegibilidade do FII para a lente de rendimento (F2B-2; ficha FII 1.1, §2 a §4 e §3a).

- **Tipo** pela composição do `ativo_passivo` do Informe Mensal (regra do universo inicial):
  fração da soma de recebíveis ("papel"), de imóveis, terrenos, direitos reais e participações
  imobiliárias ("tijolo") e de cotas de FII ("fundo de fundos"); o tipo é o que passa de 50%.
  Caixa e renda fixa ficam fora da base. Célula vazia conta zero; negativa, não numérica,
  base zero ou sem maioria estrita: classificação desconhecida.
- **Eventos de cota** pela relação da B3 (`fundsCall`, `stockDividends`): desdobramento ou
  grupamento com data na janela abstém; resposta inválida é fonte indisponível (§3a, (b)).
- **Conferência** do rendimento reconstruído com o rendimento oficial por cota da B3
  (`cashDividends`), mês a mês, arredondado a duas casas: diferença gera aviso, sem
  abstenção (§3a, (a)).

Função pura: sem rede, sem relógio, sem `config`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

TIJOLO = (
    "Direitos_Bens_Imoveis",
    "Terrenos",
    "Imoveis_Renda_Acabados",
    "Imoveis_Renda_Construcao",
    "Imoveis_Venda_Acabados",
    "Imoveis_Venda_Construcao",
    "Outros_Direitos_Reais",
    "Acoes_Sociedades_Atividades_FII",
    "Cotas_Sociedades_Atividades_FII",
)
PAPEL = ("CRI", "CRI_CRA", "Letras_Hipotecarias", "LCI", "LCI_LCA", "LIG")
FUNDO_DE_FUNDOS = ("FII",)
_GRUPOS = (("tijolo", TIJOLO), ("papel", PAPEL), ("fundo de fundos", FUNDO_DE_FUNDOS))

MOTIVO_TIPO_DESCONHECIDO = "classificação de FII desconhecida"
EVENTOS_DE_BASE = {"DESDOBRAMENTO": "desdobramento", "GRUPAMENTO": "grupamento"}
AVISO_SEM_CONFERENCIA = "conferência do rendimento com a B3 indisponível"
MESES = (
    "JANEIRO",
    "FEVEREIRO",
    "MARÇO",
    "ABRIL",
    "MAIO",
    "JUNHO",
    "JULHO",
    "AGOSTO",
    "SETEMBRO",
    "OUTUBRO",
    "NOVEMBRO",
    "DEZEMBRO",
)


@dataclass(frozen=True)
class Abstencao:
    motivo: str


def _numero(bruto: object) -> float | None:
    """Número do CSV ou da B3 (vírgula ou ponto decimal); `None` sem número finito."""
    if isinstance(bruto, bool):
        return None
    try:
        numero = float(str(bruto).strip().replace(",", "."))
    except ValueError:
        return None
    return numero if math.isfinite(numero) else None


def _vazio(bruto: object) -> bool:
    return (
        bruto is None
        or (isinstance(bruto, float) and math.isnan(bruto))
        or (isinstance(bruto, str) and not bruto.strip())
    )


def tipo_pela_composicao(linha: Mapping) -> str | Abstencao:
    """Tijolo, papel ou fundo de fundos pela maioria estrita da base; senão, abstenção."""
    somas = {}
    for tipo, colunas in _GRUPOS:
        soma = 0.0
        for coluna in colunas:
            bruto = linha.get(coluna)
            if _vazio(bruto):
                continue
            valor = _numero(bruto)
            if valor is None:
                return Abstencao(f"{MOTIVO_TIPO_DESCONHECIDO}: {coluna} não numérico")
            if valor < 0:
                return Abstencao(f"{MOTIVO_TIPO_DESCONHECIDO}: {coluna} negativo")
            soma += valor
        somas[tipo] = soma
    base = sum(somas.values())
    if not math.isfinite(base) or base <= 0:
        return Abstencao(f"{MOTIVO_TIPO_DESCONHECIDO}: base zero")
    for tipo, soma in somas.items():
        if soma / base > 0.5:
            return tipo
    return Abstencao(f"{MOTIVO_TIPO_DESCONHECIDO}: sem maioria estrita")


def resposta_b3_valida(resposta: object, codigo: str) -> bool:
    """Sucesso com a estrutura esperada e o próprio fundo (complemento (b) da §3a).

    Código desconhecido da B3 devolve um registro genérico ("ISIN GENERIC") com listas
    vazias: não é o fundo e não prova ausência de evento.
    """
    return (
        isinstance(resposta, Mapping)
        and isinstance(resposta.get("cashDividends"), list)
        and isinstance(resposta.get("stockDividends"), list)
        and str(resposta.get("code") or "").strip().upper() == codigo.upper()
        and str(resposta.get("fund") or "").strip().upper() != "ISIN GENERIC"
    )


def ler_data(bruto: object) -> date | None:
    texto = str(bruto or "").strip()
    try:
        dia, mes, ano = (int(p) for p in texto.split("/"))
        return date(ano, mes, dia)
    except ValueError:
        return None


def evento_de_cota(
    stock_dividends: Iterable[Mapping], inicio: date, fim: date
) -> str | None:
    """Motivo da abstenção por desdobramento ou grupamento oficial em [inicio, fim], ou `None`.

    Evento de base com data ilegível não demonstra continuidade: também abstém.
    """
    for evento in stock_dividends:
        nome = EVENTOS_DE_BASE.get(str(evento.get("label") or "").strip().upper())
        if nome is None:
            continue
        dia = ler_data(evento.get("lastDatePrior"))
        if dia is None:
            return f"{nome} com data ilegível: continuidade da base não demonstrável"
        if inicio <= dia <= fim:
            return f"{nome} oficial na janela ({dia.isoformat()}): base de cota incompatível"
    return None


def _mes_da_b3(relacionado: object) -> str | None:
    """ "SETEMBRO/2026" → "2026-09"."""
    try:
        nome, ano = str(relacionado or "").strip().upper().split("/")
        return f"{int(ano):04d}-{MESES.index(nome) + 1:02d}"
    except ValueError:
        return None


def conferencia_b3(
    rendimentos: Mapping[str, float],
    cash_dividends: Iterable[Mapping] | None,
    isin: str | None,
) -> list[str]:
    """Avisos da conferência mês a mês (AAAA-MM → R$/cota) com a B3, em duas casas."""
    if cash_dividends is None or not isin:
        return [AVISO_SEM_CONFERENCIA]
    da_b3: dict[str, float] = {}
    for pagamento in cash_dividends:
        if str(pagamento.get("isinCode") or "").strip() != isin:
            continue
        mes = _mes_da_b3(pagamento.get("relatedTo"))
        valor = _numero(pagamento.get("rate"))
        if mes is None or valor is None:
            continue
        da_b3[mes] = da_b3.get(mes, 0.0) + valor
    divergentes, sem_b3 = [], []
    for mes, valor in sorted(rendimentos.items()):
        if mes not in da_b3:
            sem_b3.append(mes)
        elif round(valor, 2) != round(da_b3[mes], 2):
            divergentes.append(
                f"{mes} Informe R$ {valor:.2f}, B3 R$ {da_b3[mes]:.2f}".replace(
                    ".", ","
                )
            )
    avisos = []
    if divergentes:
        avisos.append("rendimento do Informe diverge da B3: " + "; ".join(divergentes))
    if sem_b3:
        avisos.append("rendimento sem valor da B3 para conferir: " + ", ".join(sem_b3))
    return avisos
