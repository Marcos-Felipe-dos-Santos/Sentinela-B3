"""F3-6c: referência explícita não é o relógio nem a data real da coleta."""

import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

import cvm_fii_provider
import cvm_provider
import fii_engine
import market_engine
import valuation_engine
from sentinela.data.store import migracoes
from sentinela.domain.enums import AssetType, ModeloDemonstracao
from sentinela.services.analyze_asset import AnalysisService

AS_OF = datetime(2024, 1, 1, 2, tzinfo=UTC)  # ainda 31/12/2023 em São Paulo
AGORA = datetime(2026, 11, 10, 15, tzinfo=UTC)
DIA = date(2023, 12, 31)


class Relogio(datetime):
    @classmethod
    def now(cls, tz=None):
        return AGORA if tz is None else AGORA.astimezone(tz)


class Calendario(date):
    @classmethod
    def today(cls):
        return AGORA.date()


def test_montagem_de_inputs_do_motor_recebe_dia_local(monkeypatch):
    monkeypatch.setattr(valuation_engine, "date", Calendario)
    r = valuation_engine.ValuationEngine()._montar_inputs(
        10,
        10,
        1,
        False,
        True,
        classe=AssetType.STOCK,
        modelo=ModeloDemonstracao.EMPRESA,
        as_of=AS_OF,
    )
    assert r.as_of == DIA


def test_contexto_pvp_recebe_dia_local(monkeypatch):
    monkeypatch.setattr(fii_engine, "date", Calendario)
    calcular = Mock()
    monkeypatch.setattr(fii_engine._FII_NAV, "calcular", calcular)
    fii_engine.FIIEngine()._faixa_pvp(1, as_of=AS_OF)
    assert calcular.call_args.args[0].as_of == DIA


def test_cvm_ano_padrao_respeita_referencia_e_fuso(tmp_path, monkeypatch):
    monkeypatch.setattr(cvm_provider, "date", Calendario)
    p = cvm_provider.CVMProvider(tmp_path / "cvm")
    anos = []

    def baixar(ano):
        anos.append(ano)
        raise OSError("sem arquivo no cenário")

    monkeypatch.setattr(p, "baixar_dfp", baixar)
    assert p.calcular_indicadores(123, anos=1, as_of=AS_OF) == {}
    assert anos == [2022]


@pytest.mark.parametrize(
    "api,esperados",
    [("obter_dados_fii", [2023, 2022]), ("obter_rendimentos_fii", [2023, 2022, 2021])],
)
def test_informe_anos_respeitam_referencia(tmp_path, monkeypatch, api, esperados):
    monkeypatch.setattr(cvm_fii_provider, "date", Calendario)
    p = cvm_fii_provider.CVMFIIProvider(tmp_path / "fii")
    anos = []

    def baixar(ano):
        anos.append(ano)
        raise OSError("sem arquivo no cenário")

    def linhas(cnpj, ano):
        anos.append(ano)

    monkeypatch.setattr(p, "baixar_informe", baixar)
    monkeypatch.setattr(p, "_linhas_do_fundo", linhas)
    if api == "obter_rendimentos_fii":
        with pytest.raises(OSError):
            getattr(p, api)("00.000.000/0001-00", as_of=AS_OF)
    else:
        assert getattr(p, api)("00.000.000/0001-00", as_of=AS_OF) is None
    assert anos == esperados


def test_servico_entrega_referencia_a_capacidade_temporal_declarada():
    class Mercado:
        def __init__(self):
            self.chamadas = []

        def buscar_dados_ticker(self, ticker):
            pytest.fail(
                "serviço escolheu a entrada legada apesar da capacidade temporal"
            )

        def buscar_dados_ticker_em(self, ticker, as_of):
            self.chamadas.append((ticker, as_of))
            return {"ticker": ticker, "preco_atual": 10, "classe_ativo": "STOCK"}

    m = Mercado()
    val = Mock()
    val.processar.return_value = {"abstencao": "cenário sem fundamentos", "lentes": {}}
    tech = Mock()
    tech.calcular_indicadores.return_value = {}
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        s = AnalysisService(m, val, Mock(), tech, hoje=DIA, conexao_resultados=conn)
        s.analisar("TSTA3", AS_OF, use_ai=False)
    assert m.chamadas == [("TSTA3", AS_OF)]


def test_cascata_passagem_de_referencia_sem_retroagir_a_coleta(monkeypatch):
    monkeypatch.setattr(market_engine, "datetime", Relogio)
    m = market_engine.MarketEngine.__new__(market_engine.MarketEngine)
    m.asset_classifier = SimpleNamespace(
        classify=lambda *a: AssetType.STOCK, is_fii=lambda *a: False
    )
    m._aplicar_referencia = lambda t, d: d.update(classe_ativo="STOCK")
    m._buscar_yfinance = lambda t, d: d.update(preco_atual=10, fonte_preco="yfinance")
    m._buscar_brapi = Mock()
    referencias = []
    for nome in (
        "_buscar_cvm",
        "_buscar_cvm_fii",
        "_buscar_rendimento_fii",
        "_buscar_proventos_b3",
    ):
        setattr(m, nome, lambda t, d, *, as_of, n=nome: referencias.append((n, as_of)))
    m._buscar_ifdata = lambda d, *, as_of: referencias.append(("ifdata", as_of))
    m._buscar_liquidez = Mock()
    m._buscar_taxa_real = Mock()
    contextos = []
    m._contexto_janelas = lambda d, instante, *, coletado_em=None: contextos.append(
        (instante, coletado_em)
    )
    assert m.buscar_dados_ticker_em("TSTA3", AS_OF)["ticker"] == "TSTA3"
    assert len(referencias) == 5
    assert all(t == AS_OF for _, t in referencias)
    assert contextos == [(AS_OF, AGORA)]


