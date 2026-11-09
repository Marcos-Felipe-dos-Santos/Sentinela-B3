"""BUG-2C-36: evento comprovadamente fora do par não bloqueia fator elegível."""

from copy import deepcopy


from sentinela.data.fatores_acoes_b3 import fatores_da_relacao
from tests.test_janelas_fundamentais import AS_OF, dados_exemplo


def test_especie_desconhecida_fora_da_janela_nao_apaga_split_valido():
    documentos = dados_exemplo()["serie_cvm"]["exercicios"]
    for i, e in enumerate(documentos):
        e["acoes"] = 100 if i == 0 else 200
    evento = {
        "label": "DESDOBRAMENTO",
        "factor": "100",
        "isinCode": "BRTESTACNOR0",
        "assetIssued": "BRTESTACNOR0",
        "approvedOn": "01/04/2022",
        "lastDatePrior": "15/04/2022",
    }
    dados = {
        "especie": "ON",
        "classe_ativo": "STOCK",
        "proventos_b3": {
            "coleta": AS_OF.isoformat(),
            "proveniencia": {"fonte": "B3 sintética"},
            "eventos_acoes": [evento],
        },
    }
    antes = fatores_da_relacao(dados, documentos, AS_OF)
    assert antes["fatores"] == {
        "2021": 2.0,
        "2022": 1.0,
        "2023": 1.0,
        "2024": 1.0,
        "2025": 1.0,
    }
    antigo = deepcopy(evento)
    antigo.update(
        {
            "lastDatePrior": "15/04/2007",
            "approvedOn": "01/04/2007",
            "isinCode": "BRTESTDESCONHECIDO",
            "assetIssued": "",
        }
    )
    dados["proventos_b3"]["eventos_acoes"].append(antigo)
    assert fatores_da_relacao(dados, documentos, AS_OF) == antes
