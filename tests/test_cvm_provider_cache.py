import os
import threading
import time
import zipfile
from pathlib import Path

import pandas as pd
import pytest

import cvm_provider
from cvm_provider import CVMProvider


@pytest.fixture(autouse=True)
def _cache_limpo():
    cvm_provider._cache_parse.clear()
    yield
    cvm_provider._cache_parse.clear()


def _zip(dest: Path, vl: str) -> Path:
    linha = {
        "CNPJ_CIA": "00.000.000/0001-00",
        "DT_REFER": "2023-12-31",
        "VERSAO": "1",
        "CD_CVM": "1",
        "GRUPO_DFP": "DF Consolidado - Balanço Patrimonial Ativo",
        "ESCALA_MOEDA": "UNIDADE",
        "ORDEM_EXERC": "ÚLTIMO",
        "CD_CONTA": "1",
        "DS_CONTA": "Ativo Total",
        "VL_CONTA": vl,
    }
    csv = pd.DataFrame([linha]).to_csv(sep=";", index=False).encode("latin-1")
    with zipfile.ZipFile(dest, "w") as zf:
        zf.writestr("dfp_cia_aberta_BPA_con_2023.csv", csv)
    return dest


def _contar_leituras(monkeypatch, provider, pausa=0.0):
    chamadas = []
    original = provider._read_raw

    def lendo(zip_path, tipo):
        chamadas.append(tipo)
        time.sleep(pausa)
        return original(zip_path, tipo)

    monkeypatch.setattr(provider, "_read_raw", lendo)
    return chamadas


def test_segunda_leitura_nao_rele_o_csv(tmp_path, monkeypatch):
    provider = CVMProvider(cache_dir=str(tmp_path))
    zip_path = _zip(tmp_path / "dfp_2023.zip", "100")
    chamadas = _contar_leituras(monkeypatch, provider)

    primeiro = provider.parsear_demonstrativo(zip_path, "BPA_con")
    primeiro.loc[0, "VL_CONTA"] = -1.0  # mutar a cópia não pode sujar o cache
    segundo = provider.parsear_demonstrativo(zip_path, "BPA_con")

    assert len(chamadas) == 1
    assert segundo.loc[0, "VL_CONTA"] == 100.0


def test_leituras_concorrentes_leem_o_arquivo_uma_vez(tmp_path, monkeypatch):
    provider = CVMProvider(cache_dir=str(tmp_path))
    zip_path = _zip(tmp_path / "dfp_2023.zip", "100")
    chamadas = _contar_leituras(monkeypatch, provider, pausa=0.1)
    fios = [
        threading.Thread(
            target=provider.parsear_demonstrativo, args=(zip_path, "BPA_con")
        )
        for _ in range(6)
    ]
    for f in fios:
        f.start()
    for f in fios:
        f.join()
    assert len(chamadas) == 1


def test_flags_diferentes_nao_compartilham_entrada(tmp_path, monkeypatch):
    provider = CVMProvider(cache_dir=str(tmp_path))
    zip_path = _zip(tmp_path / "dfp_2023.zip", "100")
    chamadas = _contar_leituras(monkeypatch, provider)
    sem = provider.parsear_demonstrativo(zip_path, "BPA_con")
    com = provider.parsear_demonstrativo(zip_path, "BPA_con", include_cd_cvm=True)
    assert "CD_CVM" not in sem.columns
    assert "CD_CVM" in com.columns
    assert len(chamadas) == 2


def test_zip_novo_invalida_o_cache(tmp_path, monkeypatch):
    provider = CVMProvider(cache_dir=str(tmp_path))
    zip_path = _zip(tmp_path / "dfp_2023.zip", "100")
    chamadas = _contar_leituras(monkeypatch, provider)
    assert (
        provider.parsear_demonstrativo(zip_path, "BPA_con").loc[0, "VL_CONTA"] == 100.0
    )

    _zip(zip_path, "250")
    stat = zip_path.stat()
    os.utime(zip_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000_000))

    assert (
        provider.parsear_demonstrativo(zip_path, "BPA_con").loc[0, "VL_CONTA"] == 250.0
    )
    assert len(chamadas) == 2


def test_excecao_nao_fica_no_cache(tmp_path, monkeypatch):
    provider = CVMProvider(cache_dir=str(tmp_path))
    zip_path = _zip(tmp_path / "dfp_2023.zip", "100")
    chamadas = _contar_leituras(monkeypatch, provider)
    for _ in range(2):
        try:
            provider.parsear_demonstrativo(zip_path, "DRE_con")
        except FileNotFoundError:
            continue
        raise AssertionError("esperava FileNotFoundError")
    assert len(chamadas) == 2


