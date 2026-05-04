from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from backtesting.backtest_engine import (
    BacktestEngine,
    analisar_resultados,
    comparar_modelos,
    identificar_modelo_escolhido,
    rodar_backtest_completo,
)


def _historico() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [10, 11, 12, 13, 14],
            "High": [11, 12, 13, 14, 15],
            "Low": [9, 10, 11, 12, 13],
            "Close": [10, 11, 12, 13, 14],
        },
        index=pd.to_datetime(
            [
                "2024-01-02",
                "2024-02-01",
                "2024-04-01",
                "2024-05-02",
                "2024-08-01",
            ]
        ),
    )


def _fundamentos() -> dict[str, pd.DataFrame]:
    return {
        "PETR4": pd.DataFrame(
            {
                "pl": [8.0],
                "pvp": [1.2],
                "roe": [0.18],
                "dy": [0.06],
            },
            index=pd.to_datetime(["2024-04-15"]),
        )
    }


def test_simular_analise_mensal_sem_fundamentos_nao_usa_lookahead():
    engine = BacktestEngine(tickers=["PETR4.SA"], end_date="2024-08-01")
    engine.dados_historico = {"PETR4.SA": _historico()}

    resultado = engine.simular_analise_mensal("PETR4", "2024-02-15")

    assert resultado["status"] == "SEM_FUNDAMENTOS_HISTORICOS"
    assert resultado["data_analise"] == pd.Timestamp("2024-02-01")
    assert resultado["preco_analise"] == 11.0


def test_simular_analise_mensal_usa_historico_ate_a_data():
    engine = BacktestEngine(tickers=["PETR4.SA"], end_date="2024-08-01")
    engine.dados_historico = {"PETR4.SA": _historico()}

    with patch("backtesting.backtest_engine.ValuationEngine.processar") as processar:
        processar.return_value = {
            "fair_value": 15.0,
            "upside": 36.4,
            "score_final": 70,
            "recomendacao": "COMPRA",
        }
        resultado = engine.simular_analise_mensal(
            "PETR4",
            "2024-04-15",
            _fundamentos(),
        )

    dados_enviados = processar.call_args.args[0]
    assert dados_enviados["historico"].index.max() == pd.Timestamp("2024-04-01")
    assert dados_enviados["preco_atual"] == 12.0
    assert dados_enviados["lpa"] == pytest.approx(1.5)
    assert resultado["status"] == "OK"
    assert resultado["recomendacao"] == "COMPRA"


def test_validar_recomendacao_compra_acerta_quando_sobe_mais_de_5pct():
    engine = BacktestEngine(tickers=["PETR4.SA"], end_date="2024-08-01")
    engine.dados_historico = {"PETR4.SA": _historico()}

    resultado = engine.validar_recomendacao("PETR4", "2024-02-01", "COMPRA", 70)

    assert resultado["preco_analise"] == 11.0
    assert resultado["preco_futuro"] == 13.0
    assert resultado["retorno_real"] == pytest.approx((13 - 11) / 11)
    assert resultado["acertou"] is True


def test_rodar_backtest_retorna_dataframe_com_resultados_mensais():
    engine = BacktestEngine(
        tickers=["PETR4.SA"],
        start_date="2024-01-01",
        end_date="2024-05-02",
    )
    engine.dados_historico = {"PETR4.SA": _historico()}

    with (
        patch("backtesting.backtest_engine.ValuationEngine.processar") as processar,
    ):
        processar.return_value = {
            "fair_value": 15.0,
            "upside": 36.4,
            "score_final": 70,
            "recomendacao": "COMPRA",
        }
        resultados = engine.rodar_backtest(_fundamentos())

    assert not resultados.empty
    assert (resultados["status"] == "OK").sum() == 1
    assert "acertou" in resultados.columns


