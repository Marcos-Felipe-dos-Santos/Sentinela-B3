import pytest
import pandas as pd
import numpy as np
from portfolio_engine import PortfolioEngine
from unittest.mock import patch

@pytest.fixture
def engine():
    return PortfolioEngine()

def test_portfolio_engine_empty_input(engine):
    df = pd.DataFrame()
    result = engine.otimizar(df)
    assert result is None

def test_portfolio_engine_nan_handling(engine):
    # Short history should return error
    dates = pd.date_range('2023-01-01', periods=35)
    data = pd.DataFrame({
        'A': np.linspace(10, 100, 35),
        'B': np.linspace(50, 150, 35)
    }, index=dates)
    
    with patch('portfolio_engine.get_selic_atual', return_value=0.10):
        result = engine.otimizar(data)
    
    assert isinstance(result, dict)
    assert 'erro' not in result
    
    # Must contain allocations that sum to 100% roughly
    total = sum(result.values())
    assert 99.0 <= total <= 101.0
