"""BUG-2C-48: fonte não textual não comprova dado nem pode vazar NaN na saída."""

import json

import pytest

from tests.test_qualidade import documentos, quadro


@pytest.mark.parametrize("fonte", [float("nan"), True, ["CVM"], {"origem": "CVM"}])
def test_fonte_documental_nao_textual_nao_certifica(fonte):
    docs = documentos()
    docs[0]["proveniencia"]["fonte"] = fonte
    r = quadro(docs)
    assert r["lucros"]["observados"] == 4
    json.dumps(r, allow_nan=False)


def test_campos_auxiliares_nao_reintroduzem_nan():
    docs = documentos()
    docs[0]["pl_inicial_proveniencia"] = {"demonstrativo": float("nan")}
    docs[0]["proventos_b3"]["coleta_auxiliar"] = float("nan")
    json.dumps(quadro(docs), allow_nan=False)
