"""Relação sintética de proventos da B3 para os exercícios de integração do Bazin.

Não é dado de mercado. Classe única, cobertura completa: um provento antigo (antes da
janela, só para demonstrar a cobertura de 12 meses) e um dividendo na janela que reproduz
o DY do cenário sobre o preço, com a mesma conferência no yfinance.
"""

import math

REFERENCIA_PRECO = "2026-10-19"  # pregão anterior ao AS_OF_GORDON (20/10/2026)


def _br(valor: float) -> str:
    return repr(float(valor)).replace(".", ",")


def enriquecer_bazin(dados: dict) -> dict:
    """Acrescenta `proventos_b3` com D = DY × preço; DY ou preço sem número: abstenção."""
    dados = dict(dados)
    p, dy = dados.get("preco_atual"), dados.get("dy")
    numeros = all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
        for v in (p, dy)
    )
    if not numeros or p <= 0 or dy < 0:
        dados["proventos_b3"] = {"abstencao": "cenário sintético sem relação B3"}
        return dados
    d = dy * p
    especie = dados.setdefault("especie", "ON")
    dados["proventos_b3"] = {
        "registros": [
            {
                "typeStock": especie,
                "corporateAction": "DIVIDENDO",
                "valueCash": _br(d),
                "lastDatePriorEx": "10/06/2026",
                "dateApproval": "01/06/2026",
                "quotedPerShares": "1",
            },
            {
                "typeStock": especie,
                "corporateAction": "DIVIDENDO",
                "valueCash": "1,0",
                "lastDatePriorEx": "10/06/2024",
                "dateApproval": "01/06/2024",
                "quotedPerShares": "1",
            },
        ],
        "total": 2,
        "eventos_acoes": [],
        "dinheiro_complemento": [],
        "fechamentos": {REFERENCIA_PRECO: p},
        "pregoes": None,
        "conferencia_yfinance": {"2026-06-11": d},
        "coleta": "2026-10-20T12:00:00+00:00",
        "proveniencia": {"fonte": "relação B3 sintética de teste"},
    }
    return dados
