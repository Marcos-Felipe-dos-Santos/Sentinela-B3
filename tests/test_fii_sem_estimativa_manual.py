"""Sem estimativas manuais de FII (F2A-23; E-25, F-10).

`VACANCIA_CONHECIDA` (motor) e `FII_MANUAL_FALLBACK` (cascata) são estimativas sem data nem
fonte; duas atribuem vacância física a fundos de papel. Vacância, só de fonte oficial, e o
Informe Mensal não a traz.
"""

from unittest.mock import patch

import pytest

from fii_engine import VACANCIA_CONHECIDA, FIIEngine
from tests.test_market_engine import FakeBrapi, FakeCache, _engine, _historico


def _analisar(ticker):
    dados = {"ticker": ticker, "preco_atual": 150.0, "dy": 0.08, "pvp": 0.9}
    with patch("fii_engine.get_selic_atual", return_value=0.10):
        return FIIEngine(cvm_provider=None).analisar(dados)


def test_vacancia_manual_nao_altera_dy_nem_score():
    assert "CVBI11" in VACANCIA_CONHECIDA  # 25% estimados, num fundo de papel
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
