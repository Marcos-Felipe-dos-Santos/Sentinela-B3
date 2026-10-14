"""ROE convertido e guardado na fronteira de cada provedor (F2A-30; E-15).

Representação (F2A-16, `docs/decisoes/fontes-fase2a.md`, seção 8): o `returnOnEquity` do
yfinance vem em razão (ITUB4 0,215 contra 0,213 de lucro ÷ PL da DFP); o da brapi não foi
determinado, e vale a regra da V1 (acima de 1 é percentual), como inferência. Depois da
conversão, ROE não finito ou acima de 2 vira ausente, com o motivo.
"""

import pytest

from tests.test_market_engine import FakeBrapi, _engine, _historico

INFO = {
    "currentPrice": 20.0,
    "trailingPE": 8.0,
    "priceToBook": 1.2,
    "dividendYield": 4.0,
}


def test_roe_em_percentual_do_yfinance_nao_chega_ao_motor(monkeypatch):
    # O cenário da auditoria: 21% em percentual vira 2100% e o Lynch bate no teto.
    engine = _engine(
        monkeypatch, info={**INFO, "returnOnEquity": 21.0}, historico=_historico(20.0)
    )
    dados = engine.buscar_dados_ticker("TSTE3")
    assert dados.get("roe") is None
    assert any("ROE descartado (yfinance)" in r for r in dados["riscos_dados"])
    (descarte,) = dados["proveniencia"]["roe_descartes"]
    assert descarte["fonte"] == "yfinance"
    assert descarte["motivo"].startswith("ROE acima de 2")
    assert "roe" not in dados["proveniencia"]


@pytest.mark.parametrize(
    ("provedor", "bruto", "razao"),
    [
        ("yfinance", 0.215, 0.215),  # ITUB4 no F2A-16
        ("brapi", 21.5, 0.215),
        ("brapi", 0.215, 0.215),
        ("brapi", -21.5, -0.215),  # negativo: a regra da V1 olha o módulo
        ("brapi", -0.215, -0.215),
        ("cvm", 0.215, 0.215),
    ],
)
def test_mesmo_roe_mesma_razao_em_cada_fronteira(provedor, bruto, razao):
    from sentinela.data import normalizacao

    convertido = normalizacao.roe_na_fronteira(bruto, provedor)
    assert convertido.valor == pytest.approx(razao)
    assert convertido.representacao is normalizacao.REPRESENTACAO_ROE[provedor]


def test_roe_acima_do_limite_vira_ausente_com_motivo(monkeypatch):
    from sentinela.data import normalizacao

    assert normalizacao.guardar_roe(2.0) == (2.0, None)
    assert normalizacao.guardar_roe(2.0001) == (None, normalizacao.MOTIVO_ROE_ACIMA)
    assert normalizacao.guardar_roe(float("inf")) == (
        None,
        normalizacao.MOTIVO_ROE_NAO_FINITO,
    )
    assert normalizacao.guardar_roe(float("nan")) == (
        None,
        normalizacao.MOTIVO_ROE_NAO_FINITO,
    )
    assert normalizacao.guardar_roe(None) == (None, None)

    # Na cascata, pela brapi: 350 (percentual) vira 3,5 e é descartado.
    engine = _engine(
        monkeypatch,
        info=INFO,
        historico=_historico(20.0),
        brapi=FakeBrapi({"roe": 3.5, "pl": 8.0}),
    )
    dados = engine.buscar_dados_ticker("TSTE3")
    assert dados.get("roe") is None
    assert (
        f"ROE descartado (brapi): {normalizacao.MOTIVO_ROE_ACIMA}"
        in dados["riscos_dados"]
    )
    assert dados["proveniencia"]["roe_descartes"] == [
        {
            "fonte": "brapi",
            "representacao": normalizacao.Representacao.INFERIDA_V1.value,
            "inferida": True,
            "motivo": normalizacao.MOTIVO_ROE_ACIMA,
        }
    ]


def test_roe_negativo_passa(monkeypatch):
    from sentinela.data import normalizacao

    assert normalizacao.guardar_roe(-0.3) == (-0.3, None)
    engine = _engine(
        monkeypatch, info={**INFO, "returnOnEquity": -0.12}, historico=_historico(20.0)
    )
    dados = engine.buscar_dados_ticker("TSTE3")
    assert dados["roe"] == pytest.approx(-0.12)
    assert dados["proveniencia"]["roe"] == normalizacao.proveniencia_roe("yfinance")
    assert not any("ROE descartado" in r for r in dados["riscos_dados"])


