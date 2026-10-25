"""Sem estimativas manuais de FII (F2A-23; E-25, F-10).

A tabela de vacância manual do motor (removida no F2A-13) e `FII_MANUAL_FALLBACK` (cascata)
eram estimativas sem data nem fonte; duas atribuíam vacância física a fundos de papel. Vacância, só de fonte oficial, e o
Informe Mensal não a traz.
"""

from unittest.mock import patch

import pytest
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

from fii_engine import FIIEngine
from tests.test_market_engine import FakeBrapi, FakeCache, _engine, _historico


def _analisar(ticker):
    dados = {"ticker": ticker, "preco_atual": 150.0, "dy": 0.08, "pvp": 0.9}
    with patch("fii_engine.get_selic_atual", return_value=0.10):
        return FIIEngine().analisar(enriquecer_fii(dados), as_of=AS_OF_GORDON)  # F2B-2


def test_vacancia_manual_nao_altera_dy_nem_score():
    com_estimativa = _analisar("CVBI11")
    sem_estimativa = _analisar("XPML11")  # fora da tabela, mesmos números
    assert com_estimativa["dy_efetivo"] == pytest.approx(0.08)
    assert "vacancia_fonte" not in com_estimativa
    for campo in ("fair_value", "upside", "score_final", "recomendacao", "dy_efetivo"):
        assert com_estimativa[campo] == sem_estimativa[campo], campo


def test_fii_sem_fonte_nao_recebe_estimativa_manual(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(100.0),
        info={"currentPrice": 100.0},
        brapi=FakeBrapi(disponivel=False),
        cache=FakeCache(),
    )
    dados = engine.buscar_dados_ticker("CVBI11")  # está em FII_MANUAL_FALLBACK
    for campo in ("dy", "pvp", "vacancia"):
        assert campo not in dados, campo
    assert dados["dados_manual"] is False
    assert "fundamentos FII preenchidos manualmente" not in dados["riscos_dados"]
    assert set(dados["campos_faltantes"]) >= {"dy", "pvp"}
