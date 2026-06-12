import zipfile
from pathlib import Path

import pandas as pd
import pytest

from cvm_fii_map import FII_CNPJ_MAP, get_cnpj_fii, get_ticker_fii
from cvm_fii_provider import CVMFIIProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_inf_zip(dest: Path, ano: int, rows: list[dict]) -> Path:
    """Cria ZIP com CSV fake do informe mensal FII complemento."""
    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(sep=";", index=False, encoding="latin-1").encode("latin-1")
    with zipfile.ZipFile(dest, "w") as zf:
        zf.writestr(f"inf_mensal_fii_complemento_{ano}.csv", csv_bytes)
    return dest


_CNPJ_HGLG = "11.728.688/0001-47"

_ROW_BASE = {
    "CNPJ_Fundo_Classe":            _CNPJ_HGLG,
    "Data_Referencia":              "2024-11-01",
    "Versao":                       "1",
    "Total_Numero_Cotistas":        "85000",
    "Valor_Ativo":                  "2000000000",
    "Patrimonio_Liquido":           "1800000000",
    "Cotas_Emitidas":               "10000000",
    "Valor_Patrimonial_Cotas":      "180.0",
    "Percentual_Despesas_Taxa_Administracao": "0.000196",
    "Percentual_Rentabilidade_Efetiva_Mes":   "0.002166",
    "Percentual_Dividend_Yield_Mes":          "0.005723",
    "Percentual_Amortizacao_Cotas_Mes":       "0",
}


# ---------------------------------------------------------------------------
# cvm_fii_map
# ---------------------------------------------------------------------------

def test_mapa_hglg11_cnpj():
    assert get_cnpj_fii("HGLG11") == "11.728.688/0001-47"


def test_mapa_mxrf11_cnpj():
    assert get_cnpj_fii("MXRF11") == "97.521.225/0001-25"


def test_mapa_ticker_desconhecido_retorna_none():
    assert get_cnpj_fii("ZZZZ99") is None


def test_mapa_roundtrip_hglg11():
    cnpj = get_cnpj_fii("HGLG11")
    assert get_ticker_fii(cnpj) == "HGLG11"


def test_mapa_cobre_30_fiis():
    assert len(FII_CNPJ_MAP) == 30


# ---------------------------------------------------------------------------
# CVMFIIProvider — parse e obter_dados_fii
# ---------------------------------------------------------------------------

def test_parsear_complemento_formato(tmp_path):
    """DataFrame interno deve ter as colunas reais do informe mensal."""
    provider = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_inf_zip(tmp_path / "inf_2024.zip", 2024, [_ROW_BASE])

    df = provider._parsear_complemento(zip_path, 2024)

    assert "CNPJ_Fundo_Classe" in df.columns
    assert "Patrimonio_Liquido" in df.columns
    assert "Valor_Patrimonial_Cotas" in df.columns
    assert "Cotas_Emitidas" in df.columns
    assert len(df) == 1


def test_obter_dados_fii_vpa(tmp_path, monkeypatch):
    """obter_dados_fii deve retornar valor_cota (VPA) correto."""
    provider = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_inf_zip(tmp_path / "inf_2024.zip", 2024, [_ROW_BASE])

    monkeypatch.setattr(provider, "baixar_informe", lambda ano: zip_path)

    result = provider.obter_dados_fii(_CNPJ_HGLG)

    assert result is not None
    assert result["valor_cota"] == pytest.approx(180.0)
    assert result["patrimonio_liquido"] == pytest.approx(1_800_000_000.0)
    assert result["cotas_emitidas"] == pytest.approx(10_000_000.0)
    assert result["vacancia_fisica"] is None  # não disponível no informe mensal


def test_obter_dados_fii_cnpj_nao_encontrado(tmp_path, monkeypatch):
    """CNPJ ausente no CSV deve retornar None."""
    provider = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_inf_zip(tmp_path / "inf_2024.zip", 2024, [_ROW_BASE])
    monkeypatch.setattr(provider, "baixar_informe", lambda ano: zip_path)

    result = provider.obter_dados_fii("99.999.999/0001-99")
    assert result is None


def test_obter_dados_fii_retorna_mais_recente(tmp_path, monkeypatch):
    """Deve retornar o registro com Data_Referencia mais recente."""
    provider = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    rows = [
        {**_ROW_BASE, "Data_Referencia": "2024-01-01", "Valor_Patrimonial_Cotas": "170.0"},
        {**_ROW_BASE, "Data_Referencia": "2024-11-01", "Valor_Patrimonial_Cotas": "180.0"},
        {**_ROW_BASE, "Data_Referencia": "2024-06-01", "Valor_Patrimonial_Cotas": "175.0"},
    ]
    zip_path = _make_inf_zip(tmp_path / "inf_2024.zip", 2024, rows)
    monkeypatch.setattr(provider, "baixar_informe", lambda ano: zip_path)

    result = provider.obter_dados_fii(_CNPJ_HGLG)
    assert result["valor_cota"] == pytest.approx(180.0)


def test_cache_nao_rebaixa_fii(tmp_path, monkeypatch):
    """Segundo baixar_informe deve usar cache sem chamada HTTP."""
    provider = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    call_count = {"n": 0}

    class FakeResp:
        content = b"fake-zip"
        def raise_for_status(self): pass

    monkeypatch.setattr("cvm_fii_provider.requests.get",
                        lambda *a, **kw: (call_count.__setitem__("n", call_count["n"] + 1) or FakeResp()))

    p1 = provider.baixar_informe(2024)
    p2 = provider.baixar_informe(2024)

    assert p1 == p2
    assert call_count["n"] == 1
