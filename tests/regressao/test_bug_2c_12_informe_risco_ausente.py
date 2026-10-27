"""Contrato de disponibilidade do Informe: falha deve integrar os riscos."""

from types import SimpleNamespace

import pytest

from market_engine import MarketEngine


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2C-12 · falha do Informe sem riscos_dados · corrige: F2C-51 (2C-b)",
)
def test_falha_do_informe_preserva_motivo_nos_riscos() -> None:
    def indisponivel(cnpj: str) -> dict:
        raise OSError("fonte indisponível")

    motor = object.__new__(MarketEngine)
    motor._is_fii_ticker = lambda *args: True
    motor.cvm_fii = SimpleNamespace(obter_rendimentos_fii=indisponivel)
    dados = {"cnpj": "11.111.111/0001-11", "classe_ativo": "FII"}
    motor._buscar_rendimento_fii("TSTF11", dados)
    assert "fonte indisponível" in dados["informe_fii"]["abstencao"]
    assert any("Informe" in risco for risco in dados.get("riscos_dados", []))
