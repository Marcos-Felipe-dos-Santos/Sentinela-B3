"""Invariantes externos da auditoria; não reproduzem contas das lentes."""

from dataclasses import dataclass
from unittest.mock import Mock

import pytest

import auditoria


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("fair_value", float("nan")),
        ("upside", float("inf")),
        ("score_final", -1),
        ("score_final", 101),
    ],
)
def test_invariantes_rejeitam_numeros_fora_do_dominio(campo, valor):
    assert auditoria.invariantes_resultado({campo: valor})


def test_ausencia_nao_exige_numero_e_upside_sem_valor_e_invalido():
    assert auditoria.invariantes_resultado({"fair_value": None, "upside": None}) == []
    assert auditoria.invariantes_resultado({"fair_value": None, "upside": 0})
    assert (
        auditoria.invariantes_resultado(
            {"fair_value": 20, "upside": -20, "score_final": 100}
        )
        == []
    )


def test_resumo_nao_imprime_observacoes():
    resumo = auditoria.resumo_serie(
        {"exercicios": [{"documento": "CONTEUDO_EXTENSO"}] * 5}
    )
    assert resumo == {"exercicios": {"observacoes": 5}}
    assert "CONTEUDO_EXTENSO" not in str(resumo)


def test_orquestracao_e_contrato_sao_usados_sem_oraculo_autorreferente(monkeypatch):
    import valuation_engine

    @dataclass
    class AbstencaoTeste:
        motivo: str

    engine = Mock()
    engine._avaliar_metodos.return_value = {"Graham": AbstencaoTeste("insumo ausente")}
    avaliar = engine._avaliar_metodos
    dados = {"ticker": "TSTA3"}

    def processar(entrada):
        assert entrada is dados
        engine._avaliar_metodos()
        return {"fair_value": None, "upside": None, "riscos": ["insumo ausente"]}

    engine.processar.side_effect = processar
    monkeypatch.setattr(valuation_engine, "ValuationEngine", lambda: engine)
    monkeypatch.setattr(auditoria, "_rel", {"tickers": {}})
    fv, upside, resultado = auditoria.auditar_valuation("TSTA3", dados)
    engine.processar.assert_called_once_with(dados)
    avaliar.assert_called_once_with()
    assert fv is None and upside is None
    assert resultado["riscos"] == ["insumo ausente"]
    auditado = auditoria._rel["tickers"]["TSTA3"]["valuation"]
    assert auditado["metodos"]["Graham"] == {"motivo": "insumo ausente"}
    assert {e["nome"] for e in auditado["registro"]} >= {"Graham", "Lynch", "Bazin"}
