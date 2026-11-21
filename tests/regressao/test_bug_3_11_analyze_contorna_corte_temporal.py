"""BUG-3-11: decisão 1/F3-6a recusa falso histórico em toda entrada pública."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from sentinela.services.analyze_asset import AnalysisService


def test_api_legada_nao_expoe_as_of_que_contorna_a_guarda():
    mercado = Mock()
    mercado.buscar_dados_ticker.return_value = {"ticker": "TSTA3", "preco_atual": 10}
    motor = Mock()
    motor.processar.return_value = {"lentes": {}}
    tecnica = Mock()
    tecnica.calcular_indicadores.return_value = {}
    s = AnalysisService(
        mercado,
        motor,
        Mock(),
        tecnica,
        hoje=date(2026, 11, 10),
        asset_classifier=SimpleNamespace(is_fii=lambda *args: False),
    )
    with pytest.raises(TypeError, match="as_of"):
        s.analyze("TSTA3", as_of=datetime(2025, 1, 1, tzinfo=UTC), persist=False)
    mercado.buscar_dados_ticker.assert_not_called()
    motor.processar.assert_not_called()
