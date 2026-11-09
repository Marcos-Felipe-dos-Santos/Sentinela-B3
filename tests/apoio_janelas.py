"""Documentos de cinco exercícios sintéticos; não são dados do mercado/carteira."""

import math


def enriquecer_janelas(dados: dict, *, crescimento: float | None = None) -> dict:
    d = dict(dados)
    if crescimento is None:
        roe = d.get("roe")
        crescimento = (
            0.2
            if isinstance(roe, (int, float))
            and not isinstance(roe, bool)
            and math.isfinite(roe)
            and roe > 0.2
            else 0
        )
    preco, pl, pvp = d.get("preco_atual"), d.get("pl"), d.get("pvp")

    def finito(v):
        return (
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
        )

    lpa = d.get("lpa")
    if "lpa" not in d:
        lpa = preco / pl if finito(preco) and finito(pl) and pl != 0 else None
    vpa = d.get("vpa")
    if "vpa" not in d:
        vpa = preco / pvp if finito(preco) and finito(pvp) and pvp != 0 else None
    anos = range(2021, 2026)
    d["serie_cvm"] = {
        "exercicios": [
            {
                "exercicio": a,
                "acoes": 100,
                "inicio": f"{a}-01-01",
                "fim": f"{a}-12-31",
                "dt_refer": f"{a}-12-31",
                "versao": "1",
                "lpa": lpa / (1 + crescimento) ** (2025 - a) if finito(lpa) else None,
                "vpa": vpa,
                "perimetro": "controladores sintéticos",
                "evidencia_comparabilidade": "cenário explícito, sem mudança estrutural",
                "proveniencia": {
                    "fonte": "DFP sintética",
                    "data_entrega": "2026-02-12",
                    "data_coleta": "2026-03-01T12:00:00+00:00",
                },
            }
            for a in anos
        ]
    }
    d["reconciliacao_serie"] = {
        "fonte": "B3 sintética, sem evento na janela",
        "inicio": "2021-01-01",
        "fim": "2025-12-31",
        "coleta": "2026-03-01T12:00:00+00:00",
        "fatores": {str(a): 1 for a in anos},
    }
    d["ipca_serie"] = {
        "fonte": "IBGE sintético (índice constante para este controle)",
        "coleta": "2026-03-01T12:00:00+00:00",
        "indices": {f"{a}-12": 100 for a in anos},
        "publicacoes": {f"{a}-12": "2026-02-01" for a in anos},
    }
    return d
