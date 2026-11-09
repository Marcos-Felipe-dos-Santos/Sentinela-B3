"""BUG-2C-06: série e TTM compartilham fronteira que apaga dados e engole bugs.

Aceite F2C-31 e contrato F2C-29: fonte anual indisponível não invalida outro insumo
completo. TypeError é erro de programação, não evidência de ausência na fonte.
"""

import pytest

from tests.test_cvm_series import EXERCICIO_2025, EXERCICIO_2026, _Hoje
from tests.test_market_engine import _engine


class Fonte:
    def indicadores_da_serie(self, *args):
        raise OSError("DFP indisponível")

    def acumulados_ttm(self, *args):
        return EXERCICIO_2025 + EXERCICIO_2026

    def calcular_indicadores(self, *args, **kwargs):
        raise TypeError("erro de programação")


class ErroDePrograma(Fonte):
    tipo_erro = TypeError

    def indicadores_da_serie(self, *args):
        raise self.tipo_erro("erro de programação")


def test_falha_da_serie_preserva_ttm(monkeypatch):
    monkeypatch.setattr("market_engine.date", _Hoje)
    engine = _engine(monkeypatch, info={})
    dados = {"ticker": "TSTA3"}
    engine._serie_cvm("TSTA3", dados, Fonte(), 9999, "empresa")
    assert dados["ttm_cvm"]["valores"]["lucro_liquido"] == 75.0
    assert "indisponível" in str(dados["serie_cvm"])


@pytest.mark.parametrize("tipo", [TypeError, RuntimeError, AttributeError])
def test_erro_de_programacao_da_serie_propaga(monkeypatch, tipo):
    engine = _engine(monkeypatch, info={})
    fonte = ErroDePrograma()
    fonte.tipo_erro = tipo
    with pytest.raises(tipo, match="erro de programação"):
        engine._serie_cvm("TSTA3", {}, fonte, 9999, "empresa")


@pytest.mark.parametrize("tipo", [TypeError, RuntimeError, AttributeError])
def test_erro_de_programacao_na_cascata_propaga(monkeypatch, tipo):
    fonte = ErroDePrograma()
    fonte.tipo_erro = tipo
    engine = _engine(monkeypatch, info={}, cvm=fonte)
    with pytest.raises(tipo, match="erro de programação"):
        engine._buscar_cvm("PETR4", {"ticker": "PETR4", "cd_cvm": 9512})


def test_interface_anual_ausente_preserva_ttm(monkeypatch):
    engine = _engine(monkeypatch, info={})
    fonte = Fonte()
    fonte.indicadores_da_serie = None
    dados = {}
    monkeypatch.setattr("market_engine.date", _Hoje)
    engine._serie_cvm("TSTA3", dados, fonte, 9999, "empresa")
    assert dados["ttm_cvm"]["valores"]["lucro_liquido"] == 75.0


@pytest.mark.parametrize("etapa", ["anual", "ttm"])
def test_erro_de_programacao_no_provedor_propaga(tmp_path, monkeypatch, etapa):
    from datetime import date

    from cvm_provider import CVMProvider

    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))

    def quebrado(ano):
        raise TypeError("erro de programação")

    monkeypatch.setattr(provider, "baixar_dfp", quebrado)
    monkeypatch.setattr(provider, "baixar_itr", quebrado)
    with pytest.raises(TypeError, match="erro de programação"):
        if etapa == "anual":
            provider.calcular_indicadores(9999, anos=1, ano_final=2025)
        else:
            provider.acumulados_ttm(9999, date(2026, 10, 26))


def test_erro_de_programacao_do_lpa_nao_e_erro_de_formato(tmp_path, monkeypatch):
    from tests.regressao.test_bug_2c_10_escala_itr_bpp_ausente import fonte_do_itr

    p, args = fonte_do_itr(tmp_path, monkeypatch, 80)

    def quebrado(*a):
        raise KeyError("erro de programação no cálculo do LPA")

    monkeypatch.setattr("cvm_provider.lpa_divulgado", quebrado)
    with pytest.raises(KeyError, match="erro de programação"):
        p._escala_da_composicao(*args)
