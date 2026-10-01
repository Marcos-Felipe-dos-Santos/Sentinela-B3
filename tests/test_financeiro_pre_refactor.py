"""Rede de segurança financeira antes do refactor da Fase 1.

Valores sintéticos, sem rede. Três seções, filtráveis por mark:

* A (``-m preservar``)       — comportamento que a V2 deve manter;
* B (``-m quebra_esperada``) — comportamento atual que DEVE mudar (cada teste cita o achado);
* C (``-m invariante``)      — propriedades que valem antes e depois.

Na Fase 1 (refactor puro) as três seções ficam inalteradas. Na Fase 2 só a B muda,
e a mudança de um teste da B é a prova da correção do achado.
"""

import itertools
import re
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

import market_engine
from config import _normalizar_dy
from fii_engine import FIIEngine
from portfolio_engine import PortfolioEngine
from valuation_engine import ValuationEngine

SELIC = 0.10


def _acao(**kw):
    base = {
        "ticker": "TST3",
        "preco_atual": 100.0,
        "roe": 0.12,
        "pl": 10.0,
        "pvp": 1.0,
        "dy": 0.06,
    }
    base.update(kw)
    return base


def _processar(dados, selic=SELIC):
    with patch("valuation_engine.get_selic_atual", return_value=selic):
        return ValuationEngine().processar(dados)


def _fii(selic=SELIC, **kw):
    base = {"ticker": "TST11", "preco_atual": 100.0, "dy": 0.0935, "pvp": 1.0}
    base.update(kw)
    with patch("fii_engine.get_selic_atual", return_value=selic):
        return FIIEngine().analisar(base)


def _metodos(resultado):
    """{'Graham': 150.0, ...} a partir do texto de metodos_usados."""
    return {
        nome: float(valor)
        for nome, valor in re.findall(
            r"(\w+): R\$([\d.]+)", resultado["metodos_usados"]
        )
    }


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO A — preservar
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.preservar
def test_a_fair_value_com_tres_metodos_e_a_mediana_nao_a_media():
    # Graham 150,00 · Bazin 60,00 · Gordon 51,54 → mediana 60,00; a média seria 87,18.
    r = _processar(_acao())
    metodos = _metodos(r)
    assert set(metodos) == {"Graham", "Bazin", "Gordon"}
    assert r["fair_value"] == pytest.approx(60.0, abs=0.01)
    assert r["fair_value"] != pytest.approx(sum(metodos.values()) / 3, abs=1)


@pytest.mark.preservar
def test_a_fair_value_com_dois_metodos_e_a_media_inclusive_com_divergencia():
    # Com dois métodos, `statistics.median` devolve a média. É comportamento atual que
    # ninguém decidiu; a decisão é do F2C-5. Graham 150,00 · Bazin 60,00 → 105,00,
    # e a flag max/min > 2 dispara mesmo assim.
    r = _processar(_acao(roe=0.08))
    assert set(_metodos(r)) == {"Graham", "Bazin"}
    assert r["fair_value"] == pytest.approx(105.0, abs=0.01)
    assert "Métodos divergentes" in r["riscos"]


@pytest.mark.preservar
def test_a_bazin_nao_dispara_abaixo_de_5_por_cento():
    abaixo = _processar(_acao(roe=0.08, dy=0.049))
    no_limite = _processar(_acao(roe=0.08, dy=0.05))
    assert "Bazin" not in _metodos(abaixo)
    assert _metodos(no_limite)["Bazin"] == pytest.approx(50.0, abs=0.01)


