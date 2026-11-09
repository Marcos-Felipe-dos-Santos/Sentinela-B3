"""BUG-2C-43: proveniência B3 malformada deixa indicador parcial sem derrubar motor."""

from sentinela.data.qualidade_inputs import entradas
from tests.test_qualidade import AS_OF
from tests.test_qualidade_inputs import dados


def test_lista_no_lugar_de_proveniencia_nao_quebra():
    d = dados()
    d["proventos_b3"]["proveniencia"] = ["B3"]
    r = entradas(d, AS_OF)
    assert r[0]["proventos_b3"]["valor"] is None
    assert r[0]["proventos_b3"]["motivo"]
