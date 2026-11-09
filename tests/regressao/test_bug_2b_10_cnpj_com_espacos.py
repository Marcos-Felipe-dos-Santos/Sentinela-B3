"""BUG-2B-10: `proveniencia.entrega_no_indice` não acha o CNPJ com espaços nas pontas.

O índice de entregas com `" 11.111.111/0001-11 "` não casa com o documento
`"11.111.111/0001-11"`, e a data de entrega sai ausente. Origem: F2B-21, pergunta 8
(2ª passada do Gemini).
"""

import pytest

from sentinela.data import proveniencia


def test_cnpj_com_espacos_acha_a_entrega():
    linhas = [{"CNPJ_CIA": " 11.111.111/0001-11 ", "DT_RECEB": "2026-03-01"}]
    documento = {"CNPJ_CIA": "11.111.111/0001-11"}
    assert proveniencia.entrega_no_indice(linhas, documento) == "2026-03-01"


@pytest.mark.parametrize("coluna", ["CNPJ_CIA", "CNPJ_Fundo_Classe"])
@pytest.mark.parametrize("lado", ["indice", "documento", "ambos"])
def test_espacos_de_cnpj_nao_mudam_a_versao_encontrada(coluna: str, lado: str) -> None:
    identidade = "00.000.000/0001-00"
    no_indice = f" \t{identidade} " if lado in ("indice", "ambos") else identidade
    no_documento = f" {identidade}\n" if lado in ("documento", "ambos") else identidade
    linhas = [
        {coluna: no_indice, "VERSAO": "1", "DT_RECEB": "2026-03-01"},
        {coluna: no_indice, "VERSAO": "2", "DT_RECEB": "2026-04-01"},
    ]
    documento = {coluna: no_documento, "VERSAO": "2"}
    assert proveniencia.entrega_no_indice(linhas, documento) == "2026-04-01"


@pytest.mark.parametrize(
    "identidade",
    ["00.000.000/0001-01", "00000000000100", "00.000.000/0001-00 extra"],
)
def test_cnpj_distinto_nao_e_aproximado(identidade: str) -> None:
    linhas = [{"CNPJ_CIA": " 00.000.000/0001-00 ", "DT_RECEB": "2026-03-01"}]
    assert proveniencia.entrega_no_indice(linhas, {"CNPJ_CIA": identidade}) is None


@pytest.mark.parametrize("campo", ["VERSAO", "DT_REFER"])
def test_espacos_em_outros_identificadores_nao_ganham_normalizacao(campo: str) -> None:
    linhas = [
        {"CNPJ_CIA": " 00.000.000/0001-00 ", campo: " 1 ", "DT_RECEB": "2026-03-01"}
    ]
    documento = {"CNPJ_CIA": "00.000.000/0001-00", campo: "1"}
    assert proveniencia.entrega_no_indice(linhas, documento) is None
