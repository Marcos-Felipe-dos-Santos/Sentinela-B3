"""F4-C10: valores da Qualidade dos casos completos do golden, calculados à mão.

Escritos antes de gerar as linhas novas do golden, para que ele não seja o próprio oráculo
(`docs/decisoes/golden-qualidade-4.md`, §4). Insumos em `tests/apoio_qualidade.py`:
- lucro dos controladores 100, 110, 120, 130 e 140 (2021 a 2025), PL inicial 1000: ROE de
  0,10 a 0,14, média 0,12 e desvio populacional √(0,0002) = 1,4142 p.p.;
- lucro consolidado 120 a 160 e receita 1000: margem de 0,12 a 0,16;
- dívida financeira líquida 200 e EBITDA 400: alavancagem 0,5 em todos os anos;
- proventos B3 por data-ex: 1,1; 1,2; 1,3; 1,0 e 1,5 (um por ano, em 10/06).
"""

import math

import pytest
from golden_motores import executar, montar_casos

ROE = [0.10, 0.11, 0.12, 0.13, 0.14]
LUCROS = [100.0, 110.0, 120.0, 130.0, 140.0]
MARGEM = [0.12, 0.13, 0.14, 0.15, 0.16]
PROVENTOS = [1.1, 1.2, 1.3, 1.0, 1.5]


def _qualidade(id_: str) -> dict:
    (caso,) = [c for c in montar_casos() if c["id"] == id_]
    return executar(caso)["qualidade"]


def _coluna(q: dict, campo: str) -> list:
    return [e[campo] for e in q["exercicios"]]


def test_empresa_completa_preenche_os_cinco_indicadores():
    q = _qualidade("qualidade-empresa-completa")

    assert q["comparavel"] is True
    assert q["cobertura"] == {"observados": 5, "esperados": 5, "completa": True}
    assert _coluna(q, "roe") == pytest.approx(ROE)
    assert _coluna(q, "lucro_controladores") == LUCROS
    assert _coluna(q, "margem_consolidada") == pytest.approx(MARGEM)
    assert _coluna(q, "alavancagem") == pytest.approx([0.5] * 5)
    assert _coluna(q, "proventos") == pytest.approx(PROVENTOS)
    assert q["roe"]["media"] == pytest.approx(0.12)
    assert q["roe"]["desvio_populacional_pp"] == pytest.approx(math.sqrt(0.0002) * 100)
    assert (
        q["roe"]["minimo"],
        q["roe"]["maximo"],
        q["roe"]["ultimo"],
    ) == pytest.approx((0.10, 0.14, 0.14))
    assert q["lucros"]["positivos"] == 5
    assert q["proventos"]["positivos"] == 5
    assert (q["proventos"]["minimo"], q["proventos"]["maximo"]) == pytest.approx(
        (1.0, 1.5)
    )


def test_banco_completo_tem_roe_lucros_e_proventos_sem_margem_nem_alavancagem():
    q = _qualidade("qualidade-banco-completo")

    assert q["comparavel"] is True
    assert q["cobertura"] == {"observados": 5, "esperados": 5, "completa": True}
    assert _coluna(q, "roe") == pytest.approx(ROE)
    assert _coluna(q, "lucro_controladores") == LUCROS
    assert _coluna(q, "proventos") == pytest.approx(PROVENTOS)
    assert _coluna(q, "margem_consolidada") == [None] * 5
    assert _coluna(q, "alavancagem") == [None] * 5
    assert q["margem_consolidada"]["motivo"] == "não aplicável ao modelo banco"
    assert q["alavancagem"]["motivo"] == "não aplicável ao modelo banco"
