import numpy as np
import pandas as pd
from scipy.optimize import minimize
from config import get_selic_atual

class PortfolioEngine:
    def otimizar(self, dados_historicos: pd.DataFrame):
        """Otimização de Markowitz (Máximo Sharpe Ratio)."""
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

        # CORRIGIDO: taxa livre de risco dinâmica (era RISK_FREE_RATE estático=10.75%
        # enquanto a Selic real está em ~13.25%, inflando artificialmente o Sharpe).
        risk_free   = get_selic_atual()

        # CORRIGIDO: médias pré-computadas e reutilizadas na função objetivo.
        # Antes: retornos.mean() era recalculado em cada uma das ~48 chamadas do SLSQP.
        medias      = retornos.mean() * 252
        cov_matrix  = retornos.cov() * 252
        num_ativos  = len(medias)

        if num_ativos < 2:
            return {"erro": "Mínimo de 2 ativos para otimização."}

        def neg_sharpe(pesos):
            ret_port = np.dot(medias, pesos)  # usa pré-computado
            vol_port = np.sqrt(np.dot(pesos.T, np.dot(cov_matrix, pesos)))
            if vol_port == 0:
                return 0
            return -((ret_port - risk_free) / vol_port)

        cons   = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1},)
        bounds = tuple((0.0, 1.0) for _ in range(num_ativos))
        init   = [1.0 / num_ativos] * num_ativos

        try:
            opt = minimize(neg_sharpe, init, method='SLSQP',
                           bounds=bounds, constraints=cons)
            if not opt.success:
                return {"erro": f"Otimização falhou: {opt.message}"}

            # Filtra pesos < 1% e renormaliza
            pesos_brutos = {col: p for col, p in zip(df.columns, opt.x) if p > 0.01}
            total = sum(pesos_brutos.values())
            if total == 0:
                return {"erro": "Nenhum ativo selecionado após filtragem."}

            return {col: round((p / total) * 100, 1) for col, p in pesos_brutos.items()}

        except Exception as e:
            return {"erro": f"Erro interno: {e}"}