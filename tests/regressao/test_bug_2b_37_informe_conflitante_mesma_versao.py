"""BUG-2B-37: duas linhas do Informe com a mesma versão e valores diferentes.

Achado da 2ª auditoria FASE do Codex (20/10/2026): `_por_mes` só troca o registro quando a
versão é maior, então a primeira linha vence, e reordenar duas linhas conflitantes da mesma
versão muda o rendimento (12 → 13). Contraria o contrato do marcador e a ficha FII, §3:
conflito abstém, nas duas ordens; duplicata idêntica continua válida.
"""

import pytest

from sentinela.data import rendimento_fii


def _registros():
    meses = (
        [(2025, 9)]
        + [(2025, m) for m in (10, 11, 12)]
        + [(2026, m) for m in range(1, 10)]
    )
    return [
        {
            "Data_Referencia": f"{ano}-{mes:02d}-01",
            "Versao": "1",
            "Valor_Patrimonial_Cotas": "100",
            "Percentual_Dividend_Yield_Mes": None if i == 0 else "0.01",
        }
        for i, (ano, mes) in enumerate(meses)
    ]


@pytest.mark.parametrize("ordem", [1, -1])
def test_conflito_de_mesma_versao_abstem_nas_duas_ordens(ordem):
    registros = _registros()
    conflitante = {**registros[-1], "Percentual_Dividend_Yield_Mes": "0.02"}
    linhas = [registros[-1], conflitante][::ordem]
    resultado = rendimento_fii.rendimento_12_meses([*registros[:-1], *linhas], 100)
    assert resultado == rendimento_fii.Abstencao(
        "Informe com linhas conflitantes da mesma versão: 2026-09"
    )


def test_duplicata_identica_continua_valida():
    registros = _registros()
    resultado = rendimento_fii.rendimento_12_meses(
        [*registros, dict(registros[-1])], 100
    )
    assert resultado["rendimento_12m"] == pytest.approx(12.0)


def test_duplicata_com_celula_vazia_continua_valida():
    # Revisão do F2B-54: célula vazia do CSV vira NaN, e NaN != NaN; a duplicata vale.
    registros = _registros()
    linha = {**registros[-1], "Percentual_Amortizacao_Cotas_Mes": float("nan")}
    copia = {**linha, "Percentual_Amortizacao_Cotas_Mes": float("nan")}
    resultado = rendimento_fii.rendimento_12_meses([*registros[:-1], linha, copia], 100)
    assert resultado["rendimento_12m"] == pytest.approx(12.0)
