import csv
from pathlib import Path

import pytest
from cvm_ticker_map import _MANUAL_MAP, CVMTickerMap, get_cd_cvm, get_ticker

FIXTURE_OFICIAL = Path(__file__).parent / "fixtures" / "cvm_codigos_oficiais.csv"


# --- funções de módulo (mapa estático) ---


def test_mapping_petr4():
    assert get_cd_cvm("PETR4") == 9512


def test_mapping_vale3():
    assert get_cd_cvm("VALE3") == 4170


def test_roundtrip():
    assert get_ticker(get_cd_cvm("ITUB4")) == "ITUB4"


def test_get_cd_cvm_lowercase():
    assert get_cd_cvm("petr4") == 9512


def test_get_cd_cvm_unknown_returns_none():
    assert get_cd_cvm("XXXX99") is None


def test_get_ticker_unknown_returns_none():
    assert get_ticker(0) is None


def test_mapa_manual_bate_com_cadastro_oficial():
    with FIXTURE_OFICIAL.open(encoding="utf-8") as f:
        oficial = {
            r["ticker"]: int(r["cd_cvm"])
            for r in csv.DictReader(f, delimiter=";")
            if r["situacao"] != "fora"
        }
    assert {t: cd for cd, t in _MANUAL_MAP.items()} == oficial


# --- CVMTickerMap com banco em memória ---


@pytest.fixture()
def cvm_map(tmp_path):
    m = CVMTickerMap(db_path=str(tmp_path / "test_cvm.db"))
    m.ensure_seeded()
    return m


def test_class_get_cd_cvm_petr4(cvm_map):
    assert cvm_map.get_cd_cvm("PETR4") == 9512


def test_class_get_ticker_vale3(cvm_map):
    assert cvm_map.get_ticker(4170) == "VALE3"


def test_class_roundtrip_itub4(cvm_map):
    cd = cvm_map.get_cd_cvm("ITUB4")
    assert cvm_map.get_ticker(cd) == "ITUB4"


def test_class_get_cd_cvm_unknown(cvm_map):
    assert cvm_map.get_cd_cvm("ZZZZ99") is None


def test_class_refresh_skips_when_fresh(cvm_map, monkeypatch):
    # ensure_seeded popula; refresh sem force deve pular (cache fresh)
    result = cvm_map.refresh(force=False)
    # cache já foi semeado via ensure_seeded, mas atualizado_em é "agora"
    # portanto deve indicar que não atualizou
    assert result is False


def test_class_refresh_network_failure_returns_false(cvm_map, monkeypatch):
    import requests

    def fake_get(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("cvm_ticker_map.requests.get", fake_get)
    result = cvm_map.refresh(force=True)
    assert result is False
