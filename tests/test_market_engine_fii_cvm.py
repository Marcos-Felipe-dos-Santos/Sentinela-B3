"""VPA e P/VP oficiais do FII pela cascata (F2A-11; E-10, armadilha 9).

O `CVMFIIProvider` nunca rodava: o `app.py` monta `FIIEngine()` sem provedor. A busca vai
para a cascata: Informe Mensal pelo CNPJ do índice oficial (sem reserva no mapa desde o F2A-31).
"""

import pytest

from tests.test_market_engine import ReferenciaDosMapas, _engine, _historico

INFO = {
    "currentPrice": 90.0,
    "priceToBook": 1.5,
    "dividendYield": 9.0,
    "quoteType": "MUTUALFUND",
}
INFORME = {
    "cnpj_fundo": "11.728.688/0001-47",
    "dt_referencia": "2026-08-01",
    "patrimonio_liquido": 5_000_000_000.0,
    "cotas_emitidas": 50_000_000.0,
    "valor_cota": 100.0,
    "vacancia_fisica": None,
    "proveniencia": {"documento": "Informe Mensal", "periodo_referencia": "2026-08-01"},
}


class _InformeFalso:
    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.cnpjs = resposta, erro, []

    def obter_dados_fii(self, cnpj):
        self.cnpjs.append(cnpj)
        if self.erro:
            raise self.erro
        return self.resposta


def _cascata(monkeypatch, informe):
    engine = _engine(monkeypatch, info=INFO, historico=_historico(90.0))
    engine.cvm_fii = informe
    engine.referencia = ReferenciaDosMapas()  # F2A-31: o CNPJ vem só do índice
    return engine.buscar_dados_ticker("HGLG11")  # FII do mapa público


def test_fii_recebe_pvp_oficial_pela_cascata(monkeypatch):
    informe = _InformeFalso(INFORME)
    dados = _cascata(monkeypatch, informe)
    assert informe.cnpjs == ["11.728.688/0001-47"]  # do mapa, sem o índice oficial
    assert dados["vpa"] == 100.0
    assert dados["pvp"] == pytest.approx(
        0.9
    )  # preço ÷ valor da cota, sobre o 1,5 do yfinance
    assert dados["patrimonio_liquido"] == 5_000_000_000.0
    assert dados["cotas_emitidas"] == 50_000_000.0
    assert dados["cvm_fii_dt_referencia"] == "2026-08-01"
    assert dados["cvm_disponivel"] is True
    assert dados["field_provenance"]["pvp"]["provenance"]["source"] == "CVM"
    assert dados["proveniencia"]["vpa"] == INFORME["proveniencia"]


@pytest.mark.parametrize(
    "informe",
    [
        _InformeFalso(erro=OSError("sem rede")),
        _InformeFalso(None),
        _InformeFalso({**INFORME, "valor_cota": 0.0}),
    ],
)
def test_falha_do_informe_mantem_as_outras_fontes(monkeypatch, informe):
    dados = _cascata(monkeypatch, informe)
    assert dados["pvp"] == 1.5  # o do yfinance fica
    assert "vpa" not in dados
    assert dados["cvm_disponivel"] is False
    if informe.erro:
        assert "Informe Mensal do FII indisponível: sem rede" in dados["riscos_dados"]


def test_acao_nao_consulta_o_informe(monkeypatch):
    informe = _InformeFalso(INFORME)
    engine = _engine(monkeypatch, info=INFO, historico=_historico(90.0))
    engine.cvm_fii = informe
    engine.buscar_dados_ticker("PETR4")
    assert informe.cnpjs == []


def test_cnpj_do_indice_tem_prioridade(monkeypatch):
    informe = _InformeFalso(INFORME)
    engine = _engine(monkeypatch, info=INFO, historico=_historico(90.0))
    engine.cvm_fii = informe
    dados = {
        "ticker": "HGLG11",
        "cnpj": "99.999.999/0001-99",
        "preco_atual": 90.0,
        "riscos_dados": [],
    }
    assert engine._buscar_cvm_fii("HGLG11", dados) is True
    assert informe.cnpjs == ["99.999.999/0001-99"]


def test_informe_grava_valores_por_fonte(monkeypatch):
    # F2B-16 (BUG-2A-12): o que o Informe entregou fica em `valores_por_fonte['CVM']`.
    dados = _cascata(monkeypatch, _InformeFalso(INFORME))
    assert dados["valores_por_fonte"]["CVM"] == {
        "vpa": 100.0,
        "pvp": pytest.approx(0.9),
        "patrimonio_liquido": 5_000_000_000.0,
    }
    assert dados["valores_por_fonte"]["yfinance"]["pvp"] == pytest.approx(1.5)
