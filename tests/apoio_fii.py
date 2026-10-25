"""Informe Mensal e complemento da B3 sintéticos para os exercícios de integração do FII.

Não é dado de mercado. Um FII de tijolo com 13 meses (setembro/2025 a setembro/2026),
entregues no mês seguinte, VP de R$ 100 e um DY mensal igual que reproduz o DY de 12 meses do
cenário sobre o preço; a B3 responde sem eventos de cota e com os mesmos rendimentos; a taxa
real traz a NTN-B do cenário.
"""

import math

ISIN = "BRTSTICTF000"


def _meses():
    saida, ano, mes = [], 2026, 9
    for _ in range(13):
        saida.append((ano, mes))
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    return saida[::-1]


def enriquecer_fii(dados: dict, ntnb: float | None = 0.07) -> dict:
    """Acrescenta `informe_fii`, `b3_fundo` e `taxa_real`; sem DY ou preço, sem Informe."""
    dados = dict(dados)
    if ntnb is not None:
        # como o registro da taxa real em produção, sem a janela contábil (FII não tem DFP)
        dados.setdefault(
            "taxa_real",
            {
                "ntnb": ntnb,
                "custo_capital_real": ntnb + 0.05,
                "premio": 0.05,
                "data_base": "2026-10-16",
                # F2B-58: o corte temporal do registro, antes do as_of do harness.
                "dias_uteis": 2,
                "as_of": "2026-10-20T12:00:00+00:00",
                "fonte": "Tesouro Nacional, cenário sintético",
                "inflacao": {"abstencao": "janela contábil anual não demonstrada"},
                "pib": {"valor": 0.02, "ano": 2030},
            },
        )
    p, dy = dados.get("preco_atual"), dados.get("dy")
    numeros = all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
        for v in (p, dy)
    )
    if not numeros or p <= 0:
        return dados
    rendimento_mes = dy * p / 12
    registros = []
    for i, (ano, mes) in enumerate(_meses()):
        entrega = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        registros.append(
            {
                "Data_Referencia": f"{ano:04d}-{mes:02d}-01",
                "Versao": "1",
                "Data_Entrega": f"{entrega[0]:04d}-{entrega[1]:02d}-14",
                "Codigo_ISIN": ISIN,
                "Valor_Patrimonial_Cotas": "100",
                "Percentual_Dividend_Yield_Mes": None
                if i == 0
                else repr(rendimento_mes / 100),
                "Percentual_Amortizacao_Cotas_Mes": "0",
                "Cotas_Emitidas": "1000000",
            }
        )
    dados["informe_fii"] = {
        "registros": registros,
        "composicoes": [
            {
                "Data_Referencia": "2026-09-01",
                "Versao": "1",
                "Imoveis_Renda_Acabados": "900",
                "CRI": "100",
            }
        ],
        "isin": ISIN,
        "proveniencia": {
            "fonte": "Informe Mensal sintético de teste",
            "data_coleta": "2026-10-20T12:00:00+00:00",
        },
    }
    ticker = str(dados.get("ticker") or "TST11")
    dados["b3_fundo"] = {
        "resposta": {
            "code": ticker[:4],
            "fund": "FII SINTÉTICO",
            "stockDividends": [],
            "cashDividends": [],
        },
        "codigo": ticker[:4],
        "coleta": "2026-10-20T12:00:00+00:00",
    }
    return dados
