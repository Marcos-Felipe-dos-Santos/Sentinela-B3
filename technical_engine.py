import pandas as pd
import numpy as np

class TechnicalEngine:
    def calcular_indicadores(self, historico: pd.DataFrame):
        if historico is None or historico.empty or len(historico) < 30 or 'Close' not in historico.columns:
            return {
                "rsi": 50, "momento": "Neutro",
                "tendencia": "Indefinida", "ma50": 0, "ma200": 0,
                "macd_line": 0, "macd_signal": 0, "macd_hist": 0, "macd_rec": "Neutro",
                "bb_upper": 0, "bb_lower": 0, "bb_signal": "Neutro",
                "atr": 0.0
            }

        close = historico['Close']
        preco = close.iloc[-1]

        # RSI — seguro contra divisão por zero e flat prices
        delta = close.diff()
        gain  = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
        loss  = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs    = gain / loss.replace(0, np.nan)
        rsi   = (100 - (100 / (1 + rs))).fillna(50).iloc[-1]

        # Médias móveis
        ma50  = close.rolling(50).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1]
        
        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - macd_signal
        
        macd_rec = "Neutro"
        if len(macd_hist) >= 2:
            if macd_hist.iloc[-1] > 0 and macd_hist.iloc[-2] <= 0:
                macd_rec = "Compra (Cruzamento Alta)"
            elif macd_hist.iloc[-1] < 0 and macd_hist.iloc[-2] >= 0:
                macd_rec = "Venda (Cruzamento Baixa)"
            elif macd_hist.iloc[-1] > 0:
                macd_rec = "Alta"
            elif macd_hist.iloc[-1] < 0:
                macd_rec = "Baixa"

        # Bollinger Bands
        sma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        bb_upper = sma20 + (std20 * 2)
        bb_lower = sma20 - (std20 * 2)
        
        bb_upper_val = bb_upper.iloc[-1]
        bb_lower_val = bb_lower.iloc[-1]
        
        bb_signal = "Neutro"
        if not np.isnan(bb_upper_val) and preco > bb_upper_val:
            bb_signal = "Sobrecomprado (Rompimento Alta)"
        elif not np.isnan(bb_lower_val) and preco < bb_lower_val:
            bb_signal = "Sobrevendido (Rompimento Baixa)"

        # ATR — Average True Range (14 períodos)
        atr_val = 0.0
        if 'High' in historico.columns and 'Low' in historico.columns:
            high = historico['High']
            low  = historico['Low']
            tr   = pd.concat([
                high - low,
                (high - close.shift(1)).abs(),
                (low  - close.shift(1)).abs()
            ], axis=1).max(axis=1)
            atr_raw = tr.rolling(14).mean().iloc[-1]
            atr_val = round(float(atr_raw), 2) if not np.isnan(atr_raw) else 0.0

        # Momento
        momento = "Neutro"
        if rsi > 70:
            momento = "Sobrecomprado (Alto Risco)"
        elif rsi < 30:
            momento = "Sobrevendido (Oportunidade)"

        # CORRIGIDO: tendência hierárquica com NaN guard.
        tendencia = "Indefinida"
        if not np.isnan(ma200):
            tendencia = "Alta (Longo Prazo)"  if preco > ma200 else "Baixa (Longo Prazo)"
        elif not np.isnan(ma50):
            tendencia = "Alta (Curto Prazo)"  if preco > ma50  else "Baixa (Curto Prazo)"

        return {
            "rsi":      round(rsi, 1),
            "momento":  momento,
            "tendencia": tendencia,
            "ma50":     round(ma50,  2) if not np.isnan(ma50)  else 0,
            "ma200":    round(ma200, 2) if not np.isnan(ma200) else 0,
            "macd_line": round(macd_line.iloc[-1], 2) if not np.isnan(macd_line.iloc[-1]) else 0,
            "macd_signal": round(macd_signal.iloc[-1], 2) if not np.isnan(macd_signal.iloc[-1]) else 0,
            "macd_hist": round(macd_hist.iloc[-1], 2) if not np.isnan(macd_hist.iloc[-1]) else 0,
            "macd_rec": macd_rec,
            "bb_upper": round(bb_upper_val, 2) if not np.isnan(bb_upper_val) else 0,
            "bb_lower": round(bb_lower_val, 2) if not np.isnan(bb_lower_val) else 0,
            "bb_signal": bb_signal,
            "atr": atr_val
        }
