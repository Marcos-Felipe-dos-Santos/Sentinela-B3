"""OASIS OData4.01 Part2 §2.2: aspa interna de literal deve ser duplicada."""

from urllib.parse import parse_qs, urlsplit

import pytest

from sentinela.data.providers.ifdata import caminho_capital, caminho_carteira


@pytest.mark.parametrize("construir", [caminho_capital, caminho_carteira])
def test_codinst_e_literal_opaco(construir) -> None:
    caminho = construir("202606", "O'Neil")
    filtro = parse_qs(urlsplit(caminho).query)["$filter"][0]
    assert filtro == "CodInst eq 'O''Neil'"
