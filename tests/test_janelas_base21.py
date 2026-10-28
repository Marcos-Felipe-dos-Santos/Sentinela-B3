"""Decisão expressa28/10: fronteiras documentais independentes das heurísticas."""

from datetime import UTC, datetime

import pytest

from sentinela.data.janelas_fundamentais import entradas
from tests.test_janelas_fundamentais import dados_exemplo

AGORA = datetime(2026, 10, 20, tzinfo=UTC)


@pytest.mark.parametrize(
    "razao,aceita",
    [
        (0.9, False),
        (0.90001, True),
        (1, True),
        (1.09999, True),
        (1.1, False),
        (2, False),
    ],
)
def test_razao_documental_sem_inferir_evento(razao, aceita):
    d = dados_exemplo()
    d.pop("reconciliacao_serie")
    for i, e in enumerate(d["serie_cvm"]["exercicios"]):
        e["acoes"] = 100 if i == 0 else 100 * razao
        e.pop("evidencia_comparabilidade")
        e.pop("perimetro")
    r = entradas(d, AGORA)
    assert ("lpa" in r["graham"]) is aceita
    if aceita:
        assert r["graham"]["lpa"] == pytest.approx(3.2)
        assert (
            "reorganização societária no período não é detectada"
            in r["lynch"]["avisos"]
        )
    else:
        assert "fator oficial" in r["lynch"]["abstencao"]


def test_base_incompativel_com_split_oficial_acumulado():
    d = dados_exemplo()
    for i, e in enumerate(d["serie_cvm"]["exercicios"]):
        e["acoes"] = 100 if i == 0 else 200
    d["reconciliacao_serie"]["fatores"]["2021"] = 2
    assert entradas(d, AGORA)["graham"]["lpa"] == pytest.approx(3.08)


def test_reorganizacao_nao_abstem_documentos_validos():
    d = dados_exemplo()
    for i, e in enumerate(d["serie_cvm"]["exercicios"]):
        e["acoes"] = 100
        e["perimetro"] = str(i)
        e.pop("evidencia_comparabilidade")
    assert entradas(d, AGORA)["graham"]["lpa"] == pytest.approx(3.2)
