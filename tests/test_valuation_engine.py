from unittest.mock import patch

import pytest
from apoio_apresentacao import verificar_lentes
from apoio_bazin import enriquecer_bazin
from apoio_escopo import de_empresa
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON, DiaGordon, enriquecer_gordon

from fii_engine import FIIEngine
from sentinela.data import normalizacao
from valuation_engine import ValuationEngine


def test_dy_normalization_percentual() -> None:
    """F2A-4: o DY percentual do Yahoo vira razão na fronteira; o motor recebe 0,1247.

    F2B-31: o Bazin usa a relação B3 sintética com o mesmo DY (D = 12,47), a 6% fixos.
    """
    dados = {
        "ticker": "PETR4",
        "preco_atual": 100.0,
        "roe": 0.10,
        "pl": 30.0,
        "pvp": 4.0,
        "dy": normalizacao.dy_na_fronteira(12.47, "yfinance").valor,
    }
    dados = enriquecer_bazin(dados)

    # Sem fonte IPCA neste controle: Graham se abstém pela janela, não por múltiplosV1.
    dados["ipca_serie"] = None

    resultado = ValuationEngine().processar(de_empresa(dados))

    assert resultado["fair_value"] == pytest.approx(207.83, abs=0.01)
    assert resultado["metodos_usados"] == "Bazin: R$207.83"


def test_dy_invalido_acima_25pct() -> None:
    """DY acima de 25% deve ser desconsiderado e marcado como não confiável."""
    dados = {
        "ticker": "ITUB4",
        "preco_atual": 100.0,
        "roe": 0.25,
        "pl": 30.0,
        "pvp": 4.0,
        "dy": 0.45,
    }

    # Sem fonte IPCA neste controle: Graham se abstém pela janela, não por múltiplosV1.
    dados["ipca_serie"] = None

    resultado = ValuationEngine().processar(de_empresa(dados))

    assert resultado["fair_value"] == 100.0
    assert resultado["metodos_usados"] == ""
    assert resultado["perfil"] == "RENDA/VALOR"
    verificar_lentes(resultado)


def test_recomendacao_compra_forte_exige_upside() -> None:
    """Distância negativa permanece visível sem classificação agregada."""
    dados = {
        "ticker": "QUAL3",
        "preco_atual": 100.0,
        "roe": 0.10,
        "pl": 30.0,
        "pvp": 4.0,
        "dy": 0.051,
    }
    dados = enriquecer_bazin(dados)  # F2B-31: Bazin 85,00 a 6% fixos

    # Sem fonte IPCA neste controle: Graham se abstém pela janela, não por múltiplosV1.
    dados["ipca_serie"] = None

    resultado = ValuationEngine().processar(de_empresa(dados))

    verificar_lentes(resultado)
    assert resultado["upside"] == pytest.approx(-15.0, abs=0.1)
    verificar_lentes(resultado)


def test_recomendacao_qualidade_aguardar() -> None:
    """Referencial abaixo do preço conserva a distância, sem score ou rótulo."""
    dados = {
        "ticker": "QUAL3",
        "preco_atual": 100.0,
        "roe": 0.10,
        "pl": 30.0,
        "pvp": 4.0,
        "dy": 0.054,
    }
    dados = enriquecer_bazin(dados)  # F2B-31: Bazin 90,00 a 6% fixos

    # Sem fonte IPCA neste controle: Graham se abstém pela janela, não por múltiplosV1.
    dados["ipca_serie"] = None

    resultado = ValuationEngine().processar(de_empresa(dados))

    verificar_lentes(resultado)
    assert resultado["upside"] == pytest.approx(-10.0, abs=0.1)
    verificar_lentes(resultado)


def test_compra_forte_com_risco_vira_compra() -> None:
    """Score e upside altos com risco explicito nao devem virar COMPRA FORTE."""
    dados = {
        "ticker": "GROW3",
        "preco_atual": 100.0,
        "roe": 0.25,
        "pl": 5.0,
        "pvp": 4.0,
        "dy": 0.01,
        "divida_liq_ebitda": 4.0,
    }

    resultado = ValuationEngine().processar(de_empresa(dados))

    verificar_lentes(resultado)
    assert resultado["upside"] > 15
    assert resultado["riscos"]
    verificar_lentes(resultado)


def test_compra_forte_sem_risco_continua_possivel() -> None:
    """Score e upside altos sem risco explicito ainda podem virar COMPRA FORTE."""
    dados = {
        "ticker": "GROW3",
        "preco_atual": 100.0,
        "roe": 0.25,
        "pl": 5.0,
        "pvp": 0.5,  # ambas as lentes válidas, sem divergência>2 após retirar guardaV1
        "dy": 0.01,
        "divida_liq_ebitda": 0.0,
    }

    resultado = ValuationEngine().processar(de_empresa(dados))

    verificar_lentes(resultado)
    assert resultado["upside"] > 15
    assert "Dívida elevada" not in resultado["riscos"]
    verificar_lentes(resultado)


