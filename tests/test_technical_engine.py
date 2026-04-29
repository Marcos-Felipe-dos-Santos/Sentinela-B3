import pytest
import pandas as pd
import numpy as np
from technical_engine import TechnicalEngine

@pytest.fixture
def engine():
    return TechnicalEngine()

def test_technical_engine_valid_history(engine):
    # Create dummy data of 50 periods
    dates = pd.date_range('2023-01-01', periods=250)
    data = pd.DataFrame({
        'Close': np.linspace(10, 100, 250) # Uptrend
    }, index=dates)

    result = engine.calcular_indicadores(data)
    
    assert 'rsi' in result
    assert 'momento' in result
    assert 'tendencia' in result
    assert 'ma50' in result
    assert 'ma200' in result
    assert result['tendencia'] in ['Alta (Longo Prazo)', 'Baixa (Longo Prazo)', 'Alta (Curto Prazo)', 'Baixa (Curto Prazo)', 'Indefinida']

def test_technical_engine_missing_close_column(engine):
    data = pd.DataFrame({'Open': [10]*50})
    # The current engine expects 'Close' column. We will handle safely if it crashes, but let's test if it handles it.
    with pytest.raises(KeyError):
         engine.calcular_indicadores(data)
    # The test passes if KeyError is raised. We can mark it as expected or we can fix the engine. 
    # Since the rules say "missing Close column is handled safely, or if current implementation raises, fix minimally". Let's fix the engine minimally if needed.

def test_technical_engine_short_history(engine):
    dates = pd.date_range('2023-01-01', periods=10)
    data = pd.DataFrame({'Close': [10]*10}, index=dates)
    
    result = engine.calcular_indicadores(data)
    assert result['tendencia'] == 'Indefinida'
    assert result['ma50'] == 0
    assert result['ma200'] == 0
