"""Fonte comum aprovada não preenche lentes abstidas nem modifica o CAGR."""

from datetime import date

import pytest

from sentinela.reports.rastreabilidade import construir_contexto, renderizar
from tests.regressao.test_bug_2c_37_lynch_fonte_payout import cenario
from tests.test_janelas_fundamentais import AS_OF
from valuation_engine import ValuationEngine


def test_perfil_renda_nao_inventa_payout_lynch():
    d = cenario(0.08, 0.02)
    r = ValuationEngine().processar(d, as_of=AS_OF)
    assert "Lynch:" not in r["metodos_usados"]
    assert "payout_contextual" not in d["janelas_fundamentais"]["lynch"]


def test_b3_zero_nao_preenche_bazin_abstido():
    d = cenario(0.0, 0.05)
    r = ValuationEngine().processar(d, as_of=AS_OF)
    assert "Lynch:" in r["metodos_usados"]
    assert "Bazin:" not in r["metodos_usados"]
    assert d["janelas_fundamentais"]["lynch"]["payout_contextual"]["valor"] == 0


def test_payout_maior_que_um_nao_reduz_valor_nem_trunca():
    d = cenario(0.03, 0.02)
    for e in d["serie_cvm"]["exercicios"]:
        e["lpa"] = 0.01 / 1.2 ** (2025 - e["exercicio"])
    ValuationEngine().processar(d, as_of=AS_OF)
    j = d["janelas_fundamentais"]["lynch"]
    assert j["payout_contextual"]["valor"] == pytest.approx(90.0)
    assert j["crescimento_lpa"] == pytest.approx(0.2)


def test_relatorio_mostra_fonte_aviso_e_payout_contextual():
    d = cenario(None, 0.02)
    motor = ValuationEngine()
    processar = motor.processar
    motor.processar = lambda entrada: processar(entrada, as_of=AS_OF)
    ctx = construir_contexto(d, False, date(2026, 10, 20), motor, None)
    lynch = next(m for m in ctx["metodos"] if m["nome"] == "Lynch")
    c = lynch["janela"]["payout_contextual"]
    assert c["valor"] == pytest.approx(2.0 / 2.0736)
    assert c["fonte"]["fonte"] == "cascata"
    assert "aviso" in c["fonte"]
    html = renderizar(ctx)
    assert "payout_contextual" in html
    assert "perfil pelo DY da cascata:" in html
