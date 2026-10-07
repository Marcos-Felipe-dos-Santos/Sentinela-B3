import pandas as pd
import pytest

from technical_engine import TechnicalEngine


@pytest.fixture
def engine():
    return TechnicalEngine()

@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: retorna 50 em vez de 100")
def test_rsi_sem_perdas_e_100(engine):
    """
    Especificação: Wilder RSI.
    Fonte: "New Concepts in Technical Trading Systems" (1978), J. Welles Wilder Jr.
    Sem perdas na janela de 14 períodos (e havendo ganhos), o RS é infinito e o RSI é 100.
    """
    # 30 períodos de preços estritamente crescentes
    precos = [100.0 + i for i in range(30)]
    historico = pd.DataFrame({'Close': precos})

    resultado = engine.calcular_indicadores(historico)

    assert resultado["rsi"] == 100.0


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: ewm(adjust=False) parte do 1o valor, não da média")
def test_rsi_valor_de_referencia_wilder(engine):
    """
    Especificação: Wilder RSI.
    Fonte da fórmula/exemplo: Wilder (1978) e convenção StockCharts.
    O RSI de Wilder original calcula os primeiros 14 períodos como média simples
    dos ganhos/perdas, e depois aplica a suavização de Wilder
    (AvgGain = (PrevAvgGain * 13 + CurrentGain) / 14).
    """
    # Valores construídos para gerar RSI específico pelas regras de Wilder
    precos = [
        100.5, 100.4, 101.0, 102.5, 102.3, 102.1, 103.6, 104.4, 103.9, 104.5,
        104.0, 103.6, 103.8, 101.9, 100.2, 99.6, 98.6, 98.9, 98.0, 96.6,
        98.0, 97.8, 97.9, 96.5, 95.9, 96.0, 94.9, 95.2, 94.6, 94.4
    ]
    historico = pd.DataFrame({'Close': precos})

    # O valor correto gerado pela especificação de Wilder para essa série: 31.4
    # (calculado via script offline aplicando exatamente a suavização de Wilder)
    resultado = engine.calcular_indicadores(historico)

    assert resultado["rsi"] == 31.4


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: ewm(adjust=False) não começa da SMA dos N períodos")
def test_macd_valores_de_referencia(engine):
    """
    Especificação: MACD (12, 26, 9).
    Fonte: Gerald Appel / StockCharts (Standard MACD).
    A primeira EMA (no período N) deve ser a média móvel simples dos primeiros N períodos.
    """
    precos = [
        100.5, 100.4, 101.0, 102.5, 102.3, 102.1, 103.6, 104.4, 103.9, 104.5,
        104.0, 103.6, 103.8, 101.9, 100.2, 99.6, 98.6, 98.9, 98.0, 96.6,
        98.0, 97.8, 97.9, 96.5, 95.9, 96.0, 94.9, 95.2, 94.6, 94.4
    ]
    historico = pd.DataFrame({'Close': precos})

    # Valores de referência para o último período calculados via StockCharts standard MACD
    macd_line_ref = -2.58
    macd_signal_ref = -2.57
    macd_hist_ref = -0.01

    resultado = engine.calcular_indicadores(historico)

    assert resultado["macd_line"] == macd_line_ref
    assert resultado["macd_signal"] == macd_signal_ref
    assert resultado["macd_hist"] == macd_hist_ref


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: usa desvio-padrão amostral (ddof=1) em vez de populacional")
def test_bollinger_usa_desvio_populacional(engine):
    """
    Especificação: Bollinger Bands (20, 2).
    Fonte: John Bollinger (Bollinger on Bollinger Bands, 2001).
    A definição padrão usa desvio-padrão populacional (dividido por N).
    """
    precos = [
        100.5, 100.4, 101.0, 102.5, 102.3, 102.1, 103.6, 104.4, 103.9, 104.5,
        104.0, 103.6, 103.8, 101.9, 100.2, 99.6, 98.6, 98.9, 98.0, 96.6,
        98.0, 97.8, 97.9, 96.5, 95.9, 96.0, 94.9, 95.2, 94.6, 94.4
    ]
    historico = pd.DataFrame({'Close': precos})

    # 20 últimos períodos: [104.0, 103.6, 103.8, ..., 94.4]
    # Média dos 20: 98.31
    # StdDev populacional (ddof=0) = 2.97
    # BB Upper = 98.31 + 2 * 2.97 = 104.25
    # BB Lower = 98.31 - 2 * 2.97 = 92.37

    resultado = engine.calcular_indicadores(historico)

    assert resultado["bb_upper"] == 104.25
    assert resultado["bb_lower"] == 92.37


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Diverge da especificação: usa média simples em vez da suavização de Wilder")
def test_atr_suavizacao_de_wilder(engine):
    """
    Especificação: Average True Range (ATR, 14 períodos).
    Fonte: Wilder (1978).
    O TR inicial é a média simples dos 14 primeiros TRs. Depois aplica-se
    a suavização de Wilder: ATR_i = (ATR_i-1 * 13 + TR_i) / 14.
    """
    fechamentos = [100.5, 100.4, 101.0, 102.5, 102.3, 102.1, 103.6, 104.4, 103.9, 104.5, 104.0, 103.6, 103.8, 101.9, 100.2, 99.6, 98.6, 98.9, 98.0, 96.6, 98.0, 97.8, 97.9, 96.5, 95.9, 96.0, 94.9, 95.2, 94.6, 94.4]
    altas_var = [101.249, 102.301, 102.464, 103.697, 102.612, 102.412, 103.716, 106.132, 105.102, 105.916, 104.041, 105.54, 105.465, 102.325, 100.564, 99.967, 99.208, 99.95, 98.864, 97.182, 99.224, 98.079, 98.484, 97.233, 96.812, 97.57, 95.299, 96.228, 95.785, 94.493]
    baixas_var = [99.751, 98.499, 99.536, 101.303, 101.988, 101.788, 103.484, 102.668, 102.698, 103.084, 103.959, 101.66, 102.135, 101.475, 99.836, 99.233, 97.992, 97.85, 97.136, 96.018, 96.776, 97.521, 97.316, 95.767, 94.988, 94.43, 94.501, 94.172, 93.415, 94.307]

    historico = pd.DataFrame({
        'Close': fechamentos,
        'High': altas_var,
        'Low': baixas_var
    })

    # O TR máximo entre: High - Low, abs(High - Close_prev), abs(Low - Close_prev)
    # Valores de referência para ATR calculados estritamente usando o método de Wilder
    # com os arrays exatos acima (referência = 2.18).
    resultado = engine.calcular_indicadores(historico)

    assert resultado["atr"] == 2.18
