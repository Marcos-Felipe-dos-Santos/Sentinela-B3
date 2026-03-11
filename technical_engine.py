import pandas as pd
import numpy as np

class TechnicalEngine:
    def calcular_indicadores(self, historico: pd.DataFrame):
        if historico is None or historico.empty or len(historico) < 30:
            return {
                "rsi": 50, "momento": "Neutro",
                "tendencia": "Indefinida", "ma50": 0, "ma200": 0
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

        # Momento
        momento = "Neutro"
        if rsi > 70: momento = "Sobrecomprado (Alto Risco)"
        elif rsi < 30: momento = "Sobrevendido (Oportunidade)"

        # CORRIGIDO: tendência hierárquica com NaN guard.
        # Antes: `preco > ma200` com ma200=NaN sempre retornava False → "Baixa"
        # para qualquer ativo com menos de 200 dias de histórico (IPOs, splits).
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
        }