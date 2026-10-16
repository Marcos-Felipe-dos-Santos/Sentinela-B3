"""DY normalizado uma vez, na fronteira do provedor (F2A-4; E-4, E-5, armadilha 4).

Representação de cada provedor (F2A-16, `docs/decisoes/fontes-fase2a.md`, seção 8): o
`dividendYield` do yfinance vem em percentual (PETR4: 6,74); o da brapi não foi determinado,
e para ela vale a regra da V1 (acima de 1 é percentual), declarada como inferência.
"""

from unittest.mock import patch

import pytest

from valuation_engine import ValuationEngine


def _processar(dy):
    dados = {
        "ticker": "TST3",
        "preco_atual": 100.0,
        "roe": 0.15,
        "pl": 10.0,
        "pvp": 1.5,
        "dy": dy,
    }
    with patch("valuation_engine.get_selic_atual", return_value=0.145):
        return ValuationEngine().processar(dados)


def test_motor_nao_converte_percentual():
    # 5,0 chegando ao motor não é 5%: a conversão é da fronteira. O motor só aplica o
    # invariante (0 ≤ DY ≤ 25%) e marca o DY como não confiável.
    resultado = _processar(5.0)
    assert resultado["dy_confiavel"] is False
    assert "DY suspeito" in resultado["riscos"]


@pytest.mark.parametrize(
    ("provedor", "bruto", "razao"),
    [
        ("yfinance", 6.74, 0.0674),  # PETR4 no F2A-16
        (
            "yfinance",
            0.57,
            0.0057,
        ),  # BBAS3: percentual abaixo de 1, que a regra da V1 erra
        ("brapi", 7.5, 0.075),
        ("brapi", 0.075, 0.075),
    ],
)
def test_mesmo_dy_mesma_razao_em_cada_fronteira(provedor, bruto, razao):
    from sentinela.data import normalizacao

    assert normalizacao.dy_na_fronteira(bruto, provedor).valor == pytest.approx(razao)


# ── bordas do normalizador ───────────────────────────────────────────────────


def test_regra_da_v1_so_converte_acima_de_1():
    from sentinela.data import normalizacao

    assert normalizacao.dy_na_fronteira(1.0, "brapi").valor == 1.0
    assert normalizacao.dy_na_fronteira(2.0, "brapi").valor == pytest.approx(0.02)
    assert normalizacao.dy_na_fronteira(1.5, "brapi").valor == pytest.approx(0.015)
    # Não valida: negativo segue negativo; o invariante é do motor.
    assert normalizacao.dy_na_fronteira(-0.5, "brapi").valor == -0.5
    assert normalizacao.dy_na_fronteira(-5.0, "yfinance").valor == pytest.approx(-0.05)


@pytest.mark.parametrize("bruto", [None, "abc", float("nan"), float("inf"), True])
def test_sem_numero_finito_vira_none(bruto):
    from sentinela.data import normalizacao

    assert normalizacao.dy_na_fronteira(bruto, "yfinance").valor is None
    assert normalizacao.dy_na_fronteira("6.74", "yfinance").valor == pytest.approx(
        0.0674
    )


def test_representacao_e_proveniencia_por_provedor():
    from sentinela.data import normalizacao

    assert normalizacao.dy_na_fronteira(1.0, "yfinance").representacao is (
        normalizacao.Representacao.PERCENTUAL
    )
    assert normalizacao.proveniencia_dy("yfinance") == {
        "fonte": "yfinance",
        "representacao": "percentual (evidência do F2A-16)",
        "inferida": False,
    }
    assert normalizacao.proveniencia_dy("brapi") == {
        "fonte": "brapi",
        "representacao": "inferida pela regra da V1: acima de 1 é percentual, senão razão",
        "inferida": True,
    }
    with pytest.raises(KeyError):
        normalizacao.dy_na_fronteira(1.0, "fundamentus")


def test_cascata_converte_e_marca_a_proveniencia(monkeypatch):
    from tests.test_market_engine import FakeBrapi, _engine, _historico

    engine = _engine(
        monkeypatch,
        info={"currentPrice": 20.0, "dividendYield": 0.57},
        historico=_historico(20.0),
    )
    dados = engine.buscar_dados_ticker("TSTE3")
    assert dados["dy"] == pytest.approx(0.0057)
    assert dados["proveniencia"]["dy"]["inferida"] is False

    engine = _engine(
        monkeypatch,
        info={"currentPrice": 20.0, "dividendYield": 0.57},
        historico=_historico(20.0),
        brapi=FakeBrapi({"dy": 0.075}),
    )
    dados = engine.buscar_dados_ticker("TSTE3")
    assert dados["dy"] == pytest.approx(0.075)
    assert dados["proveniencia"]["dy"]["fonte"] == "brapi"
    assert dados["proveniencia"]["dy"]["inferida"] is True
