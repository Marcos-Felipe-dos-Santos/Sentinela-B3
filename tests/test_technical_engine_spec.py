import pytest
import pandas as pd
from technical_engine import TechnicalEngine


@pytest.fixture
def engine():
    return TechnicalEngine()

# Preços base para testes de especificação (50 períodos)
FECHAMENTOS = [
    100.5, 100.36, 101.01, 102.53, 102.3, 102.06, 103.64, 104.41, 103.94, 104.48,
    104.02, 103.55, 103.79, 101.88, 100.16, 99.59, 98.58, 98.89, 97.99, 96.57,
    98.04, 97.81, 97.88, 96.46, 95.91, 96.02, 94.87, 95.25, 94.65, 94.36,
    93.75, 95.61, 95.59, 94.53, 95.36, 94.14, 94.35, 92.39, 91.06, 91.25,
    91.99, 92.16, 92.05, 91.75, 90.27, 89.55, 89.09, 90.15, 90.49, 88.73
]

ALTAS = [
    100.78, 101.96, 101.16, 104.5, 103.84, 102.46, 103.65, 106.04, 105.35, 105.94,
    105.56, 103.7, 104.51, 102.11, 101.88, 100.84, 99.24, 99.02, 98.61, 97.22,
    99.5, 99.09, 99.66, 97.4, 96.15, 97.45, 96.39, 96.37, 96.19, 95.34,
    94.8, 96.46, 95.64, 94.75, 95.42, 95.41, 94.97, 93.4, 92.87, 91.75,
    92.81, 93.68, 92.51, 91.9, 90.85, 89.87, 90.95, 91.76, 91.76, 90.47
]

BAIXAS = [
    98.89, 99.99, 99.22, 101.45, 100.68, 100.27, 103.0, 104.19, 103.48, 103.63,
    102.38, 101.83, 103.78, 100.86, 99.32, 99.15, 98.34, 98.22, 96.1, 95.93,
    97.0, 96.41, 97.15, 94.51, 93.99, 95.52, 93.88, 94.65, 94.08, 94.28,
    92.53, 94.6, 95.49, 93.98, 93.54, 93.66, 94.06, 91.41, 89.09, 90.77,
    90.65, 90.64, 91.57, 90.29, 89.53, 88.28, 87.82, 89.07, 90.31, 87.06
]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: retorna 50 em vez de 100")
def test_rsi_sem_perdas_e_100(engine):
    """
    Especificação: Wilder RSI.
    Fonte: "New Concepts in Technical Trading Systems" (1978), J. Welles Wilder Jr.
    Sem perdas na janela de 14 períodos (e havendo ganhos), o RS é infinito e o RSI é 100.
    """
    # 50 períodos de preços estritamente crescentes
    precos = [100.0 + i for i in range(50)]
    historico = pd.DataFrame({'Close': precos})

    resultado = engine.calcular_indicadores(historico)

    assert resultado["rsi"] == 100.0


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: ewm(adjust=False) parte do 1o valor, não da média")
def test_rsi_valor_de_referencia_wilder(engine):
    """
    Especificação: Wilder RSI.
    Fonte: https://school.stockcharts.com/doku.php?id=technical_indicators:relative_strength_index_rsi
    O RSI de Wilder original calcula os primeiros 14 períodos como média simples
    dos ganhos/perdas, e depois aplica a suavização de Wilder
    (AvgGain = (PrevAvgGain * 13 + CurrentGain) / 14).
    """
    historico = pd.DataFrame({'Close': FECHAMENTOS})

    # Valor calculado exatamente pelas regras do ChartSchool para esta série (tolerância 1 casa decimal)
    resultado = engine.calcular_indicadores(historico)
    assert pytest.approx(resultado["rsi"], abs=0.1) == 30.0


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: ewm(adjust=False) não começa da SMA dos N períodos")
def test_macd_valores_de_referencia(engine):
    """
    Especificação: MACD (12, 26, 9).
    Fonte: https://school.stockcharts.com/doku.php?id=technical_indicators:moving_average_convergence_divergence_macd
    A primeira EMA (no período N) deve ser a média móvel simples dos primeiros N períodos.
    """
    historico = pd.DataFrame({'Close': FECHAMENTOS})

    # Valores de referência para MACD (50 períodos dá suporte suficiente para 9 períodos de linha de sinal)
    # Tolerância de 2 casas decimais, conforme arredondamento do engine
    resultado = engine.calcular_indicadores(historico)
    assert pytest.approx(resultado["macd_line"], abs=0.01) == -2.17
    assert pytest.approx(resultado["macd_signal"], abs=0.01) == -2.18
    assert pytest.approx(resultado["macd_hist"], abs=0.01) == 0.01


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: usa desvio-padrão amostral (ddof=1) em vez de populacional")
def test_bollinger_usa_desvio_populacional(engine):
    """
    Especificação: Bollinger Bands (20, 2).
    Fonte: https://school.stockcharts.com/doku.php?id=technical_indicators:bollinger_bands
    A definição padrão usa desvio-padrão populacional (dividido por N).
    """
    historico = pd.DataFrame({'Close': FECHAMENTOS})

    # 20 últimos períodos: desvio populacional (ddof=0) dão exatamente 96.49 e 87.94
    resultado = engine.calcular_indicadores(historico)
    assert pytest.approx(resultado["bb_upper"], abs=0.01) == 96.49
    assert pytest.approx(resultado["bb_lower"], abs=0.01) == 87.94


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: usa média simples em vez da suavização de Wilder")
def test_atr_suavizacao_de_wilder(engine):
    """
    Especificação: Average True Range (ATR, 14 períodos).
    Fonte: https://school.stockcharts.com/doku.php?id=technical_indicators:average_true_range_atr
    O TR inicial é a média simples dos 14 primeiros TRs. Depois aplica-se
    a suavização de Wilder: ATR_i = (ATR_i-1 * 13 + TR_i) / 14.
    """
    historico = pd.DataFrame({
        'Close': FECHAMENTOS,
        'High': ALTAS,
        'Low': BAIXAS
    })

    # O valor correto gerado pela especificação do ChartSchool/Wilder para essa série: 2.21
    resultado = engine.calcular_indicadores(historico)
    assert pytest.approx(resultado["atr"], abs=0.01) == 2.21