@pytest.mark.preservar
def test_a_fii_compara_dy_com_a_selic_liquida_de_ir():
    # Selic 10% → líquida 8,5%. DY 9,35% / 8,5% = 1,10 → preço justo 110,00.
    # Com a Selic bruta o resultado seria 93,50.
    r = _fii()
    assert r["fair_value"] == pytest.approx(110.0, abs=0.01)
    assert r["upside"] == pytest.approx(10.0, abs=0.1)


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO B — deve mudar (caracteriza o estado atual)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.quebra_esperada
@pytest.mark.f4_gordon_nominal
def test_b_gordon_desconta_pela_selic_nominal_mais_premio():
    # QUEBRA ESPERADA: F-4 — Gordon usa k = Selic nominal + 7%, com g nominal.
    # A Fase 2B troca por taxa real (NTN-B + prêmio) com k e g no mesmo regime.
    # dy 6%, lpa 10 → payout 60%, g = 12% × 40% = 4,8%; k = 17%.
    esperado = (6.0 * 1.048) / (0.10 + 0.07 - 0.048)
    assert _metodos(_processar(_acao()))["Gordon"] == pytest.approx(esperado, abs=0.01)


@pytest.mark.quebra_esperada
@pytest.mark.f4_gordon_nominal
def test_b_gordon_acompanha_a_selic_um_para_um():
    # QUEBRA ESPERADA: F-4 — a Selic é a taxa de desconto; subir 5 pontos reduz o Gordon.
    baixa = _metodos(_processar(_acao(), selic=0.10))["Gordon"]
    alta = _metodos(_processar(_acao(), selic=0.15))["Gordon"]
    assert alta == pytest.approx((6.0 * 1.048) / (0.15 + 0.07 - 0.048), abs=0.01)
    assert alta < baixa


@pytest.mark.quebra_esperada
@pytest.mark.f9_fii_selic
def test_b_fii_nao_considera_o_patrimonio_no_fair_value():
    # QUEBRA ESPERADA: F-9 — o preço justo do FII é só DY ÷ Selic líquida; P/VP entra
    # apenas no score. Um FII a 0,5× e outro a 2× o patrimônio têm o mesmo fair value.
    barato = _fii(pvp=0.5)
    caro = _fii(pvp=2.0)
    assert barato["fair_value"] == caro["fair_value"] == pytest.approx(110.0, abs=0.01)
    assert barato["score_final"] > caro["score_final"]


@pytest.mark.quebra_esperada
@pytest.mark.f12_alavancagem_total
def test_b_divida_pl_da_cvm_e_endividamento_contabil_total_rotulado_como_liquido():
    # QUEBRA ESPERADA: F-12 — (passivo_total − PL) / PL entra como `div_liq_patrimonio`.
    assert market_engine._CVM_TO_MARKET["divida_pl"] == "div_liq_patrimonio"


@pytest.mark.quebra_esperada
@pytest.mark.f12_alavancagem_total
def test_b_alavancagem_acima_de_3x_penaliza_score_e_confianca_sem_distinguir_setor():
    # QUEBRA ESPERADA: F-12/F-13 — o mesmo limite 3,0 vale para qualquer setor.
    normal = _processar(_acao(divida_liq_ebitda=2.9))
    alavancada = _processar(_acao(divida_liq_ebitda=3.1))
    assert normal["score_final"] - alavancada["score_final"] == 15
    assert normal["confianca"] - alavancada["confianca"] == 15
    assert "Dívida elevada" in alavancada["riscos"]


@pytest.mark.quebra_esperada
@pytest.mark.f15_markowitz_um_ano
def test_b_markowitz_divide_40_por_cento_fiis_e_60_por_cento_acoes_fixo():
    # QUEBRA ESPERADA: F-15 — divisão fixa independente de risco ou retorno (F2C-9).
    datas = pd.date_range("2023-01-01", periods=35)
    precos = pd.DataFrame(
        {"ITUB4": np.linspace(10, 20, 35), "HGLG11": np.linspace(100, 110, 35)},
        index=datas,
    )
    with patch("portfolio_engine.get_selic_atual", return_value=SELIC):
        r = PortfolioEngine().otimizar(precos)
    assert r["HGLG11"] == 40.0
    assert r["ITUB4"] == 60.0


