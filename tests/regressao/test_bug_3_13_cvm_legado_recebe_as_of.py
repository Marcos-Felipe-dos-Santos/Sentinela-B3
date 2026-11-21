"""BUG-3-13: provedor com seleção anual antiga não recebe keyword nova.

Spec externa: aceite F3-P13 exige preservar provedores antigos. O ano escolhido
já é suficiente para o snapshot; a API antiga não declara as_of.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from apoio_escopo import de_empresa

from market_engine import MarketEngine
from tests.regressao.test_bug_2c_62_qualidade_produtor import fonte_anual
from tests.test_cvm_series import _Hoje


def test_snapshot_com_ano_escolhido_preserva_assinatura_antiga(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = fonte_anual(tmp_path, monkeypatch)
    original = p.calcular_indicadores

    def antigo(
        cd_cvm: int,
        anos: int = 5,
        modelo: str = "empresa",
        ano_final: int | None = None,
    ) -> dict:
        return original(cd_cvm, anos=anos, modelo=modelo, ano_final=ano_final)

    monkeypatch.setattr(p, "calcular_indicadores", antigo)
    monkeypatch.setattr("market_engine.date", _Hoje)
    m = MarketEngine.__new__(MarketEngine)
    m.cvm = p
    dados = de_empresa(
        {"ticker": "TSTA3", "cd_cvm": 9999, "preco_atual": 100, "especie": "ON"}
    )
    assert m._buscar_cvm("TSTA3", dados, as_of=datetime(2026, 10, 13, 12, tzinfo=UTC))
    assert dados["modelo_bpp_proveniencia"]["periodo_referencia"] == "2025-12-31"
