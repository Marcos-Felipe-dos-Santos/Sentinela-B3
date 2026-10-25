"""DFP sintética de banco no formato da cascata (F2B-32): exemplo da ficha bancos 1.1.

Valores em mil reais do exemplo independente (ITUB4, DFP 2025): lucro dos controladores,
PL inicial, DVA dos controladores, PL final e ações finais. Não é dado de mercado.
"""

from apoio_gordon import AS_OF_GORDON

LUCRO = 44_857_000.0
PL_INICIAL = 211_090_000.0
PL_FINAL = 204_501_000.0
ACOES = 11_026_524.0
PROVENTOS = 33_704_000.0
VPA = PL_FINAL / ACOES
NTNB = 74.38 / 1100
INFLACAO = 0.0426
TETO = 0.02
PROV = {
    "periodo_referencia": "2025-12-31",
    "data_entrega": "2026-02-12",
    "data_coleta": "2026-02-20T18:00:00+00:00",
}


def enriquecer_bancos(dados: dict, **fonte) -> dict:
    """Classe, modelo banco, a fronteira documental do Gordon/bancos e a taxa real."""
    dados = dict(dados)
    dados.setdefault("classe_ativo", "STOCK")
    dados.setdefault("modelo_bpp", "banco")
    dados["base_acionaria_gordon"] = {"proveniencia": dict(PROV)}
    dados["taxa_real"] = {
        "ntnb": NTNB,
        "custo_capital_real": NTNB + 0.05,
        "premio": 0.05,
        "inflacao": {"valor": INFLACAO, "inicio": "2025-01-01", "fim": "2025-12-31"},
        "pib": {"valor": TETO, "ano": 2030},
    }
    dados["gordon_cvm"] = {
        "modelo": "banco",
        "documento": "DFP",
        "inicio": "2025-01-01",
        "fim": "2025-12-31",
        "data_entrega": "2026-02-12",
        "base_acionaria_compativel": True,
        "hipotese_dva_anual": True,
        "lucro_controladores": LUCRO,
        "pl_inicial_controladores": PL_INICIAL,
        "proventos_controladores": PROVENTOS,
        "acoes_base": ACOES,
        "vpa": VPA,
        "lpa": None,
        "fator_unit": 1,
        "direitos_compativeis": True,
        "proveniencia": {"fonte": "DFP sintética de teste", **PROV},
        **fonte,
    }
    return dados


__all__ = ["AS_OF_GORDON", "enriquecer_bancos"]
