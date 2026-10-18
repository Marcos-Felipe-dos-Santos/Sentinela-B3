"""Validação cruzada entre fontes independentes (F2A-5, E-2, armadilha 2).

No caminho da CVM, o P/L é preço ÷ LPA por definição: comparar os dois é identidade. A
validação passa a comparar as ações da CVM com as do yfinance e o LPA da cascata com o LPA
básico divulgado pela companhia, por espécie.
"""

import pytest

from data_quality import DataQualityReport
from sentinela.data.acoes_cvm import MOTIVO_SINAL_CONTROLADORES
from tests.test_market_engine_acoes_cvm import _ind, _motor
from tests.test_market_engine_referencia import FakeReferencia, _indice, _registro


def _alertas(dados):
    return DataQualityReport(dados).validacao_cruzada()


def _cvm(monkeypatch, ticker="TSTA4", especie="PN", shares=360.0, **ind):
    registro = _registro(ticker, especie=especie)
    engine = _motor(
        monkeypatch,
        _ind(**ind),
        shares=shares,
        referencia=FakeReferencia(_indice(registro)),
    )
    return engine.buscar_dados_ticker(ticker)


# ── aceite ───────────────────────────────────────────────────────────────────


def test_acoes_da_cvm_divergentes_do_yfinance_geram_alerta(monkeypatch):
    # PN 400 − tesouraria PN 40 = 360 na CVM; o yfinance informa 450 (+25%).
    dados = _cvm(monkeypatch, shares=450.0)
    alertas = _alertas(dados)
    assert any("ações" in a and "25%" in a and "PN" in a for a in alertas), alertas


def test_lpa_divergente_do_divulgado_gera_alerta(monkeypatch):
    por_especie = {"ON": 2.5, "PN": 2.5}
    dados = _cvm(monkeypatch, lpa_divulgado_por_especie=por_especie)
    (alerta,) = [a for a in _alertas(dados) if "LPA" in a]
    assert "2,00" in alerta and "2,50" in alerta and "20%" in alerta
    assert "média ponderada" in alerta and "fim do período" in alerta


def test_lpa_comparado_com_o_divulgado_da_mesma_especie(monkeypatch):
    por_especie = {"ON": 2.5, "PN": 2.04}
    pn = _cvm(monkeypatch, lpa_divulgado_por_especie=por_especie)
    assert not [a for a in _alertas(pn) if "LPA" in a]
    on = _cvm(
        monkeypatch, ticker="TSTA3", especie="ON", shares=640.0,
        lpa_divulgado_por_especie=por_especie,
    )  # fmt: skip
    (alerta,) = [a for a in _alertas(on) if "LPA" in a]
    assert "ON" in alerta


def test_identidade_da_cvm_nao_e_comparada():
    # P/L e LPA da mesma fonte (CVM): a comparação seria identidade, mesmo com valores soltos.
    dados = {
        "preco_atual": 20.0, "pl": 10.0, "lpa": 1.0, "pvp": 2.0, "vpa": 5.0,
        "field_provenance": {
            "pl": {"provenance": {"source": "CVM"}},
            "pvp": {"provenance": {"source": "CVM"}},
        },
        "valores_por_fonte": {"CVM": {"pl": 10.0, "lpa": 1.0, "pvp": 2.0, "vpa": 5.0}},
    }  # fmt: skip
    assert _alertas(dados) == []


def test_fontes_diferentes_seguem_comparadas():
    dados = {
        "preco_atual": 20.0, "pl": 10.0, "lpa": 1.0, "pvp": 2.0, "vpa": 5.0,
        "field_provenance": {
            "pl": {"provenance": {"source": "brapi"}},
            "pvp": {"provenance": {"source": "brapi"}},
        },
        "valores_por_fonte": {
            "brapi": {"pl": 10.0, "pvp": 2.0},
            "fundamentus": {"lpa": 1.0, "vpa": 5.0},
        },
    }  # fmt: skip
    alertas = _alertas(dados)
    assert any(a.startswith("pl=10.0 inconsistente") for a in alertas)
    assert any(a.startswith("pvp=2.00 inconsistente") for a in alertas)


