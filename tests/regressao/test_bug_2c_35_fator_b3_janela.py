"""BUG-2C-35: fator B3 coletado não chegava às janelas, F2C-1."""

import pytest
from tests.test_janelas_fundamentais import AS_OF, dados_exemplo
from sentinela.data.janelas_fundamentais import entradas


def test_fator_oficial_existente_e_consumido():
    d = dados_exemplo()
    d.pop("reconciliacao_serie")
    d.update(
        {
            "especie": "ON",
            "classe_ativo": "STOCK",
            "proventos_b3": {
                "coleta": AS_OF.isoformat(),
                "proveniencia": {"fonte": "B3 sintética"},
                "eventos_acoes": [
                    {
                        "label": "DESDOBRAMENTO",
                        "factor": "100",
                        "isinCode": "BRTESTACNOR0",
                        "assetIssued": "BRTESTACNOR0",
                        "approvedOn": "01/04/2022",
                        "lastDatePrior": "15/04/2022",
                    }
                ],
            },
        }
    )
    for i, e in enumerate(d["serie_cvm"]["exercicios"]):
        e["acoes"] = 100 if i == 0 else 200
    r = entradas(d, AS_OF)
    assert r["graham"]["lpa"] == pytest.approx(3.08)
    assert r["lynch"]["crescimento_lpa"] == pytest.approx(10**0.25 - 1)
    assert r["graham"]["fonte_eventos"] == "B3 sintética"
