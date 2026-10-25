"""Complemento do FII listado na B3: rendimentos por cota e eventos de cota (F2B-2; ficha FII 1.1, §3a).

Serviço `fundsProxy/fundsCall/GetListedSupplementFunds` de `sistemaswebb3-listados.b3.com.br`,
conferido em 21/10/2026 (contrato D18 em `tests/fixtures/contratos/b3_fundos_hglg_2026.json`).
Os parâmetros vão em JSON, codificados em base64, no fim do caminho: `cnpj` (só dígitos),
`identifierFund` (as quatro letras do código) e `typeFund` = 7. A resposta traz `code`, `fund`,
`cashDividends` (os rendimentos recentes: `rate`, `relatedTo`, `lastDatePrior`, `isinCode`,
`label`), `stockDividends` (desdobramentos e grupamentos: `label`, `lastDatePrior`, `factor`)
e `subscriptions`.

Comportamentos observados em 21/10/2026: código desconhecido devolve um registro genérico
(`fund` "ISIN GENERIC", listas vazias); fundo deslistado (MALL) devolve corpo vazio. A
validade da resposta é conferida por `sentinela.data.fii_elegibilidade.resposta_b3_valida`;
aqui só se lê. Sem cache: a cascata consulta a cada análise. `agora` é o instante da coleta.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sentinela.data.providers.b3_proventos import obter_json

URL_BASE = "https://sistemaswebb3-listados.b3.com.br/fundsProxy/fundsCall"
TIPO_FII = 7


def url(cnpj: str, codigo: str) -> str:
    parametros = {
        "cnpj": re.sub(r"\D", "", cnpj),
        "identifierFund": codigo[:4].upper(),
        "typeFund": TIPO_FII,
    }
    codificado = base64.b64encode(json.dumps(parametros).encode()).decode()
    return f"{URL_BASE}/GetListedSupplementFunds/{codificado}"


def coletar(
    cnpj: str,
    ticker: str,
    agora: datetime,
    obter: Callable[[str], tuple[Any, dict]] = obter_json,
) -> dict:
    """A resposta literal, a fonte (URL, bytes, SHA-256), o código e o instante da coleta.

    Falha de rede ou corpo que não é JSON (fundo deslistado): a exceção sobe para a cascata.
    """
    corpo, fonte = obter(url(cnpj, ticker))
    return {
        "resposta": corpo,
        "codigo": ticker[:4].upper(),
        "fonte": fonte,
        "coleta": agora.isoformat(),
    }
