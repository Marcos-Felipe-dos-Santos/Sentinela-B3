from unittest.mock import patch

import pytest
from apoio_apresentacao import verificar_lentes
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

from config import MACRO
from fii_engine import FIIEngine


@pytest.fixture
def engine():
    return FIIEngine()


def test_fii_engine_valid_input(engine):
    dados = {"ticker": "HGLG11", "preco_atual": 150.0, "pvp": 0.9, "dy": 0.08}
    with patch("fii_engine.get_selic_atual", return_value=0.10):
        result = engine.analisar(enriquecer_fii(dados), as_of=AS_OF_GORDON)  # F2B-2
    assert result is not None
    assert "fair_value" in result
    assert "upside" in result
    verificar_lentes(result)
    assert "recomendacao" not in result
    assert "tipo" in result
    assert result["tipo"] == "TIPO INDISPONÍVEL"
    verificar_lentes(result)


def test_fii_engine_missing_optional_values(engine):
    dados = {
        "ticker": "HGLG11",
        "preco_atual": 150.0,
        # missing pvp and dy
    }
    with patch("fii_engine.get_selic_atual", return_value=0.10):
        result = engine.analisar(dados)

    assert result is not None
    # Will fallback due to missing dy
    assert result["metodos_usados"] == "Dados insuficientes (DY ausente ou inválido)"
    verificar_lentes(result)
    verificar_lentes(result)


def test_fii_engine_vacancy_adjustment(engine):
    dados = {"ticker": "VAC11", "preco_atual": 100.0, "pvp": 1.0, "dy": 0.10}
    with patch("fii_engine.get_selic_atual", return_value=0.10):
        result = engine.analisar(enriquecer_fii(dados), as_of=AS_OF_GORDON)

    # F2A-23: a vacância manual não é lida; o DY efetivo é o próprio DY.
    assert result["dy"] == pytest.approx(0.10)
    assert result["dy_efetivo"] == pytest.approx(0.10)
    # F2B-2: rendimento de 12 meses ÷ (NTN-B real + spread), sem a vacância.
    assert result["fair_value"] == pytest.approx(
        round(10.0 / (0.07 + MACRO.FII_SPREAD_TIJOLO), 2)
    )
    assert "vacancia_fonte" not in result


# ── Teste de baseline para bug conhecido ─────────────────────────────────────


def test_fii_preco_justo_pela_ntnb_e_spread_sem_selic(engine):
    """F2B-2: o preço justo é o rendimento ÷ (NTN-B real + spread); a Selic não entra.

    Antes (F-9), era preço × DY ÷ (Selic × 0,85): 117,65 com Selic de 10% e DY de 10%.
    """
    dados = {
        "ticker": "FIIX11",
        "preco_atual": 100.0,
        "dy": 0.10,
        "pvp": 1.0,
    }
    for selic in (0.05, 0.10, 0.20):
        with patch("fii_engine.get_selic_atual", return_value=selic):
            result = engine.analisar(enriquecer_fii(dados), as_of=AS_OF_GORDON)
        assert result["fair_value"] == pytest.approx(
            round(10.0 / (0.07 + MACRO.FII_SPREAD_TIJOLO), 2)
        )


def test_fii_vacancia_manual_tem_flag():
    """F2A-23: a vacância manual não é lida; sem fonte oficial, não há vacância."""
    engine = FIIEngine()
    dados = {"ticker": "HGLG11", "preco_atual": 150.0, "dy": 0.08, "pvp": 0.9}

    with patch("fii_engine.get_selic_atual", return_value=0.10):
        result = engine.analisar(enriquecer_fii(dados), as_of=AS_OF_GORDON)

    assert "vacancia_fonte" not in result
    assert result["dy_efetivo"] == pytest.approx(0.08)
