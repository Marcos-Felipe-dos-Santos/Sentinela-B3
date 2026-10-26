"""BUG-2B-02: o mesmo demonstrativo é lido e guardado duas vezes (série e TTM).

`cvm_provider.CVMProvider.parsear_demonstrativo` guarda uma projeção por combinação de
parâmetros: o `DRE_con` da DFP lido sem e com `include_periodo` é aberto duas vezes e fica
duas vezes no cache (5,2 MB e 7,0 MB na DFP 2025). Nenhum número muda; é custo. Origem:
F2B-21, pergunta 7 (1ª passada do Gemini, "cache duplicado entre série e TTM").
"""

import zipfile

import pytest

from cvm_provider import CVMProvider
from tests.test_cvm_series import CD_CVM, CNPJ, COLUNAS


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-02 · demonstrativo lido duas vezes para a série e o TTM · corrige: F2C-13",
)
def test_mesmo_demonstrativo_e_lido_uma_vez(tmp_path, monkeypatch):
    dt, ini = "2025-12-31", "2025-01-01"
    linha = [CNPJ, dt, "1", CD_CVM, "DF Consolidado", "MIL", "ÚLTIMO", ini, dt, "3.11",
             "Lucro/Prejuízo Consolidado do Período", 100]  # fmt: skip
    caminho = tmp_path / "dfp.zip"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr(
            "dfp_cia_aberta_DRE_con_2025.csv",
            (";".join(COLUNAS) + "\n" + ";".join(map(str, linha))).encode("latin-1"),
        )
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    leituras = []
    original = provider._read_raw

    def contar(zip_path, tipo):
        leituras.append(tipo)
        return original(zip_path, tipo)

    monkeypatch.setattr(provider, "_read_raw", contar)
    opcoes = {"include_cd_cvm": True, "include_versao": True}
    provider.parsear_demonstrativo(caminho, "DRE_con", **opcoes)
    provider.parsear_demonstrativo(caminho, "DRE_con", **opcoes, include_periodo=True)
    assert leituras == ["DRE_con"]
