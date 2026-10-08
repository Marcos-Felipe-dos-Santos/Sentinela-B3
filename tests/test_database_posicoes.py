from datetime import datetime

import pytest

from database import DatabaseManager


@pytest.fixture
def db(tmp_path):
    """Retorna uma instância de DatabaseManager com um banco SQLite temporário."""
    return DatabaseManager(db_path=str(tmp_path / "test.db"))

def test_primeira_compra_insere_com_data_de_hoje(db):
    db.adicionar_posicao("TST3", 100, 15.5)
    carteira = db.listar_carteira()
    assert len(carteira) == 1
    posicao = carteira[0]
    assert posicao['ticker'] == "TST3"
    assert posicao['quantidade'] == 100
    assert posicao['preco_medio'] == pytest.approx(15.5)
    assert posicao['data_aporte'] == datetime.now().strftime("%Y-%m-%d")

def test_aporte_adicional_media_ponderada(db):
    db.adicionar_posicao("TST3", 100, 10.0)
    db.adicionar_posicao("TST3", 50, 16.0)
    carteira = db.listar_carteira()
    assert len(carteira) == 1
    posicao = carteira[0]
    assert posicao['quantidade'] == 150
    # PM = (100 * 10.0 + 50 * 16.0) / 150 = (1000 + 800) / 150 = 1800 / 150 = 12.0
    assert posicao['preco_medio'] == pytest.approx(12.0)

@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Bug: Venda parcial recalcula o preço médio erroneamente. 50 de 100 a preço diferente do PM muda o PM, contrariando a regra do custo médio.")
def test_venda_parcial_preserva_preco_medio(db):
    db.adicionar_posicao("TST3", 100, 10.0)
    # Vende 50 a um preço de 20.0
    # A regra diz que venda parcial não altera preço médio, portanto deve continuar 10.0
    db.adicionar_posicao("TST3", -50, 20.0)
    carteira = db.listar_carteira()
    assert len(carteira) == 1
    posicao = carteira[0]
    assert posicao['quantidade'] == 50
    assert posicao['preco_medio'] == pytest.approx(10.0)

def test_zeragem_remove_posicao(db):
    db.adicionar_posicao("TST3", 100, 10.0)
    db.adicionar_posicao("TST3", -100, 12.0)
    carteira = db.listar_carteira()
    assert len(carteira) == 0

def test_venda_maior_que_posicao(db):
    """
    Documenta o comportamento atual de vender uma quantidade maior que a posição existente.
    O código atual, `nova_qtd = qtd_antiga + qtd`, caso fique negativo, cai no else de `nova_qtd > 0`
    e executa `DELETE FROM carteira_real WHERE ticker=?`.
    Portanto, a posição é removida da mesma forma que a zeragem.
    """
    db.adicionar_posicao("TST3", 100, 10.0)
    db.adicionar_posicao("TST3", -150, 12.0)
    carteira = db.listar_carteira()
    assert len(carteira) == 0

def test_compra_quantidade_zero_nao_insere(db):
    db.adicionar_posicao("TST3", 0, 10.0)
    carteira = db.listar_carteira()
    assert len(carteira) == 0

def test_ticker_normalizado(db):
    db.adicionar_posicao(" tst3 ", 100, 10.0)
    carteira = db.listar_carteira()
    assert len(carteira) == 1
    posicao = carteira[0]
    assert posicao['ticker'] == "TST3"

def test_venda_de_ticker_inexistente_nao_insere(db):
    db.adicionar_posicao("TST3", -100, 10.0)
    carteira = db.listar_carteira()
    assert len(carteira) == 0

def test_compra_quantidade_um_insere_normalmente(db):
    db.adicionar_posicao("TST3", 1, 10.0)
    carteira = db.listar_carteira()
    assert len(carteira) == 1
    assert carteira[0]['quantidade'] == 1

def test_venda_deixando_um_na_posicao(db):
    db.adicionar_posicao("TST3", 2, 10.0)
    db.adicionar_posicao("TST3", -1, 10.0)
    carteira = db.listar_carteira()
    assert len(carteira) == 1
    assert carteira[0]['quantidade'] == 1
