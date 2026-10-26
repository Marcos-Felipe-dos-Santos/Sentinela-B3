import os
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from cvm_download import baixar_arquivo


@pytest.fixture
def mock_sleep(monkeypatch):
    import time
    sleeps = []
    def fake_sleep(x):
        sleeps.append(x)
    monkeypatch.setattr(time, "sleep", fake_sleep)
    return sleeps

def test_zip_corrompido_nao_substitui_cache(tmp_path):
    dest = tmp_path / "arquivo.zip"

    with zipfile.ZipFile(dest, 'w') as zf:
        zf.writestr("test.csv", "valid data")
    os.utime(dest, (0, 0))

    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.iter_content.return_value = [b"isso nao e um zip"]
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(zipfile.BadZipFile):
            baixar_arquivo("http://fake.url", dest)

    with zipfile.ZipFile(dest, 'r') as zf:
        assert zf.read("test.csv") == b"valid data"

def test_download_interrompido_nao_deixa_destino_parcial(tmp_path, mock_sleep):
    dest = tmp_path / "arquivo.zip"

    # Com o novo código (iter_content), vamos simular iter_content falhando
    mock_response = MagicMock()
    def mock_iter_content(*args, **kwargs):
        yield b"partial data"
        raise requests.ConnectionError("Interrupted")

    mock_response.iter_content = mock_iter_content
    mock_response.__enter__.return_value = mock_response
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(requests.ConnectionError):
            baixar_arquivo("http://fake.url", dest)

    assert not dest.exists()
    assert not dest.with_suffix('.tmp').exists()

def test_retry_com_backoff(tmp_path, mock_sleep):
    dest = tmp_path / "arquivo.zip"

    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

    with patch("requests.get", return_value=mock_response) as mock_get:
        with pytest.raises(requests.HTTPError):
            baixar_arquivo("http://fake.url", dest)

        assert mock_get.call_count == 3
        assert mock_sleep == [1, 2]


@pytest.mark.parametrize("status", [429, 500, 503])
def test_erro_transitorio_com_resposta_preserva_tentativas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """F2C-14: só o 404 modifica a política anterior de retentativa."""
    erro = requests.HTTPError(str(status))
    erro.response = requests.Response()
    erro.response.status_code = status
    resposta = MagicMock()
    resposta.__enter__.return_value = resposta
    resposta.raise_for_status.side_effect = erro
    get = MagicMock(return_value=resposta)
    sleep = MagicMock()
    monkeypatch.setattr("cvm_download.requests.get", get)
    monkeypatch.setattr("cvm_download.time.sleep", sleep)
    with pytest.raises(requests.HTTPError) as capturado:
        baixar_arquivo("https://fonte.invalid/dfp.zip", tmp_path / "dfp.zip")
    assert capturado.value is erro
    assert get.call_count == 3
    assert [chamada.args[0] for chamada in sleep.call_args_list] == [1, 2]


def test_404_preserva_cache_antigo_e_limpa_temporario(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O erro permanente não substitui arquivo válido nem retém download parcial."""
    destino = tmp_path / "dfp.zip"
    with zipfile.ZipFile(destino, "w") as arquivo:
        arquivo.writestr("dados.csv", "oficial")
    original = destino.read_bytes()
    os.utime(destino, (0, 0))
    temporario = destino.with_suffix(".tmp")
    temporario.write_bytes(b"parcial")
    erro = requests.HTTPError("ausente")
    erro.response = requests.Response()
    erro.response.status_code = 404
    resposta = MagicMock()
    resposta.__enter__.return_value = resposta
    resposta.raise_for_status.side_effect = erro
    get = MagicMock(return_value=resposta)
    sleep = MagicMock()
    monkeypatch.setattr("cvm_download.requests.get", get)
    monkeypatch.setattr("cvm_download.time.sleep", sleep)
    with pytest.raises(requests.HTTPError) as capturado:
        baixar_arquivo("https://fonte.invalid/dfp.zip", destino)
    assert capturado.value is erro
    assert get.call_count == 1
    sleep.assert_not_called()
    assert destino.read_bytes() == original
    assert not temporario.exists()


def test_download_transitorio_se_recupera_sem_nova_tentativa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ZIP íntegro após uma falha preserva a política e a substituição atômica."""
    import io

    conteudo = io.BytesIO()
    with zipfile.ZipFile(conteudo, "w") as arquivo:
        arquivo.writestr("dados.csv", "oficial")
    resposta = MagicMock()
    resposta.__enter__.return_value = resposta
    resposta.iter_content.return_value = [b"", conteudo.getvalue()]
    get = MagicMock(side_effect=[requests.ConnectionError("transitório"), resposta])
    sleep = MagicMock()
    monkeypatch.setattr("cvm_download.requests.get", get)
    monkeypatch.setattr("cvm_download.time.sleep", sleep)
    destino = tmp_path / "dfp.zip"
    assert baixar_arquivo("https://fonte.invalid/dfp.zip", destino) == destino
    assert get.call_count == 2
    sleep.assert_called_once_with(1)
    assert destino.read_bytes() == conteudo.getvalue()
    assert not destino.with_suffix(".tmp").exists()
