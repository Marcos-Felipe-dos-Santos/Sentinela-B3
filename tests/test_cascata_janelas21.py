"""Fontes das janelas 2.1 atravessam a cascata e chegam ao motor de ação."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
import requests

from market_engine import MarketEngine
from sentinela.data.providers.macro import MacroProvider
from valuation_engine import ValuationEngine

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)


def sem_valor(resultado: dict, motivo: str) -> bool:
    """Abstenção mantém a causa e não fornece número; metadados são permitidos."""
    return (
        resultado.get("abstencao") == motivo
        and "lpa" not in resultado
        and "vpa" not in resultado
    )


def _dados() -> dict:
    """Cinco DFP sintéticas com base constante; CAGR nominal independente de 20%."""
    return {
        "ticker": "TEST3",
        "classe_ativo": "STOCK",
        "modelo_bpp": "empresa",
        "preco_atual": 30,
        "pl": 15,
        "pvp": 1.5,
        "roe": 0.25,
        "dy": 0.02,
        "serie_cvm": {
            "exercicios": [
                {
                    "exercicio": ano,
                    "inicio": f"{ano}-01-01",
                    "fim": f"{ano}-12-31",
                    "acoes": 100,
                    "lpa": lpa,
                    "vpa": 20,
                    "proveniencia": {
                        "fonte": "DFP sintética",
                        "data_entrega": f"{ano + 1}-03-01",
                        "data_coleta": "2026-04-01T12:00:00+00:00",
                    },
                }
                for ano, lpa in zip(
                    range(2021, 2026), [1, 1.2, 1.44, 1.728, 2.0736], strict=True
                )
            ]
        },
    }


def _ipca() -> dict:
    return {
        "fonte": "IBGE sintético",
        "coleta": "2026-04-01T12:00:00+00:00",
        "indices": {f"{ano}-12": 1 for ano in range(2021, 2026)},
        "publicacoes": {f"{ano}-12": f"{ano + 1}-01-10" for ano in range(2021, 2026)},
    }


def _engine() -> MarketEngine:
    # Esta etapa não depende de inicializar os outros provedores da cascata.
    return MarketEngine.__new__(MarketEngine)


def test_produtor_recebe_exercicios_e_corte_exatos_e_motores_consumem_valores(
    monkeypatch,
):
    dados, ipca = _dados(), _ipca()
    produtor = Mock(return_value=ipca)
    monkeypatch.setattr(MacroProvider, "ipca_serie", produtor)
    _engine()._contexto_janelas(dados, AS_OF)
    produtor.assert_called_once_with(dados["serie_cvm"]["exercicios"], AS_OF)
    assert dados["ipca_serie"] is ipca
    janela = dados["janelas_fundamentais"]
    media = (1 + 1.2 + 1.44 + 1.728 + 2.0736) / 5
    assert janela["graham"]["lpa"] == pytest.approx(media)
    assert janela["lynch"]["crescimento_lpa"] == pytest.approx(0.2)
    resultado = ValuationEngine().processar(dados, as_of=AS_OF)
    assert "Graham: R$" in resultado["metodos_usados"]
    assert "Lynch: R$41.47" in resultado["metodos_usados"]
    assert dados["janelas_fundamentais"]["graham"]["lpa"] == pytest.approx(media)


@pytest.mark.parametrize(
    "erro",
    [
        ValueError("IPCA não publicado"),
        OSError("calendário indisponível"),
        requests.RequestException("SIDRA indisponível"),
    ],
)
def test_falha_de_fonte_abstem_graham_sem_apagar_cagr_nominal(monkeypatch, erro):
    dados = _dados()
    produtor = Mock(side_effect=erro)
    monkeypatch.setattr(MacroProvider, "ipca_serie", produtor)
    _engine()._contexto_janelas(dados, AS_OF)
    assert sem_valor(dados["ipca_serie"], str(erro))
    janela = dados["janelas_fundamentais"]
    assert sem_valor(janela["graham"], str(erro))
    assert janela["lynch"]["regime"] == "nominal"
    assert janela["lynch"]["crescimento_lpa"] == pytest.approx(0.2)
    resultado = ValuationEngine().processar(dados, as_of=AS_OF)
    assert "Graham" not in resultado["metodos_usados"]
    assert "Lynch: R$41.47" in resultado["metodos_usados"]


@pytest.mark.parametrize(
    "registro", [_ipca(), {"abstencao": "publicação ainda não disponível"}]
)
def test_registro_existente_preservado_sem_reconsulta(monkeypatch, registro):
    dados = _dados()
    dados["ipca_serie"] = registro
    produtor = Mock(
        side_effect=AssertionError("registro existente não deve ser substituído")
    )
    monkeypatch.setattr(MacroProvider, "ipca_serie", produtor)
    _engine()._contexto_janelas(dados, AS_OF)
    produtor.assert_not_called()
    assert dados["ipca_serie"] is registro
    assert dados["janelas_fundamentais"]["lynch"]["crescimento_lpa"] == pytest.approx(
        0.2
    )


@pytest.mark.parametrize("quantidade", [0, 1, 4])
def test_serie_incompleta_nao_dispara_coleta_ipca(monkeypatch, quantidade):
    dados = _dados()
    dados["serie_cvm"]["exercicios"] = dados["serie_cvm"]["exercicios"][:quantidade]
    produtor = Mock(side_effect=AssertionError("sem cinco exercícios não há janela"))
    monkeypatch.setattr(MacroProvider, "ipca_serie", produtor)
    _engine()._contexto_janelas(dados, AS_OF)
    produtor.assert_not_called()
    assert "ipca_serie" not in dados
    assert sem_valor(
        dados["janelas_fundamentais"]["graham"],
        "exige cinco exercícios completos contínuos",
    )
    assert sem_valor(
        dados["janelas_fundamentais"]["lynch"],
        "exige cinco exercícios completos contínuos",
    )


def test_erro_de_programacao_tem_motivo_proprio_e_log(monkeypatch, caplog):
    dados = _dados()
    monkeypatch.setattr(
        MacroProvider, "ipca_serie", Mock(side_effect=KeyError("coluna"))
    )
    _engine()._contexto_janelas(dados, AS_OF)
    assert sem_valor(dados["ipca_serie"], "erro inesperado no provedor macro: KeyError")
    assert sem_valor(
        dados["janelas_fundamentais"]["graham"], dados["ipca_serie"]["abstencao"]
    )
    assert "erro inesperado no provedor macro" in caplog.text
    assert dados["janelas_fundamentais"]["lynch"]["crescimento_lpa"] == pytest.approx(
        0.2
    )
