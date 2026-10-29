"""BUG-2C-41: metadados malformados devem tornar o quadro parcial, sem crash."""

from tests.test_qualidade import documentos, quadro


def test_perimetro_lista_nao_certifica_nem_quebra():
    docs = documentos()
    docs[0]["perimetro"] = ["controladores"]
    r = quadro(docs)
    assert r["comparavel"] is False
