"""BUG-2B-36: o rendimento de 12 meses do FII sai infinito com entradas finitas.

Achado da 2ª auditoria FASE do Codex (20/10/2026): com 13 meses, DY mensal 1e308, valor da
cota 10 e preço 10, `rendimento_12_meses` devolvia `rendimento_12m=inf` e `dy=inf`. Produto,
soma ou divisão não finitos devem abster com motivo, sem infinito na saída.
"""

import pytest

from sentinela.data import rendimento_fii


def _registros(dy):
    meses = [
        f"{ano}-{mes:02d}-01"
        for ano, mes in [(2025, 9)]
        + [(2025, m) for m in (10, 11, 12)]
        + [(2026, m) for m in range(1, 10)]
    ]
    return [
        {
            "Data_Referencia": mes,
            "Versao": "1",
            "Valor_Patrimonial_Cotas": "10",
            "Percentual_Dividend_Yield_Mes": None if i == 0 else dy,
        }
        for i, mes in enumerate(meses)
    ]


@pytest.mark.parametrize(("dy", "preco"), [("1e308", 10), ("1e300", 1e-300)])
def test_resultado_nao_finito_abstem(dy, preco):
    resultado = rendimento_fii.rendimento_12_meses(_registros(dy), preco)
    assert isinstance(resultado, rendimento_fii.Abstencao), resultado
    assert resultado.motivo == "resultado não finito: rendimento de 12 meses do FII"
