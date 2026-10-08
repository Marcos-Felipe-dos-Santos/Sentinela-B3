import os
import zipfile
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
