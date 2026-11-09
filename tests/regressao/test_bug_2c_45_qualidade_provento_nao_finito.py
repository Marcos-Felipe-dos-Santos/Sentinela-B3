"""BUG-2C-45: valor de provento inválido não reaparece sob chave de proveniência."""

import math

from tests.test_qualidade import documentos, quadro


def test_nan_recusado_nao_vaza_na_saida_por_fonte():
    docs = documentos()
    docs[0]["proventos_b3"]["valor"] = math.nan
    r = quadro(docs)
    assert r["exercicios"][0]["proventos"] is None
    fonte = r["exercicios"][0]["fonte_proventos"]
    assert (
        "valor" not in fonte
    )  # proveniência tem fonte/janela/coleta, valor recusado não é evidência
