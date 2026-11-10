"""F3-6a aditivo: o transporte conserva os dados e metadados recebidos da borda.

Os esperados são payloads explícitos, independentes dos motores. A conversão de
objetos aninhados usa dataclasses.asdict como referência da biblioteca padrão.
Não há decisão de método ou valor econômico nestes contratos de transporte.
"""

from copy import deepcopy
from dataclasses import asdict

import pytest

from sentinela.domain.models import (
    AnalysisResult,
    DataQualityReport,
    FundamentalsSnapshot,
    MarketSnapshot,
    TechnicalResult,
    ValuationResult,
)

CONTEXTO = {
    "source": "documento oficial",
    "collected_at": "2026-11-10T15:00:00+00:00",
    "confidence": 0.8,
    "warnings": ["lacuna identificada"],
    "detalhe_adicional": {"hash": "a" * 64},
    "extra": {"documento": "DFP"},
}
MERCADO = {"ticker": "TSTA3", "preco_atual": 12.5, "quote_type": "EQUITY", **CONTEXTO}
FUNDAMENTOS = {"ticker": "TSTA3", "pl": 12, "roe": 0.1, **CONTEXTO}
QUALIDADE = {
    "dados_parciais": True,
    "campos_faltantes": ["vpa"],
    "riscos_dados": ["documento incompleto"],
    "erro_scraper": False,
    **CONTEXTO,
}
TECNICA = {"rsi": 42.0, "tendencia": "Neutro", "atr": 1.5, **CONTEXTO}
VALUATION = {"perfil": "DESCRITIVO", "riscos": ["sem histórico"], **CONTEXTO}
ANALISE = {
    "ticker": "TSTA3",
    "is_fii": True,
    "success": False,
    "error": "dado indisponível",
    "as_of": "2026-11-10T15:00:00+00:00",
    "execucao_id": "execucao-1",
    "market": MERCADO,
    "fundamentals": FUNDAMENTOS,
    "data_quality": QUALIDADE,
    "valuation": VALUATION,
    "technical": TECNICA,
    "peers": {"motivo": "indisponível"},
    "ai_analysis": "texto não confiável",
    "raw": {"ticker": "TSTA3", "lentes": {}, "proveniencia": {"hash": "b" * 64}},
    **CONTEXTO,
}


def _contem(esperado, recebido):
    for chave, valor in esperado.items():
        if chave == "extra":
            _contem(valor, recebido)
        elif isinstance(valor, dict):
            _contem(valor, recebido[chave])
        else:
            assert recebido[chave] == valor, chave


@pytest.mark.parametrize(
    "modelo,payload",
    [
        (MarketSnapshot, MERCADO),
        (FundamentalsSnapshot, FUNDAMENTOS),
        (DataQualityReport, QUALIDADE),
        (TechnicalResult, TECNICA),
        (ValuationResult, VALUATION),
        (AnalysisResult, ANALISE),
    ],
)
def test_payload_explicito_sobrevive_ao_transporte(modelo, payload):
    entrada = deepcopy(payload)
    r = modelo.from_dict(entrada)
    _contem(payload, r.to_dict())
    assert entrada == payload
    # Campos declarados permanecem atributos tipados, além do dicionário de saída.
    assert r.source == CONTEXTO["source"]
    assert r.collected_at == CONTEXTO["collected_at"]
    assert r.confidence == CONTEXTO["confidence"]
    assert r.warnings == CONTEXTO["warnings"]
    assert r.extra["documento"] == "DFP"
    assert modelo.from_dict(r.to_dict()).to_dict() == r.to_dict()


def test_campos_tipados_da_analise_nao_desaparecem_em_extras():
    r = AnalysisResult.from_dict(deepcopy(ANALISE))
    assert isinstance(r.market, MarketSnapshot)
    assert isinstance(r.fundamentals, FundamentalsSnapshot)
    assert isinstance(r.data_quality, DataQualityReport)
    assert isinstance(r.valuation, ValuationResult)
    assert isinstance(r.technical, TechnicalResult)
    assert r.ticker == "TSTA3"
    assert r.is_fii is True
    assert r.success is False
    assert r.error == "dado indisponível"
    assert r.peers == ANALISE["peers"]
    assert r.ai_analysis == ANALISE["ai_analysis"]
    assert r.raw == ANALISE["raw"]
    assert r.as_of == ANALISE["as_of"]
    assert r.execucao_id == "execucao-1"
    assert r.market.preco_atual == 12.5
    assert r.fundamentals.roe == 0.1
    assert r.data_quality.dados_parciais is True
    assert r.valuation.perfil == "DESCRITIVO"
    assert r.technical.rsi == 42.0


