"""Testes para peers_engine.py — foco em resiliência a falhas do scraper."""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

# Garantir que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from peers_engine import PeersEngine


def _make_engine(side_effect_fn):
    """Cria PeersEngine com market_engine mockado."""
    market = MagicMock()
    market.buscar_dados_ticker = MagicMock(side_effect=side_effect_fn)
    return PeersEngine(market)


# ── Cenário 1: Todos os peers retornam erro_scraper ──────────────────────────

def test_all_peers_erro_scraper_returns_safe_default():
    """Quando TODOS os peers devolvem {erro_scraper: True}, não deve crashar.
    Deve retornar resultado seguro com Peers_Utilizados vazio.
    """
    engine = _make_engine(lambda t: {"erro_scraper": True, "preco_atual": 10.0})

    result = engine.comparar("PETR4")

    assert "erro" in result
    assert result["Peers_Utilizados"] == []
    assert result.get("Setor") == "petroleo"
    assert result.get("PL_Media_Peers") is None


# ── Cenário 2: Mix de peers válidos e inválidos ──────────────────────────────

def test_mixed_valid_and_invalid_peers():
    """Peers com erro_scraper devem ser filtrados; válidos devem ser mantidos."""
    def fake_buscar(ticker):
        if ticker == "PRIO3":
            return {"erro_scraper": True, "preco_atual": 40.0}
        return {
            "ticker": ticker,
            "preco_atual": 30.0,
            "pl": 8.0,
            "pvp": 1.2,
            "dy": 0.05,
        }

    engine = _make_engine(fake_buscar)
    result = engine.comparar("PETR4")

    assert "erro" not in result
    assert "PRIO3" not in result["Peers_Utilizados"]
    assert len(result["Peers_Utilizados"]) > 0
    assert result["PL_Media_Peers"] is not None


# ── Cenário 3: Peer retorna None (falha de rede) ────────────────────────────

def test_peers_returning_none_are_ignored():
    """Peers que retornam None (timeout, rede) não devem crashar."""
    engine = _make_engine(lambda t: None)

    result = engine.comparar("PETR4")

    assert "erro" in result
    assert result["Peers_Utilizados"] == []


# ── Cenário 4: Peer dict sem chave 'ticker' ─────────────────────────────────

def test_peer_dict_without_ticker_key_filtered():
    """Dict sem 'ticker' (mas com preco_atual) deve ser filtrado, não crashar."""
    engine = _make_engine(lambda t: {"preco_atual": 25.0, "pl": 10.0})

    result = engine.comparar("PETR4")

    assert "erro" in result
    assert result["Peers_Utilizados"] == []


# ── Cenário 5: Todos válidos (happy path) ────────────────────────────────────

def test_all_valid_peers_happy_path():
    """Quando todos os peers são válidos, resultado deve conter médias corretas."""
    def fake_buscar(ticker):
        return {
            "ticker": ticker,
            "preco_atual": 20.0,
            "pl": 10.0,
            "pvp": 1.5,
            "dy": 0.06,
        }

    engine = _make_engine(fake_buscar)
    result = engine.comparar("PETR4")

    assert "erro" not in result
    assert result["Setor"] == "petroleo"
    assert result["PL_Media_Peers"] == 10.0
    assert result["PVP_Media_Peers"] == 1.5
    assert result["DY_Media_Peers"] == 0.06
    assert len(result["Peers_Utilizados"]) == 4  # PETR4 excluído dos próprios peers


# ── Cenário 6: Setor não cadastrado ─────────────────────────────────────────

def test_ticker_sem_setor_retorna_erro():
    """Ticker sem setor mapeado deve retornar erro sem crash."""
    engine = _make_engine(lambda t: None)

    result = engine.comparar("XYZW3")

    assert "erro" in result
