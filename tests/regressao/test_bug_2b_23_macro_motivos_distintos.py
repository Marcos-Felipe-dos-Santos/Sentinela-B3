"""Marcador §2.1: motivos distintos por insumo, antes do domínio (F2B-30)."""

from datetime import UTC, date, datetime

import pytest

from sentinela.data.providers import macro


@pytest.mark.parametrize(
    "valor,motivo",
    [
        (None, "insumo ausente"),
        (" ", "insumo ausente"),
        (True, "insumo inválido"),
        ("texto", "insumo inválido"),
        ("NaN", "NaN"),
        ("inf", "infinito"),
        (-100, "insumo fora do domínio"),
    ],
)
@pytest.mark.parametrize("insumo", ["IPCA", "PIB"])
def test_motivos_distintos_antes_do_dominio(valor, motivo, insumo):
    instante = datetime(2026, 10, 20, 15, tzinfo=UTC)
    with pytest.raises(ValueError) as erro:
        if insumo == "PIB":
            macro.pib_focus(
                [
                    {
                        "Indicador": "PIB Total",
                        "baseCalculo": 0,
                        "Data": "2026-10-16",
                        "DataReferencia": "2030",
                        "Mediana": valor,
                    }
                ],
                {date(2026, 10, 16): datetime(2026, 10, 19, 11, 30, tzinfo=UTC)},
                as_of=instante,
            )
        else:
            linhas = [
                {
                    "D1C": "1",
                    "D2C": "63",
                    "D3C": f"2025{m:02}",
                    "MN": "%",
                    "V": valor if m == 1 else "0",
                }
                for m in range(1, 13)
            ]
            macro.ipca_da_janela(
                linhas,
                {f"2025{m:02}": date(2026, 1, 9) for m in range(1, 13)},
                inicio=date(2025, 1, 1),
                fim=date(2025, 12, 31),
                as_of=instante,
            )
    assert motivo in str(erro.value)
    assert insumo in str(erro.value)
