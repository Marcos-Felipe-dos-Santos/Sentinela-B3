"""BUG-2C-04: fluxo de empresa é aceito com balanço que demonstra modelo banco.

D20 e F2C-29/30: não reconciliar perímetros/modelos por presunção. Pares oficiais
CVM2.07/PL de banco e DRE de empresa; dados sintéticos, sem rede.
"""

import zipfile
from dataclasses import replace
from datetime import date

from cvm_provider import CVMProvider
from sentinela.data import series_cvm
from tests.regressao.test_bug_2c_03_ttm_bpp_nao_demonstrado import DT, documento
from tests.test_cvm_series import CD_CVM, CNPJ, COLUNAS


def test_modelo_incompativel_abstem_os_campos_do_documento(tmp_path):
    caminho = documento(tmp_path, "ausente", 80)
    linha = [
        CNPJ,
        DT,
        "1",
        CD_CVM,
        "DF Consolidado",
        "MIL",
        "ÚLTIMO",
        DT,
        DT,
        "2.07",
        "Patrimônio Líquido Consolidado",
        50,
    ]
    texto = ";".join(COLUNAS) + "\n" + ";".join(map(str, linha))
    with zipfile.ZipFile(caminho, "a") as zf:
        zf.writestr("itr_cia_aberta_BPP_con_2025.csv", texto.encode("latin-1"))
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    (a,) = provider._acumulados_do_arquivo(caminho, "ITR", CD_CVM, "empresa")
    assert all(v is None for v in a.valores.values())
    assert all("modelo" in a.motivos[c] for c in a.valores)
    assert a.proveniencia["lucro_controladores"]["reserva"] is None
    bons = [
        replace(
            a,
            dt_refer=dt,
            inicio=date(2025, 1, 1),
            fim=date.fromisoformat(dt),
            valores=dict.fromkeys(a.valores, float(i * 100_000)),
            motivos={},
            proveniencia={},
        )
        for i, dt in enumerate(["2025-06-30", "2025-09-30", "2025-12-31"], 2)
    ]
    ttm = series_cvm.ttm([a, *bons], date(2025, 12, 31))
    assert ttm["valores"]["lucro_liquido"] is None
    assert "modelo" in ttm["motivos"]["lucro_liquido"]
    assert ttm["proveniencia"]["lucro_liquido"][0]["demonstrativo"] == "DRE_con"
    assert ttm["proveniencia"]["lucro_liquido"][0]["versao"] == 1
    assert ttm["proveniencia"]["lucro_liquido"][0]["dt_refer"] == DT
    assert "modelo" in ttm["proveniencia"]["lucro_liquido"][0]["motivo"]
