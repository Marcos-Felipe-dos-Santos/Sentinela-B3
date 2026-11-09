"""BUG-2C-49: exercícios de entidades/modelos contraditórios não são comparáveis."""

import pytest

from tests.test_qualidade import documentos, quadro


@pytest.mark.parametrize(
    "campo,valor", [("cnpj", "99.999.999/0001-99"), ("modelo", "banco")]
)
def test_identidade_documental_conflitante_nao_e_media(campo, valor):
    docs = documentos()
    for e in docs:
        e.update(cnpj="00.000.000/0001-00", modelo="empresa")
    docs[0][campo] = valor
    r = quadro(docs)
    assert r["comparavel"] is False and r["roe"]["media"] is None
