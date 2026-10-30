"""Sem migração: colunas legadas não recebem score/rótulo fabricado na apresentação1.0."""

import json

from database import DatabaseManager


def test_nova_analise_grava_payload_sem_sintese_e_colunas_legadas_nulas(tmp_path):
    db = DatabaseManager(str(tmp_path / "teste.db"))
    dados = {
        "ticker": "TST3",
        "apresentacao_versao": "1.0",
        "lentes": {"X": {"valor": 100}},
        "score_final": 90,
        "recomendacao": "resíduo",
        "fair_value": 200,
    }
    db.salvar_analise(dados)
    with db._get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM analises WHERE ticker = ?", ("TST3",)
        ).fetchone()
        assert row["score"] is None and row["recomendacao"] is None
        payload = json.loads(row["dados_completos"])
        assert payload["lentes"] == dados["lentes"]
        assert not {"fair_value", "score_final", "recomendacao"} & payload.keys()
    assert dados["score_final"] == 90
