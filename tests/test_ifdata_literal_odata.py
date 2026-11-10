"""Contrato do literal OData de CodInst no IF.data (F3-P05, BUG-2C-13).

O literal é opaco: apóstrofo duplicado (OASIS OData 4.01, Part 2, §2.2) e codificado na
query, de modo que a leitura da URL devolve o código original, para capital e carteira.
"""

from urllib.parse import parse_qs, urlsplit

import pytest

from sentinela.data.providers.ifdata import caminho_capital, caminho_carteira

CONSTRUTORES = pytest.mark.parametrize(
    ("construir", "relatorio"), [(caminho_capital, "'5'"), (caminho_carteira, "'16'")]
)


def _consulta(caminho):
    return parse_qs(urlsplit(caminho).query)


@CONSTRUTORES
@pytest.mark.parametrize(
    "codinst",
    [
        "Banco São João",
        "Ünïcödé 銀行",
        "A&B",
        "A+B",
        "A#B",
        "A%B",
        "A=B",
        "A;B",
        "A/B?C",
        "D'Ávila & Cia",
        "''",
    ],
)
def test_literal_volta_igual_ao_codigo(construir, relatorio, codinst):
    consulta = _consulta(construir("202606", codinst))
    literal = codinst.replace("'", "''")
    assert consulta["$filter"] == [f"CodInst eq '{literal}'"]
    assert consulta["@Relatorio"] == [relatorio]
    assert consulta["@AnoMes"] == ["202606"]
    assert consulta["$format"] == ["json"]


@CONSTRUTORES
def test_codigo_numerico_mantem_a_identidade(construir, relatorio):
    caminho = construir("202606", "1000080099")
    assert caminho == (
        "IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)"
        f"?@AnoMes=202606&@TipoInstituicao=1&@Relatorio={relatorio}"
        "&$filter=CodInst eq '1000080099'&$format=json"
    )


@CONSTRUTORES
def test_reservado_nao_abre_parametro_novo(construir, relatorio):
    consulta = _consulta(construir("202606", "X&$top=1"))
    assert "$top" not in consulta
    assert consulta["$filter"] == ["CodInst eq 'X&$top=1'"]


@CONSTRUTORES
@pytest.mark.parametrize("codinst", ["Banco São João", "Ünïcödé 銀行", "A%26B"])
def test_unicode_e_percentual_saem_codificados(construir, relatorio, codinst):
    caminho = construir("202606", codinst)
    assert caminho.isascii()
    assert _consulta(caminho)["$filter"] == [f"CodInst eq '{codinst}'"]
