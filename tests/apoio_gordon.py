"""DFP sintética explícita para exercícios de integração; não é dado de mercado."""

import math
from datetime import UTC, date, datetime

AS_OF_GORDON = datetime(2026, 10, 20, 15, tzinfo=UTC)


class DiaGordon(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 20)


def enriquecer_gordon(
    dados: dict,
    *,
    com_dva: bool = True,
    ntnb: float = 0.07,
    inflacao: float = 0.055,
    teto: float = 0.02,
    dividendo: float = 3.0,
) -> dict:
    """Cenário contábil independente do DY:100ações, provento anual3poração.

    Os casos de dois métodos omitem explicitamente a DVA. Não há guarda de ROE
    antiga escondida no helper; ROE positivo abaixo de10% é testado no método.
    """
    dados = dict(dados)
    dados.setdefault("classe_ativo", "STOCK")
    prov = {
        "periodo_referencia": "2025-12-31",
        "data_entrega": "2026-02-12",
        "data_coleta": "2026-02-20T18:00:00+00:00",
    }
    dados["base_acionaria_gordon"] = {"proveniencia": dict(prov)}
    dados["taxa_real"] = {
        "ntnb": ntnb,
        "custo_capital_real": ntnb + 0.05,
        "premio": 0.05,
        "inflacao": {"valor": inflacao, "inicio": "2025-01-01", "fim": "2025-12-31"},
        "pib": {"valor": teto, "ano": 2030},
    }
    if not com_dva:
        dados["gordon_cvm"] = {
            "abstencao": "cenário sintético sem DVA: exercício de dois métodos"
        }
        return dados
    p, pl, roe = dados.get("preco_atual", 0), dados.get("pl", 0), dados.get("roe", 0)
    if (
        not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in (p, pl, roe)
        )
        or pl <= 0
        or roe <= 0
    ):
        dados["gordon_cvm"] = {
            "abstencao": "insumo contábil inválido no cenário sintético"
        }
        return dados
    lpa = p / pl
    comp = dados.get("acoes_por_unit") or {}
    unit = dados["classe_ativo"] == "UNIT"
    fator = (
        sum(comp.values())
        if comp
        and all(
            isinstance(q, (int, float))
            and not isinstance(q, bool)
            and math.isfinite(q)
            and q > 0
            and q % 1 == 0
            for q in comp.values()
        )
        else 1
    )
    dados["gordon_cvm"] = {
        "modelo": "empresa",
        "documento": "DFP",
        "inicio": "2025-01-01",
        "fim": "2025-12-31",
        "data_entrega": "2026-02-12",
        "base_acionaria_compativel": True,
        "hipotese_dva_anual": True,
        "lucro_controladores": lpa * 100,
        "pl_inicial_controladores": lpa * 100 / roe,
        "proventos_controladores": dividendo * 100,
        "acoes_base": 100.0,
        "lpa": lpa,
        "fator_unit": fator,
        "direitos_compativeis": bool(comp) if unit else True,
        "proveniencia": {"fonte": "DFP sintética de teste", **prov},
    }
    return dados
