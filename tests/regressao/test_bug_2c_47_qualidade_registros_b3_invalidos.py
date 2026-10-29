"""BUG-2C-47: registros B3 malformados devem tornar a fonte indisponível."""

from sentinela.data.qualidade_inputs import entradas
from tests.test_qualidade import AS_OF
from tests.test_qualidade_inputs import dados


def test_registro_b3_texto_nao_quebra():
    d = dados()
    d["proventos_b3"]["registros"] = ["registro ilegível"]
    d["proventos_b3"]["total"] = 1
    r = entradas(d, AS_OF)
    assert r[0]["proventos_b3"]["valor"] is None and r[0]["proventos_b3"]["motivo"]
