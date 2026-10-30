"""Ficha apresentação1.0: metadados, contexto e ausência de síntese."""

from datetime import UTC, datetime

import pytest
from test_financeiro_pre_refactor import _acao, _processar

from sentinela.domain.apresentacao import finalizar, mesclar_analise


@pytest.mark.parametrize(
    "dy,texto",
    [
        (0, "não atinge 6%"),
        (0.049, "não atinge 6%"),
        (0.06, "atinge 6%"),
        (0.08, "atinge 6%"),
    ],
)
def test_bazin_criterio_nominal_da_fonte_b3(dy, texto):
    d = _acao(dy=dy)
    r = _processar(d)
    l = r["lentes"]["Bazin"]
    assert l["criterio_6pct"] == texto
    assert l["dy_bruto_12m"] == pytest.approx(dy)
    assert l["tipo_valor"] == "preço-limite informativo"
    if dy < 0.05:
        assert l["valor"] is None and l["abstencao"]
    else:
        assert l["valor"] == pytest.approx(dy * 100 / 0.06)


def test_bazin_sem_b3_nao_inventa_criterio_com_cascata():
    d = _acao(dy=0.08)
    d["proventos_b3"] = {"abstencao": "sem fonte B3"}
    l = _processar(d)["lentes"]["Bazin"]
    assert l["valor"] is None and l["abstencao"]
    assert l["criterio_6pct"] is None
    assert l["criterio_motivo"]


def test_metadata_de_corte_nao_inventa_data_de_preco():
    instante = datetime(2026, 10, 20, 15, tzinfo=UTC)
    dados = {"preco_atual": 80, "fonte_preco": "fonte sintética"}
    original = {"lentes": {"X": {"valor": 100}}}
    r = finalizar(original, dados, instante)
    assert original == {"lentes": {"X": {"valor": 100}}}
    assert r["apresentacao_versao"] == "1.0"
    assert r["lentes"]["X"]["as_of"] == instante.isoformat()
    assert r["lentes"]["X"]["preco"] == 80
    assert r["lentes"]["X"]["fonte_preco"] == "fonte sintética"
    assert r["lentes"]["X"]["data_preco"] is None


def test_mescla_nova_nao_herda_sintese_do_cache():
    d = {
        "ticker": "TST3",
        "fair_value": 999,
        "upside": 900,
        "score_final": 100,
        "recomendacao": "legado",
        "classificacao_heuristica": "legado",
    }
    analise = {"apresentacao_versao": "1.0", "lentes": {"X": {"valor": 100}}}
    r = mesclar_analise(d, analise)
    assert r == {"ticker": "TST3", **analise}
    assert d["fair_value"] == 999


def test_prompt_novo_explica_lentes_sem_pedir_sintese_ou_sinal():
    from ai_core import SentinelaAI

    ai = SentinelaAI.__new__(SentinelaAI)
    p = ai._montar_prompt(
        "TST3", {"apresentacao_versao": "1.0", "lentes": {"Graham": {"valor": 150}}}
    )
    assert "Não altere nem substitua os valores" in p
    assert "lentes separadas" in p
    assert "4. Classificação Heurística" not in p
    assert "4. Hipóteses e limites" in p
