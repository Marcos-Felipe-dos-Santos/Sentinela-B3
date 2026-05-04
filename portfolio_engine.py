import numpy as np
import pandas as pd
from scipy.optimize import minimize
from config import FIIS_CONHECIDOS, UNITS_CONHECIDAS, get_selic_atual


class PortfolioResult(dict):
    """Dict de resultado que mantém metadados fora de values()."""

    def values(self):
        return [
            value
            for key, value in super().items()
            if not str(key).startswith('_')
        ]


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

        def _metricas_portfolio(pesos_decimais: dict) -> dict:
            if not pesos_decimais:
                return {
                    '_sharpe_otimizado': 0.0,
                    '_retorno_anual': 0.0,
                    '_volatilidade_anual': 0.0,
                }

            cols = list(pesos_decimais.keys())
            pesos_opt = np.array([pesos_decimais[col] for col in cols], dtype=float)
            ret = retornos[cols]
            medias = ret.mean() * 252
            cov_matrix = ret.cov() * 252
            ret_opt = float(np.dot(medias, pesos_opt))
            vol_opt = float(np.sqrt(np.dot(pesos_opt.T, np.dot(cov_matrix, pesos_opt))))
            if not np.isfinite(ret_opt):
                ret_opt = 0.0
            if not np.isfinite(vol_opt):
                vol_opt = 0.0
            sharpe_opt = round((ret_opt - risk_free) / vol_opt, 3) if vol_opt > 0 else 0.0

            return {
                '_sharpe_otimizado': sharpe_opt,
                '_retorno_anual': round(ret_opt * 100, 1),
                '_volatilidade_anual': round(vol_opt * 100, 1),
            }

        def otimizar_grupo(cols):
            ret = retornos[cols]
            if ret.empty or len(cols) == 0:
                return {}, _metricas_portfolio({})
            if len(cols) == 1:
                pesos = {cols[0]: 1.0}
                return pesos, _metricas_portfolio(pesos)

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
            limite_superior = 0.95 if num_ativos == 2 else 0.35
            bounds = tuple((0.05, limite_superior) for _ in range(num_ativos))
            init = [1.0 / num_ativos] * num_ativos

            opt = minimize(neg_sharpe, init, method='SLSQP', bounds=bounds, constraints=cons)
            if not opt.success:
                pesos = {c: 1.0 / num_ativos for c in cols}
                return pesos, _metricas_portfolio(pesos)

            pesos_brutos = {col: p for col, p in zip(cols, opt.x) if p > 0.01}
            pesos_opt = opt.x
            ret_opt = float(np.dot(medias, pesos_opt))
            vol_opt = float(np.sqrt(np.dot(pesos_opt.T, np.dot(cov_matrix, pesos_opt))))
            sharpe_opt = round((ret_opt - risk_free) / vol_opt, 3) if vol_opt > 0 else 0.0
            metricas = {
                '_sharpe_otimizado': sharpe_opt,
                '_retorno_anual': round(ret_opt * 100, 1),
                '_volatilidade_anual': round(vol_opt * 100, 1),
            }
            total = sum(pesos_brutos.values())
            if total == 0:
                pesos = {c: 1.0 / num_ativos for c in cols}
                return pesos, _metricas_portfolio(pesos)

            return {c: p / total for c, p in pesos_brutos.items()}, metricas

        def _is_fii(ticker: str) -> bool:
            return (
                ticker in FIIS_CONHECIDOS
                or (ticker.endswith('11') and ticker not in UNITS_CONHECIDAS)
            )

        try:
            fiis = [c for c in df.columns if _is_fii(c)]
            stocks = [c for c in df.columns if not _is_fii(c)]

            if fiis and stocks:
                pesos_fiis, _ = otimizar_grupo(fiis)
                pesos_stocks, _ = otimizar_grupo(stocks)
                resultado = PortfolioResult(
                    {col: round(p * 40, 1) for col, p in pesos_fiis.items()}
                )
                resultado.update({col: round(p * 60, 1) for col, p in pesos_stocks.items()})
                resultado.update(
                    _metricas_portfolio({col: p / 100 for col, p in resultado.items()})
                )
                return resultado
            elif fiis:
                pesos_fiis, metricas = otimizar_grupo(fiis)
                resultado = PortfolioResult(
                    {col: round(p * 100, 1) for col, p in pesos_fiis.items()}
                )
                resultado.update(metricas)
                return resultado
            elif stocks:
                pesos_stocks, metricas = otimizar_grupo(stocks)
                resultado = PortfolioResult(
                    {col: round(p * 100, 1) for col, p in pesos_stocks.items()}
                )
                resultado.update(metricas)
                return resultado
            else:
                return {"erro": "Nenhum ativo para otimizar."}
        except Exception as e:
            return {"erro": f"Erro interno: {e}"}
