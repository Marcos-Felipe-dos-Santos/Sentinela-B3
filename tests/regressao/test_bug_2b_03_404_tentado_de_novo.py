"""BUG-2B-03: o download tenta de novo um HTTP 404 (erro permanente).

`cvm_download.baixar_arquivo` repete três vezes, com espera de 1 s e 2 s, qualquer
`RequestException`, inclusive o 404 de um mês do COTAHIST que não existe. Nenhum número
muda; é custo. Origem: F2B-21, pergunta 7 (1ª passada do Gemini).
"""

from unittest.mock import MagicMock

import pytest
import requests

import cvm_download


def test_404_nao_e_tentado_de_novo(tmp_path, monkeypatch):
    erro = requests.HTTPError("404 Client Error: Not Found")
    erro.response = MagicMock(status_code=404)
    resposta = MagicMock()
    resposta.__enter__.return_value = resposta
    resposta.raise_for_status.side_effect = erro
    get = MagicMock(return_value=resposta)
    monkeypatch.setattr(cvm_download.requests, "get", get)
    sleep = MagicMock()
    monkeypatch.setattr(cvm_download.time, "sleep", sleep)
    with pytest.raises(requests.RequestException):
        cvm_download.baixar_arquivo(
            "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2099.ZIP",
            tmp_path / "ausente.zip",
        )
    assert get.call_count == 1
    sleep.assert_not_called()
