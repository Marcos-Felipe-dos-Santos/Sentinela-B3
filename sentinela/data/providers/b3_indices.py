"""Série histórica oficial do Ibovespa (B3) e leitura dos benchmarks por data (F3-7a).

Serviço `indexStatisticsProxy/IndexCall/GetPortfolioDay` de `sistemaswebb3-listados.b3.com.br`,
conferido no L1 (`docs/decisoes/l1-fontes-historicas.md` §1 e §3): parâmetros em JSON
codificado em base64 no fim do caminho (`{"index": "IBOV", "language": "pt-br", "year": "AAAA"}`);
a resposta traz `results`, uma linha por dia do mês (`day`), com o fechamento de cada mês em
`rateValue1` a `rateValue12` (texto com ponto de milhar e vírgula decimal; nulo sem pregão), e
`min`/`max` do mês, que não são fechamentos.

`benchmarks_ate` lê do banco único as séries do Ibovespa e do CDI (SGS 12, `macro.gravar_cdi`)
com data anterior ao dia local de D. `mensal` fecha cada mês no último pregão da B3 (DD-36,
decisão 7) e acumula o CDI pela convenção do Fator DI da B3 (DD-55): do fechamento anterior,
inclusive, ao do mês, exclusive; nos dezembros, a taxa do último dia útil sem pregão fica no
período que termina no fechamento de janeiro. Recebe o dia local de D (`date`); sem leitura de relógio aqui.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Iterable, Mapping
from datetime import date, datetime
from typing import Any

from sentinela.data.providers.b3_proventos import obter_json

URL_BASE = "https://sistemaswebb3-listados.b3.com.br/indexStatisticsProxy/IndexCall"
MOTIVO_CDI_SEM_IBOV = "CDI sem observação no intervalo do mês do Ibovespa"


def url(ano: int, indice: str = "IBOV") -> str:
    parametros = {"index": indice, "language": "pt-br", "year": str(ano)}
    codigo = base64.b64encode(json.dumps(parametros).encode()).decode()
    return f"{URL_BASE}/GetPortfolioDay/{codigo}"


def _numero(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", "."))


def ler(corpo: Any, ano: int) -> list[tuple[date, str, float]]:
    """(data, texto literal, valor) de cada fechamento do ano, em ordem de data.

    Corpo fora do leiaute, dia fora do mês ou texto que não é número: `ValueError`.
    """
    if not isinstance(corpo, dict) or not isinstance(corpo.get("results"), list):
        # Formato errado é falha da fonte (ValueError), não erro do código (TypeError).
        raise ValueError("série do índice da B3 fora do leiaute")  # noqa: TRY004
    fechamentos = []
    for linha in corpo["results"]:
        if not isinstance(linha, dict) or type(linha.get("day")) is not int:
            raise ValueError("série do índice da B3 com dia ilegível")
        for mes in range(1, 13):
            texto = linha.get(f"rateValue{mes}")
            if texto is None:
                continue
            if not isinstance(texto, str):
                raise ValueError("série do índice da B3 com fechamento ilegível")  # noqa: TRY004
            fechamentos.append((date(ano, mes, linha["day"]), texto, _numero(texto)))
    return sorted(fechamentos)


def coletar(
    ano: int, obter: Callable[[str], tuple[Any, dict]] = obter_json
) -> tuple[list[tuple[date, str, float]], dict]:
    """Fechamentos do ano e a fonte da resposta (URL, bytes e SHA-256)."""
    corpo, fonte = obter(url(ano))
    return ler(corpo, ano), fonte


def gravar_ibovespa(
    conn,
    fechamentos: Iterable[tuple[date, str, float]],
    fonte: Mapping,
    coleta: datetime,
) -> dict:
    """Grava os fechamentos em `benchmarks` (série `IBOV`), num `SAVEPOINT`.

    Já gravado com o mesmo hash de resposta, conta como repetido.
    """
    if coleta.utcoffset() is None:
        raise ValueError("coleta exige fuso horário")
    resumo = {"inseridos": 0, "repetidos": 0}
    conn.execute("SAVEPOINT ibovespa")
    try:
        for dia, texto, valor in fechamentos:
            chave = ("IBOV", dia.isoformat(), fonte["sha256"])
            if conn.execute(
                "SELECT 1 FROM benchmarks WHERE serie = ? AND data = ? AND hash_sha256 = ?",
                chave,
            ).fetchone():
                resumo["repetidos"] += 1
                continue
            conn.execute(
                "INSERT INTO benchmarks (serie, data, valor, valor_texto, fonte, coleta, "
                "hash_sha256) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("IBOV", dia.isoformat(), valor, texto, fonte["url"], coleta.isoformat(),
                 fonte["sha256"]),
            )  # fmt: skip
            resumo["inseridos"] += 1
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK TO ibovespa")
            conn.execute("RELEASE ibovespa")
        raise
    conn.execute("RELEASE ibovespa")
    return resumo


def benchmarks_ate(conn, serie: str, dia: date) -> list[dict]:
    """Observações da série com data anterior ao dia local de D, uma por data.

    Na mesma data vinda de coletas diferentes, vale a coleta mais recente (pelo instante).
    """
    if isinstance(dia, datetime) or not isinstance(dia, date):
        raise TypeError(
            "benchmarks_ate recebe o dia local de D (date), não um instante"
        )
    por_data: dict[str, tuple] = {}
    for data, valor, fonte, coleta, hash_ in conn.execute(
        "SELECT data, valor, fonte, coleta, hash_sha256 FROM benchmarks "
        "WHERE serie = ? AND data < ? ORDER BY data",
        (serie, dia.isoformat()),
    ):
        atual = por_data.get(data)
        if atual is None or datetime.fromisoformat(coleta) > datetime.fromisoformat(
            atual[2]
        ):
            por_data[data] = (valor, fonte, coleta, hash_)
    return [
        {"data": d, "valor": v, "fonte": f, "coleta": c, "hash_sha256": h}
        for d, (v, f, c, h) in sorted(por_data.items())
    ]


MOTIVO_CDI_INCOMPLETO = "CDI sem a taxa de algum pregão do Ibovespa no mês"


def mensal(ibov: Iterable[Mapping], cdi: Iterable[Mapping]) -> list[dict]:
    """Fechamento mensal do Ibovespa e o fator do CDI no mesmo período (DD-36, DD-55).

    Cada mês fecha no último pregão do Ibovespa no mês. O fator do CDI segue o Fator DI da B3:
    multiplica `1 + taxa/100` das taxas do fechamento anterior, inclusive, ao fechamento do
    mês, exclusive (a taxa do dia d remunera de d ao dia útil seguinte). O primeiro mês só dá o
    ponto de partida. Cada pregão do Ibovespa no período precisa da taxa do CDI do mesmo dia;
    sem ela, o mês fica sem fator, com o motivo.
    """
    observacoes = sorted(ibov, key=lambda o: o["data"])
    ultimos: dict[str, Mapping] = {}
    for obs in observacoes:
        ultimos[obs["data"][:7]] = obs
    taxas = dict(sorted((o["data"], o["valor"]) for o in cdi))
    pregoes = [o["data"] for o in observacoes]
    meses, anterior = [], None
    for mes in sorted(ultimos):
        fechamento = ultimos[mes]
        item = {"mes": mes, "data": fechamento["data"], "ibov": fechamento["valor"]}
        if anterior is not None:
            periodo = [p for p in pregoes if anterior <= p < fechamento["data"]]
            dentro = [t for d, t in taxas.items() if anterior <= d < fechamento["data"]]
            if not dentro:
                item["motivo_cdi"] = MOTIVO_CDI_SEM_IBOV
            elif any(p not in taxas for p in periodo):
                item["motivo_cdi"] = MOTIVO_CDI_INCOMPLETO
            else:
                fator = 1.0
                for taxa in dentro:
                    fator *= 1 + taxa / 100
                item["fator_cdi"] = fator
        meses.append(item)
        anterior = fechamento["data"]
    return meses
