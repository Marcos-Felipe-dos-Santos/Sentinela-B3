"""Taxa aditiva fora do prompt, sem alterar a saída dos métodos."""

from unittest.mock import patch

from ai_core import SentinelaAI
from market_engine import MarketEngine


def test_registro_entra_em_dados_fora_do_prompt():
    registro = {
        "ntnb": 0.07,
        "custo_capital_real": 0.12,
        "proveniencia": {"fonte": "Tesouro"},
    }
    dados = {}
    mercado = MarketEngine.__new__(MarketEngine)
    with patch("market_engine.get_taxa_real", return_value=registro) as obter:
        mercado._buscar_taxa_real(dados)
    assert dados["taxa_real"] == registro
    obter.assert_called_once()
    assert "taxa_real" not in SentinelaAI.__new__(SentinelaAI)._formatar_dados(dados)


def test_janela_vem_da_dre_da_dfp_e_nao_do_ano_inferido(monkeypatch):
    from datetime import date
    from types import SimpleNamespace

    from sentinela.data import series_cvm

    documento = series_cvm.Acumulado(
        "DFP", "2025-09-30", 1, date(2024, 10, 1), date(2025, 9, 30)
    )
    cvm = SimpleNamespace(
        indicadores_da_serie=lambda *a: {}, acumulados_ttm=lambda *a: [documento]
    )
    monkeypatch.setattr(
        series_cvm,
        "serie_anual",
        lambda *a, **kw: [{"dt_refer": "2025-09-30", "versao": "1"}],
    )
    monkeypatch.setattr(series_cvm, "ttm", lambda *a: series_cvm.Abstencao("sem TTM"))
    mercado = MarketEngine.__new__(MarketEngine)
    dados = {}
    mercado._serie_cvm("TST3", dados, cvm, 1, "empresa")
    assert dados["janela_contabil_cvm"] == (date(2024, 10, 1), date(2025, 9, 30))
    with patch("market_engine.get_taxa_real", return_value=None) as obter:
        mercado._buscar_taxa_real(dados)
    assert obter.call_args.kwargs["janela"] == dados["janela_contabil_cvm"]


def test_janela_da_versao_errada_nao_e_usada(monkeypatch):
    from datetime import date
    from types import SimpleNamespace

    from sentinela.data import series_cvm

    documento = series_cvm.Acumulado(
        "DFP", "2025-12-31", 2, date(2025, 1, 1), date(2025, 12, 31)
    )
    cvm = SimpleNamespace(
        indicadores_da_serie=lambda *a: {}, acumulados_ttm=lambda *a: [documento]
    )
    monkeypatch.setattr(
        series_cvm,
        "serie_anual",
        lambda *a, **kw: [{"dt_refer": "2025-12-31", "versao": "1"}],
    )
    monkeypatch.setattr(series_cvm, "ttm", lambda *a: series_cvm.Abstencao("sem TTM"))
    dados = {}
    MarketEngine.__new__(MarketEngine)._serie_cvm("TST3", dados, cvm, 1, "empresa")
    assert "janela_contabil_cvm" not in dados
