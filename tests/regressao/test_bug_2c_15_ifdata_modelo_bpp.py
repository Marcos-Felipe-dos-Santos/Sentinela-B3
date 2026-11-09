"""F2C-36: elegibilidade do contexto bancário segue BPP, não setor cadastral."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from market_engine import MarketEngine
from sentinela.data.providers.ifdata import Capital


@pytest.mark.parametrize(
    "setor,modelo,consultar",
    [
        ("Outros", "banco", True),
        ("Bancos", "empresa", False),
        ("Bancos", "seguradora", False),
        ("Bancos", None, False),
    ],
)
def test_ifdata_segue_modelo_documental(setor, modelo, consultar: bool) -> None:
    chamadas = []

    def capital(cnpj, data_referencia, *, as_of):
        chamadas.append((cnpj, data_referencia, as_of))
        return Capital(0.15, 0.02, "202606", "C0000001")

    motor = object.__new__(MarketEngine)
    motor.ifdata = SimpleNamespace(capital=capital)
    dados = {"setor": setor, "modelo_bpp": modelo, "cnpj": "11.111.111/0001-11"}
    motor._buscar_ifdata(dados, as_of=datetime(2026, 10, 26, 12, tzinfo=UTC))
    assert bool(chamadas) is consultar
    if consultar:
        assert dados["basileia"] == 0.15
        assert dados["inadimplencia"] == 0.02
    else:
        assert "ifdata" not in dados and "basileia" not in dados
