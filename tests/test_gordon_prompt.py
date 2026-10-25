"""Rito dos dados: blocos documentais Gordon não entram no prompt livre."""

import pytest

from ai_core import SentinelaAI


@pytest.mark.parametrize(
    "campo", ["gordon_cvm", "gordon_diagnostico", "base_acionaria_gordon"]
)
def test_prompt_exclui_blocos_documentais_do_gordon(campo):
    ai = SentinelaAI.__new__(SentinelaAI)
    prompt = ai._formatar_dados(
        {"preco_atual": 10, campo: "conteudo_documental_excluido"}
    )
    assert "conteudo_documental_excluido" not in prompt
    assert campo not in prompt
    assert "preco_atual: 10" in prompt


@pytest.mark.parametrize("campo", ["bancos_diagnostico", "modelo_bpp_proveniencia"])
def test_prompt_exclui_diagnostico_da_lente_e_evidencia_do_bpp(campo):
    # F2B-32 (e F2B-4, a proveniência do BPP): o mesmo rito dos blocos do Gordon.
    ai = SentinelaAI.__new__(SentinelaAI)
    prompt = ai._formatar_dados(
        {"preco_atual": 10, campo: "conteudo_documental_excluido"}
    )
    assert "conteudo_documental_excluido" not in prompt
    assert campo not in prompt
