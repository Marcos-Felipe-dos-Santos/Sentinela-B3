"""BUG-2C-40: razão não representável não é zero observado (ficha qualidade1.0)."""

from tests.test_qualidade import documentos, quadro


def test_roe_positivo_nao_representavel_nao_vira_zero():
    docs = documentos()
    docs[0]["lucro_controladores"] = 1e-308
    docs[0]["pl_inicial_controladores"] = 1e308
    r = quadro(docs)
    assert r["exercicios"][0]["roe"] is None
    assert r["roe"]["observados"] == 4
