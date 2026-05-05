import sqlite3
from copy import deepcopy

from sentinela.domain.models import AnalysisResult
from sentinela.repositories.analysis_repository import AnalysisRepository


def _repo(tmp_path):
    return AnalysisRepository(str(tmp_path / "analysis_repo.db"))


def _payload_with_field_provenance():
    return {
        "ticker": "PETR4",
        "preco_atual": 35.0,
        "dy": 0.08,
        "field_provenance": {
            "preco_atual": {
                "name": "preco_atual",
                "value": 35.0,
                "unit": "BRL",
                "provenance": {
                    "source": "yfinance",
                    "confidence": 1.0,
                    "cached": False,
                    "manual": False,
                    "stale": False,
                    "warnings": [],
                },
            },
            "dy": {
                "name": "dy",
                "value": 0.08,
                "unit": "ratio",
                "provenance": {
                    "source": "brapi",
                    "confidence": 0.9,
                    "cached": False,
                    "manual": False,
                    "stale": False,
                    "warnings": [],
                },
            },
        },
    }


def test_save_run_inserts_append_only_for_same_ticker(tmp_path):
    repo = _repo(tmp_path)

    first_id = repo.save_run({"ticker": "petr4", "recomendacao": "NEUTRO"})
    second_id = repo.save_run({"ticker": "PETR4", "recomendacao": "COMPRA"})

    assert first_id != second_id
    assert repo.count_runs("PETR4") == 2


def test_get_latest_returns_most_recent_run(tmp_path):
    repo = _repo(tmp_path)

    repo.save_run({"ticker": "VALE3", "recomendacao": "NEUTRO", "fair_value": 50.0})
    second_id = repo.save_run({"ticker": "VALE3", "recomendacao": "VENDA", "fair_value": 40.0})

    latest = repo.get_latest("vale3")

    assert latest is not None
    assert latest["id"] == second_id
    assert latest["recommendation"] == "VENDA"
    assert latest["fair_value"] == 40.0
    assert latest["payload"]["recomendacao"] == "VENDA"


def test_list_runs_returns_most_recent_first(tmp_path):
    repo = _repo(tmp_path)

    first_id = repo.save_run({"ticker": "ITUB4", "fair_value": 10.0})
    second_id = repo.save_run({"ticker": "ITUB4", "fair_value": 20.0})
    third_id = repo.save_run({"ticker": "ITUB4", "fair_value": 30.0})

    runs = repo.list_runs("ITUB4")

    assert [run["id"] for run in runs] == [third_id, second_id, first_id]
    assert [run["payload"]["fair_value"] for run in runs] == [30.0, 20.0, 10.0]


def test_save_run_accepts_analysis_result(tmp_path):
    repo = _repo(tmp_path)
    analysis = AnalysisResult.from_dict(
        {
            "ticker": "MXRF11",
            "is_fii": True,
            "market": {"ticker": "MXRF11", "preco_atual": 10.0},
            "valuation": {
                "fair_value": 11.0,
                "upside": 10.0,
                "recomendacao": "COMPRA",
                "confianca": 80,
            },
            "data_quality": {"score": 90},
        }
    )

    row_id = repo.save_run(analysis)
    latest = repo.get_latest("MXRF11")

    assert latest is not None
    assert latest["id"] == row_id
    assert latest["asset_type"] == "FII"
    assert latest["recommendation"] == "COMPRA"
    assert latest["current_price"] == 10.0
    assert latest["payload"]["valuation"]["fair_value"] == 11.0


def test_missing_optional_fields_do_not_crash(tmp_path):
    repo = _repo(tmp_path)

    row_id = repo.save_run({"ticker": "BBDC4"})
    latest = repo.get_latest("BBDC4")

    assert row_id > 0
    assert latest is not None
    assert latest["ticker"] == "BBDC4"
    assert latest["recommendation"] is None
    assert latest["payload"]["ticker"] == "BBDC4"