def test_graham_nao_e_recusado_so_pelo_flag_pl() -> None:
    """Ficha2.0: o PLnãoéinsumo; documentos completos sustentamGraham."""
    dados = {
        "ticker": "RUIM3",
        "preco_atual": 100.0,
        "roe": 0.0,
        "pl": 10.0,
        "pvp": 1.0,
        "dy": 0.0,
        "pl_confiavel": False,
    }

    resultado = ValuationEngine().processar(de_empresa(dados))

    assert "Graham: R$150.00" in resultado["metodos_usados"]


def test_lynch_usa_cagr_sem_reaplicar_retencao() -> None:
    """Cenário nominal20%emquatrointervalos; payoutnãoalteraCAGR aprovado."""
    dados = {
        "ticker": "GROW3",
        "preco_atual": 100.0,
        "roe": 0.25,
        "pl": 12.5,
        "pvp": 4.0,
        "dy": 0.032,
    }

    dados["ipca_serie"] = None  # Lynch não precisa de IPCA, isola a lente.
    resultado = ValuationEngine().processar(de_empresa(dados))

    assert resultado["fair_value"] == pytest.approx(160.0, abs=0.01)
    assert "Lynch: R$160.00" in resultado["metodos_usados"]


def test_fii_score_penaliza_pvp_alto() -> None:
    """FII com P/VP 1.2 deve pontuar menos que FII com P/VP neutro."""
    dados_base = {
        "ticker": "HGLG11",
        "preco_atual": 100.0,
        "dy": 0.12,
    }

    with patch("fii_engine.get_selic_atual", return_value=0.10):
        # F2B-2: o FII calcula com o Informe e a B3 sintéticos.
        fii_pvp_alto = FIIEngine().analisar(
            enriquecer_fii({**dados_base, "pvp": 1.2}), as_of=AS_OF_GORDON
        )
        fii_pvp_neutro = FIIEngine().analisar(
            enriquecer_fii({**dados_base, "pvp": 0.95}), as_of=AS_OF_GORDON
        )

    verificar_lentes(fii_pvp_alto)
    verificar_lentes(fii_pvp_neutro)
    assert fii_pvp_alto["pvp"] == 1.2 and fii_pvp_neutro["pvp"] == 0.95
    assert fii_pvp_alto["lentes"] == fii_pvp_neutro["lentes"]


def test_divida_liq_ebitda_none() -> None:
    # divida_liq_ebitda=None does not crash
    dados = {
        "ticker": "TEST3",
        "preco_atual": 10.0,
        "pvp": 1.0,
        "pl": 10.0,
        "dy": 0.05,
        "roe": 0.15,
        "divida_liq_ebitda": None,
    }
    result = ValuationEngine().processar(de_empresa(dados))
    assert result is not None
    verificar_lentes(result)
    verificar_lentes(result)


def test_divida_liq_ebitda_malformed_string() -> None:
    # divida_liq_ebitda as malformed string does not crash
    dados = {
        "ticker": "TEST3",
        "preco_atual": 10.0,
        "pvp": 1.0,
        "pl": 10.0,
        "dy": 0.05,
        "roe": 0.15,
        "divida_liq_ebitda": "abc,def",
    }
    result = ValuationEngine().processar(de_empresa(dados))
    assert result is not None
    verificar_lentes(result)


def test_divida_liq_ebitda_brazilian_format() -> None:
    # divida_liq_ebitda as "1.234,56" parses safely
    dados = {
        "ticker": "TEST3",
        "preco_atual": 10.0,
        "pvp": 1.0,
        "pl": 10.0,
        "dy": 0.05,
        "roe": 0.15,
        "divida_liq_ebitda": "1.234,56",
    }
    result = ValuationEngine().processar(de_empresa(dados))
    assert result is not None
    verificar_lentes(result)


def test_valuation_engine_expected_keys() -> None:
    dados = {
        "ticker": "TEST3",
        "preco_atual": 25.0,
        "pvp": 1.5,
        "pl": 8.0,
        "dy": 0.06,
        "roe": 0.18,
        "divida_liq_ebitda": 1.5,
    }
    result = ValuationEngine().processar(de_empresa(dados))
    assert "fair_value" in result
    assert "upside" in result
    verificar_lentes(result)
    assert "recomendacao" not in result
    assert "confianca" in result
    assert "riscos" in result
    assert "dy_confiavel" in result
    assert isinstance(result["dy_confiavel"], bool)
    verificar_lentes(result)


