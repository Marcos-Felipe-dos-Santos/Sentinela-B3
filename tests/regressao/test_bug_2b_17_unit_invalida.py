"""F2B-48: quantidade inválida da unit nunca vira LPA ou erro de soma."""

import math

import pytest

from market_engine import MarketEngine
from sentinela.data import acoes_cvm as a
from sentinela.data import series_cvm as s


@pytest.mark.parametrize("q", [0.5, 0, -1, True, math.nan, math.inf, "2"])
@pytest.mark.parametrize("caminho", ["lpa", "market", "serie"])
def test_unit_invalida_abstem_sem_typeerror(q, caminho):
    composicao = {"ON": q, "PN": 1}
    ind = {
        "lucro_controladores": 1000.0,
        "lucro_liquido": 1000.0,
        "pl_controladores": 10000.0,
        "composicao_capital": a.Composicao(500, 500, 0, 0, 0, "2025-12-31", "1"),
        "lpa_basico_por_classe": {"ON": [1.0], "PN": [1.0]},
    }
    if caminho == "lpa":
        valor = a.lpa_dos_metodos(
            especie=None,
            classe=None,
            classes_preferenciais=None,
            eh_unit=True,
            acoes_por_unit=composicao,
            divulgados=a.divulgados_coerentes(
                ind["lpa_basico_por_classe"], 1000.0, 1000.0
            ),
            recalculado=1.0,
        )
        assert valor == a.Abstencao(a.MOTIVO_UNIT)
    elif caminho == "serie":
        valor = s.exercicio(2025, ind, eh_unit=True, acoes_por_unit=composicao)
        assert valor["lpa"] is None and valor["motivos"]["lpa"] == a.MOTIVO_UNIT
    else:
        dados = {
            "classe_ativo": "UNIT",
            "acoes_por_unit": composicao,
            "preco_atual": 10.0,
        }
        valor = MarketEngine.__new__(MarketEngine)._por_acao_cvm("ZZZZ11", dados, ind)
        assert "lpa" not in valor
        assert a.MOTIVO_UNIT in str(dados.get("riscos_dados"))
