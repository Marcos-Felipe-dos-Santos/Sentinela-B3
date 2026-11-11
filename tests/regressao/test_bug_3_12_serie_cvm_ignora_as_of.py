"""BUG-3-12: o corte explícito deve prevalecer sobre o relógio da cascata.

Spec: F3-P13/FC2C-66R e decisão 09/11. São Paulo ainda está em 2023;
os documentos anuais de 2024/2025 não podem compor a série desse corte.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from apoio_escopo import de_empresa

from market_engine import MarketEngine
from tests.regressao.test_bug_2c_62_qualidade_produtor import fonte_anual
from tests.test_cvm_series import _Hoje


def test_serie_e_snapshot_nao_usam_exercicio_posterior_ao_corte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provedor = fonte_anual(tmp_path, monkeypatch)
    monkeypatch.setattr("market_engine.date", _Hoje)  # 13/10/2026
    motor = MarketEngine.__new__(MarketEngine)
    motor.cvm = provedor
    dados = de_empresa(
        {"ticker": "TSTA3", "cd_cvm": 9999, "preco_atual": 100, "especie": "ON"}
    )
    corte = datetime(2024, 1, 1, 2, tzinfo=UTC)  # 31/12/2023 em São Paulo
    assert motor._buscar_cvm("TSTA3", dados, as_of=corte)
    assert dados["serie_cvm"]["exercicios"][-1]["exercicio"] == 2023
    assert dados["lucro_liquido"] == -2
    assert dados["modelo_bpp_proveniencia"]["periodo_referencia"] == "2023-12-31"
