"""Compatibilidade autorizada: identificação sem recálculo ou escrita retroativa."""

import json
from copy import deepcopy

import pytest

from database import DatabaseManager
from sentinela.domain import apresentacao
from sentinela.repositories.analysis_repository import AnalysisRepository

LEGADO = {
    "ticker": "TSTA3",
    "recomendacao": "COMPRA",
    "score_final": 87,
    "fair_value": 12.345,
    "upside": 23.45,
    "preco_atual": 10,
    "historico": [9, 10],
    "motivo": "original",
    "extra": {"custom": True},
}
ATUAL = {
    "apresentacao_versao": "1.0",
    "lentes": {
        "Graham": {
            "valor": None,
            "abstencao": "documento ausente",
            "distancia_ao_preco_pct": None,
        }
    },
}


@pytest.mark.parametrize("payload", [LEGADO, {"valuation": LEGADO}, {"raw": LEGADO}])
def test_legado_preserva_todos_os_campos_e_identifica_historico(payload):
    original = deepcopy(payload)
    saida = apresentacao.adaptar_leitura(payload)
    assert payload == original
    assert {k: v for k, v in saida.items() if k != "_compat_apresentacao"} == original
    assert saida["_compat_apresentacao"] == {"tipo": "historico", "recalculado": False}
    assert apresentacao.contexto_leitura(saida)[0] == "historico"
    assert apresentacao.adaptar_leitura(saida) == saida


@pytest.mark.parametrize(
    "payload",
    [ATUAL, {"valuation": ATUAL}, {"raw": ATUAL}, {"valuation": {}, "raw": ATUAL}],
)
def test_versao_um_flat_ou_transportada_permanece_exatamente_igual(payload):
    original = deepcopy(payload)
    assert apresentacao.adaptar_leitura(payload) == original
    tipo, contexto = apresentacao.contexto_leitura(payload)
    assert tipo == "atual" and contexto == ATUAL
    assert payload == original


@pytest.mark.parametrize("versao", ["2.0", "", None, 1])
def test_versao_desconhecida_nao_ganha_sinal_ou_distancia(versao):
    payload = {**LEGADO, "apresentacao_versao": versao}
    saida = apresentacao.adaptar_leitura(payload)
    assert saida["_compat_apresentacao"]["tipo"] == "versao_desconhecida"
    tipo, contexto = apresentacao.contexto_leitura(saida)
    assert tipo == "versao_desconhecida"
    assert all(contexto[k] == v for k, v in payload.items())
    assert all(saida[k] == v for k, v in payload.items())
    assert "lentes" not in saida


def test_namespace_de_usuario_nao_e_sobrescrito():
    payload = {**LEGADO, "_compat_apresentacao": {"usuario": "reservado"}}
    assert apresentacao.adaptar_leitura(payload) == payload
    assert apresentacao.contexto_leitura(payload)[0] == "historico"


@pytest.mark.parametrize("payload", [None, [], "original", 2])
def test_formato_nao_mapping_preservado(payload):
    assert apresentacao.adaptar_leitura(payload) is payload


@pytest.mark.parametrize(
    "payload", [LEGADO, {"valuation": LEGADO}, ATUAL, {"raw": ATUAL}]
)
def test_leituras_sqlite_identificam_sem_escrever_json_ou_colunas(tmp_path, payload):
    db = DatabaseManager(str(tmp_path / "db.sqlite"))
    texto = json.dumps(payload, ensure_ascii=False, indent=3)
    with db._get_conn() as conn:
        conn.execute(
            "INSERT INTO analises VALUES (?, ?, ?, ?, ?)",
            ("TSTA3", "2020", 87, "COMPRA", texto),
        )
    with db._get_conn() as conn:
        antes = tuple(conn.execute("SELECT * FROM analises").fetchone())
    leitura = db.buscar_analise("TSTA3")
    assert leitura == apresentacao.adaptar_leitura(payload)
    with db._get_conn() as conn:
        assert tuple(conn.execute("SELECT * FROM analises").fetchone()) == antes
    repo = AnalysisRepository(str(tmp_path / "repo.sqlite"))
    repo.save_run({"ticker": "TSTA3"})
    with repo._get_conn() as conn:
        conn.execute("UPDATE analysis_runs SET payload_json=?", (texto,))
    with repo._get_conn() as conn:
        antes_repo = tuple(conn.execute("SELECT * FROM analysis_runs").fetchone())
    assert repo.get_latest("TSTA3")["payload"] == leitura
    assert repo.list_runs("TSTA3")[0]["payload"] == leitura
    with repo._get_conn() as conn:
        assert (
            tuple(conn.execute("SELECT * FROM analysis_runs").fetchone()) == antes_repo
        )


@pytest.mark.parametrize(
    "chave", ["recomendacao", "score_final", "fair_value", "upside"]
)
def test_contexto_historico_aninhado_identifica_valores_originais(chave):
    dados = {chave: 17, "campo_custom": "original"}
    assert apresentacao.contexto_leitura({"valuation": dados}) == ("historico", dados)
    assert apresentacao.contexto_leitura({"raw": dados}) == ("historico", dados)


def test_versao_explicita_desconhecida_nao_e_desviada_por_nested_atual():
    dados = {"apresentacao_versao": "9.0", "raw": ATUAL}
    assert apresentacao.contexto_leitura(dados) == ("versao_desconhecida", dados)


def test_contexto_vazio_nao_inventa_dados():
    assert apresentacao.contexto_leitura({}) == ("historico", {})
    assert apresentacao.contexto_leitura({"valuation": [], "raw": None}) == (
        "historico",
        {"valuation": [], "raw": None},
    )
