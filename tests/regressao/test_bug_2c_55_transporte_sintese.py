"""O transporte novo não reintroduz a síntese retirada pelo motor (apresentação1.0)."""

from unittest.mock import MagicMock

from sentinela.domain.models import ValuationResult
from sentinela.services.analyze_asset import AnalysisService

NOVO = {"apresentacao_versao": "1.0", "lentes": {"Graham": {"valor": 100}}}
AGREGADOS = {"fair_value", "upside", "score_final", "recomendacao"}


def test_dataclass_nova_nao_inventa_campos_agregados():
    saida = ValuationResult.from_dict(NOVO).to_dict()
    assert not AGREGADOS & saida.keys()
    assert saida["lentes"] == NOVO["lentes"]


def test_servico_novo_nao_herda_agregado_do_cache():
    market, engine, fii, tech, ai = [MagicMock() for _ in range(5)]
    market.buscar_dados_ticker.return_value = {
        "ticker": "TST3",
        "preco_atual": 50,
        "quote_type": "EQUITY",
        "fair_value": 200,
        "score_final": 90,
    }
    engine.processar.return_value = NOVO
    ai.analisar.return_value = {"content": "hipóteses"}
    service = AnalysisService(market, engine, fii, tech, ai_engine=ai)
    result = service.analyze("TST3", persist=False)
    assert not AGREGADOS & result.raw.keys()
    assert not AGREGADOS & ai.analisar.call_args.args[1].keys()