def test_dy_muito_alto_penaliza_bazin() -> None:
    """DY acima de 15% deve reduzir a confiança por ser armadilha."""
    dados = {
        "ticker": "TRAP3",
        "preco_atual": 100.0,
        "roe": 0.10,
        "pl": 5.0,
        "pvp": 1.0,
        "dy": 0.18,
    }
    dados = enriquecer_bazin(dados)
    resultado = ValuationEngine().processar(de_empresa(dados))

    assert "DY muito alto (possível armadilha)" in resultado["riscos"]
    assert resultado["confianca"] == 100


def test_gordon_ignorado_k_menor_g() -> None:
    """Gordon Growth deve ser ignorado se o custo de capital (k) for menor ou igual ao crescimento (g)."""
    dados = {
        "ticker": "FAST3",
        "preco_atual": 100.0,
        "roe": 0.90,  # Crescimento enorme
        "pl": 15.0,
        "pvp": 3.0,
        "dy": 0.05,
    }
    # F2B-1: g real no teto2%, k real1%; Selic é independente desse desconto.
    dados = enriquecer_gordon(dados, ntnb=-0.04)
    with patch("valuation_engine.date", DiaGordon):
        resultado = ValuationEngine().processar(de_empresa(dados), as_of=AS_OF_GORDON)

    assert "Gordon" not in resultado["metodos_usados"]


# ── Testes de guards de segurança ────────────────────────────────────────────


def test_distressed_ticker_retorna_alto_risco() -> None:
    """Situação especial impede as lentes e conserva motivo, sem score."""
    dados = {
        "ticker": "AMER3",
        "preco_atual": 5.69,
        "roe": 0.02,
        "pl": 8.5,
        "pvp": 0.24,
        "dy": 0.0,
    }
    resultado = ValuationEngine().processar(de_empresa(dados))

    verificar_lentes(resultado)
    assert resultado["confianca"] == 0
    assert "Empresa em situação especial/distressed" in resultado["riscos"]
    assert resultado["perfil"] == "DISTRESSED"
    assert resultado["metodos_usados"] == ""
    assert all(
        l["valor"] is None and "distressed" in l["abstencao"]
        for l in resultado["lentes"].values()
    )


def test_distressed_ticker_nunca_compra_forte() -> None:
    """Situação especial prevalece mesmo com insumos numericamente elegíveis."""
    dados = {
        "ticker": "OIBR3",
        "preco_atual": 0.11,
        "roe": 0.30,
        "pl": 3.0,
        "pvp": 0.5,
        "dy": 0.10,
    }
    resultado = ValuationEngine().processar(de_empresa(dados))

    verificar_lentes(resultado)
    assert resultado["perfil"] == "DISTRESSED"
    assert resultado["metodos_usados"] == ""
    assert all(
        l["valor"] is None and "distressed" in l["abstencao"]
        for l in resultado["lentes"].values()
    )


def test_scraper_falhou_compra_vira_dados_insuficientes() -> None:
    """Campo obrigatório ausente (F2A-22) + COMPRA deve virar DADOS INSUFICIENTES — AGUARDAR."""
    dados = {
        "ticker": "ITUB4",
        "preco_atual": 42.87,
        "roe": 0.21,
        "pl": 10.69,
        "pvp": 2.31,
        "dy": 0.0124,
        "fundamentos_incompletos": True,
    }
    resultado = ValuationEngine().processar(de_empresa(dados))

    verificar_lentes(resultado)
    assert resultado["confianca"] == 70
    assert "Dados fundamentais obrigatórios ausentes" in resultado["riscos"]
    # Valores calculados são preservados para transparência
    assert resultado["fair_value"] > 0
    verificar_lentes(resultado)


def test_scraper_falhou_nao_sobrescreve_venda() -> None:
    """Scraper failure não deve sobrescrever VENDA — VENDA tem prioridade.

    dy=0.06 garante que Bazin dispara (gate >= 5%) e produz VENDA,
    preservando a intenção do teste.
    """
    dados = {
        "ticker": "LIXO3",
        "preco_atual": 100.0,
        "roe": 0.02,
        "pl": 50.0,
        "pvp": 5.0,
        "dy": 0.06,
        "fundamentos_incompletos": True,
    }
    resultado = ValuationEngine().processar(de_empresa(dados))

    # upside < -15% = VENDA; scraper guard não interfere
    verificar_lentes(resultado)


def test_scraper_falhou_nao_sobrescreve_alto_risco() -> None:
    """Scraper failure não deve sobrescrever ALTO RISCO — EVITAR."""
    dados = {
        "ticker": "AMER3",
        "preco_atual": 5.69,
        "roe": 0.02,
        "pl": 8.5,
        "pvp": 0.24,
        "dy": 0.0,
        "fundamentos_incompletos": True,
    }
    resultado = ValuationEngine().processar(de_empresa(dados))

    # Distressed guard fires first — must remain ALTO RISCO
    verificar_lentes(resultado)
    assert resultado["perfil"] == "DISTRESSED"
    assert resultado["metodos_usados"] == ""
    assert all(
        l["valor"] is None and "distressed" in l["abstencao"]
        for l in resultado["lentes"].values()
    )


