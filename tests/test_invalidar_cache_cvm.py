import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "invalidar_cache_cvm.py"


def _carregar():
    spec = importlib.util.spec_from_file_location("invalidar_cache_cvm", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _banco(tmp_path):
    caminho = str(tmp_path / "t.db")
    with closing(sqlite3.connect(caminho)) as conn, conn:
        conn.execute(
            "CREATE TABLE fundamentals_cache (ticker TEXT PRIMARY KEY, dados_json TEXT, fonte TEXT, atualizado_em TEXT)"
        )
        conn.executemany(
            "INSERT INTO fundamentals_cache VALUES (?, '{}', 'CVM', '2026-01-01')",
            [("TST3",), ("TST4",), ("TST5",)],
        )
    return caminho


def _restantes(caminho):
    with closing(sqlite3.connect(caminho)) as conn:
        return {r[0] for r in conn.execute("SELECT ticker FROM fundamentals_cache")}


def test_sem_aplicar_nao_apaga_nada(tmp_path):
    banco = _banco(tmp_path)
    achados = _carregar().invalidar(banco, ["TST3", "TST4"], aplicar=False)
    assert sorted(achados) == ["TST3", "TST4"]
    assert _restantes(banco) == {"TST3", "TST4", "TST5"}


def test_aplicar_apaga_so_os_tickers_pedidos(tmp_path):
    banco = _banco(tmp_path)
    achados = _carregar().invalidar(banco, ["TST3", "NAOEXISTE"], aplicar=True)
    assert achados == ["TST3"]
    assert _restantes(banco) == {"TST4", "TST5"}
