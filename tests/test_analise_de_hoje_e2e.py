"""R1 (b): matriz das lentes da análise de hoje pela cascata de produção."""

import json
import os
import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import timedelta
from io import BytesIO

import pandas as pd
import pytest
import requests

import config
import fii_engine
import market_engine
from fii_engine import FIIEngine
from regressao.test_bug_3_63_coleta_da_execucao_apos_o_as_of import (
    AGORA,
    CONTRATOS,
    CNPJ_HGLG,
    HOJE,
    _http,
    _Resposta,
    _Referencia,
    _Relogio,
    DEPOIS,
    _Ticker,
)
from sentinela.data.providers import b3_fundos, b3_proventos, macro, tesouro
from sentinela.data.referencia.carga import ReferenciaOficial
from sentinela.data.referencia.indice import salvar_indice
from sentinela.data.store import migracoes
from sentinela.services.analyze_asset import AnalysisService
from technical_engine import TechnicalEngine
from test_contratos_provedores import _montar
from valuation_engine import ValuationEngine

# A relação gravada da Ambev comprova R$ 0,8464 brutos por ação na janela.
BAZIN = 0.8464 / 0.06
# Soma de (DY mensal × VP do mês anterior), de nov/2025 a out/2026 no Informe.
# A taxa de 19/11 é a média das 11 ofertas elegíveis do Tesouro (vencimento >= 2035).
RENDIMENTO = 13.2894829421 / (0.0763363636364 + 0.03505842448151178)
JANELA_INCOMPLETA = "exige cinco exercícios completos contínuos"
IPCA_INDISPONIVEL = "inflação indisponível: IPCA com cobertura desatualizada ou futura"
TOLERANCIA = 1e-6
CLASSES = {"ABEV3": "STOCK", "TAEE11": "UNIT", "HGLG11": "FII"}
MATRIZ = {
    "ABEV3": {
        "Graham": JANELA_INCOMPLETA,
        "Bazin": BAZIN,
        "Lynch": JANELA_INCOMPLETA,
        "Gordon": IPCA_INDISPONIVEL,
        "Bancos": "modelo empresa fora do escopo do método",
    },
    "TAEE11": {
        "Graham": JANELA_INCOMPLETA,
        "Bazin": "relação de proventos da B3 indisponível: GetDetail da unit fora do cenário",
        "Lynch": JANELA_INCOMPLETA,
        "Gordon": IPCA_INDISPONIVEL,
        "Bancos": "modelo empresa fora do escopo do método",
    },
    "HGLG11": {"Rendimento do FII": RENDIMENTO},
}


