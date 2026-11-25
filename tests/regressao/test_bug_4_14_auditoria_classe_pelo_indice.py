"""BUG-4-14: a auditoria manda ao motor de FII todo ticker terminado em 11 fora das units fixas.

`auditoria.main` roteava FII × ação pelo sufixo: `FIIS_CONHECIDOS`, `quote_type` `MUTUALFUND`
ou "11" no ticker fora de `UNITS_CONHECIDAS`. ETF (BOVA11) e unit nova iam ao `FIIEngine`,
ao contrário do `app.py`, que usa `AssetClassifier().is_fii(ticker, dados)` e a classe do
índice oficial (armadilha 14; achado 17 do Gemini, primeira parte).

Arranjo da BUG-2C-29: `main()` real, coleta simulada com a classe oficial nos `dados`.
"""

from unittest.mock import Mock

import pytest

import auditoria


def _auditar(monkeypatch, tmp_path, ticker: str, dados: dict) -> tuple[Mock, Mock]:
    import fii_engine

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(auditoria.sys, "argv", ["auditoria.py", ticker])
    monkeypatch.setattr(auditoria, "_rel", {"meta": {}, "tickers": {ticker: {}}})
    for nome in (
        "auditar_selic",
        "auditar_banco",
        "auditar_tecnica",
        "auditar_prompt",
        "auditar_referencia",
    ):
        monkeypatch.setattr(auditoria, nome, Mock())
    monkeypatch.setattr(
        auditoria,
        "auditar_dados_scraper",
        lambda t: {"ticker": t, "preco_atual": 100, **dados},
    )
    valuation = Mock(return_value=(None, None, {}))
    monkeypatch.setattr(auditoria, "auditar_valuation", valuation)
    motor_fii = Mock()
    motor_fii.analisar.return_value = {"fair_value": None, "upside": None}
    monkeypatch.setattr(fii_engine, "FIIEngine", lambda: motor_fii)
    auditoria.main()
    return valuation, motor_fii


@pytest.mark.parametrize(
    ("ticker", "classe"),
    [
        pytest.param("BOVA11", "ETF", id="etf"),
        pytest.param("TSTA11", "UNIT", id="unit_fora_das_conhecidas"),
    ],
)
def test_ticker_11_que_nao_e_fii_nao_vai_ao_motor_de_fii(
    monkeypatch, tmp_path, ticker, classe
):
    valuation, motor_fii = _auditar(
        monkeypatch, tmp_path, ticker, {"classe_ativo": classe}
    )

    motor_fii.analisar.assert_not_called()
    valuation.assert_called_once()


def test_ticker_11_sem_classe_oficial_nao_vira_fii(monkeypatch, tmp_path):
    _, motor_fii = _auditar(
        monkeypatch, tmp_path, "TSTB11", {"quote_type": "MUTUALFUND"}
    )

    motor_fii.analisar.assert_not_called()


def test_fii_do_indice_continua_no_motor_de_fii(monkeypatch, tmp_path):
    valuation, motor_fii = _auditar(
        monkeypatch, tmp_path, "TSTF11", {"classe_ativo": "FII"}
    )

    motor_fii.analisar.assert_called_once()
    valuation.assert_not_called()