@pytest.mark.quebra_esperada
@pytest.mark.f15_markowitz_um_ano
def test_b_markowitz_aceita_trinta_pregoes_e_rejeita_menos():
    # QUEBRA ESPERADA: F-15 — retorno esperado estimado com janela curta (aqui, 30 pregões;
    # na tela, um ano) não tem significância estatística.
    datas30 = pd.date_range("2023-01-01", periods=30)
    datas29 = pd.date_range("2023-01-01", periods=29)
    with patch("portfolio_engine.get_selic_atual", return_value=SELIC):
        ok = PortfolioEngine().otimizar(
            pd.DataFrame({"ITUB4": np.linspace(10, 20, 30)}, index=datas30)
        )
        curto = PortfolioEngine().otimizar(
            pd.DataFrame({"ITUB4": np.linspace(10, 20, 29)}, index=datas29)
        )
    assert "erro" not in ok
    assert "erro" in curto


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO C — invariantes
# ══════════════════════════════════════════════════════════════════════════════

_GRADE_ACOES = list(
    itertools.product(
        [0, 3, 8, 15, 24],  # pl
        [0, 0.5, 1, 2.4],  # pvp
        [-0.1, 0.03, 0.12, 0.3],  # roe
        [0, 0.02, 0.06, 0.2, 5, 12],  # dy (decimal ou percentual)
        [0.05, 0.1475],  # selic
    )
)
_GRADE_FII = list(
    itertools.product([0, 0.02, 0.08, 0.12, 9, 12], [0.5, 1, 1.3], [0.05, 0.1475])
)


@pytest.mark.invariante
@pytest.mark.parametrize("dy_bruto", [0, 0.01, 0.0935, 0.25, 1, 3.02, 12.47, 30])
def test_c_dy_normalizado_fica_entre_zero_e_trinta_por_cento(dy_bruto):
    dy, _ = _normalizar_dy(dy_bruto)
    assert 0.0 <= dy <= 0.30


@pytest.mark.invariante
@pytest.mark.xfail(
    reason="BUG (armadilha 4): percentual acima de 30 passa como DY confiável (45 → 0,45)"
)
def test_c_dy_percentual_acima_de_30_nao_pode_sair_confiavel():
    dy, confiavel = _normalizar_dy(45.0)
    assert not (confiavel and dy > 0.30)


@pytest.mark.invariante
def test_c_score_da_acao_fica_entre_0_e_100():
    for pl, pvp, roe, dy, selic in _GRADE_ACOES:
        r = _processar(
            _acao(pl=pl, pvp=pvp, roe=roe, dy=dy, divida_liq_ebitda=4), selic=selic
        )
        assert 0 <= r["score_final"] <= 100, (pl, pvp, roe, dy, selic)


@pytest.mark.invariante
def test_c_score_do_fii_fica_entre_0_e_100():
    for dy, pvp, selic in _GRADE_FII:
        r = _fii(selic=selic, dy=dy, pvp=pvp, ticker="CVBI11")
        assert 0 <= r["score_final"] <= 100, (dy, pvp, selic)


@pytest.mark.invariante
def test_c_fair_value_e_preco_estao_na_mesma_escala():
    # Pega erro de fator 100 (percentual × decimal) ou de mil/unidade.
    preco = 50.0
    for pl, pvp, roe, dy, selic in _GRADE_ACOES:
        r = _processar(
            _acao(preco_atual=preco, pl=pl, pvp=pvp, roe=roe, dy=dy), selic=selic
        )
        assert 0.1 <= r["fair_value"] / preco <= 20, (pl, pvp, roe, dy, selic)
    for dy, pvp, selic in _GRADE_FII:
        r = _fii(selic=selic, preco_atual=preco, dy=dy, pvp=pvp)
        assert 0.1 <= r["fair_value"] / preco <= 20, (dy, pvp, selic)
