"""BUG-2A-14: Informe Mensal reapresentado escolhido sem desempate pela maior `Versao`.

`cvm_fii_provider.CVMFIIProvider.obter_dados_fii` ordena só por `Data_Referencia`; com duas
versões da mesma data, fica a primeira linha do arquivo, não a reapresentação. Origem:
auditoria externa da Fase 2A (Codex, 15/10/2026).
"""

import pytest

from cvm_fii_provider import CVMFIIProvider
from tests.test_cvm_fii_provider import _CNPJ_HGLG, _ROW_BASE, _make_inf_zip


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-14 · Informe reapresentado na mesma data sem desempate pela maior Versao "
        "· corrige: F2B-38"
    ),
)
def test_reapresentacao_da_mesma_data_prevalece(tmp_path, monkeypatch):
    provider = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    rows = [
        {**_ROW_BASE, "Versao": "1", "Valor_Patrimonial_Cotas": "180.0"},
        {**_ROW_BASE, "Versao": "2", "Valor_Patrimonial_Cotas": "190.0"},
    ]
    zip_path = _make_inf_zip(tmp_path / "inf_2024.zip", 2024, rows)
    monkeypatch.setattr(provider, "baixar_informe", lambda ano: zip_path)
    resultado = provider.obter_dados_fii(_CNPJ_HGLG)
    assert resultado["valor_cota"] == pytest.approx(190.0)
