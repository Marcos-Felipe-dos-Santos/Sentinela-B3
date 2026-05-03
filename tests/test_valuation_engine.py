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
    assert 'dy_confiavel' in result
    assert isinstance(result['dy_confiavel'], bool)
    assert result['recomendacao'] in [
        'COMPRA FORTE', 'COMPRA', 'NEUTRO', 'VENDA',
        'QUALIDADE — AGUARDAR', 'ALTO RISCO — EVITAR',
        'DADOS INSUFICIENTES — AGUARDAR',
    ]

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
    # k = selic + 0.07 -> 0.01 + 0.07 = 0.08
    # k <= g
    with patch('valuation_engine.get_selic_atual', return_value=0.01):
        resultado = ValuationEngine().processar(dados)
    
    assert 'Gordon' not in resultado['metodos_usados']


# ── Testes de guards de segurança ────────────────────────────────────────────

def test_distressed_ticker_retorna_alto_risco() -> None:
    """Ticker distressed (AMER3) deve retornar ALTO RISCO — EVITAR, nunca COMPRA."""
    dados = {
        'ticker': 'AMER3',
        'preco_atual': 5.69,
        'roe': 0.02,
        'pl': 8.5,
        'pvp': 0.24,
        'dy': 0.0,
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.145):
        resultado = ValuationEngine().processar(dados)

    assert resultado['recomendacao'] == 'ALTO RISCO — EVITAR'
    assert resultado['score_final'] <= 45
    assert resultado['confianca'] == 0
    assert 'Empresa em situação especial/distressed' in resultado['riscos']


def test_distressed_ticker_nunca_compra_forte() -> None:
    """Mesmo com dados excelentes, distressed não pode virar COMPRA FORTE."""
    dados = {
        'ticker': 'OIBR3',
        'preco_atual': 0.11,
        'roe': 0.30,
        'pl': 3.0,
        'pvp': 0.5,
        'dy': 0.10,
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.10):
        resultado = ValuationEngine().processar(dados)

    assert resultado['recomendacao'] not in ('COMPRA', 'COMPRA FORTE')
    assert resultado['recomendacao'] == 'ALTO RISCO — EVITAR'


def test_scraper_falhou_compra_vira_dados_insuficientes() -> None:
    """Scraper failure + COMPRA deve virar DADOS INSUFICIENTES — AGUARDAR."""
    dados = {
        'ticker': 'ITUB4',
        'preco_atual': 42.87,
        'roe': 0.21,
        'pl': 10.69,
        'pvp': 2.31,
        'dy': 0.0124,
        'erro_scraper': True,
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.145):
        resultado = ValuationEngine().processar(dados)

    assert resultado['recomendacao'] == 'DADOS INSUFICIENTES — AGUARDAR'
    assert resultado['confianca'] <= 50
    assert 'Dados fundamentais insuficientes para análise precisa' in resultado['riscos']
    # Valores calculados são preservados para transparência
    assert resultado['fair_value'] > 0
    assert resultado['score_final'] > 0


def test_scraper_falhou_nao_sobrescreve_venda() -> None:
    """Scraper failure não deve sobrescrever VENDA — VENDA tem prioridade."""
    dados = {
        'ticker': 'LIXO3',
        'preco_atual': 100.0,
        'roe': 0.02,
        'pl': 50.0,
        'pvp': 5.0,
        'dy': 0.01,
        'erro_scraper': True,
        'tecnico_negativo': True,
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.145):
        resultado = ValuationEngine().processar(dados)

    # upside < -15% + tecnico_negativo = VENDA; scraper guard não interfere
    assert resultado['recomendacao'] != 'DADOS INSUFICIENTES — AGUARDAR'


def test_scraper_falhou_nao_sobrescreve_alto_risco() -> None:
    """Scraper failure não deve sobrescrever ALTO RISCO — EVITAR."""
    dados = {
        'ticker': 'AMER3',
        'preco_atual': 5.69,
        'roe': 0.02,
        'pl': 8.5,
        'pvp': 0.24,
        'dy': 0.0,
        'erro_scraper': True,
    }
    with patch('valuation_engine.get_selic_atual', return_value=0.145):
        resultado = ValuationEngine().processar(dados)

    # Distressed guard fires first — must remain ALTO RISCO
    assert resultado['recomendacao'] == 'ALTO RISCO — EVITAR'