def test_roe_da_cvm_passa_pela_guarda(monkeypatch):
    from sentinela.data import normalizacao

    class _CVM:
        def __init__(self, roe):
            self.roe = roe

        def calcular_indicadores(self, cd_cvm, anos=1, **kwargs):
            return {2025: {"roe": self.roe, "lucro_liquido": 10.0}}

    engine = _engine(monkeypatch, info=INFO, historico=_historico(20.0), cvm=_CVM(2.5))
    dados = engine.buscar_dados_ticker("PETR4")  # ticker do mapa público
    assert dados.get("roe") is None
    assert (
        f"ROE descartado (cvm): {normalizacao.MOTIVO_ROE_ACIMA}"
        in dados["riscos_dados"]
    )
    assert dados["lucro_liquido"] == 10.0  # o resto da CVM entra

    engine = _engine(monkeypatch, info=INFO, historico=_historico(20.0), cvm=_CVM(0.18))
    assert engine.buscar_dados_ticker("PETR4")["roe"] == pytest.approx(0.18)


def test_yfinance_valido_marca_a_representacao(monkeypatch):
    from sentinela.data import normalizacao

    engine = _engine(
        monkeypatch, info={**INFO, "returnOnEquity": 0.215}, historico=_historico(20.0)
    )
    dados = engine.buscar_dados_ticker("TSTE3")
    assert dados["roe"] == pytest.approx(0.215)
    assert dados["proveniencia"]["roe"]["inferida"] is False
    assert (
        dados["proveniencia"]["roe"]["representacao"]
        == normalizacao.Representacao.RAZAO.value
    )


def test_relatorio_declara_a_guarda_e_o_descarte():
    from datetime import date
    from unittest.mock import patch

    from fii_engine import FIIEngine
    from sentinela.reports import rastreabilidade
    from valuation_engine import ValuationEngine

    dados = {
        "ticker": "TST3", "preco_atual": 100.0, "pl": 10.0, "pvp": 1.5, "dy": 0.08,
        "proveniencia": {"roe_descartes": [{"fonte": "cvm", "motivo": "ROE acima de 2 (200%) depois da conversão: descartado"}]},
    }  # fmt: skip
    with (
        patch("valuation_engine.get_selic_atual", return_value=0.145),
        patch("fii_engine.get_selic_atual", return_value=0.145),
    ):
        contexto = rastreabilidade.construir_contexto(
            dados, False, date(2026, 10, 13), ValuationEngine(), FIIEngine()
        )
    texto = next(i["proveniencia"] for i in contexto["insumos"] if i["campo"] == "roe")
    assert "guarda de fronteira (F2A-30)" in texto
    assert (
        "descartado de cvm: ROE acima de 2 (200%) depois da conversão: descartado"
        in texto
    )


class _CVMComRoe:
    def __init__(self, roe):
        self.roe = roe

    def calcular_indicadores(self, cd_cvm, anos=1, **kwargs):
        return {2025: {"roe": self.roe}}


def test_descarte_de_outra_fonte_nao_apaga_a_proveniencia_do_roe_vigente(monkeypatch):
    from sentinela.data import normalizacao

    # yfinance válido e CVM acima do limite: o ROE do yfinance fica, com a proveniência dele.
    engine = _engine(
        monkeypatch,
        info={**INFO, "returnOnEquity": 0.18},
        historico=_historico(20.0),
        cvm=_CVMComRoe(2.5),
    )
    dados = engine.buscar_dados_ticker("PETR4")  # ticker do mapa público
    assert dados["roe"] == pytest.approx(0.18)
    assert dados["proveniencia"]["roe"] == normalizacao.proveniencia_roe("yfinance")
    assert [d["fonte"] for d in dados["proveniencia"]["roe_descartes"]] == ["cvm"]

    # yfinance válido e brapi acima do limite: idem.
    engine = _engine(
        monkeypatch,
        info={**INFO, "returnOnEquity": 0.18},
        historico=_historico(20.0),
        brapi=FakeBrapi({"roe": 3.5, "pl": 8.0}),
    )
    dados = engine.buscar_dados_ticker("TSTE3")
    assert dados["roe"] == pytest.approx(0.18)
    assert dados["proveniencia"]["roe"]["fonte"] == "yfinance"
    assert [d["fonte"] for d in dados["proveniencia"]["roe_descartes"]] == ["brapi"]


def test_regra_por_modulo_vale_so_para_o_roe():
    from sentinela.data import normalizacao

    assert normalizacao.roe_na_fronteira(-5.0, "brapi").valor == pytest.approx(-0.05)
    # O DY segue a regra da V1 do F2A-4, sem o módulo.
    assert normalizacao.dy_na_fronteira(-5.0, "brapi").valor == -5.0
    assert normalizacao.converter(-5.0, normalizacao.Representacao.INFERIDA_V1) == -5.0
