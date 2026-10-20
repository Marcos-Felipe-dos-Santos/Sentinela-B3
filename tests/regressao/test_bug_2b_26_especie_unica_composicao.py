"""FCA isolado não comprova espécie única contra a Composição do Capital."""

from market_engine import MarketEngine
from sentinela.data.acoes_cvm import Composicao


def test_especie_unica_do_indice_nao_sobrepoe_duas_especies_na_composicao():
    ind = {
        "composicao_capital": Composicao(100, 100, 0, 0, 0, "2025-12-31", "1"),
        "composicao_motivo": None,
        "cvm_dt_refer": "2025-12-31",
        "cvm_versao": "1",
        "cnpj": "00.000.000/0001-00",
        "lucro_controladores": 200.0,
        "lucro_liquido": 200.0,
        "pl_controladores": 1000.0,
        "lpa_basico_por_classe": {},
        "lpa_basico_agregado": {"3.99.01": 1.0, "3.99": None},
    }
    dados = {
        "classe_ativo": "STOCK",
        "especie": "ON",
        "especies_da_companhia": ["ON"],
        "preco_atual": 10.0,
    }
    campos = MarketEngine.__new__(MarketEngine)._por_acao_cvm("TST3", dados, ind)
    assert "lpa" not in campos
