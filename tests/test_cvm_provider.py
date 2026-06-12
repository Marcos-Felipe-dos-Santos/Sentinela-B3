import zipfile
from pathlib import Path

import pandas as pd
import pytest

from cvm_provider import CVMProvider, _OUTPUT_COLS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_zip(dest: Path, tipo: str, rows: list[dict]) -> Path:
    """Cria um ZIP com um CSV fake do tipo indicado."""
    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(sep=";", index=False, encoding="latin-1").encode("latin-1")
    with zipfile.ZipFile(dest, "w") as zf:
        zf.writestr(f"dfp_cia_aberta_{tipo}_2023.csv", csv_bytes)
    return dest


_ROW_BASE = {
    "CNPJ_CIA":             "33.000.167/0001-01",
    "DT_REFER":             "2023-12-31",
    "VERSAO":               "1",
    "DENOM_CIA":            "PETROLEO BRASILEIRO S.A.",
    "CD_CVM":               "9512",
    "GRUPO_DFP":            "DF Consolidado - Balanço Patrimonial Ativo",
    "MOEDA":                "REAL",
    "ESCALA_MOEDA":         "MIL",
    "ORDEM_EXERC":          "ÚLTIMO",
    "DT_INI_EXERC":         "2023-01-01",
    "DT_FIM_EXERC":         "2023-12-31",
    "CD_CONTA":             "1",
    "DS_CONTA":             "Ativo Total",
    "VL_CONTA":             "500000",
    "ST_CONTA_FIXED_ASSETS": "0",
}


# ---------------------------------------------------------------------------
# test_parsear_demonstrativo_formato
# ---------------------------------------------------------------------------

def test_parsear_demonstrativo_formato(tmp_path):
    """DataFrame retornado deve ter exatamente as 5 colunas especificadas."""
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [_ROW_BASE])

    df = provider.parsear_demonstrativo(zip_path, "BPA_con")

    assert list(df.columns) == _OUTPUT_COLS
    assert len(df) == 1
    assert df.iloc[0]["CD_CONTA"] == "1"
    assert df.iloc[0]["VL_CONTA"] == pytest.approx(500_000.0)


def test_parsear_demonstrativo_filtra_ordem_exerc(tmp_path):
    """Apenas ORDEM_EXERC == 'ÚLTIMO' deve sobrar."""
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    rows = [
        {**_ROW_BASE, "ORDEM_EXERC": "ÚLTIMO",    "CD_CONTA": "1"},
        {**_ROW_BASE, "ORDEM_EXERC": "PENÚLTIMO", "CD_CONTA": "1.01"},
    ]
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", rows)

    df = provider.parsear_demonstrativo(zip_path, "BPA_con")

    assert len(df) == 1
    assert df.iloc[0]["CD_CONTA"] == "1"


def test_parsear_demonstrativo_filtra_grupo_dfp(tmp_path):
    """Apenas linhas com 'Consolidado' em GRUPO_DFP devem sobrar."""
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    rows = [
        {**_ROW_BASE, "GRUPO_DFP": "DF Consolidado - Balanço Patrimonial Ativo", "CD_CONTA": "1"},
        {**_ROW_BASE, "GRUPO_DFP": "DF Individual - Balanço Patrimonial Ativo",  "CD_CONTA": "1.01"},
    ]
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", rows)

    df = provider.parsear_demonstrativo(zip_path, "BPA_con")

    assert len(df) == 1
    assert df.iloc[0]["CD_CONTA"] == "1"


# ---------------------------------------------------------------------------
# test_calcular_indicadores_mock
# ---------------------------------------------------------------------------

def test_calcular_indicadores_mock(tmp_path, monkeypatch):
    """ROE calculado deve ser exatamente lucro_liquido / patrimonio_liquido."""
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))

    lucro = 60_000.0
    pl    = 300_000.0

    bpa_df = pd.DataFrame([{
        "CD_CVM": 9512, "CD_CONTA": "1",
        "DS_CONTA": "Ativo Total", "VL_CONTA": 1_000_000.0,
        "CNPJ_CIA": "33.000.167/0001-01", "DT_REFER": "2023-12-31",
    }])
    bpp_df = pd.DataFrame([
        {"CD_CVM": 9512, "CD_CONTA": "2",    "DS_CONTA": "Passivo Total",
         "VL_CONTA": 700_000.0, "CNPJ_CIA": "33.000.167/0001-01", "DT_REFER": "2023-12-31"},
        {"CD_CVM": 9512, "CD_CONTA": "2.01", "DS_CONTA": "Passivo Circulante",
         "VL_CONTA": 200_000.0, "CNPJ_CIA": "33.000.167/0001-01", "DT_REFER": "2023-12-31"},
        {"CD_CVM": 9512, "CD_CONTA": "2.03", "DS_CONTA": "Patrimônio Líquido",
         "VL_CONTA": pl,        "CNPJ_CIA": "33.000.167/0001-01", "DT_REFER": "2023-12-31"},
    ])
    dre_df = pd.DataFrame([
        {"CD_CVM": 9512, "CD_CONTA": "3.01", "DS_CONTA": "Receita",
         "VL_CONTA": 500_000.0, "CNPJ_CIA": "33.000.167/0001-01", "DT_REFER": "2023-12-31"},
        {"CD_CVM": 9512, "CD_CONTA": "3.05", "DS_CONTA": "EBIT",
         "VL_CONTA": 90_000.0,  "CNPJ_CIA": "33.000.167/0001-01", "DT_REFER": "2023-12-31"},
        {"CD_CVM": 9512, "CD_CONTA": "3.11", "DS_CONTA": "Lucro Líquido",
         "VL_CONTA": lucro,     "CNPJ_CIA": "33.000.167/0001-01", "DT_REFER": "2023-12-31"},
    ])

    tipo_map = {"BPA_con": bpa_df, "BPP_con": bpp_df, "DRE_con": dre_df}

    monkeypatch.setattr(provider, "baixar_dfp",       lambda ano: tmp_path / "fake.zip")
    monkeypatch.setattr(provider, "_parsear_com_cvm", lambda path, tipo: tipo_map[tipo])

    resultado = provider.calcular_indicadores(9512, anos=1)

    assert len(resultado) == 1
    ind = next(iter(resultado.values()))

    assert ind["patrimonio_liquido"] == pytest.approx(pl)
    assert ind["lucro_liquido"]      == pytest.approx(lucro)
    assert ind["roe"]                == pytest.approx(lucro / pl)
    assert ind["margem_liquida"]     == pytest.approx(lucro / 500_000.0)
    assert ind["divida_pl"]          == pytest.approx((700_000.0 - pl) / pl)


# ---------------------------------------------------------------------------
# test_cache_nao_rebaixa
# ---------------------------------------------------------------------------

def test_cache_nao_rebaixa(tmp_path, monkeypatch):
    """O segundo download do mesmo arquivo não deve fazer nova requisição HTTP."""
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))

    call_count = {"n": 0}

    class FakeResponse:
        content = b"fake-zip-content"

        def raise_for_status(self):
            pass

    def fake_get(url, **kwargs):
        call_count["n"] += 1
        return FakeResponse()

    monkeypatch.setattr("cvm_provider.requests.get", fake_get)

    p1 = provider.baixar_dfp(2023)
    p2 = provider.baixar_dfp(2023)

    assert p1 == p2
    assert p1.exists()
    assert call_count["n"] == 1  # segundo download usou cache
