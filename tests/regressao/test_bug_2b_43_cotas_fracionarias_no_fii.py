"""BUG-2B-43: quantidade de cotas fracionária no Informe tira o FII da lente de rendimento.

A ficha FII 1.2 (§3b, decisão do Marcos de 25/10/2026) aceita `Cotas_Emitidas` positiva e
finita, com ou sem fração; 35% das linhas do Informe de 2026 trazem fração sem evento de cota.
"""

from datetime import date

import pytest

from sentinela.data import fii_elegibilidade as fe
from sentinela.data import rendimento_fii as rf


def _linhas(cotas):
    meses = [(2025, 9), (2025, 10), (2025, 11), (2025, 12)] + [
        (2026, m) for m in range(1, 10)
    ]
    linhas = []
    for i, (ano, mes) in enumerate(meses):
        entrega = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        linhas.append(
            {
                "Data_Referencia": f"{ano:04d}-{mes:02d}-01",
                "Versao": "1",
                "Data_Entrega": f"{entrega[0]:04d}-{entrega[1]:02d}-14",
                "Valor_Patrimonial_Cotas": "100",
                "Percentual_Dividend_Yield_Mes": None if i == 0 else "0.01",
                "Percentual_Amortizacao_Cotas_Mes": "0",
                "Cotas_Emitidas": cotas,
            }
        )
    return linhas


def test_cotas_fracionarias_nao_abstem():
    composicao = {c: "0" for c in (*fe.TIJOLO, *fe.PAPEL, *fe.FUNDO_DE_FUNDOS)}
    composicao.update(
        {
            "Imoveis_Renda_Acabados": "90",
            "CRI": "10",
            "Data_Referencia": "2026-09-01",
            "Versao": "1",
        }
    )
    resultado = rf.avaliar(
        _linhas("1324930.00003248"),
        [composicao],
        b3={
            "code": "TSTI",
            "fund": "FII TESTE",
            "stockDividends": [],
            "cashDividends": [],
        },
        codigo="TSTI",
        isin="BRTSTICTF000",
        preco=100.0,
        dia_as_of=date(2026, 10, 19),
    )
    assert not isinstance(resultado, rf.Abstencao), resultado
    assert resultado["rendimento_12m"] == pytest.approx(12.0)
    assert resultado["emissoes"] == []