def test_count_runs_all_and_by_ticker(tmp_path):
    repo = _repo(tmp_path)

    repo.save_run({"ticker": "PETR4"})
    repo.save_run({"ticker": "PETR4"})
    repo.save_run({"ticker": "VALE3"})

    assert repo.count_runs() == 3
    assert repo.count_runs("petr4") == 2
    assert repo.count_runs("VALE3") == 1


def test_repository_does_not_create_or_modify_legacy_analises_table(tmp_path):
    db_path = tmp_path / "analysis_repo.db"
    AnalysisRepository(str(db_path))

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "analysis_runs" in tables
    assert "analises" not in tables


def test_save_run_preserves_field_provenance_payload(tmp_path):
    repo = _repo(tmp_path)
    payload = _payload_with_field_provenance()

    repo.save_run(payload)
    latest = repo.get_latest("PETR4")

    assert latest is not None
    saved_payload = latest["payload"]
    assert saved_payload["preco_atual"] == 35.0
    assert saved_payload["dy"] == 0.08
    assert "field_provenance" in saved_payload
    assert (
        saved_payload["field_provenance"]["preco_atual"]["provenance"]["source"]
        == "yfinance"
    )
    assert saved_payload["field_provenance"]["dy"]["provenance"]["source"] == "brapi"
    assert saved_payload["field_provenance"]["dy"]["value"] == saved_payload["dy"]


def test_field_provenance_roundtrip_for_cached_and_manual_flags(tmp_path):
    repo = _repo(tmp_path)
    payload = {
        "ticker": "MXRF11",
        "pvp": 0.98,
        "dy": 0.11,
        "field_provenance": {
            "pvp": {
                "value": 0.98,
                "unit": "ratio",
                "provenance": {
                    "source": "fundamentals_cache",
                    "cached": True,
                    "manual": False,
                    "stale": False,
                    "confidence": 0.75,
                    "warnings": [],
                },
            },
            "dy": {
                "value": 0.11,
                "unit": "ratio",
                "provenance": {
                    "source": "manual_fallback",
                    "cached": False,
                    "manual": True,
                    "stale": False,
                    "confidence": 0.6,
                    "warnings": ["manual_fallback"],
                },
            },
        },
    }

    repo.save_run(payload)
    latest = repo.get_latest("MXRF11")

    assert latest is not None
    field_provenance = latest["payload"]["field_provenance"]
    assert field_provenance["pvp"]["provenance"]["cached"] is True
    assert field_provenance["dy"]["provenance"]["manual"] is True
    assert "manual_fallback" in field_provenance["dy"]["provenance"]["warnings"]


def test_input_hash_changes_when_field_provenance_changes(tmp_path):
    repo = _repo(tmp_path)
    first = _payload_with_field_provenance()
    second = deepcopy(first)
    second["field_provenance"]["dy"]["provenance"]["source"] = "fundamentus"

    first_id = repo.save_run(first)
    second_id = repo.save_run(second)
    runs = repo.list_runs("PETR4")

    assert first_id != second_id
    assert repo.count_runs("PETR4") == 2
    assert runs[0]["input_hash"] != runs[1]["input_hash"]


def test_missing_field_provenance_is_still_allowed(tmp_path):
    repo = _repo(tmp_path)

    row_id = repo.save_run({"ticker": "VALE3", "preco_atual": 60.0, "dy": 0.05})
    latest = repo.get_latest("VALE3")

    assert row_id > 0
    assert latest is not None
    assert latest["payload"]["ticker"] == "VALE3"
    assert latest["payload"]["preco_atual"] == 60.0
    assert "field_provenance" not in latest["payload"]


def test_analysis_result_with_field_provenance_is_preserved(tmp_path):
    repo = _repo(tmp_path)
    payload = _payload_with_field_provenance()
    payload.update(
        {
            "market": {"ticker": "PETR4", "preco_atual": 35.0},
            "valuation": {"recomendacao": "NEUTRO", "fair_value": 36.0},
        }
    )
    analysis = AnalysisResult.from_dict(payload)

    repo.save_run(analysis)
    latest = repo.get_latest("PETR4")

    assert latest is not None
    assert "field_provenance" in latest["payload"]
    assert latest["payload"]["field_provenance"]["dy"]["provenance"]["source"] == "brapi"
