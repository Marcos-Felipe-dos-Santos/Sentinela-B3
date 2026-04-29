import pytest
from fii_engine import FIIEngine
from unittest.mock import patch

@pytest.fixture
def engine():
    return FIIEngine()

def test_fii_engine_valid_input(engine):
    dados = {
        'ticker': 'HGLG11',
        'preco_atual': 150.0,
        'pvp': 0.9,
        'dy': 0.08
    }
    with patch('fii_engine.get_selic_atual', return_value=0.10):
        result = engine.analisar(dados)
    assert result is not None
    assert 'fair_value' in result
    assert 'upside' in result
    assert 'score_final' in result
    assert 'recomendacao' in result
    assert 'tipo' in result
    assert result['tipo'] == 'TIPO INDISPONÍVEL'
    assert 0 <= result['score_final'] <= 100

def test_fii_engine_missing_optional_values(engine):
    dados = {
        'ticker': 'HGLG11',
        'preco_atual': 150.0,
        # missing pvp and dy
    }
    with patch('fii_engine.get_selic_atual', return_value=0.10):
        result = engine.analisar(dados)
    
    assert result is not None
    # Will fallback due to missing dy
    assert result['metodos_usados'] == 'Dados insuficientes (DY ausente ou inválido)'
    assert result['recomendacao'] == 'NEUTRO'
    assert result['score_final'] == 50

def test_fii_engine_vacancy_adjustment(engine):
    import fii_engine
    fii_engine.VACANCIA_CONHECIDA['VAC11'] = 0.10
    
    dados = {
        'ticker': 'VAC11',
        'preco_atual': 100.0,
        'pvp': 1.0,
        'dy': 0.10
    }
    with patch('fii_engine.get_selic_atual', return_value=0.10):
        result = engine.analisar(dados)
        
    assert result['dy'] == pytest.approx(0.10)
    assert result['dy_efetivo'] == pytest.approx(0.09) # 0.10 * (1 - 0.10)
    assert result['fair_value'] == pytest.approx(90.0) # (100 * 0.09) / 0.10