def test_limite_de_entradas(tmp_path, monkeypatch):
    monkeypatch.setattr(cvm_provider, "_CACHE_MAX_ENTRADAS", 2)
    provider = CVMProvider(cache_dir=str(tmp_path))
    zips = [_zip(tmp_path / f"dfp_{i}.zip", "100") for i in range(3)]
    for z in zips:
        provider.parsear_demonstrativo(z, "BPA_con")
    chamadas = _contar_leituras(monkeypatch, provider)
    provider.parsear_demonstrativo(zips[0], "BPA_con")  # a mais antiga saiu
    provider.parsear_demonstrativo(zips[2], "BPA_con")  # a mais nova ficou
    assert len(chamadas) == 1


@pytest.mark.parametrize("periodo_primeiro", [False, True])
def test_periodo_compartilha_leitura_preservando_projecoes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, periodo_primeiro: bool
) -> None:
    """F2C-13: memoizar não muda os campos declarados no CSV sintético."""
    provider = CVMProvider(cache_dir=str(tmp_path))
    caminho = tmp_path / "periodos.zip"
    linhas = [
        ["00.000.000/0001-00", "2025-12-31", "2", "7", "DF Consolidado",
         "MIL", "ÚLTIMO", "2025-01-01", "2025-12-31", "3.11", "Lucro", "123"],
        ["00.000.000/0001-00", "2025-12-31", "1", "7", "DF Consolidado",
         "MIL", "PENÚLTIMO", "2024-01-01", "2024-12-31", "3.11", "Lucro", "99"],
    ]  # fmt: skip
    colunas = [
        "CNPJ_CIA", "DT_REFER", "VERSAO", "CD_CVM", "GRUPO_DFP", "ESCALA_MOEDA",
        "ORDEM_EXERC", "DT_INI_EXERC", "DT_FIM_EXERC", "CD_CONTA", "DS_CONTA", "VL_CONTA",
    ]  # fmt: skip
    with zipfile.ZipFile(caminho, "w") as arquivo:
        arquivo.writestr(
            "dfp_cia_aberta_DRE_con_2025.csv",
            pd.DataFrame(linhas, columns=colunas)
            .to_csv(sep=";", index=False)
            .encode("latin-1"),
        )
    chamadas = _contar_leituras(monkeypatch, provider)
    opcoes = {"include_cd_cvm": True, "include_versao": True}
    primeiro = provider.parsear_demonstrativo(
        caminho, "DRE_con", **opcoes, include_periodo=periodo_primeiro
    )
    segundo = provider.parsear_demonstrativo(
        caminho, "DRE_con", **opcoes, include_periodo=not periodo_primeiro
    )
    sem, com = (segundo, primeiro) if periodo_primeiro else (primeiro, segundo)
    assert chamadas == ["DRE_con"]
    assert len(cvm_provider._cache_parse) == 1
    assert list(sem.columns) == [
        "CNPJ_CIA",
        "DT_REFER",
        "CD_CONTA",
        "DS_CONTA",
        "VL_CONTA",
        "CD_CVM",
        "VERSAO",
    ]
    assert list(com.columns) == [*sem.columns, "DT_INI_EXERC", "DT_FIM_EXERC"]
    assert len(com) == 1
    assert com.iloc[0].to_dict() == {
        "CNPJ_CIA": "00.000.000/0001-00",
        "DT_REFER": "2025-12-31",
        "CD_CONTA": "3.11",
        "DS_CONTA": "Lucro",
        "VL_CONTA": 123000,
        "CD_CVM": 7,
        "VERSAO": "2",
        "DT_INI_EXERC": "2025-01-01",
        "DT_FIM_EXERC": "2025-12-31",
    }
    pd.testing.assert_frame_equal(sem, com.loc[:, sem.columns])
    com.loc[0, "DT_INI_EXERC"] = "alterado"
    sem.loc[0, "VL_CONTA"] = -1
    preservado = provider.parsear_demonstrativo(
        caminho, "DRE_con", **opcoes, include_periodo=True
    )
    assert preservado.loc[0, "VL_CONTA"] == 123000
    assert preservado.loc[0, "DT_INI_EXERC"] == "2025-01-01"
