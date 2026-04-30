import numpy as np
import pandas as pd
from scipy.optimize import minimize
from config import FIIS_CONHECIDOS, UNITS_CONHECIDAS, get_selic_atual

class PortfolioEngine:
    def otimizar(self, dados_historicos: pd.DataFrame):
        """Otimização de Markowitz (Máximo Sharpe Ratio) segmentada."""
        if dados_historicos is None or dados_historicos.empty:
            return None

        df = dados_historicos.replace(0, np.nan).dropna()
        if len(df) < 30:
            return {"erro": "Dados insuficientes (mínimo 30 pregões)."}
        if (df <= 0).any().any():
            return {"erro": "Preços negativos ou zero detectados."}

        retornos = np.log(df / df.shift(1)).dropna()
        if retornos.empty:
            return {"erro": "Retornos vazios após limpeza."}

        risk_free = get_selic_atual()

        def otimizar_grupo(cols):
            ret = retornos[cols]
            if ret.empty or len(cols) == 0:
                return {}
            if len(cols) == 1:
                return {cols[0]: 1.0}

            medias = ret.mean() * 252
            cov_matrix = ret.cov() * 252
            num_ativos = len(cols)

            def neg_sharpe(pesos):
                ret_port = np.dot(medias, pesos)
                vol_port = np.sqrt(np.dot(pesos.T, np.dot(cov_matrix, pesos)))
                if vol_port == 0:
                    return 0
                return -((ret_port - risk_free) / vol_port)

            cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1},)
            bounds = tuple((0.0, 1.0) for _ in range(num_ativos))
            init = [1.0 / num_ativos] * num_ativos

            opt = minimize(neg_sharpe, init, method='SLSQP', bounds=bounds, constraints=cons)
            if not opt.success:
                return {c: 1.0 / num_ativos for c in cols}

            pesos_brutos = {col: p for col, p in zip(cols, opt.x) if p > 0.01}
            total = sum(pesos_brutos.values())
            if total == 0:
                return {c: 1.0 / num_ativos for c in cols}

            return {c: p / total for c, p in pesos_brutos.items()}

        def _is_fii(ticker: str) -> bool:
            return (
                ticker in FIIS_CONHECIDOS
                or (ticker.endswith('11') and ticker not in UNITS_CONHECIDAS)
            )

        try:
            fiis = [c for c in df.columns if _is_fii(c)]
            stocks = [c for c in df.columns if not _is_fii(c)]

            if fiis and stocks:
                pesos_fiis = otimizar_grupo(fiis)
                pesos_stocks = otimizar_grupo(stocks)
                resultado = {col: round(p * 40, 1) for col, p in pesos_fiis.items()}
                resultado.update({col: round(p * 60, 1) for col, p in pesos_stocks.items()})
                return resultado
            elif fiis:
                pesos_fiis = otimizar_grupo(fiis)
                return {col: round(p * 100, 1) for col, p in pesos_fiis.items()}
            elif stocks:
                pesos_stocks = otimizar_grupo(stocks)
                return {col: round(p * 100, 1) for col, p in pesos_stocks.items()}
            else:
                return {"erro": "Nenhum ativo para otimizar."}
        except Exception as e:
            return {"erro": f"Erro interno: {e}"}
