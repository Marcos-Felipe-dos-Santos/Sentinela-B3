"""Liquidez pelo COTAHIST (F2A-26; insumo da [LIQUIDEZ] e do F2A-10, que são da 2B).

Mede e aplica a regra explícita do F2A-10, sem acessar os motores. Para cada janela (21 e 63 pregões), a partir das cotações do
mercado à vista (F2A-18):
- volume financeiro diário mediano e médio, somado por dia no código do ticker;
- negócios por dia (mediana);
- presença: pregões com negócio no ticker ÷ pregões do arquivo na janela.

Os pregões são as datas em que o arquivo tem algum negócio; dia sem negócio no ticker conta
zero. Janela com menos pregões que o pedido vem marcada como incompleta. Mês que faltou na
coleta vai em `meses_ausentes`: com ele, a janela pode juntar meses separados por um buraco.
Ticker que não aparece em nenhuma cotação do período se abstém (código mudou, fora do
mercado à vista), em vez de sair com volume zero.

Função pura: sem rede, sem relógio, sem `config`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean, median
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # só o tipo: o provedor carrega rede (requests) no import
    from sentinela.data.providers.b3_cotahist import Cotacao

JANELAS = (21, 63)
FONTE = "B3, Séries Históricas (COTAHIST) mensais, mercado à vista"
MOTIVO_SEM_PREGOES = "COTAHIST sem pregões no período"
MOTIVO_TICKER_AUSENTE = (
    "ticker sem cotação no COTAHIST do período (não é o mesmo que não negociar)"
)


@dataclass(frozen=True)
class Abstencao:
    motivo: str


def metricas(
    cotacoes: Iterable[Cotacao],
    ticker: str,
    janelas: tuple[int, ...] = JANELAS,
    meses_ausentes: tuple[str, ...] = (),
) -> dict | Abstencao:
    """Volume, negócios e presença do ticker nas janelas, com a data final e a fonte."""
    pregoes: set = set()
    volume: dict = {}
    negocios: dict = {}
    for cotacao in cotacoes:
        pregoes.add(cotacao.data)
        if cotacao.codigo_negociacao == ticker:
            volume[cotacao.data] = (
                volume.get(cotacao.data, 0.0) + cotacao.volume_financeiro
            )
            negocios[cotacao.data] = negocios.get(cotacao.data, 0) + cotacao.negocios
    if not pregoes:
        return Abstencao(MOTIVO_SEM_PREGOES)
    if not volume:
        return Abstencao(MOTIVO_TICKER_AUSENTE)
    ordenados = sorted(pregoes)
    saida: dict = {}
    for tamanho in janelas:
        datas = ordenados[-tamanho:]
        volumes = [volume.get(d, 0.0) for d in datas]
        por_dia = [negocios.get(d, 0) for d in datas]
        saida[str(tamanho)] = {
            "pregoes": len(datas),
            "incompleta": len(datas) < tamanho,
            "volume_mediano": median(volumes),
            "volume_medio": mean(volumes),
            "negocios_mediana": median(por_dia),
            "presenca": sum(1 for n in por_dia if n > 0) / len(datas),
        }
    return {
        "janelas": saida,
        "data_final": ordenados[-1].isoformat(),
        "fonte": FONTE,
        "meses_ausentes": list(meses_ausentes),
    }


def _percentual(razao: float) -> str:
    """Razão como percentual pt-BR com uma casa: 0,7936 → "79,4%"."""
    return f"{razao * 100:.1f}".replace(".", ",") + "%"


def _reais(valor: float) -> str:
    """Valor em reais pt-BR com duas casas: 64290,123 → "R$ 64.290,12"."""
    texto = f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def avaliar(
    bloco: dict | None, *, janela: int, presenca_min: float, volume_min: float
) -> dict[str, str] | None:
    """Motivo, aviso ou nada; a regra entra por parâmetro, sem configuração global."""

    def aviso(motivo: str) -> dict[str, str]:
        return {"aviso": f"liquidez não medida: {motivo}"}

    def abaixo(presenca: float, volume: float) -> dict[str, str]:
        return {
            "abstencao": (
                "liquidez abaixo do mínimo para análise: "
                f"presença de {_percentual(presenca)} e volume mediano de "
                f"{_reais(volume)} nos últimos {janela} pregões "
                f"(mínimo: {_percentual(presenca_min)} e {_reais(volume_min)})"
            )
        }

    if not isinstance(bloco, dict) or not bloco:
        return aviso("bloco sem dados")
    if bloco.get("meses_ausentes"):
        return aviso(
            "mês ausente na coleta: " + ", ".join(map(str, bloco["meses_ausentes"]))
        )
    if bloco.get("incompleta"):
        return aviso("janela incompleta")
    if "abstencao" in bloco:
        if bloco["abstencao"] == MOTIVO_TICKER_AUSENTE:
            if bloco.get("incompleta") is not False:
                return aviso("cobertura da janela não demonstrada")
            return abaixo(0.0, 0.0)
        return aviso(str(bloco["abstencao"]))
    janelas = bloco.get("janelas")
    j = janelas.get(str(janela)) if isinstance(janelas, dict) else None
    if not isinstance(j, dict):
        return aviso(f"janela de {janela} pregões ausente")
    if j.get("incompleta") is not False or j.get("pregoes") != janela:
        return aviso("janela incompleta")
    presenca, volume = j.get("presenca"), j.get("volume_mediano")
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in (presenca, volume)
    ):
        return aviso("presença ou volume inválido")
    if not 0 <= presenca <= 1 or volume < 0:
        return aviso("presença ou volume fora do domínio")
    if presenca < presenca_min or volume < volume_min:
        return abaixo(presenca, volume)
    return None