def test_modelos_ja_tipados_preservam_identidade():
    mercado = MarketSnapshot(ticker="TSTA3", preco_atual=12.5)
    fundamentos = FundamentalsSnapshot(roe=0.1)
    qualidade = DataQualityReport(dados_parciais=True)
    valuation = ValuationResult(perfil="DESCRITIVO")
    tecnica = TechnicalResult(rsi=42)
    r = AnalysisResult(
        market=mercado,
        fundamentals=fundamentos,
        data_quality=qualidade,
        valuation=valuation,
        technical=tecnica,
    )
    assert r.market is mercado
    assert r.fundamentals is fundamentos
    assert r.data_quality is qualidade
    assert r.valuation is valuation
    assert r.technical is tecnica


def test_estrutura_aninhada_preserva_listas_tuplas_e_modelos():
    mercado = MarketSnapshot(ticker="TSTA3", preco_atual=12.5)
    esperado = asdict(mercado)
    esperado.pop("extra")
    r = AnalysisResult(
        raw={"lista": [mercado], "tupla": (mercado,), "mapa": {"m": mercado}}
    )
    assert r.to_dict()["raw"] == {
        "lista": [esperado],
        "tupla": (esperado,),
        "mapa": {"m": esperado},
    }


def test_metadado_extra_nao_substitui_campo_publico_explicito():
    r = MarketSnapshot.from_dict(
        {"ticker": "TSTA3", "extra": {"ticker": "OUTR3", "fonte": "CVM"}}
    )
    assert r.ticker == "TSTA3"
    assert r.to_dict()["ticker"] == "TSTA3"
    assert r.to_dict()["fonte"] == "CVM"


@pytest.mark.parametrize(
    "modelo",
    [
        MarketSnapshot,
        FundamentalsSnapshot,
        DataQualityReport,
        ValuationResult,
        TechnicalResult,
    ],
)
def test_avisos_ausentes_sao_lista_vazia(modelo):
    assert modelo.from_dict({"warnings": None}).warnings == []


def test_payload_plano_do_app_preserva_valores_contexto_e_aliases_legados():
    # Contrato de compatibilidade: o app entrega o dict plano, não snapshots aninhados.
    payload = {
        "ticker": "TSTA3",
        "preco_atual": 12.5,
        "roe": 0.1,
        "pl": 12,
        "dados_parciais": True,
        "campos_faltantes": ["vpa"],
        "perfil": "DESCRITIVO",
        "tech": {"rsi": 42.0},
        "peers_data": {"grupo": "teste"},
        "analise_ia": "texto não confiável",
        "as_of": "2026-11-10T15:00:00+00:00",
        "execucao_id": "execucao-1",
    }
    r = AnalysisResult.from_dict(deepcopy(payload))
    assert r.market.preco_atual == 12.5
    assert r.market.ticker == "TSTA3"
    assert r.fundamentals.pl == 12
    assert r.fundamentals.roe == 0.1
    assert r.data_quality.dados_parciais is True
    assert r.data_quality.campos_faltantes == ["vpa"]
    assert r.valuation.perfil == "DESCRITIVO"
    assert r.technical.rsi == 42.0
    assert r.peers == {"grupo": "teste"}
    assert r.ai_analysis == "texto não confiável"
    assert r.raw == payload
    assert r.as_of == payload["as_of"]
    assert r.execucao_id == payload["execucao_id"]


def test_campos_canonicos_explicitos_prevalecem_sobre_aliases_legados():
    r = AnalysisResult.from_dict(
        {
            "peers": {"grupo": "atual"},
            "peers_data": {"grupo": "legado"},
            "ai_analysis": "texto atual",
            "analise_ia": "texto legado",
            "technical": {"rsi": 42},
            "tech": {"rsi": 99},
        }
    )
    assert r.peers == {"grupo": "atual"}
    assert r.ai_analysis == "texto atual"
    assert r.technical.rsi == 42
