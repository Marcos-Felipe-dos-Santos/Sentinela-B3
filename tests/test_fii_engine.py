import pytest
from fii_engine import FIIEngine, VACANCIA_CONHECIDA
from unittest.mock import patch


class FakeFIIProvider:
    """CVMFIIProvider stub para testes de FIIEngine."""

    def __init__(self, resultado=None):
        self._resultado = resultado

    def obter_dados_fii(self, cnpj: str) -> dict | None:
        return self._resultado


@pytest.fixture
def engine():
    # CVM desabilitado por padrão — sem chamadas de rede
    return FIIEngine(cvm_provider=None)

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
    assert result['fair_value'] == pytest.approx(105.88, abs=0.01) # (100 * 0.09) / (0.10 * 0.85) ≈ 105.88


# ── Teste de baseline para bug conhecido ─────────────────────────────────────

def test_fii_preco_justo_desconta_ir_selic_liquida(engine):
    """FII é isento de IR: comparar com Selic*0.85, não Selic bruta.

    Com selic=0.10 e dy=0.10:
      BUG:  fair_value = (100 * 0.10) / 0.10        = 100.00
      FIX:  fair_value = (100 * 0.10) / (0.10*0.85) ≈ 117.65
    """
    dados = {
        'ticker': 'FIIX11',
        'preco_atual': 100.0,
        'dy': 0.10,
        'pvp': 1.0,
    }
    with patch('fii_engine.get_selic_atual', return_value=0.10):
        result = engine.analisar(dados)

    assert result['fair_value'] == pytest.approx(117.65, abs=0.01)


# ---------------------------------------------------------------------------
# CVM FII integration tests
# ---------------------------------------------------------------------------

def test_fii_cvm_vpa_substitui_pvp_dados():
    """VPA da CVM (Valor_Patrimonial_Cotas) deve substituir o pvp dos dados."""
    engine = FIIEngine(cvm_provider=FakeFIIProvider({
        'valor_cota':        155.0,
        'patrimonio_liquido': 1_550_000_000.0,
        'vacancia_fisica':   None,
    }))
    dados = {'ticker': 'XPML11', 'preco_atual': 150.0, 'pvp': 0.9, 'dy': 0.08}

    with patch('fii_engine.get_selic_atual', return_value=0.10):
        result = engine.analisar(dados)

    assert result is not None
    assert result['pvp'] == pytest.approx(150.0 / 155.0)  # CVM VPA, não Yahoo pvp


def test_fii_cvm_vacancia_disponivel_usa_cvm():
    """Quando CVM fornece vacância, deve ter precedência sobre VACANCIA_CONHECIDA."""
    # HGLG11 está em VACANCIA_CONHECIDA com 0.08; CVM simula 0.12
    engine = FIIEngine(cvm_provider=FakeFIIProvider({
        'valor_cota':      None,
        'vacancia_fisica': 0.12,
    }))
    dados = {'ticker': 'HGLG11', 'preco_atual': 150.0, 'dy': 0.08, 'pvp': 0.9}

    with patch('fii_engine.get_selic_atual', return_value=0.10):
        result = engine.analisar(dados)

    assert result['vacancia_fonte'] == 'CVM'
    assert result['dy_efetivo'] == pytest.approx(0.08 * (1 - 0.12))


def test_fii_vacancia_manual_tem_flag():
    """VACANCIA_CONHECIDA como fallback deve marcar vacancia_fonte='manual'."""
    engine = FIIEngine(cvm_provider=None)
    dados = {'ticker': 'HGLG11', 'preco_atual': 150.0, 'dy': 0.08, 'pvp': 0.9}

    with patch('fii_engine.get_selic_atual', return_value=0.10):
        result = engine.analisar(dados)

    assert result['vacancia_fonte'] == 'manual'
    assert result['dy_efetivo'] == pytest.approx(0.08 * (1 - VACANCIA_CONHECIDA['HGLG11']))


def test_fii_cvm_falha_graceful():
    """Exceção no CVMFIIProvider não deve impedir a análise — usa pvp dos dados."""
    class ErrorProvider:
        def obter_dados_fii(self, cnpj):
            raise RuntimeError("CVM offline")

    engine = FIIEngine(cvm_provider=ErrorProvider())
    dados = {'ticker': 'HGLG11', 'preco_atual': 150.0, 'dy': 0.08, 'pvp': 0.9}

    with patch('fii_engine.get_selic_atual', return_value=0.10):
        result = engine.analisar(dados)

    assert result is not None
    assert result['pvp'] == pytest.approx(0.9)  # fallback to dados pvp