@pytest.fixture
def cascata(monkeypatch, tmp_path):
    """Semeia os arquivos públicos que os provedores leem do cache da análise do dia."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_Relogio, "atual", DEPOIS)
    monkeypatch.setattr(market_engine, "datetime", _Relogio)
    monkeypatch.setattr(config, "datetime", _Relogio)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    # Desfaz a semente global do conftest para usar o provedor real, com HTTP gravado.
    monkeypatch.setattr(
        config,
        "_carregar_taxa_real",
        macro.MacroProvider().registro,
    )
    monkeypatch.setattr(fii_engine, "MacroContext", config.MacroContext)

    # O carregador de referência real lê um índice local com três registros públicos.
    indice = _Referencia().indice(AGORA)
    indice.registros["TAEE11"] = replace(
        indice.registros["ABEV3"],
        ticker="TAEE11",
        classe="UNIT",
        especie=None,
        acoes_por_unit={"ON": 1, "PN": 2},
        cnpj="07.859.971/0001-30",
        cd_cvm=20257,
        setor="Energia Elétrica",
    )
    pasta_dados = tmp_path / "data"
    salvar_indice(indice, pasta_dados / "referencia")
    motor = market_engine.MarketEngine()
    motor.referencia = ReferenciaOficial(pasta_dados)

    for fixture, pasta, nome in (
        ("hoje_dfp_cia_aberta_2025.json", motor.cvm.cache_dir, "dfp_2025.zip"),
        (
            "hoje_inf_mensal_fii_2025.json",
            motor.cvm_fii.cache_dir,
            "inf_mensal_fii_2025.zip",
        ),
        (
            "hoje_inf_mensal_fii_2026.json",
            motor.cvm_fii.cache_dir,
            "inf_mensal_fii_2026.zip",
        ),
    ):
        arquivo, _ = _montar(fixture, tmp_path)
        destino = arquivo.replace(pasta / nome)
        coleta = (AGORA - timedelta(minutes=5)).timestamp()
        os.utime(destino, (coleta, coleta))

    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        yield AnalysisService(
            motor,
            ValuationEngine(),
            FIIEngine(),
            TechnicalEngine(),
            hoje=HOJE,
            conexao_resultados=conn,
        )


def _corpo(nome: str) -> str:
    contrato = json.loads((CONTRATOS / nome).read_text(encoding="utf-8"))
    return contrato["membros"][contrato["arquivo_original"]]


@pytest.fixture
def borda(monkeypatch):
    contrato = json.loads(
        (CONTRATOS / "yfinance_taee11_2026.json").read_text(encoding="utf-8")
    )
    unit = json.loads(contrato["membros"]["yf_TAEE11.json"])

    class TickerGravado(_Ticker):
        def __init__(self, simbolo):
            super().__init__(simbolo)
            if simbolo == "TAEE11.SA":
                divs = pd.Series(unit["divs"], dtype=float)
                divs.index = pd.to_datetime(divs.index)
                # O recorte preserva proventos e último preço, não a série de fechamentos.
                self._historico = pd.DataFrame(
                    {"Close": float("nan"), "Dividends": divs, "Volume": 0}
                )
                self._historico.loc[divs.index[-1], "Close"] = unit["preco"]
                self.info = {
                    "currentPrice": unit["preco"],
                    "sharesOutstanding": unit["shares"],
                }

    instituicoes = {
        tesouro.URL: _corpo("hoje_precotaxatesourodireto.json"),
        macro.ANBIMA.format(ano=2026): _corpo("hoje_anbima_2026.json"),
    }
    fundo = json.loads(
        (CONTRATOS / "b3_fundos_hglg_2026.json").read_text(encoding="utf-8")
    )
    taesa = b3_proventos.url("GetDetail", {"codeCVM": "20257", "language": "pt-br"})

    def http(url, *args, **kwargs):
        if url in instituicoes:
            return _Resposta(instituicoes[url])
        if url.endswith((".zip", ".ZIP")):
            resposta = requests.Response()
            resposta.status_code = 404
            resposta.url = url
            resposta.raw = BytesIO()
            return resposta
        if url == taesa:
            raise requests.ConnectionError("GetDetail da unit fora do cenário")
        if url == b3_fundos.url(CNPJ_HGLG, "HGLG11"):
            return _Resposta(fundo["membros"]["GetListedSupplementFunds"])
        return _http(url, *args, **kwargs)

    monkeypatch.setattr(market_engine.yf, "Ticker", TickerGravado)
    monkeypatch.setattr(requests, "get", http)
    return TickerGravado


@pytest.mark.parametrize("ticker", MATRIZ)
def test_lentes_da_analise_de_hoje(cascata, borda, ticker):
    raw = cascata.analisar(ticker, as_of=AGORA, use_ai=False).raw
    assert raw["classe_ativo"] == CLASSES[ticker]
    lentes = raw["lentes"]
    esperadas = MATRIZ[ticker]
    assert set(lentes) == set(esperadas)
    for nome, esperado in esperadas.items():
        lente = lentes[nome]
        if isinstance(esperado, str):
            assert lente["abstencao"] == esperado, nome
            assert lente["valor"] is None, nome
        else:
            assert lente["abstencao"] is None, nome
            assert lente["valor"] == pytest.approx(esperado, rel=TOLERANCIA), nome

    if ticker == "ABEV3":
        assert raw["proventos_b3"]["coleta"] == AGORA.isoformat()
    if ticker == "TAEE11":
        assert raw["acoes_por_unit"] == {"ON": 1, "PN": 2}
        assert raw["preco_atual"] == pytest.approx(41.81, abs=0.001)
    if ticker == "HGLG11":
        assert raw["b3_fundo"]["coleta"] == AGORA.isoformat()


def test_fii_de_hoje_com_informe_valido_e_sem_dy_da_cascata(
    cascata, borda, monkeypatch
):
    class TickerSemDY(borda):
        def __init__(self, simbolo):
            super().__init__(simbolo)
            self.info.pop("dividendYield", None)

    monkeypatch.setattr(market_engine.yf, "Ticker", TickerSemDY)
    raw = cascata.analisar("HGLG11", as_of=AGORA, use_ai=False).raw
    lente = raw["lentes"]["Rendimento do FII"]
    assert lente["abstencao"] is None
    assert lente["valor"] == pytest.approx(RENDIMENTO, rel=TOLERANCIA)