def test_rodar_backtest_completo_nao_valida_snapshot_sem_fundamentos(monkeypatch):
    class FakeEngine:
        tickers = ["PETR4.SA"]

        def coletar_historico(self):
            return {}

        def simular_analise_mensal(self, ticker, data, fundamentos_historicos=None):
            return {
                "ticker": ticker.replace(".SA", ""),
                "data_analise": pd.Timestamp(data),
                "status": "SEM_FUNDAMENTOS_HISTORICOS",
            }

        def validar_recomendacao(self, *args, **kwargs):
            raise AssertionError("nao deve validar snapshots sem analise OK")

    monkeypatch.setattr("backtesting.backtest_engine.BacktestEngine", FakeEngine)

    resultado = rodar_backtest_completo()

    assert len(resultado) == 29
    assert set(resultado["status"]) == {"SEM_FUNDAMENTOS_HISTORICOS"}


def test_analisar_resultados_calcula_metricas_e_salva_csv():
    df = pd.DataFrame(
        [
            {
                "status": "OK",
                "recomendacao": "COMPRA",
                "score_final": 70,
                "acertou": True,
                "retorno_real": 0.08,
            },
            {
                "status": "OK",
                "recomendacao": "COMPRA",
                "score_final": 65,
                "acertou": False,
                "retorno_real": -0.02,
            },
            {
                "status": "OK",
                "recomendacao": "VENDA",
                "score_final": 35,
                "acertou": True,
                "retorno_real": -0.07,
            },
            {
                "status": "SEM_FUNDAMENTOS_HISTORICOS",
                "recomendacao": "NEUTRO",
                "score_final": 50,
                "acertou": False,
                "retorno_real": 0.30,
            },
        ]
    )
    output = Path(".pytest_cache") / "backtest_results_test.csv"
    output.parent.mkdir(exist_ok=True)

    try:
        resumo = analisar_resultados(df, output_csv=output)
        arquivo_salvo = output.exists()
    finally:
        output.unlink(missing_ok=True)

    assert resumo["total"] == 4
    assert resumo["avaliados"] == 3
    assert resumo["por_recomendacao"]["COMPRA"]["taxa_acerto"] == 0.5
    assert resumo["por_recomendacao"]["VENDA"]["taxa_acerto"] == 1.0
    assert resumo["retorno_medio"]["COMPRA"] == 0.03
    assert arquivo_salvo


def test_identificar_modelo_escolhido_por_fair_value_mais_proximo():
    row = pd.Series(
        {
            "fair_value": 70.0,
            "metodos_usados": "Graham: R$40.00, Lynch: R$106.00, Bazin: R$73.00",
        }
    )

    assert identificar_modelo_escolhido(row) == "Bazin"


def test_comparar_modelos_calcula_acuracia_por_modelo():
    df = pd.DataFrame(
        [
            {
                "status": "OK",
                "fair_value": 70.0,
                "metodos_usados": "Graham: R$40.00, Bazin: R$73.00",
                "recomendacao": "COMPRA",
                "upside": 15.0,
                "score_final": 70,
                "acertou": True,
                "retorno_real": 0.10,
            },
            {
                "status": "OK",
                "fair_value": 30.0,
                "metodos_usados": "Graham: R$31.00, Gordon: R$80.00",
                "recomendacao": "VENDA",
                "upside": -20.0,
                "score_final": 35,
                "acertou": False,
                "retorno_real": 0.04,
            },
            {
                "status": "SEM_FUNDAMENTOS_HISTORICOS",
                "fair_value": 10.0,
                "metodos_usados": "Lynch: R$10.00",
                "recomendacao": "COMPRA",
                "upside": 50.0,
                "score_final": 80,
                "acertou": True,
                "retorno_real": 0.20,
            },
        ]
    )

    resumo = comparar_modelos(df)

    assert resumo["avaliados"] == 2
    assert resumo["por_modelo"]["Bazin"]["casos"] == 1
    assert resumo["por_modelo"]["Bazin"]["taxa_acerto"] == 1.0
    assert resumo["por_modelo"]["Graham"]["casos"] == 1
    assert resumo["por_modelo"]["Graham"]["taxa_acerto"] == 0.0
    assert resumo["por_modelo"]["Lynch"]["casos"] == 0
