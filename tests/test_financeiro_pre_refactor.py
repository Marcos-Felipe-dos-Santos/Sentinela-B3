"""Rede de segurança financeira antes do refactor da Fase 1.

Valores sintéticos, sem rede. Três seções, filtráveis por mark:

* A (``-m preservar``)       — comportamento que a V2 deve manter;
* B (``-m quebra_esperada``) — comportamento atual que DEVE mudar (cada teste cita o achado);
* C (``-m invariante``)      — propriedades que valem antes e depois.

Quebra aprovada pelo Marcos em29/10/2026: somente os dois testes C de score
são substituídos no F2C-3 por invariantes de lentes individuais/distância, na
mesma grade, sem score agregado. Os dois testes A de síntese têm substituição
autorizada no F2C-5; nenhuma outra asserção de A/C pode mudar.

Regra original da Fase 1: as três seções ficam inalteradas; na Fase 2 só B muda.
As exceções acima têm autorização expressa e não dispensam os demais controles.
"""

import itertools
import math
import re
from unittest.mock import patch

import pytest
from apoio_bazin import enriquecer_bazin
from apoio_escopo import de_empresa
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON, DiaGordon, enriquecer_gordon

import market_engine
from config import MACRO, _normalizar_dy
from fii_engine import FIIEngine
from valuation_engine import ValuationEngine

SELIC = 0.10


def _acao(*, com_dva=True, **kw):
    base = {
        "ticker": "TST3",
        "preco_atual": 100.0,
        "roe": 0.12,
        "pl": 10.0,
        "pvp": 1.0,
        "dy": 0.06,
    }
    base.update(kw)
    return enriquecer_bazin(enriquecer_gordon(base, com_dva=com_dva))


def _processar(dados, selic=SELIC):
    # F2B-5: o motor não lê mais a Selic; ela entra no MACRO para provar a independência.
    with (
        patch.object(MACRO, "_selic", selic),
        patch("valuation_engine.date", DiaGordon),
    ):
        return ValuationEngine().processar(de_empresa(dados), as_of=AS_OF_GORDON)


def _fii(selic=SELIC, **kw):
    # F2B-2: só os insumos do novo contrato (Informe, B3 e NTN-B real sintéticos, as_of
    # fixo), como a ressalva dos helpers do F2B-1; nenhuma asserção muda por isso.
    base = {"ticker": "TST11", "preco_atual": 100.0, "dy": 0.0935, "pvp": 1.0}
    base.update(kw)
    with patch("fii_engine.get_selic_atual", return_value=selic):
        return FIIEngine().analisar(enriquecer_fii(base), as_of=AS_OF_GORDON)


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


# Taxas injetadas pelos testes da seção A: as propriedades valem para qualquer uma delas.
# Os números que dependem da Selic como taxa estão na seção B (F2B-7, [SEÇÃO A] em (c)).
TAXAS = (0.06, 0.10, 0.1475, 0.20)


@pytest.mark.preservar
@pytest.mark.parametrize("selic", TAXAS)
def test_a_fair_value_com_tres_metodos_e_a_mediana_nao_a_media(selic):
    r = _processar(_acao(), selic=selic)
    metodos = _metodos(r)
    assert set(metodos) == {"Graham", "Bazin", "Gordon"}
    valores = sorted(metodos.values())
    assert len(set(valores)) == 3
    assert r["fair_value"] == pytest.approx(valores[1], abs=0.01)
    assert r["fair_value"] != pytest.approx(sum(valores) / 3, abs=1)


@pytest.mark.preservar
@pytest.mark.parametrize("selic", TAXAS)
def test_a_fair_value_com_dois_metodos_e_a_media_inclusive_com_divergencia(selic):
    # Com dois métodos, `statistics.median` devolve a média. É comportamento atual que
    # ninguém decidiu; a decisão é do F2C-5.
    r = _processar(_acao(roe=0.08, com_dva=False), selic=selic)
    metodos = _metodos(r)
    assert set(metodos) == {"Graham", "Bazin"}
    assert r["fair_value"] == pytest.approx(sum(metodos.values()) / 2, abs=0.01)


@pytest.mark.preservar
@pytest.mark.parametrize("selic", TAXAS)
def test_a_bazin_nao_dispara_abaixo_de_5_por_cento(selic):
    abaixo = _processar(_acao(roe=0.08, dy=0.049), selic=selic)
    no_limite = _processar(_acao(roe=0.08, dy=0.05), selic=selic)
    assert "Bazin" not in _metodos(abaixo)
    assert "Bazin" in _metodos(no_limite)


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO B — deve mudar (caracteriza o estado atual)
# ══════════════════════════════════════════════════════════════════════════════

