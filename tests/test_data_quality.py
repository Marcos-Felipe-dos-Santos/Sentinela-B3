"""Testes para DataQualityReport (data_quality.py).

Todos os dados são sintéticos — sem chamadas de rede.
"""
import pytest

from data_quality import (
    DataQualityReport,
    _BADGE_CVM,
    _BADGE_PARCIAL,
    _BADGE_SEM_CVM,
    _best_fonte,
    _normalize_fonte,
)


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _dados_completos() -> dict:
    """10 campos presentes, brapi, sem CVM. Valores internamente consistentes."""
    return {
        "ticker":            "PETR4",
        "preco_atual":       40.0,
        "dy":                0.08,
        "pl":                8.0,    # = preco / lpa = 40 / 5 ✓
        "pvp":               1.2,    # = preco / vpa = 40 / 33.33 ≈ 1.20 ✓
        "roe":               0.15,
        "lpa":               5.0,
        "vpa":               33.33,
        "divida_liq_ebitda": 2.5,
        "margem_liquida":    0.12,
        "receita_liquida":   500_000_000.0,
        "fonte_fundamentos": "brapi",
        "cvm_disponivel":    False,
    }


# ---------------------------------------------------------------------------
# _normalize_fonte / _best_fonte
# ---------------------------------------------------------------------------

def test_normalize_yfinance_partial():
    assert _normalize_fonte("yfinance_partial") == "yfinance"


def test_normalize_fundamentals_cache():
    assert _normalize_fonte("fundamentals_cache") == "fundamentus"


def test_normalize_manual_fii():
    assert _normalize_fonte("manual_fii") == "manual"


def test_normalize_passthrough():
    assert _normalize_fonte("CVM") == "CVM"
    assert _normalize_fonte("brapi") == "brapi"


def test_best_fonte_composto_retorna_maior_confianca():
    # CVM (100) > brapi (80) > fundamentus (40)
    assert _best_fonte("brapi+fundamentus") == "brapi"
    assert _best_fonte("CVM+brapi+fundamentus") == "CVM"


def test_best_fonte_alias():
    # yfinance_partial normaliza para yfinance (60) > fundamentus (40)
    assert _best_fonte("yfinance_partial+fundamentus") == "yfinance"


# ---------------------------------------------------------------------------
# completude()
# ---------------------------------------------------------------------------

def test_completude_todos_campos_presentes():
    r = DataQualityReport(_dados_completos())
    comp = r.completude()
    assert comp["completude_pct"] == 100
    assert all(v["presente"] for v in comp["campos"].values())


def test_completude_campos_ausentes():
    dados = _dados_completos()
    for campo in ("lpa", "vpa", "divida_liq_ebitda", "margem_liquida", "receita_liquida"):
        del dados[campo]
    r = DataQualityReport(dados)
    comp = r.completude()
    assert comp["completude_pct"] == 50


def test_completude_score_confianca_brapi():
    """10 campos brapi (80 cada) → score = 80."""
    r = DataQualityReport(_dados_completos())
    comp = r.completude()
    assert comp["score_confianca"] == 80


def test_completude_score_confianca_parcial():
    """5 campos brapi + 5 ausentes → score = 40."""
    dados = _dados_completos()
    for campo in ("lpa", "vpa", "divida_liq_ebitda", "margem_liquida", "receita_liquida"):
        del dados[campo]
    r = DataQualityReport(dados)
    comp = r.completude()
    assert comp["score_confianca"] == 40


def test_completude_confianca_cvm_campos():
    """cvm_disponivel=True → _CVM_CAMPOS têm fonte 'CVM' e confiança 100."""
    dados = _dados_completos()
    dados["cvm_disponivel"] = True
    dados["fonte_fundamentos"] = "CVM"
    r = DataQualityReport(dados)
    comp = r.completude()
    for campo in ("roe", "margem_liquida", "receita_liquida", "lpa", "vpa"):
        assert comp["campos"][campo]["fonte"] == "CVM", campo
        assert comp["campos"][campo]["confianca"] == 100, campo


def test_completude_divida_liq_ebitda_nao_e_cvm():
    """divida_liq_ebitda não deve ser atribuída à CVM mesmo com cvm_disponivel=True."""
    dados = _dados_completos()
    dados["cvm_disponivel"] = True
    dados["fonte_fundamentos"] = "CVM"
    r = DataQualityReport(dados)
    comp = r.completude()
    assert comp["campos"]["divida_liq_ebitda"]["fonte"] != "CVM"


