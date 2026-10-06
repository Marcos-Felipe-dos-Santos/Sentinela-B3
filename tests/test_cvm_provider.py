import zipfile
from pathlib import Path

import pandas as pd
import pytest

from cvm_provider import _OUTPUT_COLS, CVMProvider

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
    """DataFrame retornado deve ter exatamente as 5 colunas especificadas. O valor testado com a base foi alterado para 500_000_000.0, porque a escala ESCALA_MOEDA MIL agora é aplicada corretamente, em vez de ignorada."""
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [_ROW_BASE])

    df = provider.parsear_demonstrativo(zip_path, "BPA_con")

    assert list(df.columns) == _OUTPUT_COLS
    assert len(df) == 1
    assert df.iloc[0]["CD_CONTA"] == "1"
    assert df.iloc[0]["VL_CONTA"] == pytest.approx(500_000_000.0)


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
    monkeypatch.setattr(provider, "parsear_demonstrativo", lambda path, tipo, include_cd_cvm=False: tipo_map[tipo])

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


# ---------------------------------------------------------------------------
# test_parser_aplica_escala_mil e test_parser_unico_sem_duplicata
# ---------------------------------------------------------------------------

def test_parser_aplica_escala_mil(tmp_path):
    """Se a ESCALA_MOEDA for MIL, o valor deve ser multiplicado por 1000."""
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [_ROW_BASE])

    df = provider.parsear_demonstrativo(zip_path, "BPA_con")

    assert len(df) == 1
    assert df.iloc[0]["VL_CONTA"] == pytest.approx(500_000_000.0)


def test_parser_unico_sem_duplicata(tmp_path):
    """O parser público deve ter o mesmo comportamento que o antigo privado (aceitar CD_CVM e escalar)."""
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [_ROW_BASE])

    assert not hasattr(provider, "_parsear_com_cvm"), "_parsear_com_cvm deve ser removido"

    df = provider.parsear_demonstrativo(zip_path, "BPA_con", include_cd_cvm=True)
    assert "CD_CVM" in df.columns
    assert df.iloc[0]["VL_CONTA"] == pytest.approx(500_000_000.0)

# ---------------------------------------------------------------------------
# Extra tests for better mutation coverage in _find_csv_name, _read_raw, parsear_demonstrativo
# ---------------------------------------------------------------------------

def test_find_csv_name_not_found_raises(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [_ROW_BASE])

    with pytest.raises(FileNotFoundError, match="Tipo 'DRE_con' não encontrado"):
        provider._find_csv_name(zip_path, "DRE_con")

def test_find_csv_name_wrong_extension(tmp_path):
    """Garante que if tipo in name and name.lower().endswith(".csv") é cumprido.
    Colocamos um arquivo com o tipo, mas que não termina em .csv."""
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = tmp_path / "dfp_2023_fake.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"dfp_cia_aberta_BPA_con_2023.txt", b"fake data")

    with pytest.raises(FileNotFoundError, match="Tipo 'BPA_con' não encontrado"):
        provider._find_csv_name(zip_path, "BPA_con")

def test_read_raw_low_memory(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [_ROW_BASE])

    df = provider._read_raw(zip_path, "BPA_con")
    assert not df.empty

def test_parsear_demonstrativo_na_handling(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    row_na = {**_ROW_BASE, "VL_CONTA": "xyz", "CD_CVM": "abc"}
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [row_na])

    df = provider.parsear_demonstrativo(zip_path, "BPA_con", include_cd_cvm=True)
    assert pd.isna(df.iloc[0]["VL_CONTA"])
    assert pd.isna(df.iloc[0]["CD_CVM"])

def test_parsear_demonstrativo_no_cd_cvm_or_escala_moeda(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    row_no_cd = _ROW_BASE.copy()
    del row_no_cd["CD_CVM"]
    del row_no_cd["ESCALA_MOEDA"]
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [row_no_cd])

    df = provider.parsear_demonstrativo(zip_path, "BPA_con", include_cd_cvm=True)
    assert "CD_CVM" not in df.columns
    assert df.iloc[0]["VL_CONTA"] == 500000.0  # Sem escala MIL

def test_parsear_demonstrativo_escala_moeda_outra(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    row_outra = {**_ROW_BASE, "ESCALA_MOEDA": "UNIDADE"}
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [row_outra])

    df = provider.parsear_demonstrativo(zip_path, "BPA_con")
    assert df.iloc[0]["VL_CONTA"] == 500000.0

def test_parsear_demonstrativo_grupo_dfp_na(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    row_na_grupo = {**_ROW_BASE}
    del row_na_grupo["GRUPO_DFP"]
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [row_na_grupo])

    df = provider.parsear_demonstrativo(zip_path, "BPA_con")
    assert len(df) == 1

def test_parsear_demonstrativo_grupo_dfp_none_or_nan(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    row_nan_grupo = {**_ROW_BASE, "GRUPO_DFP": ""}
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [row_nan_grupo])

    df = provider.parsear_demonstrativo(zip_path, "BPA_con")
    assert len(df) == 0


def test_parsear_demonstrativo_cd_cvm_typing(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    row_na = {**_ROW_BASE, "CD_CVM": "1234"}
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [row_na])

    df = provider.parsear_demonstrativo(zip_path, "BPA_con", include_cd_cvm=True)
    assert df["CD_CVM"].dtype.name == "Int64"
    assert df.iloc[0]["CD_CVM"] == 1234

def test_read_raw_separador_invalido(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [_ROW_BASE])

    # Sobrescrevemos read_csv do pandas no teste pra garantir que é chamado com os kwargs corretos
    import pandas as pd
    original_read_csv = pd.read_csv

    def mock_read_csv(*args, **kwargs):
        assert kwargs.get("sep") == ";"
        assert kwargs.get("low_memory") is False
        assert kwargs.get("dtype") is str
        return original_read_csv(*args, **kwargs)

    pd.read_csv = mock_read_csv
    try:
        df = provider._read_raw(zip_path, "BPA_con")
        assert not df.empty
    finally:
        pd.read_csv = original_read_csv

def test_read_raw_encoding_latin1(tmp_path):
    # Cifrão, acentos
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    row_encoding = {**_ROW_BASE, "DS_CONTA": "Ação de R$ 1,00"}
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [row_encoding])

    df = provider._read_raw(zip_path, "BPA_con")
    assert df.iloc[0]["DS_CONTA"] == "Ação de R$ 1,00"


def test_read_raw_encoding_latin1_capitalized(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    row_encoding = {**_ROW_BASE, "DS_CONTA": "Ação de R$ 1,00"}
    zip_path = _make_zip(tmp_path / "dfp_2023.zip", "BPA_con", [row_encoding])

    # Sobrescrevemos read_csv do pandas no teste pra garantir que é chamado com "latin-1" e não "LATIN-1"
    import pandas as pd
    import io
    original_read_csv = pd.read_csv

    def mock_read_csv(filepath_or_buffer, *args, **kwargs):
        assert isinstance(filepath_or_buffer, io.TextIOWrapper)
        assert filepath_or_buffer.encoding == "latin-1"
        return original_read_csv(filepath_or_buffer, *args, **kwargs)

    pd.read_csv = mock_read_csv
    try:
        df = provider._read_raw(zip_path, "BPA_con")
        assert not df.empty
    finally:
        pd.read_csv = original_read_csv
