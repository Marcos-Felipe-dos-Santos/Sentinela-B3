import csv
from pathlib import Path

from cvm_ticker_map import _MANUAL_MAP

FIXTURE_OFICIAL = Path(__file__).parent / "fixtures" / "cvm_codigos_oficiais.csv"


def test_mapa_manual_bate_com_cadastro_oficial():
    with FIXTURE_OFICIAL.open(encoding="utf-8") as f:
        oficial = {
            r["ticker"]: int(r["cd_cvm"])
            for r in csv.DictReader(f, delimiter=";")
            if r["situacao"] != "fora"
        }
    assert {t: cd for cd, t in _MANUAL_MAP.items()} == oficial
