"""BUG-2B-29: a relação de proventos da B3 pelo nome de pregão com barra vem vazia.

Observado em 20/10/2026 no serviço real: GetDetail da Ambev (código CVM 23264) devolve o
nome de pregão "AMBEV S/A", e GetListedCashDividends com esse nome devolve zero registros
("AMBEV SA" devolve 40; "AMBEV", 134); o mesmo com "KLABIN S/A". O complemento do emissor
tem proventos recentes, então o Bazin se abstém pela conferência do emissor, embora a
companhia pague proventos. A B3 falsa abaixo reproduz esse comportamento. Esta regressão
assume que o correto é a série do emissor chegar ao Bazin; a forma da correção (variação
do nome ou outra chamada) não está decidida e vai para a proposta da 2C.
"""

import base64
import json
from datetime import UTC, date, datetime

import pytest

from sentinela.data import proventos_b3
from sentinela.data.providers import b3_proventos

EVENTO = {
    "typeStock": "ON",
    "corporateAction": "JRS CAP PROPRIO",
    "valueCash": "0,10",
    "lastDatePriorEx": "21/09/2026",
    "dateApproval": "01/09/2026",
    "quotedPerShares": "1",
}
ANTIGO = {**EVENTO, "lastDatePriorEx": "10/06/2020", "dateApproval": "01/06/2020"}
COMPLEMENTO = {
    "stockDividends": [],
    "cashDividends": [
        {
            "isinCode": "BRABEVACNOR1",
            "label": "JRS CAP PROPRIO",
            "lastDatePrior": "21/09/2026",
            "rate": "0,10000000000",
        }
    ],
}


def _b3_como_a_real(endereco):
    metodo, codificado = endereco.removeprefix(b3_proventos.URL_BASE + "/").split(
        "/", 1
    )
    parametros = json.loads(base64.b64decode(codificado))
    if metodo == "GetDetail":
        return {"tradingName": "AMBEV S/A", "issuingCompany": "ABEV"}, {}
    if metodo == "GetListedSupplementCompany":
        return [COMPLEMENTO], {}
    registros = [EVENTO, ANTIGO] if "/" not in parametros["tradingName"] else []
    return {
        "page": {"totalRecords": len(registros), "totalPages": 1},
        "results": registros,
    }, {}


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-29 · relação B3 vazia pelo nome de pregão com barra · corrige: proposta da 2C",
)
def test_nome_de_pregao_com_barra_traz_a_relacao_do_emissor():
    relacao = b3_proventos.coletar(
        23264, datetime(2026, 10, 20, 15, tzinfo=UTC), _b3_como_a_real
    )
    serie = proventos_b3.serie_12_meses(
        relacao.registros,
        total=relacao.total,
        referencia=date(2026, 9, 30),
        dia_as_of=date(2026, 10, 19),
        especie="ON",
        dinheiro_complemento=relacao.dinheiro_complemento,
    )
    assert not isinstance(serie, proventos_b3.Abstencao), serie
    assert serie["d_bruto_12m"] == pytest.approx(0.10)
