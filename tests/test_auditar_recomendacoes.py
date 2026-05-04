import pandas as pd

from auditar_recomendacoes import (
    calcular_metricas_dados,
    calcular_metricas_operacionais,
    classificar_qualidade_dados,
)


def _dados_base(**extras):
    dados = {
        "preco_atual": 10.0,
        "historico": pd.DataFrame({"Close": [9.0, 10.0]}),
        "campos_faltantes": [],
        "dados_parciais": False,
    }
    dados.update(extras)
    return dados


def test_failure_rate_ignores_scraper_error_when_data_is_complete():
    dados = _dados_base(erro_scraper=True)

    assert classificar_qualidade_dados(dados) == "full"

    metricas = calcular_metricas_dados([dados])

    assert metricas["full_data_count"] == 1
    assert metricas["partial_data_count"] == 0
    assert metricas["no_data_count"] == 0
    assert metricas["failure_rate_percent"] == 0.0


def test_failure_rate_counts_no_data_tickers_correctly():
    completo = _dados_base()
    parcial = _dados_base(campos_faltantes=["roe"], dados_parciais=True)
    sem_preco = {"historico": pd.DataFrame({"Close": [10.0]})}
    sem_historico = {"preco_atual": 10.0, "historico": pd.DataFrame()}

    metricas = calcular_metricas_dados([
        completo,
        parcial,
        sem_preco,
        sem_historico,
    ])

    assert metricas["total_tickers_analyzed"] == 4
    assert metricas["full_data_count"] == 1
    assert metricas["partial_data_count"] == 1
    assert metricas["no_data_count"] == 2
    assert metricas["failure_rate_percent"] == 75.0


def test_operational_failure_rate_excludes_distressed():
    distressed = {
        "ticker": "AMER3",
        "dados": _dados_base(campos_faltantes=["dy"], dados_parciais=True),
        "analise": {
            "perfil": "DISTRESSED",
            "recomendacao": "ALTO RISCO — EVITAR",
        },
    }
    normal_full = {
        "ticker": "PETR4",
        "dados": _dados_base(),
        "analise": {"perfil": "RENDA/VALOR", "recomendacao": "NEUTRO"},
    }

    metricas = calcular_metricas_operacionais([distressed, normal_full])

    assert metricas["total_tickers_analyzed"] == 1
    assert metricas["excluded_count"] == 1
    assert metricas["full_data_count"] == 1
    assert metricas["failure_rate_percent"] == 0.0


def test_operational_failure_rate_excludes_no_data():
    no_data = {
        "ticker": "CVBI11",
        "dados": None,
        "analise": None,
    }
    normal_full = {
        "ticker": "HGLG11",
        "dados": _dados_base(),
        "analise": {"perfil": "FII", "recomendacao": "VENDA"},
    }

    metricas = calcular_metricas_operacionais([no_data, normal_full])

    assert metricas["total_tickers_analyzed"] == 1
    assert metricas["excluded_count"] == 1
    assert metricas["full_data_count"] == 1
    assert metricas["failure_rate_percent"] == 0.0


def test_operational_failure_rate_counts_partial_normal_asset():
    parcial = {
        "ticker": "CASHX3",
        "dados": _dados_base(campos_faltantes=["roe"], dados_parciais=True),
        "analise": {"perfil": "RENDA/VALOR", "recomendacao": "NEUTRO"},
    }
    full = {
        "ticker": "ITUB4",
        "dados": _dados_base(),
        "analise": {"perfil": "CRESCIMENTO", "recomendacao": "COMPRA"},
    }

    metricas = calcular_metricas_operacionais([parcial, full])

    assert metricas["total_tickers_analyzed"] == 2
    assert metricas["full_data_count"] == 1
    assert metricas["partial_data_count"] == 1
    assert metricas["failure_rate_percent"] == 50.0


def test_operational_failure_rate_counts_full_normal_asset_as_success():
    full = {
        "ticker": "ITUB4",
        "dados": _dados_base(erro_scraper=True),
        "analise": {"perfil": "CRESCIMENTO", "recomendacao": "COMPRA"},
    }

    metricas = calcular_metricas_operacionais([full])

    assert metricas["total_tickers_analyzed"] == 1
    assert metricas["full_data_count"] == 1
    assert metricas["partial_data_count"] == 0
    assert metricas["no_data_count"] == 0
    assert metricas["failure_rate_percent"] == 0.0