# ── demais regras ────────────────────────────────────────────────────────────


def test_divergencia_de_ate_5_por_cento_nao_gera_alerta(monkeypatch):
    assert not [a for a in _alertas(_cvm(monkeypatch, shares=378.0)) if "ações" in a]
    assert [a for a in _alertas(_cvm(monkeypatch, shares=378.4)) if "ações" in a]


def test_divergencia_negativa_tambem_gera_alerta(monkeypatch):
    dados = _cvm(monkeypatch, shares=300.0)
    assert any("ações" in a and "-17%" in a for a in _alertas(dados))


def test_lpa_ate_10_por_cento_nao_gera_alerta(monkeypatch):
    dados = _cvm(monkeypatch, lpa_divulgado_por_especie={"ON": 2.2, "PN": 2.2})
    assert not [a for a in _alertas(dados) if "LPA" in a]
    dados = _cvm(monkeypatch, lpa_divulgado_por_especie={"ON": 2.23, "PN": 2.23})
    assert [a for a in _alertas(dados) if "LPA" in a]


def test_lpa_de_unit_compara_por_acao(monkeypatch):
    unit = _registro(
        "TSTA11", classe="UNIT", especie=None, acoes_por_unit={"ON": 1, "PN": 2}
    )
    engine = _motor(
        monkeypatch, _ind(lpa_divulgado_por_especie={"ON": 2.0, "PN": 2.0}),
        referencia=FakeReferencia(_indice(unit)),
    )  # fmt: skip
    dados = engine.buscar_dados_ticker("TSTA11")
    assert dados["lpa"] == pytest.approx(6.0)
    assert not [a for a in _alertas(dados) if "LPA" in a]


def test_sem_especie_compara_com_o_lpa_da_escala(monkeypatch):
    dados = _motor(monkeypatch, _ind()).buscar_dados_ticker("PETR4")
    assert dados["acoes_cvm"]["lpa_divulgado_comparado"] == {
        "especie": "ON",
        "valor": 2.1,
    }
    assert not [a for a in _alertas(dados) if "LPA" in a]


def test_cascata_guarda_o_que_cada_fonte_entregou(monkeypatch):
    dados = _cvm(monkeypatch)
    por_fonte = dados["valores_por_fonte"]
    assert por_fonte["yfinance"]["preco_atual"] == pytest.approx(20.0)
    assert por_fonte["CVM"]["lpa"] == pytest.approx(2.0)
    assert por_fonte["CVM"]["roe"] == pytest.approx(0.2)


def test_valores_por_fonte_ficam_fora_do_prompt():
    from ai_core import SentinelaAI

    texto = SentinelaAI.__new__(SentinelaAI)._formatar_dados(
        {"ticker": "TSTA3", "valores_por_fonte": {"CVM": {"lpa": 1.0}}}
    )
    assert "valores_por_fonte" not in texto


def test_caminho_da_cvm_nao_compara_pl_com_preco_sobre_lpa(monkeypatch):
    dados = _cvm(monkeypatch)
    assert dados["field_provenance"]["pl"]["provenance"]["source"] == "CVM"
    dados["lpa"] = 1.0  # mesmo solto, o lado do LPA é da mesma fonte do P/L
    dados["valores_por_fonte"]["CVM"]["lpa"] = 1.0
    del dados["valores_coletados"]
    assert not [a for a in _alertas(dados) if a.startswith("pl=")]


# ── conferência só contra o divulgado coerente (F2B-14; BUG-2A-11; ficha, 7.3 e 7.5) ──


def test_divulgado_incoerente_nao_entra_na_conferencia(monkeypatch):
    # Lucro dos controladores positivo (2.000); a PN divulgada negativa é incoerente (7.5).
    dados = _cvm(
        monkeypatch,
        lpa_basico_por_classe={"ON": [2.1], "PN": [-2.0]},
        lpa_divulgado_por_especie={"ON": 2.1, "PN": -2.0},
    )
    assert dados["acoes_cvm"]["lpa_divulgado_comparado"] is None
    assert not [a for a in _alertas(dados) if "LPA básico divulgado" in a]
    assert (
        f"CVM sem LPA: {MOTIVO_SINAL_CONTROLADORES}" in dados["riscos_dados"]
    )  # o alerta é só o da incoerência