def test_informe_recebe_corte_mas_complemento_b3_grava_coleta_real(monkeypatch):
    monkeypatch.setattr(market_engine, "datetime", Relogio)
    m = market_engine.MarketEngine.__new__(market_engine.MarketEngine)
    m._is_fii_ticker = lambda *a: True
    ler, coletar = Mock(return_value={}), Mock(return_value={})
    m.cvm_fii = SimpleNamespace(obter_rendimentos_fii=ler)
    m.b3_fundos = SimpleNamespace(coletar=coletar)
    m._buscar_rendimento_fii("TSTF11", {"cnpj": "00.000.000/0001-00"}, as_of=AS_OF)
    ler.assert_called_once_with("00.000.000/0001-00", as_of=AS_OF)
    coletar.assert_called_once_with("00.000.000/0001-00", "TSTF11", AGORA)


def test_janelas_cortam_na_referencia_e_adquirem_na_coleta(monkeypatch):
    m = market_engine.MarketEngine.__new__(market_engine.MarketEngine)
    obter = Mock(return_value={"abstencao": "fonte posterior"})
    monkeypatch.setattr(
        "sentinela.data.providers.macro.MacroProvider.ipca_serie", obter
    )
    consumir = Mock(return_value={})
    monkeypatch.setattr("sentinela.data.janelas_fundamentais.entradas", consumir)
    m._contexto_janelas(
        {"serie_cvm": {"exercicios": [{"exercicio": a} for a in range(2019, 2024)]}},
        AS_OF,
        coletado_em=AGORA,
    )
    assert obter.call_args.args[1] == AGORA
    assert consumir.call_args.args[1] == AS_OF


def test_proventos_cortam_fechamento_sem_retroagir_coleta(monkeypatch):
    from tests.test_b3_proventos import RELACAO, _Provedor

    monkeypatch.setattr(market_engine, "datetime", Relogio)
    m = market_engine.MarketEngine.__new__(market_engine.MarketEngine)
    fonte = _Provedor(RELACAO)
    fonte.coletar = Mock(wraps=fonte.coletar)
    m.b3_proventos = fonte
    calendario = Mock(return_value=None)
    m._pregoes_da_data_ex = calendario
    datas = pd.to_datetime(["2023-12-29", "2024-01-02"])
    dados = {
        "classe_ativo": "STOCK",
        "modelo_bpp": "empresa",
        "cd_cvm": 123,
        "historico": pd.DataFrame({"Close": [10, 11]}, index=datas),
        "fonte_preco": "yfinance",
        "fechamentos_brutos": {"2023-12-29": 10, "2024-01-02": 11},
    }
    m._buscar_proventos_b3("TSTA3", dados, as_of=AS_OF)
    assert calendario.call_args.args[1] == date(2023, 12, 29)
    fonte.coletar.assert_called_once_with(123, AGORA)


def test_snapshot_gordon_recebe_referencia_explicita(monkeypatch):
    monkeypatch.setattr(market_engine, "datetime", Relogio)
    m = market_engine.MarketEngine.__new__(market_engine.MarketEngine)
    indicador = {"cnpj": "00.000.000/0001-00"}
    calcular = Mock(return_value={2022: indicador})
    documento = Mock(return_value={"abstencao": "disponibilidade não demonstrada"})
    m.cvm = SimpleNamespace(
        calcular_indicadores=calcular, gordon_do_documento=documento
    )
    m._por_acao_cvm = Mock(return_value={})
    m._buscar_cvm("TSTA3", {"cd_cvm": 123, "classe_ativo": "STOCK"}, as_of=AS_OF)
    assert calcular.call_args.kwargs["as_of"] == AS_OF
    documento.assert_called_once_with(123, indicador, AS_OF)


def test_cascata_recusa_referencia_sem_fuso_antes_de_consultar():
    m = market_engine.MarketEngine.__new__(market_engine.MarketEngine)
    m._aplicar_referencia = Mock()
    with pytest.raises(ValueError, match="fuso"):
        m.buscar_dados_ticker_em("TSTA3", datetime(2024, 1, 1))  # noqa: DTZ001
    m._aplicar_referencia.assert_not_called()


@pytest.mark.parametrize("api", ["obter_dados_fii", "obter_rendimentos_fii"])
def test_informe_recusa_corte_sem_fuso(tmp_path, api):
    p = cvm_fii_provider.CVMFIIProvider(tmp_path / "fii")
    p.baixar_informe = Mock()
    with pytest.raises(ValueError, match="fuso"):
        getattr(p, api)("00.000.000/0001-00", as_of=datetime(2024, 1, 1))  # noqa: DTZ001
    p.baixar_informe.assert_not_called()


@pytest.mark.parametrize(("as_of", "esperado"), [(None, AGORA), (AS_OF, AS_OF)])
def test_taxa_real_pela_referencia_da_cascata(monkeypatch, as_of, esperado):
    """F3-A-F10 (BUG-3-22): sem as_of, o instante atual; com ele, o as_of, e a janela contábil."""
    monkeypatch.setattr(market_engine, "datetime", Relogio)
    pedidos = []
    monkeypatch.setattr(
        market_engine,
        "get_taxa_real",
        lambda *, as_of, janela=None: pedidos.append((as_of, janela)) or {"r": 1},
    )
    m = market_engine.MarketEngine.__new__(market_engine.MarketEngine)
    dados = {"janela_contabil_cvm": ("2024-01-01", "2024-12-31")}
    if as_of is None:
        m._buscar_taxa_real(dados)
    else:
        m._buscar_taxa_real(dados, as_of=as_of)
    assert pedidos == [(esperado, ("2024-01-01", "2024-12-31"))]
    assert dados["taxa_real"] == {"r": 1}