def test_completude_usa_field_provenance():
    """Quando field_provenance presente, usar fonte de lá (prioritário)."""
    dados = _dados_completos()
    dados["field_provenance"] = {
        "dy": {
            "value": 0.08,
            "unit": "ratio",
            "provenance": {"source": "CVM"},
            "name": "dy",
            "extra": {},
        }
    }
    r = DataQualityReport(dados)
    comp = r.completude()
    assert comp["campos"]["dy"]["fonte"] == "CVM"
    assert comp["campos"]["dy"]["confianca"] == 100


def test_completude_field_provenance_normaliza_alias():
    """fonte em field_provenance também deve ser normalizada via _ALIAS."""
    dados = _dados_completos()
    dados["field_provenance"] = {
        "dy": {
            "value": 0.08,
            "unit": "ratio",
            "provenance": {"source": "yfinance_partial"},
            "name": "dy",
            "extra": {},
        }
    }
    r = DataQualityReport(dados)
    comp = r.completude()
    assert comp["campos"]["dy"]["fonte"] == "yfinance"
    assert comp["campos"]["dy"]["confianca"] == 60


def test_completude_fonte_yfinance_partial_normalizada():
    """fonte_fundamentos='yfinance_partial' deve ser normalizada → yfinance (60)."""
    dados = {
        "preco_atual":       40.0,
        "dy":                0.08,
        "pl":                8.0,
        "fonte_fundamentos": "yfinance_partial",
        "cvm_disponivel":    False,
    }
    r = DataQualityReport(dados)
    comp = r.completude()
    # dy e pl presentes sem field_provenance → usa fonte_base = yfinance
    for campo in ("dy", "pl"):
        assert comp["campos"][campo]["fonte"] == "yfinance"
        assert comp["campos"][campo]["confianca"] == 60


def test_completude_dado_none():
    r = DataQualityReport({})
    comp = r.completude()
    assert comp["completude_pct"] == 0
    assert comp["score_confianca"] == 0


# ---------------------------------------------------------------------------
# badge()
# ---------------------------------------------------------------------------

def test_badge_cvm():
    dados = _dados_completos()
    dados["cvm_disponivel"] = True
    assert DataQualityReport(dados).badge() == _BADGE_CVM


def test_badge_parcial():
    """Sem CVM mas completude >= 40% → amarelo."""
    dados = _dados_completos()  # completude 100%
    dados["cvm_disponivel"] = False
    assert DataQualityReport(dados).badge() == _BADGE_PARCIAL


def test_badge_sem_cvm():
    """Sem CVM e completude < 40% → vermelho."""
    r = DataQualityReport({"ticker": "XPTO11", "preco_atual": 10.0, "cvm_disponivel": False})
    assert r.badge() == _BADGE_SEM_CVM


# ---------------------------------------------------------------------------
# validacao_cruzada()
# ---------------------------------------------------------------------------

def test_validacao_dados_consistentes_sem_alertas():
    """Dados de _dados_completos() são internamente consistentes — lista vazia."""
    r = DataQualityReport(_dados_completos())
    assert r.validacao_cruzada() == []


def test_validacao_dy_alto():
    dados = _dados_completos()
    dados["dy"] = 0.35  # > 0.25 → improvável
    alertas = DataQualityReport(dados).validacao_cruzada()
    assert any("dy" in a for a in alertas)


def test_validacao_pl_divergente():
    dados = _dados_completos()
    dados["preco_atual"] = 40.0
    dados["lpa"] = 5.0    # derivado = 40 / 5 = 8.0
    dados["pl"] = 15.0    # declarado 15.0 → divergência 87%
    alertas = DataQualityReport(dados).validacao_cruzada()
    assert any("pl" in a for a in alertas)


def test_validacao_pl_consistente_sem_alerta():
    dados = _dados_completos()
    dados["preco_atual"] = 40.0
    dados["lpa"] = 5.0
    dados["pl"] = 8.0     # = 40/5 → divergência 0% ✓
    alertas = DataQualityReport(dados).validacao_cruzada()
    assert not any("pl=" in a for a in alertas)


def test_validacao_pvp_divergente():
    dados = _dados_completos()
    dados["preco_atual"] = 40.0
    dados["vpa"] = 33.33  # derivado = 40 / 33.33 ≈ 1.20
    dados["pvp"] = 2.5    # declarado 2.5 → divergência 52%
    alertas = DataQualityReport(dados).validacao_cruzada()
    assert any("pvp" in a for a in alertas)


def test_validacao_roe_positivo_margem_negativa():
    dados = _dados_completos()
    dados["roe"] = 0.20
    dados["margem_liquida"] = -0.05
    alertas = DataQualityReport(dados).validacao_cruzada()
    assert any("roe" in a for a in alertas)


def test_validacao_sem_dados_retorna_lista_vazia():
    assert DataQualityReport({}).validacao_cruzada() == []