# Selic dos testes do F-5: abaixo do piso antigo de 5% e acima de 6%; nenhuma coincide com
# o critério fixo de 6%, em que a taxa antiga e a nova dariam o mesmo número.
TAXAS_F5 = (0.03, 0.10, 0.1475, 0.20)


@pytest.mark.quebra_esperada
@pytest.mark.f4_gordon_nominal
@pytest.mark.f5_bazin_selic
@pytest.mark.parametrize("selic", TAXAS_F5)
def test_b_mediana_de_tres_metodos_pela_selic(selic):
    # F-4 e F-5 — veio da seção A (F2B-7). Era, com Selic de 10%, Graham 150,00 · Bazin
    # 60,00 (DY ÷ Selic) · Gordon 51,54 (Selic + prêmio) → mediana 60,00. Com a taxa real
    # (F2B-1, Gordon 30,60) e o critério fixo de 6% do Bazin (F2B-31, ficha 1.0): Bazin
    # 100,00 e mediana 100,00, a mesma em qualquer Selic.
    r = _processar(_acao(), selic=selic)
    assert set(_metodos(r)) == {"Graham", "Bazin", "Gordon"}
    assert r["fair_value"] == pytest.approx(100.0, abs=0.01)


@pytest.mark.quebra_esperada
@pytest.mark.f5_bazin_selic
@pytest.mark.parametrize("selic", TAXAS_F5)
def test_b_media_de_dois_metodos_pela_selic(selic):
    # F-5 — veio da seção A (F2B-7). Era, com Selic de 10%, Graham 150,00 · Bazin 60,00
    # → 105,00, com a flag max/min > 2. Com 6% fixos (F2B-31): Bazin 100,00 → 125,00 em
    # qualquer Selic, e a razão 1,5 não dispara a flag.
    r = _processar(_acao(roe=0.08, com_dva=False), selic=selic)
    assert set(_metodos(r)) == {"Graham", "Bazin"}
    assert r["fair_value"] == pytest.approx(125.0, abs=0.01)
    assert "Métodos divergentes" not in r["riscos"]


@pytest.mark.quebra_esperada
@pytest.mark.f5_bazin_selic
@pytest.mark.parametrize("selic", TAXAS_F5)
def test_b_bazin_no_limite_de_5_por_cento_pela_selic(selic):
    # F-5 — veio da seção A (F2B-7). Era DY 5% ÷ Selic 10% → 50,00. Com 6% fixos
    # (F2B-31): 5 ÷ 0,06 = 83,33 em qualquer Selic.
    no_limite = _processar(_acao(roe=0.08, dy=0.05), selic=selic)
    assert _metodos(no_limite)["Bazin"] == pytest.approx(500 / 6, abs=0.01)


@pytest.mark.quebra_esperada
@pytest.mark.f9_fii_selic
def test_b_fii_compara_dy_com_a_selic_liquida_de_ir():
    # F-9, resolvida no F2B-2 (checkpoint da Fase 0, seção 4, item 3): o preço justo é o
    # rendimento de 12 meses ÷ (NTN-B real + spread). Era DY 9,35% ÷ Selic líquida 8,5% =
    # 110,00. Agora 9,35 ÷ (7% + spread calibrado), igual com qualquer Selic.
    esperado = 9.35 / (0.07 + MACRO.FII_SPREAD_TIJOLO)
    for selic in (0.05, 0.10, 0.15):
        r = _fii(selic=selic)
        assert r["fair_value"] == pytest.approx(esperado, abs=0.01)
    assert r["upside"] == pytest.approx((esperado / 100 - 1) * 100, abs=0.1)


@pytest.mark.quebra_esperada
@pytest.mark.f4_gordon_nominal
def test_b_gordon_desconta_pela_selic_nominal_mais_premio():
    # resolvida no F2B-1: DVA3/ação, payout30%, ROE12%, Fisher e teto2%.
    # g nominal8,4% -> real2,7488...%, limitado a2%; kreal12%.
    esperado = 3.06 / 0.10
    assert _metodos(_processar(_acao()))["Gordon"] == pytest.approx(esperado, abs=0.01)


@pytest.mark.quebra_esperada
@pytest.mark.f4_gordon_nominal
def test_b_gordon_acompanha_a_selic_um_para_um():
    # resolvida no F2B-1: Selic só move os métodos nominais remanescentes.
    baixa = _metodos(_processar(_acao(), selic=0.10))["Gordon"]
    alta = _metodos(_processar(_acao(), selic=0.15))["Gordon"]
    assert alta == pytest.approx(30.6, abs=0.01)
    assert alta == baixa


