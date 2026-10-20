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
