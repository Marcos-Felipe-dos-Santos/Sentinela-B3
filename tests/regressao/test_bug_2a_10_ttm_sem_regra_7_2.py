"""BUG-2A-10: o TTM lê o lucro dos controladores sem a regra 7.2 da ficha.

`cvm_provider.CVMProvider._acumulados_do_arquivo` lê a 3.11.01 direto pela tabela: linha
zerada entra como zero literal no acumulado. A decisão 7.2 (`docs/metodologia/por-acao.md`)
manda tratar controladora e não controladores zerados pela reserva com conferência do
balanço, ou abster; zero nunca. Origem: auditoria externa da Fase 2A (Gemini e Codex,
15/10/2026).
"""

import pytest

from cvm_provider import CVMProvider
from tests.test_cvm_series import CD_CVM, _zip

CONSOLIDADO = "Lucro/Prejuízo Consolidado do Período"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-10 · TTM lê o lucro dos controladores zerado sem a regra 7.2 · corrige: "
        "F2B-37"
    ),
)
def test_controladora_zerada_nao_entra_como_zero_no_acumulado(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    dt, ini = "2025-03-31", "2025-01-01"
    dre = [
        (dt, "1", "ÚLTIMO", ini, dt, "3.11", CONSOLIDADO, 100),
        (dt, "1", "ÚLTIMO", ini, dt, "3.11.01", "Atribuído a Sócios da Empresa Controladora", 0),
        (dt, "1", "ÚLTIMO", ini, dt, "3.11.02", "Atribuído a Sócios Não Controladores", 0),
    ]  # fmt: skip
    caminho = _zip(tmp_path / "itr.zip", "itr", 2025, dre, [])
    (acumulado,) = provider._acumulados_do_arquivo(caminho, "ITR", CD_CVM, "empresa")
    assert acumulado.valores["lucro_liquido"] == 100_000.0
    assert acumulado.valores["lucro_controladores"] != 0.0