# ── Testes de baseline para bugs conhecidos ──────────────────────────────────


def test_bazin_nao_aciona_dy_abaixo_5pct() -> None:
    """Ação com DY de 3% (abaixo do mínimo Bazin de 5%) não deve usar Bazin."""
    dados = {
        "ticker": "REND3",
        "preco_atual": 100.0,
        "roe": 0.10,
        "pl": 30.0,
        "pvp": 4.0,
        "dy": 0.03,
    }
    resultado = ValuationEngine().processar(de_empresa(dados))

    assert "Bazin" not in resultado["metodos_usados"]


def test_bazin_aciona_no_limite_de_5pct() -> None:
    """Ação com DY exatamente 5% deve acionar Bazin (limite mínimo)."""
    dados = {
        "ticker": "REND3",
        "preco_atual": 100.0,
        "roe": 0.10,
        "pl": 30.0,
        "pvp": 4.0,
        "dy": 0.05,
    }
    dados = enriquecer_bazin(dados)
    resultado = ValuationEngine().processar(de_empresa(dados))

    assert "Bazin" in resultado["metodos_usados"]


def test_fair_value_usa_mediana_com_tres_metodos() -> None:
    """Com Graham+Bazin+Gordon divergindo, fair_value deve ser a mediana, não a média.

    Valores calculados manualmente (a Selic de 5% não entra no Bazin desde o F2B-31):
      Graham ≈ 106.07  (sqrt(22.5 * 10 * 50))
      Bazin  = 166.67  ((0.10 * 100) / 0.06)
      Gordon = 30.60 (DVA3/ação, kreal12%, greal2%)
    Mediana = 106.07 | Média ≈ 101.11
    """
    dados = {
        "ticker": "DIVG3",
        "preco_atual": 100.0,
        "roe": 0.15,
        "pl": 10.0,
        "pvp": 2.0,
        "dy": 0.10,
    }
    dados = enriquecer_bazin(enriquecer_gordon(dados))
    with patch("valuation_engine.date", DiaGordon):
        resultado = ValuationEngine().processar(de_empresa(dados), as_of=AS_OF_GORDON)

    assert resultado["fair_value"] == pytest.approx(106.07, abs=0.5)


def test_sinal_tecnico_nao_altera_resultado() -> None:
    """Métodos e classificação não leem sinal técnico (armadilha 12)."""
    base = {
        "ticker": "TST3",
        "preco_atual": 100.0,
        "roe": 0.02,
        "pl": 50.0,
        "pvp": 5.0,
        "dy": 0.06,
    }
    sem = ValuationEngine().processar(dict(base))
    com = ValuationEngine().processar({**base, "tecnico_negativo": True})

    assert com == sem


# ── F2B-45: dívida que não é número finito não é avaliada ─────────────────────

_ACAO_F2B45 = {
    "ticker": "TEST3",
    "preco_atual": 10.0,
    "pvp": 1.0,
    "pl": 10.0,
    "dy": 0.05,
    "roe": 0.15,
}


def _com_divida(divida):
    dados = dict(_ACAO_F2B45)
    if divida != "sem-chave":
        dados["divida_liq_ebitda"] = divida
    return ValuationEngine().processar(de_empresa(dados))


def test_divida_em_texto_nao_e_avaliada():
    r = _com_divida("9,5")
    assert "Dívida elevada" not in r["riscos"]
    assert r["aviso_alavancagem"] == (
        "alavancagem não avaliada: dívida líquida/EBITDA em texto"
    )
    verificar_lentes(r)
    verificar_lentes(_com_divida(None))


@pytest.mark.parametrize(
    ("divida", "motivo"),
    [
        ("sem-chave", "ausente"),
        (None, "ausente"),
        (float("nan"), "não numérica ou não finita"),
        (float("inf"), "não numérica ou não finita"),
        (True, "não numérica ou não finita"),
    ],
)
def test_divida_invalida_ganha_o_aviso_fora_de_riscos(divida, motivo):
    r = _com_divida(divida)
    assert r["aviso_alavancagem"] == (
        f"alavancagem não avaliada: dívida líquida/EBITDA {motivo}"
    )
    assert not any("alavancagem" in s for s in r["riscos"])


def test_divida_numerica_segue_a_regra_sem_aviso():
    alta = _com_divida(9.5)
    assert "Dívida elevada" in alta["riscos"]
    assert "aviso_alavancagem" not in alta
    assert "aviso_alavancagem" not in _com_divida(1.0)
