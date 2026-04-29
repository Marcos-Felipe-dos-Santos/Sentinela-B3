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

    assert resultado['fair_value'] == pytest.approx(124.7, abs=0.01)
    assert resultado['metodos_usados'] == 'Bazin: R$124.70'


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
    assert resultado['upside'] == pytest.approx(-32.0, abs=0.1)
    assert resultado['recomendacao'] == 'QUALIDADE — AGUARDAR'


def test_recomendacao_qualidade_aguardar() -> None:
    """Empresa boa mas cara deve retornar QUALIDADE — AGUARDAR."""
    dados = {
        'ticker': 'QUAL3',
        'preco_atual': 100.0,
        'roe': 0.10,
        'pl': 30.0,
        'pvp': 4.0,
        'dy': 0.09,
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

    assert resultado['fair_value'] == pytest.approx(180.0, abs=0.01)
    assert 'Lynch: R$180.00' in resultado['metodos_usados']


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

def test_divida_liq_ebitda_none() -> None:
    # divida_liq_ebitda=None does not crash
    dados = {
        'ticker': 'TEST3',
        'preco_atual': 10.0,
        'pvp': 1.0,
        'pl': 10.0,
        'dy': 0.05,
        'roe': 0.15,
        'divida_liq_ebitda': None
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        result = ValuationEngine().processar(dados)
    assert result is not None
    assert 'score_final' in result
    assert 0 <= result['score_final'] <= 100

def test_divida_liq_ebitda_malformed_string() -> None:
    # divida_liq_ebitda as malformed string does not crash
    dados = {
        'ticker': 'TEST3',
        'preco_atual': 10.0,
        'pvp': 1.0,
        'pl': 10.0,
        'dy': 0.05,
        'roe': 0.15,
        'divida_liq_ebitda': "abc,def"
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        result = ValuationEngine().processar(dados)
    assert result is not None
    assert 'score_final' in result

def test_divida_liq_ebitda_brazilian_format() -> None:
    # divida_liq_ebitda as "1.234,56" parses safely
    dados = {
        'ticker': 'TEST3',
        'preco_atual': 10.0,
        'pvp': 1.0,
        'pl': 10.0,
        'dy': 0.05,
        'roe': 0.15,
        'divida_liq_ebitda': "1.234,56"
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        result = ValuationEngine().processar(dados)
    assert result is not None
    assert 0 <= result['score_final'] <= 100

def test_valuation_engine_expected_keys() -> None:
    dados = {
        'ticker': 'TEST3',
        'preco_atual': 25.0,
        'pvp': 1.5,
        'pl': 8.0,
        'dy': 0.06,
        'roe': 0.18,
        'divida_liq_ebitda': 1.5
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        result = ValuationEngine().processar(dados)
    assert 'fair_value' in result
    assert 'upside' in result
    assert 'score_final' in result
    assert 'recomendacao' in result
    assert 'confianca' in result
    assert 'riscos' in result
    assert result['recomendacao'] in ['COMPRA FORTE', 'COMPRA', 'NEUTRO', 'VENDA', 'QUALIDADE — AGUARDAR']

def test_dy_muito_alto_penaliza_bazin() -> None:
    """DY acima de 15% deve reduzir a confiança por ser armadilha."""
    dados = {
        'ticker': 'TRAP3',
        'preco_atual': 100.0,
        'roe': 0.10,
        'pl': 5.0,
        'pvp': 1.0,
        'dy': 0.18,
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        resultado = ValuationEngine().processar(dados)
    
    assert "DY muito alto (possível armadilha)" in resultado['riscos']
    assert resultado['confianca'] < 100

def test_gordon_ignorado_k_menor_g() -> None:
    """Gordon Growth deve ser ignorado se o custo de capital (k) for menor ou igual ao crescimento (g)."""
    dados = {
        'ticker': 'FAST3',
        'preco_atual': 100.0,
        'roe': 0.90,  # Crescimento enorme
        'pl': 15.0,
        'pvp': 3.0,
        'dy': 0.05,
    }
    # g_uncapped = roe * retencao -> 0.90 * ~0.9 = ~0.81
    # g_capped = 0.08
    # k = selic + 0.04 -> 0.03 + 0.04 = 0.07
    # k < g
    with patch('valuation_engine.get_selic_atual', return_value=0.03):
        resultado = ValuationEngine().processar(dados)
    
    assert 'Gordon' not in resultado['metodos_usados']
