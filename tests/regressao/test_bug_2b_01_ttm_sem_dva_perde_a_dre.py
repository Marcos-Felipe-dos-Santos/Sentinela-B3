"""BUG-2B-01: um ITR sem DVA perde a DRE inteira no TTM.

`cvm_provider.CVMProvider._acumulados_do_arquivo` lê o `DVA_con` sem tratar arquivo
ausente; a exceção sobe até `acumulados_ttm`, que descarta o arquivo todo, inclusive o
lucro e a receita da DRE. Origem: F2B-21, pergunta 7 (1ª passada do Gemini, "DVA sem try").
"""

import zipfile

import pytest

from cvm_provider import CVMProvider
from tests.test_cvm_series import CD_CVM, CNPJ, COLUNAS


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-01 · ITR sem DVA perde a DRE inteira no TTM · corrige: a decidir no marcador",
)
def test_documento_sem_dva_mantem_a_dre(tmp_path):
    dt, ini = "2025-03-31", "2025-01-01"
    linha = [CNPJ, dt, "1", CD_CVM, "DF Consolidado", "MIL", "ÚLTIMO", ini, dt, "3.11",
             "Lucro/Prejuízo Consolidado do Período", 100]  # fmt: skip
    texto = ";".join(COLUNAS) + "\n" + ";".join(map(str, linha))
    caminho = tmp_path / "itr.zip"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("itr_cia_aberta_DRE_con_2025.csv", texto.encode("latin-1"))
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    (acumulado,) = provider._acumulados_do_arquivo(caminho, "ITR", CD_CVM, "empresa")
    assert acumulado.valores["lucro_liquido"] == 100_000.0
