from unittest.mock import patch

import pytest

from fii_engine import FIIEngine
from valuation_engine import ValuationEngine


def test_dy_normalization_percentual() -> None:
    """DY percentual vindo do Yahoo deve ser convertido para decimal."""
    dados = {
        'ticker': 'PETR4',
        'preco_atual': 100.0,
        'roe': 0.10,
        'pl': 30.0,
        'pvp': 4.0,
        'dy': 12.47,
    }

    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        resultado = ValuationEngine().processar(dados)

    assert resultado['fair_value'] == pytest.approx(146.71, abs=0.01)
    assert resultado['metodos_usados'] == 'Bazin: R$146.71'


def test_dy_invalido_acima_25pct() -> None:
    """DY acima de 25% deve ser desconsiderado e marcado como não confiável."""
    dados = {
        'ticker': 'ITUB4',
        'preco_atual': 100.0,
        'roe': 0.25,
        'pl': 30.0,
        'pvp': 4.0,
        'dy': 0.45,
    }

    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        resultado = ValuationEngine().processar(dados)

    assert resultado['fair_value'] == 100.0
    assert resultado['metodos_usados'] == ''
    assert resultado['perfil'] == 'RENDA/VALOR'
    assert resultado['score_final'] == 55


def test_recomendacao_compra_forte_exige_upside() -> None:
    """Score alto com upside negativo não deve virar COMPRA FORTE."""
    dados = {
        'ticker': 'QUAL3',
        'preco_atual': 100.0,
        'roe': 0.10,
        'pl': 30.0,
        'pvp': 4.0,
        'dy': 0.068,
    }

    with (
        patch('valuation_engine.get_selic_atual', return_value=0.10),
        patch('valuation_engine.math.exp', return_value=0.2),
    ):
        resultado = ValuationEngine().processar(dados)

    assert resultado['score_final'] >= 75
    assert resultado['upside'] == pytest.approx(-20.0, abs=0.1)
    assert resultado['recomendacao'] != 'COMPRA FORTE'


def test_recomendacao_qualidade_aguardar() -> None:
    """Empresa boa mas cara deve retornar QUALIDADE — AGUARDAR."""
    dados = {
        'ticker': 'QUAL3',
        'preco_atual': 100.0,
        'roe': 0.10,
        'pl': 30.0,
        'pvp': 4.0,
        'dy': 0.0765,
    }

    with (
        patch('valuation_engine.get_selic_atual', return_value=0.10),
        patch('valuation_engine.math.exp', return_value=0.2),
    ):
        resultado = ValuationEngine().processar(dados)

    assert resultado['score_final'] >= 75
    assert resultado['upside'] == pytest.approx(-10.0, abs=0.1)
    assert resultado['recomendacao'] == 'QUALIDADE — AGUARDAR'


def test_graham_ignorado_pl_negativo() -> None:
    """pl_confiavel=False deve excluir Graham dos métodos usados."""
    dados = {
        'ticker': 'RUIM3',
        'preco_atual': 100.0,
        'roe': 0.0,
        'pl': 10.0,
        'pvp': 1.0,
        'dy': 0.0,
        'pl_confiavel': False,
    }

    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        resultado = ValuationEngine().processar(dados)

    assert 'Graham' not in resultado['metodos_usados']


def test_lynch_desconta_payout() -> None:
    """ROE 25% com payout 40% deve usar crescimento real próximo de 15%."""
    dados = {
        'ticker': 'GROW3',
        'preco_atual': 100.0,
        'roe': 0.25,
        'pl': 12.5,
        'pvp': 4.0,
        'dy': 0.032,
    }

    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        resultado = ValuationEngine().processar(dados)

    assert resultado['fair_value'] == pytest.approx(120.0, abs=0.01)
    assert 'Lynch: R$120.00' in resultado['metodos_usados']


def test_fii_score_penaliza_pvp_alto() -> None:
    """FII com P/VP 1.2 deve pontuar menos que FII com P/VP neutro."""
    dados_base = {
        'ticker': 'HGLG11',
        'preco_atual': 100.0,
        'dy': 0.12,
    }

    with patch('fii_engine.get_selic_atual', return_value=0.10):
        fii_pvp_alto = FIIEngine().analisar({**dados_base, 'pvp': 1.2})
        fii_pvp_neutro = FIIEngine().analisar({**dados_base, 'pvp': 0.95})

    assert fii_pvp_alto['score_final'] < fii_pvp_neutro['score_final']
