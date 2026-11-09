"""BUG-2C-54: a apresentação nova não herda score/rótulo em colunas legadas."""

import json

import pytest

from database import DatabaseManager


@pytest.mark.parametrize(
    "restos",
    [{}, {"score_final": 90, "recomendacao": "registro antigo", "fair_value": 200}],
)
def test_nova_persistencia_sem_sintese_padrao_ou_herdada(tmp_path, restos):
    db = DatabaseManager(str(tmp_path / "teste.db"))
    d = {
        "ticker": "TST3",
        "apresentacao_versao": "1.0",
        "lentes": {"X": {"valor": 100}},
        **restos,
    }
    db.salvar_analise(d)
    with db._get_conn() as conn:
        r = conn.execute(
            "SELECT score,recomendacao,dados_completos FROM analises WHERE ticker = ?",
            ("TST3",),
        ).fetchone()
    assert r["score"] is None and r["recomendacao"] is None
    assert (
        not {"fair_value", "score_final", "recomendacao"}
        & json.loads(r["dados_completos"]).keys()
    )
