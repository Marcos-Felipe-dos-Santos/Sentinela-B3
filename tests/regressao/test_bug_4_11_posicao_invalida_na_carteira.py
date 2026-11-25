"""BUG-4-11: a carteira grava posição com ticker, quantidade ou preço inválidos.

`DatabaseManager.adicionar_posicao` normalizava o ticker sem validá-lo e gravava qualquer
quantidade e preço: ticker vazio, fora do padrão da B3, `True` como quantidade (vale 1) e
preço `NaN`, infinito ou zero entravam na tabela `carteira_real`. Um erro do SQLite na
inclusão ou na remoção subia até a aba Carteira, ao contrário de `salvar_analise`, que o
registra no log (achado 14 da auditoria Gemini, médio).

Banco SQLite temporário; tickers sintéticos, sem dado da carteira real.
"""

import logging
import math
import sqlite3

import pytest

from database import DatabaseManager


@pytest.fixture
def db(tmp_path):
    return DatabaseManager(db_path=str(tmp_path / "carteira.db"))


@pytest.mark.parametrize(
    ("ticker", "qtd", "preco", "motivo"),
    [
        pytest.param("", 10, 10.0, "ticker inválido", id="ticker_vazio"),
        pytest.param("   ", 10, 10.0, "ticker inválido", id="ticker_so_espacos"),
        pytest.param("PETR", 10, 10.0, "ticker inválido", id="ticker_sem_digito"),
        pytest.param(
            "PETR4; DROP", 10, 10.0, "ticker inválido", id="ticker_fora_do_padrao"
        ),
        pytest.param(
            "TSTA3", True, 10.0, "quantidade inválida", id="quantidade_booleana"
        ),
        pytest.param(
            "TSTA3", 2.5, 10.0, "quantidade inválida", id="quantidade_fracionaria"
        ),
        pytest.param("TSTA3", 10, math.nan, "preço inválido", id="preco_nan"),
        pytest.param("TSTA3", 10, math.inf, "preço inválido", id="preco_infinito"),
        pytest.param("TSTA3", 10, 0.0, "preço inválido", id="preco_zero"),
        pytest.param("TSTA3", 10, -1.0, "preço inválido", id="preco_negativo"),
        pytest.param("TSTA3", 10, True, "preço inválido", id="preco_booleano"),
    ],
)
def test_posicao_invalida_nao_grava_linha(db, ticker, qtd, preco, motivo):
    with pytest.raises(ValueError, match=motivo):
        db.adicionar_posicao(ticker, qtd, preco)

    assert db.listar_carteira() == []


def test_quantidade_zero_e_recusada_sem_alterar_a_posicao(db):
    db.adicionar_posicao("TSTA3", 10, 10.0)

    with pytest.raises(ValueError):
        db.adicionar_posicao("TSTA3", 0, 12.0)

    assert db.listar_carteira()[0]["quantidade"] == 10


def test_reducao_com_preco_invalido_nao_altera_a_posicao(db):
    db.adicionar_posicao("TSTA3", 10, 10.0)

    with pytest.raises(ValueError):
        db.adicionar_posicao("TSTA3", -5, math.nan)

    assert db.listar_carteira()[0]["quantidade"] == 10


def _banco_fora(*args, **kwargs):
    raise sqlite3.OperationalError("database is locked")


def test_erro_sqlite_na_inclusao_e_registrado_e_devolve_falso(db, monkeypatch, caplog):
    monkeypatch.setattr(db, "_get_conn", _banco_fora)

    assert db.adicionar_posicao("TSTA3", 10, 10.0) is False
    assert "database is locked" in caplog.text


def test_erro_sqlite_na_remocao_e_registrado_e_devolve_falso(db, monkeypatch, caplog):
    monkeypatch.setattr(db, "_get_conn", _banco_fora)

    assert db.remover_posicao("TSTA3") is False
    assert "database is locked" in caplog.text


def test_posicao_valida_continua_gravada(db):
    assert db.adicionar_posicao(" tsta3 ", 10, 10.0) is True
    assert db.adicionar_posicao("TSTA3", -4, 99.0) is True

    assert [
        (p["ticker"], p["quantidade"], p["preco_medio"]) for p in db.listar_carteira()
    ] == [("TSTA3", 6, 10.0)]


def test_remocao_apaga_so_a_posicao_do_ticker_e_devolve_verdadeiro(db, caplog):
    db.adicionar_posicao("TSTA3", 10, 10.0)
    db.adicionar_posicao("TSTB4", 5, 20.0)

    with caplog.at_level(logging.INFO, logger="Database"):
        assert db.remover_posicao(" tsta3 ") is True

    assert [p["ticker"] for p in db.listar_carteira()] == ["TSTB4"]
    assert "Posição removida: TSTA3" in caplog.text
