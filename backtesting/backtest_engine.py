import argparse
import logging
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yfinance as yf

from valuation_engine import ValuationEngine

logger = logging.getLogger("Backtest")

FundamentosProvider = Callable[[str, pd.Timestamp], Optional[dict[str, Any]]]
MODELOS_VALUATION = ("Graham", "Bazin", "Gordon", "Lynch")


class BacktestEngine:
    """
    Simula analises mensais historicas e valida acuracia apos 90 dias.

    Observacao importante: preco e OHLC historicos vem do yfinance, mas
    fundamentos historicos point-in-time precisam ser fornecidos por CSV,
    DataFrame ou provider externo. Usar fundamentos atuais em datas passadas
    criaria lookahead bias.
    """

    REQUIRED_FUNDAMENTALS = ("pl", "pvp", "roe", "dy")

    def __init__(
        self,
        tickers: Optional[list[str]] = None,
        start_date: str = "2024-01-01",
        end_date: str = "2026-05-04",
        horizonte_dias: int = 90,
        fundamentos_provider: Optional[FundamentosProvider] = None,
        fundamentos_match: str = "same_month",
    ) -> None:
        self.tickers = tickers or ["PETR4.SA", "ITUB4.SA", "VALE3.SA"]
        self.start_date = start_date
        self.end_date = end_date
        self.horizonte_dias = horizonte_dias
        self.fundamentos_provider = fundamentos_provider
        self.fundamentos_match = fundamentos_match
        self.dados_historico: dict[str, pd.DataFrame] = {}
        self.fundamentos_historicos: dict[str, Any] = {}

    def coletar_historico(self) -> dict[str, pd.DataFrame]:
        """Baixa OHLC historico dos tickers configurados."""
        dados: dict[str, pd.DataFrame] = {}
        for ticker in self.tickers:
            ticker_download = self._ticker_download(ticker)
            df = yf.download(
                ticker_download,
                start=self.start_date,
                end=self._download_end_exclusive(),
                progress=False,
                auto_adjust=False,
                threads=False,
            )
            dados[ticker_download] = self._normalizar_historico(df)

        self.dados_historico = dados
        return dados

    def carregar_fundamentos_csv(self, caminho: str | Path) -> dict[str, pd.DataFrame]:
        """
        Carrega fundamentos historicos de um CSV point-in-time.

        Colunas esperadas: ticker, data, pl, pvp, roe, dy.
        Colunas opcionais, quando existentes, sao preservadas.
        """
        df = pd.read_csv(caminho)
        faltantes = {"ticker", "data", *self.REQUIRED_FUNDAMENTALS} - set(df.columns)
        if faltantes:
            raise ValueError(f"CSV sem colunas obrigatorias: {sorted(faltantes)}")

        df = df.copy()
        df["ticker"] = df["ticker"].astype(str).map(self._ticker_base)
        df["data"] = pd.to_datetime(df["data"])

        fundamentos: dict[str, pd.DataFrame] = {}
        for ticker, grupo in df.groupby("ticker"):
            fundamentos[ticker] = grupo.sort_values("data").set_index("data")

        self.fundamentos_historicos = fundamentos
        return fundamentos

    def simular_analise_mensal(
        self,
        ticker: str,
        data_analise: datetime | pd.Timestamp | str,
        fundamentos_historicos: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Simula a analise disponivel no dia informado, sem lookahead de preco.
        """
        ticker_download = self._ticker_download(ticker)
        ticker_base = self._ticker_base(ticker)
        data = self._normalizar_data(data_analise)
        historico = self._historico_do_ticker(ticker_download)
        fundamentos = self._obter_fundamentos(
            ticker_base,
            data,
            fundamentos_historicos,
        )
        data_efetiva = self._normalizar_data(
            fundamentos.get("_data_fundamentos", data) if fundamentos else data
        )

        historico_ate_data = historico.loc[historico.index <= data_efetiva].copy()
        if historico_ate_data.empty:
            return {
                "ticker": ticker_base,
                "data_analise": data_efetiva,
                "status": "SEM_HISTORICO",
                "motivo": "Nao ha OHLC ate a data de analise.",
            }

        data_trade = historico_ate_data.index[-1]
        preco = float(historico_ate_data["Close"].iloc[-1])
        if not fundamentos:
            return {
                "ticker": ticker_base,
                "data_analise": data_trade,
                "status": "SEM_FUNDAMENTOS_HISTORICOS",
                "motivo": (
                    "Forneca fundamentos point-in-time para evitar lookahead bias."
                ),
                "preco_analise": preco,
            }

        dados = {
            "ticker": ticker_base,
            "preco_atual": preco,
            "historico": historico_ate_data,
            "fonte_preco": "yfinance_historico",
            "fonte_fundamentos": fundamentos.get(
                "fonte_fundamentos", "fundamentos_historicos"
            ),
            "erro_scraper": False,
            **fundamentos,
        }
        dados.pop("_data_fundamentos", None)
        self._preencher_derivados(dados)
        dados["campos_faltantes"] = self._campos_faltantes(dados)
        dados["dados_parciais"] = bool(dados["campos_faltantes"])

        resultado = ValuationEngine().processar(dados)
        if not resultado:
            return {
                "ticker": ticker_base,
                "data_analise": data_trade,
                "status": "DADOS_INSUFICIENTES",
                "motivo": "ValuationEngine recusou o snapshot historico.",
                "preco_analise": preco,
                "campos_faltantes": dados["campos_faltantes"],
            }

        return {
            "ticker": ticker_base,
            "data_analise": data_trade,
            "status": "OK",
            "preco_analise": preco,
            **resultado,
        }

    def validar_recomendacao(
        self,
        ticker: str,
        data_analise: datetime | pd.Timestamp | str,
        recomendacao: str,
        score: int | float,
    ) -> dict[str, Any]:
        """
        Valida se a recomendacao foi coerente com o retorno 90 dias depois.
        """
        ticker_download = self._ticker_download(ticker)
        ticker_base = self._ticker_base(ticker)
        data = self._normalizar_data(data_analise)
        historico = self._historico_do_ticker(ticker_download)

        data_preco, preco_analise = self._preco_em_ou_apos(historico, data)
        alvo = min(
            data_preco + timedelta(days=self.horizonte_dias),
            self._normalizar_data(self.end_date),
        )
        data_futura, preco_futuro = self._preco_em_ou_apos(historico, alvo)
        retorno_real = (preco_futuro - preco_analise) / preco_analise

        sinal = self._sinal_recomendacao(recomendacao)
        if sinal == "COMPRA":
            acertou = retorno_real > 0.05
        elif sinal == "VENDA":
            acertou = retorno_real < -0.05
        else:
            acertou = abs(retorno_real) < 0.10

        return {
            "ticker": ticker_base,
            "data_analise": data_preco,
            "data_futura": data_futura,
            "recomendacao": recomendacao,
            "score": score,
            "preco_analise": preco_analise,
            "preco_futuro": preco_futuro,
            "retorno_real": retorno_real,
            "acertou": bool(acertou),
        }

    def rodar_backtest(
        self,
        fundamentos_historicos: Optional[dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Executa simulacoes mensais para todos os tickers."""
        if not self.dados_historico:
            self.coletar_historico()

        registros: list[dict[str, Any]] = []
        for ticker in self.tickers:
            for data in self.gerar_datas_mensais(ticker):
                analise = self.simular_analise_mensal(
                    ticker,
                    data,
                    fundamentos_historicos,
                )
                if analise.get("status") != "OK":
                    registros.append(analise)
                    continue

                validacao = self.validar_recomendacao(
                    ticker,
                    analise["data_analise"],
                    analise["recomendacao"],
                    analise["score_final"],
                )
                registros.append({**analise, **validacao})

        return pd.DataFrame(registros)

    def gerar_datas_mensais(self, ticker: str) -> list[pd.Timestamp]:
        """Retorna o primeiro pregao disponivel de cada mes."""
        ticker_download = self._ticker_download(ticker)
        historico = self._historico_do_ticker(ticker_download)
        meses = pd.date_range(self.start_date, self.end_date, freq="MS")
        datas: list[pd.Timestamp] = []
        for mes in meses:
            candidatos = historico.loc[historico.index >= mes]
            if candidatos.empty:
                continue
            data = candidatos.index[0]
            if data <= self._normalizar_data(self.end_date) and data not in datas:
                datas.append(data)
        return datas

    @staticmethod
    def resumo(resultados: pd.DataFrame) -> dict[str, Any]:
        """Resume taxa de acerto das simulacoes executadas."""
        if resultados.empty:
            return {"total": 0, "avaliados": 0, "taxa_acerto": 0.0}

        avaliados = resultados[resultados.get("status") == "OK"]
        total_avaliado = len(avaliados)
        acertos = int(avaliados.get("acertou", pd.Series(dtype=bool)).sum())
        taxa = (acertos / total_avaliado * 100) if total_avaliado else 0.0
        return {
            "total": int(len(resultados)),
            "avaliados": int(total_avaliado),
            "ignorados": int(len(resultados) - total_avaliado),
            "acertos": acertos,
            "taxa_acerto": round(taxa, 1),
        }

    def _obter_fundamentos(
        self,
        ticker_base: str,
        data_analise: pd.Timestamp,
        fundamentos_historicos: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        if self.fundamentos_provider:
            snapshot = self.fundamentos_provider(ticker_base, data_analise)
            if snapshot:
                return dict(snapshot)

        fonte = fundamentos_historicos or self.fundamentos_historicos
        if not fonte:
            return None

        snapshot = fonte.get(ticker_base)
        if snapshot is None:
            snapshot = fonte.get(self._ticker_download(ticker_base))
        if snapshot is None:
            return None

        if isinstance(snapshot, pd.DataFrame):
            df = snapshot.copy()
            if "data" in df.columns:
                df["data"] = pd.to_datetime(df["data"])
                df = df.set_index("data")
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            if self.fundamentos_match == "same_month":
                periodo = data_analise.to_period("M")
                linhas = df.loc[df.index.to_period("M") == periodo]
            else:
                linhas = df.loc[df.index <= data_analise]
            if linhas.empty:
                return None
            row = linhas.iloc[-1].dropna().to_dict()
            row["_data_fundamentos"] = linhas.index[-1]
            return row

        if isinstance(snapshot, dict):
            if any(chave in snapshot for chave in self.REQUIRED_FUNDAMENTALS):
                return dict(snapshot)

            candidatos: list[tuple[pd.Timestamp, dict[str, Any]]] = []
            for data_raw, dados in snapshot.items():
                data = self._normalizar_data(data_raw)
                if data <= data_analise and isinstance(dados, dict):
                    candidatos.append((data, dados))
            if not candidatos:
                return None
            candidatos.sort(key=lambda item: item[0])
            return dict(candidatos[-1][1])

        return None

    @classmethod
    def _campos_faltantes(cls, dados: dict[str, Any]) -> list[str]:
        faltantes = []
        for campo in cls.REQUIRED_FUNDAMENTALS:
            valor = dados.get(campo)
            if valor is None:
                faltantes.append(campo)
                continue
            try:
                if campo != "dy" and float(valor) <= 0:
                    faltantes.append(campo)
            except (TypeError, ValueError):
                faltantes.append(campo)
        return faltantes

    @staticmethod
    def _preencher_derivados(dados: dict[str, Any]) -> None:
        preco = float(dados.get("preco_atual") or 0)
        pl = float(dados.get("pl") or 0)
        pvp = float(dados.get("pvp") or 0)
        if preco > 0 and pl > 0 and not dados.get("lpa"):
            dados["lpa"] = preco / pl
        if preco > 0 and pvp > 0 and not dados.get("vpa"):
            dados["vpa"] = preco / pvp

    def _historico_do_ticker(self, ticker_download: str) -> pd.DataFrame:
        if not self.dados_historico:
            self.coletar_historico()
        historico = self.dados_historico.get(ticker_download)
        if historico is None or historico.empty:
            raise ValueError(f"Sem historico para {ticker_download}")
        return historico

    @staticmethod
    def _normalizar_historico(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        normalizado = df.copy()
        if isinstance(normalizado.columns, pd.MultiIndex):
            normalizado.columns = normalizado.columns.get_level_values(0)

        normalizado.index = pd.to_datetime(normalizado.index).tz_localize(None)
        normalizado = normalizado.sort_index()
        return normalizado

    @staticmethod
    def _preco_em_ou_apos(
        historico: pd.DataFrame,
        data: pd.Timestamp,
    ) -> tuple[pd.Timestamp, float]:
        candidatos = historico.loc[historico.index >= data]
        if candidatos.empty:
            candidatos = historico.tail(1)
        data_preco = candidatos.index[0]
        return data_preco, float(candidatos["Close"].iloc[0])

    @staticmethod
    def _sinal_recomendacao(recomendacao: str) -> str:
        rec = str(recomendacao or "").upper()
        if rec in {"COMPRA", "COMPRA FORTE"}:
            return "COMPRA"
        if rec == "VENDA":
            return "VENDA"
        return "NEUTRO"

    @staticmethod
    def _ticker_download(ticker: str) -> str:
        ticker_base = BacktestEngine._ticker_base(ticker)
        return f"{ticker_base}.SA"

    @staticmethod
    def _ticker_base(ticker: str) -> str:
        return str(ticker).upper().replace(".SA", "").strip()

    @staticmethod
    def _normalizar_data(data: datetime | pd.Timestamp | str) -> pd.Timestamp:
        return pd.Timestamp(data).tz_localize(None)

    def _download_end_exclusive(self) -> str:
        """Converte end_date inclusivo do backtest para end exclusivo do yfinance."""
        return (self._normalizar_data(self.end_date) + timedelta(days=1)).strftime("%Y-%m-%d")


def rodar_backtest_completo(
    fundamentos_historicos: Optional[dict[str, Any]] = None,
    fundamentos_csv: str | Path | None = None,
) -> pd.DataFrame:
    """
    Roda analise mensal de jan/2024 a mai/2026 e valida recomendacoes.

    Sem fundamentos historicos point-in-time, os snapshots sao mantidos como
    SEM_FUNDAMENTOS_HISTORICOS para evitar lookahead bias.
    """
    engine = BacktestEngine()
    engine.coletar_historico()

    if fundamentos_csv:
        engine.carregar_fundamentos_csv(fundamentos_csv)

    resultados: list[dict[str, Any]] = []
    data_atual = pd.Timestamp("2024-01-01")
    data_final = pd.Timestamp("2026-05-04")

    while data_atual <= data_final:
        for ticker in engine.tickers:
            print(f"Analisando {ticker} em {data_atual.strftime('%Y-%m-%d')}")
            analise = engine.simular_analise_mensal(
                ticker,
                data_atual,
                fundamentos_historicos,
            )

            if not analise or analise.get("status") != "OK":
                if analise:
                    resultados.append(analise)
                continue

            validacao = engine.validar_recomendacao(
                ticker,
                analise["data_analise"],
                analise["recomendacao"],
                analise["score_final"],
            )
            resultados.append({**analise, **validacao})

        data_atual += pd.DateOffset(months=1)

    return pd.DataFrame(resultados)


def analisar_resultados(
    df_backtest: pd.DataFrame,
    output_csv: str | Path | None = "backtesting/backtest_results.csv",
) -> dict[str, Any]:
    """
    Calcula metricas de acuracia por recomendacao, score e retorno medio.
    """
    if df_backtest.empty:
        resumo = {
            "total": 0,
            "avaliados": 0,
            "por_recomendacao": {},
            "por_score": {},
            "retorno_medio": {},
        }
        print("Backtest vazio.")
        return resumo

    df = df_backtest.copy()
    if "status" in df.columns:
        df = df[df["status"] == "OK"].copy()

    if df.empty:
        resumo = {
            "total": int(len(df_backtest)),
            "avaliados": 0,
            "por_recomendacao": {},
            "por_score": {},
            "retorno_medio": {},
        }
        print("Nenhum caso avaliado. Forneca fundamentos historicos point-in-time.")
        if output_csv:
            Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
            df_backtest.to_csv(output_csv, index=False)
            print(f"\nResultados salvos em {output_csv}")
        return resumo

    score_col = "score" if "score" in df.columns else "score_final"
    resumo = {
        "total": int(len(df_backtest)),
        "avaliados": int(len(df)),
        "por_recomendacao": {},
        "por_score": {},
        "retorno_medio": {},
    }

    print("Acuracia por recomendacao:")
    for rec in ["COMPRA", "VENDA", "NEUTRO"]:
        subset = df[df["recomendacao"] == rec]
        taxa_acerto = subset["acertou"].mean() if len(subset) > 0 else 0.0
        resumo["por_recomendacao"][rec] = {
            "taxa_acerto": round(float(taxa_acerto), 4),
            "casos": int(len(subset)),
        }
        print(f"{rec}: {taxa_acerto:.1%} de acuracia ({len(subset)} casos)")

    df["score_bucket"] = pd.cut(
        df[score_col],
        bins=[0, 40, 60, 80, 100],
        include_lowest=True,
    )

    print("\nAcuracia por Score:")
    for bucket in df["score_bucket"].cat.categories:
        subset = df[df["score_bucket"] == bucket]
        taxa = subset["acertou"].mean() if len(subset) > 0 else 0.0
        resumo["por_score"][str(bucket)] = {
            "taxa_acerto": round(float(taxa), 4),
            "casos": int(len(subset)),
        }
        print(f"Score {bucket}: {taxa:.1%} ({len(subset)} casos)")

    print("\nRetorno Medio (3 meses):")
    for rec in ["COMPRA", "VENDA", "NEUTRO"]:
        subset = df[df["recomendacao"] == rec]
        ret_medio = subset["retorno_real"].mean() if len(subset) > 0 else 0.0
        resumo["retorno_medio"][rec] = round(float(ret_medio), 4)
        print(f"{rec}: {ret_medio:.2%}")

    if output_csv:
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        df_backtest.to_csv(output_csv, index=False)
        print(f"\nResultados salvos em {output_csv}")

    return resumo


def identificar_modelo_escolhido(row: pd.Series | dict[str, Any]) -> str:
    """
    Identifica o modelo mais representativo da linha de backtest.

    Se a linha ja tiver modelo explicito, usa esse valor. Caso contrario,
    extrai FVs de metodos_usados e escolhe o metodo mais proximo do fair_value
    composto. Essa regra evita mudar o valuation core, que usa media de modelos.
    """
    dados = row if isinstance(row, dict) else row.to_dict()

    for campo in ("modelo_escolhido", "modelo", "metodo", "metodo_escolhido"):
        modelo = _normalizar_modelo(dados.get(campo))
        if modelo:
            return modelo

    metodos = _extrair_fvs_metodos(dados)
    if not metodos:
        return "Indefinido"
    if len(metodos) == 1:
        return next(iter(metodos))

    fair_value = _to_float(dados.get("fair_value"))
    if fair_value is None:
        for modelo in MODELOS_VALUATION:
            if modelo in metodos:
                return modelo
        return next(iter(metodos))

    return min(
        metodos,
        key=lambda modelo: (
            abs(metodos[modelo] - fair_value),
            MODELOS_VALUATION.index(modelo)
            if modelo in MODELOS_VALUATION
            else len(MODELOS_VALUATION),
        ),
    )


def comparar_modelos(df_backtest: pd.DataFrame) -> dict[str, Any]:
    """
    Compara acuracia por modelo de valuation mais representativo.
    """
    if df_backtest.empty:
        print("Backtest vazio.")
        return {"total": 0, "avaliados": 0, "por_modelo": {}, "estimado_vs_real": {}}

    df = df_backtest.copy()
    if "status" in df.columns:
        df = df[df["status"] == "OK"].copy()

    if df.empty:
        print("Nenhum caso avaliado para comparar modelos.")
        return {
            "total": int(len(df_backtest)),
            "avaliados": 0,
            "por_modelo": {},
            "estimado_vs_real": {},
        }

    df["modelo_escolhido"] = df.apply(identificar_modelo_escolhido, axis=1)
    resumo = {
        "total": int(len(df_backtest)),
        "avaliados": int(len(df)),
        "por_modelo": {},
        "estimado_vs_real": {},
    }

    print("Acuracia por Modelo:")
    for modelo in MODELOS_VALUATION:
        subset = df[df["modelo_escolhido"] == modelo]
        taxa = subset["acertou"].mean() if len(subset) > 0 else 0.0
        resumo["por_modelo"][modelo] = {
            "taxa_acerto": round(float(taxa), 4),
            "casos": int(len(subset)),
        }
        print(f"{modelo}: {taxa:.1%} ({len(subset)} casos)")

    estimado_col = "upside" if "upside" in df.columns else None
    score_col = "score" if "score" in df.columns else (
        "score_final" if "score_final" in df.columns else None
    )

    print("\nUpside Estimado vs Real:")
    for modelo in MODELOS_VALUATION:
        subset = df[df["modelo_escolhido"] == modelo]
        if len(subset) == 0:
            estimado = 0.0
            real = 0.0
        else:
            if estimado_col:
                estimado = float(subset[estimado_col].mean()) / 100
            elif score_col:
                estimado = float(subset[score_col].mean()) / 100
            else:
                estimado = 0.0
            real = float(subset["retorno_real"].mean())

        resumo["estimado_vs_real"][modelo] = {
            "estimado": round(estimado, 4),
            "real": round(real, 4),
        }
        print(f"{modelo}: Est={estimado:.2%}, Real={real:.2%}")

    return resumo


def _extrair_fvs_metodos(dados: dict[str, Any]) -> dict[str, float]:
    metodos: dict[str, float] = {}

    for modelo in MODELOS_VALUATION:
        for coluna in (f"fv_{modelo.lower()}", modelo.lower()):
            valor = _to_float(dados.get(coluna))
            if valor is not None and valor > 0:
                metodos[modelo] = valor

    texto = str(dados.get("metodos_usados") or "")
    for nome, valor in re.findall(r"([^:,]+):\s*R?\$?\s*([0-9]+(?:[.,][0-9]+)?)", texto):
        modelo = _normalizar_modelo(nome)
        numero = _to_float(valor)
        if modelo and numero is not None and numero > 0:
            metodos[modelo] = numero

    return metodos


def _normalizar_modelo(valor: Any) -> Optional[str]:
    texto = str(valor or "").strip().lower()
    if not texto:
        return None
    if "graham" in texto:
        return "Graham"
    if "bazin" in texto:
        return "Bazin"
    if "gordon" in texto:
        return "Gordon"
    if "lynch" in texto:
        return "Lynch"
    return None


def _to_float(valor: Any) -> Optional[float]:
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, str):
        texto = valor.strip().replace("R$", "").replace(" ", "")
        if not texto:
            return None
        if "," in texto and "." in texto:
            if texto.rfind(",") > texto.rfind("."):
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", "")
        else:
            texto = texto.replace(",", ".")
        valor = texto
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtesting Sentinela B3")
    parser.add_argument("--fundamentos-csv", help="CSV point-in-time de fundamentos")
    parser.add_argument(
        "--output",
        default="backtesting/backtest_results.csv",
        help="CSV de saida dos resultados do backtest",
    )
    args = parser.parse_args()

    engine = BacktestEngine()
    engine.coletar_historico()
    if args.fundamentos_csv:
        engine.carregar_fundamentos_csv(args.fundamentos_csv)

    resultados = engine.rodar_backtest()
    print(resultados)
    print(BacktestEngine.resumo(resultados))
    analisar_resultados(resultados, output_csv=args.output)
    comparar_modelos(resultados)

    if not args.fundamentos_csv:
        print(
            "Backtest de valuation ignorado onde faltam fundamentos historicos "
            "point-in-time. Use --fundamentos-csv para evitar lookahead bias."
        )


if __name__ == "__main__":
    main()