@pytest.mark.quebra_esperada
@pytest.mark.f9_fii_selic
def test_b_fii_nao_considera_o_patrimonio_no_fair_value():
    # QUEBRA ESPERADA: F-9 — o preço justo do FII não usa o patrimônio; P/VP entra apenas no
    # score (contexto pelo checkpoint). Um FII a 0,5× e outro a 2× o patrimônio têm o mesmo
    # fair value. F2B-2: o benchmark passou a NTN-B real + spread (era 110,00 pela Selic).
    barato = _fii(pvp=0.5)
    caro = _fii(pvp=2.0)
    esperado = 9.35 / (0.07 + MACRO.FII_SPREAD_TIJOLO)
    assert barato["fair_value"] == caro["fair_value"] == pytest.approx(esperado, abs=0.01)
    assert barato["pvp"] == 0.5 and caro["pvp"] == 2.0
    assert barato["lentes"] == caro["lentes"]
    assert "score_final" not in barato and "score_final" not in caro


@pytest.mark.quebra_esperada
@pytest.mark.f12_alavancagem_total
def test_b_divida_pl_da_cvm_e_endividamento_contabil_total_rotulado_como_liquido():
    # F-12, resolvida no F2A-8: (passivo_total − PL) / PL deixa de entrar como
    # `div_liq_patrimonio`; a CVM entrega a dívida financeira líquida sobre o PL.
    assert market_engine._CVM_TO_MARKET.get("divida_pl") != "div_liq_patrimonio"
    assert market_engine._CVM_TO_MARKET["div_liq_patrimonio"] == "div_liq_patrimonio"


@pytest.mark.quebra_esperada
@pytest.mark.f12_alavancagem_total
def test_b_alavancagem_acima_de_3x_penaliza_score_e_confianca_sem_distinguir_setor():
    # QUEBRA ESPERADA: F-12/F-13 — o mesmo limite 3,0 vale para qualquer setor.
    normal = _processar(_acao(divida_liq_ebitda=2.9))
    alavancada = _processar(_acao(divida_liq_ebitda=3.1))
    assert "score_final" not in normal and "score_final" not in alavancada
    assert normal["lentes"] == alavancada["lentes"]
    assert normal["confianca"] == alavancada["confianca"]
    assert "Dívida elevada" in alavancada["riscos"]


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
def test_c_dy_percentual_acima_de_30_nao_pode_sair_confiavel():
    dy, confiavel = _normalizar_dy(45.0)
    assert not (confiavel and dy > 0.30)


@pytest.mark.invariante
def test_c_score_da_acao_fica_entre_0_e_100():
    for pl, pvp, roe, dy, selic in _GRADE_ACOES:
        r = _processar(
            _acao(pl=pl, pvp=pvp, roe=roe, dy=dy, divida_liq_ebitda=4), selic=selic
        )
        assert "score_final" not in r, (pl, pvp, roe, dy, selic)
        assert r["lentes"], (pl, pvp, roe, dy, selic)
        for lente in r["lentes"].values():
            if lente["valor"] is None:
                assert lente["abstencao"], (pl, pvp, roe, dy, selic)
                assert lente["distancia_ao_preco_pct"] is None
            else:
                assert math.isfinite(lente["valor"]) and lente["valor"] > 0
                assert not lente["abstencao"]
                assert math.isfinite(lente["distancia_ao_preco_pct"])


@pytest.mark.invariante
def test_c_score_do_fii_fica_entre_0_e_100():
    for dy, pvp, selic in _GRADE_FII:
        r = _fii(selic=selic, dy=dy, pvp=pvp, ticker="CVBI11")
        assert "score_final" not in r, (dy, pvp, selic)
        assert r["lentes"], (dy, pvp, selic)
        for lente in r["lentes"].values():
            if lente["valor"] is None:
                assert lente["abstencao"], (dy, pvp, selic)
                assert lente["distancia_ao_preco_pct"] is None
            else:
                assert math.isfinite(lente["valor"]) and lente["valor"] > 0
                assert not lente["abstencao"]
                assert math.isfinite(lente["distancia_ao_preco_pct"])


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
        # F2B-62 (BUG-2B-50): a abstenção do FII não traz número; quem tem valor, na escala.
        if "fair_value" not in r:
            assert "upside" not in r and r["metodos_usados"].startswith(
                "Dados insuficientes ("
            ), (dy, pvp, selic)
            continue
        assert 0.1 <= r["fair_value"] / preco <= 20, (dy, pvp, selic)