def test_divulgado_coerente_segue_conferido(monkeypatch):
    dados = _cvm(
        monkeypatch,
        lpa_basico_por_classe={"ON": [2.5], "PN": [2.5]},
        lpa_divulgado_por_especie={"ON": 2.5, "PN": 2.5},
    )
    assert dados["acoes_cvm"]["lpa_divulgado_comparado"] == {
        "especie": "PN",
        "valor": 2.5,
    }
    (alerta,) = [a for a in _alertas(dados) if "LPA básico divulgado" in a]
    assert "2,00" in alerta and "2,50" in alerta and "(PN)" in alerta


# ── FII: P/VP da CVM × fonte de mercado (F2B-16; BUG-2A-12; armadilha 2) ──────


def _fii(monkeypatch, price_to_book):
    from tests.test_market_engine import ReferenciaDosMapas, _engine, _historico
    from tests.test_market_engine_fii_cvm import INFO, INFORME, _InformeFalso

    info = {**INFO, "priceToBook": price_to_book}
    engine = _engine(monkeypatch, info=info, historico=_historico(90.0))
    engine.cvm_fii = _InformeFalso(INFORME)
    engine.referencia = ReferenciaDosMapas()
    return engine.buscar_dados_ticker("HGLG11")  # P/VP da CVM: 90 ÷ 100 = 0,9


def test_identidade_do_fii_e_reconhecida(monkeypatch):
    # O P/VP do FII é preço ÷ VPA do próprio Informe: a checagem 3 é identidade (F2A-5).
    report = DataQualityReport(_fii(monkeypatch, 0.9))
    assert report._mesma_fonte("pvp", "vpa") is True


@pytest.mark.parametrize(
    ("price_to_book", "alerta"),
    [
        (1.5, True),  # 66,7% acima do P/VP da CVM
        (0.999, True),  # 11,0%
        (0.8, True),  # 11,1% abaixo
        (0.99, False),  # 10,0%: até o limiar, sem alerta
        (0.95, False),  # 5,6%
    ],
)
def test_pvp_do_fii_divergente_da_fonte_de_mercado_gera_alerta(
    monkeypatch, price_to_book, alerta
):
    alertas = [
        a for a in _alertas(_fii(monkeypatch, price_to_book)) if "P/VP da CVM" in a
    ]
    assert bool(alertas) is alerta
    if alerta:
        (texto,) = alertas
        assert "yfinance" in texto and "0,90" in texto


def _pvp_fii(cvm=0.9, informe="2026-08-01", **mercado):
    dados = {
        "cvm_fii_dt_referencia": informe,
        "valores_por_fonte": {
            "CVM": {"pvp": cvm},
            **{f: {"pvp": v} for f, v in mercado.items()},
        },
    }
    return [a for a in _alertas(dados) if "P/VP da CVM" in a]


def test_alerta_do_pvp_do_fii_so_com_o_informe_e_valores_validos():
    assert len(_pvp_fii(yfinance=1.5)) == 1
    assert _pvp_fii(informe=None, yfinance=1.5) == []  # sem o Informe aplicado
    assert _pvp_fii(cvm=-0.5, yfinance=1.5) == []  # P/VP da CVM ≤ 0
    assert _pvp_fii(cvm=0.0, yfinance=1.5) == []
    assert _pvp_fii(yfinance=0.0) == []  # P/VP de mercado ≤ 0 não é comparado


def test_alerta_do_pvp_do_fii_confere_cada_fonte_de_mercado():
    (so_brapi,) = _pvp_fii(yfinance=0.0, brapi=1.2)
    assert "brapi" in so_brapi and "1,20" in so_brapi and "33%" in so_brapi
    assert len(_pvp_fii(yfinance=1.5, brapi=1.2)) == 2
