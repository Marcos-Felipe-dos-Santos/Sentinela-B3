"""BUG-3-63 [e2e]: na análise de hoje, a coleta da própria execução cai depois do as_of.

O app captura o `as_of` no clique e o `MarketEngine` carimbava as coletas com
`datetime.now(UTC)` segundos depois (`_buscar_proventos_b3`, `_buscar_rendimento_fii`,
`_contexto_janelas`); as guardas exigem coleta ≤ as_of, e Graham ("coleta sem fuso ou
posterior ao as_of"), Bazin ("relação B3 sem coleta até o as_of") e Rendimento do FII ("coleta
da B3 não demonstrada até o as_of") se abstinham para ABEV3 e HGLG11 (uso, 20/11/2026).

Arranjo: `AnalysisService.analisar(ticker, as_of=AGORA)` com o `MarketEngine` real, os motores
reais e os coletores reais da B3 (`b3_proventos`, `b3_fundos`) e do IBGE (`MacroProvider`).
O HTTP é simulado só no `requests.get`: as respostas da B3 da Ambev são o contrato D18
(`tests/fixtures/contratos/b3_proventos_abev_2026.json`); a do fundo e a série do IPCA são
sintéticas. O relógio do motor anda 3 s depois do clique, como na execução real. Os documentos
que a cascata lê do cache local (índice oficial, DFP da CVM, Informe Mensal e o histórico do
yfinance) entram já montados e com coleta anterior ao clique: não são o que está sob teste.
Nenhum valor é dado de mercado.
"""

import hashlib
import json
import sqlite3
from collections import OrderedDict
from contextlib import closing
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
import requests
from apoio_fii import enriquecer_fii
from conftest import TAXA_REAL_SEMENTE

import config
import market_engine
from fii_engine import FIIEngine
from market_engine import MarketEngine
from sentinela.data.providers import b3_fundos, b3_proventos, macro
from sentinela.data.referencia.registro import Indice, Registro
from sentinela.data.store import migracoes
from sentinela.services.analyze_asset import AnalysisService
from sentinela.services.historico import MotorHistorico
from technical_engine import TechnicalEngine
from valuation_engine import ValuationEngine

AGORA = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)  # o clique
DEPOIS = AGORA + timedelta(seconds=3)  # o relógio enquanto a cascata coleta
HOJE = date(2026, 11, 20)
CNPJ_ABEV = "07.526.557/0001-00"
CNPJ_HGLG = "11.728.688/0001-47"
ANTES = "2026-10-01T12:00:00+00:00"  # coleta dos documentos do cache local

CONTRATOS = Path(__file__).resolve().parents[1] / "fixtures" / "contratos"
ABEV = json.loads(
    (CONTRATOS / "b3_proventos_abev_2026.json").read_text(encoding="utf-8")
)["membros"]
FII = enriquecer_fii({"ticker": "HGLG11", "preco_atual": 100.0, "dy": 0.09}, ntnb=None)


class _Relogio(datetime):
    """`datetime` do `market_engine` e do `config`: o relógio 3 s depois do clique, ou o que o
    teste da meia-noite puser em `atual`."""

    atual = DEPOIS

    @classmethod
    def now(cls, tz=None):
        # sem fuso, a hora local ingênua, como o `datetime` real
        return (
            cls.atual.astimezone(tz)
            if tz
            else cls.atual.astimezone().replace(tzinfo=None)
        )


class _Resposta:
    def __init__(self, corpo):
        self.text = corpo if isinstance(corpo, str) else json.dumps(corpo)
        self.content = self.text.encode("utf-8")
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return json.loads(self.text)


def _ipca():
    """Calendário 9256 e variável 63 da SIDRA: 1% ao mês, divulgado no dia 10 seguinte."""
    linhas, eventos = [], []
    for numero in range(2021 * 12 + 11, 2025 * 12 + 12):
        ano, mes = divmod(numero, 12)
        mes += 1
        linhas.append(
            {"D1C": "1", "D2C": "63", "D3C": f"{ano:04}{mes:02}", "MN": "%", "V": "1"}
        )
        ano_pub, mes_pub = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        eventos.append(
            {
                "produto_id": 9256,
                "ano_referencia_inicio": ano,
                "mes_referencia_inicio": mes,
                "data_divulgacao": f"10/{mes_pub:02}/{ano_pub} 09:00:00",
            }
        )
    return {"items": eventos}, linhas


def _http(endereco, *args, **kwargs):
    """A borda: só as fontes desta análise respondem; o resto da rede está fora do ar."""
    calendario, sidra = _ipca()
    if endereco == macro.IBGE_CALENDARIO:
        return _Resposta(calendario)
    if endereco.startswith("https://apisidra.ibge.gov.br/values/t/1737/"):
        return _Resposta(sidra)
    if endereco == b3_fundos.url(CNPJ_HGLG, "HGLG11"):
        return _Resposta(FII["b3_fundo"]["resposta"] | {"code": "HGLG", "fund": "HGLG"})
    if endereco.startswith(b3_proventos.URL_BASE + "/"):
        metodo = endereco.removeprefix(b3_proventos.URL_BASE + "/").split("/", 1)[0]
        membro = {
            "GetDetail": "GetDetail.json",
            "GetListedSupplementCompany": "GetListedSupplementCompany.json",
            "GetListedCashDividends": "GetListedCashDividends_AMBEV_SA.json",
        }[metodo]
        return _Resposta(ABEV[membro])
    raise requests.ConnectionError(f"fora do ar no teste: {endereco}")


class _Ticker:
    """yfinance: um ano de pregões até a véspera do clique, sem proventos."""

    def __init__(self, simbolo):
        fii = simbolo.startswith("HGLG")
        preco = 100.0 if fii else 12.0
        dias = pd.bdate_range(end=HOJE - timedelta(days=1), periods=250)
        self._historico = pd.DataFrame(
            {"Close": preco, "Dividends": 0.0, "Volume": 1_000_000}, index=dias
        )
        self.info = {
            "currentPrice": preco,
            "dividendYield": 9.0 if fii else 6.0,
        }  # percentual

    def history(self, *args, **kwargs):
        return self._historico


class _Referencia:
    def indice(self, agora):
        registros = {
            "ABEV3": Registro(
                ticker="ABEV3", classe="STOCK", regra="índice de teste", fonte={},
                especie="ON", cnpj=CNPJ_ABEV, cd_cvm=23264, setor="Bebidas",
            ),
            "HGLG11": Registro(
                ticker="HGLG11", classe="FII", regra="índice de teste", fonte={},
                cnpj=CNPJ_HGLG, segmento="Logística",
            ),
        }  # fmt: skip
        return Indice(
            gerado_em="2026-10-01", fontes={}, registros=registros, excecoes=[]
        )


class _InformeFII:
    """Informe Mensal já no cache local, entregue e coletado antes do clique."""

    def obter_dados_fii(self, cnpj, as_of=None):
        return {
            "valor_cota": 100.0,
            "patrimonio_liquido": 100_000_000.0,
            "cotas_emitidas": 1_000_000,
            "dt_referencia": "2026-09-01",
            "proveniencia": {"fonte": "Informe Mensal sintético", "data_coleta": ANTES},
        }

    def obter_rendimentos_fii(self, cnpj, as_of=None):
        return FII["informe_fii"] | {
            "proveniencia": {"fonte": "Informe Mensal sintético", "data_coleta": ANTES}
        }


def _documentos_cvm(ticker, dados, *, as_of=None):
    """As DFP de 2021 a 2025 do cache local (coleta anterior ao clique), modelo empresa."""
    dados.update(
        {
            "modelo_bpp": "empresa",
            "cvm_disponivel": True,
            "fonte_fundamentos": "CVM",
            "lpa": 1.0,
            "vpa": 8.0,
            "roe": 0.125,
            "pl": 12.0,
            "pvp": 1.5,
            "serie_cvm": {
                "exercicios": [
                    {
                        "exercicio": ano,
                        "inicio": f"{ano}-01-01",
                        "fim": f"{ano}-12-31",
                        "acoes": 100,
                        "lpa": 1.0,
                        "vpa": 8.0,
                        "proveniencia": {
                            "fonte": "DFP sintética",
                            "data_entrega": f"{ano + 1}-03-01",
                            "data_coleta": ANTES,
                        },
                    }
                    for ano in range(2021, 2026)
                ]
            },
        }
    )
    return True


@pytest.fixture
def servico(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # caches dos provedores (data/macro) na pasta do teste
    monkeypatch.setattr(_Relogio, "atual", DEPOIS)
    monkeypatch.setattr(market_engine, "datetime", _Relogio)
    monkeypatch.setattr(config, "datetime", _Relogio)  # a taxa real também lê o relógio
    monkeypatch.setattr(requests, "get", _http)
    monkeypatch.setattr(market_engine.yf, "Ticker", _Ticker)
    # a cesta do Tesouro já carregada no dia: no mesmo dia, o corte é a própria coleta (2B)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    monkeypatch.setattr(
        config,
        "_carregar_taxa_real",
        lambda instante, janela, coleta=None: (
            TAXA_REAL_SEMENTE
            | {
                "as_of": instante.isoformat(),
                "data_base": "2026-11-18",
                "dias_uteis": 2,
            }
        ),
    )
    for cache in (b3_proventos._COLETAS, b3_fundos._COLETAS):
        monkeypatch.setattr(cache, "_dados", OrderedDict())
    motor = MarketEngine()
    motor.referencia = _Referencia()
    motor.cvm_fii = _InformeFII()
    motor.cotahist = None
    monkeypatch.setattr(motor, "_buscar_cvm", _documentos_cvm)
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        yield AnalysisService(
            motor, ValuationEngine(), FIIEngine(), TechnicalEngine(),
            hoje=HOJE, conexao_resultados=conn,
        )  # fmt: skip


def test_acao_de_hoje_aceita_a_coleta_da_propria_execucao(servico):
    resultado = servico.analisar("ABEV3", AGORA, use_ai=False)
    lentes, dados = resultado.raw["lentes"], resultado.raw
    # Sem a correção, os motivos do app: "coleta sem fuso ou posterior ao as_of" e
    # "relação B3 sem coleta até o as_of".
    assert {n: lentes[n]["abstencao"] for n in ("Graham", "Bazin")} == {
        "Graham": None,
        "Bazin": None,
    }
    # A coleta desta execução fica no instante da borda, nunca depois dele.
    assert dados["proventos_b3"]["coleta"] == AGORA.isoformat()
    assert dados["ipca_serie"]["coleta"] == AGORA.isoformat()
    # Graham: LPA de 1,00 corrigido por 1% ao mês até 2025, VPA 8: √(22,5 × média × 8).
    media = sum(1.01 ** (12 * k) for k in range(5)) / 5
    assert lentes["Graham"]["valor"] == pytest.approx((22.5 * media * 8) ** 0.5)
    # Bazin: R$ 0,8464 brutos com data ex nos 12 meses até 19/11/2026 no contrato da
    # Ambev, sobre 6%.
    assert lentes["Bazin"]["valor"] == pytest.approx(0.8464 / 0.06)


def test_fii_de_hoje_aceita_a_coleta_da_propria_execucao(servico):
    resultado = servico.analisar("HGLG11", AGORA, use_ai=False)
    lente = resultado.raw["lentes"]["Rendimento do FII"]
    # Sem a correção, o motivo do app: "coleta da B3 não demonstrada até o as_of".
    assert lente["abstencao"] is None
    assert resultado.raw["b3_fundo"]["coleta"] == AGORA.isoformat()
    # R$ 9,00 por cota em 12 meses ÷ (NTN-B 7% da taxa do dia + spread do tijolo).
    assert lente["valor"] == pytest.approx(9.0 / (0.07 + 0.03505842448151178))


def test_coleta_de_outra_execucao_depois_do_as_of_continua_barrada(servico, tmp_path):
    """O calendário do IBGE gravado no cache por outra execução 1 s depois do clique não vale."""
    calendario = json.dumps(_ipca()[0])
    copia = macro.SnapshotMacro(
        calendario,
        macro.IBGE_CALENDARIO,
        (AGORA + timedelta(seconds=1)).isoformat(),
        hashlib.sha256(calendario.encode()).hexdigest(),
    )
    pasta = tmp_path / "data" / "macro"
    pasta.mkdir(parents=True)
    nome = hashlib.sha256(macro.IBGE_CALENDARIO.encode()).hexdigest() + ".json"
    (pasta / nome).write_text(json.dumps(copia.__dict__), encoding="utf-8")
    resultado = servico.analisar("ABEV3", AGORA, use_ai=False)
    assert resultado.raw["ipca_serie"] == {
        "abstencao": "coleta macro posterior ao as_of"
    }
    graham = resultado.raw["lentes"]["Graham"]
    assert graham["abstencao"] == "coleta macro posterior ao as_of"
    assert graham.get("valor") is None


@pytest.mark.parametrize(
    ("as_of", "esperado"),
    [
        (None, DEPOIS),  # sem as_of: o relógio, como antes
        (AGORA, AGORA),  # análise do dia: o instante da borda
        (
            AGORA + timedelta(hours=1),
            DEPOIS,
        ),  # mais tarde no mesmo dia: nunca depois do relógio
        (AGORA - timedelta(days=1), DEPOIS),  # data passada (decisão 40): o relógio
    ],
)
def test_instante_da_coleta(monkeypatch, as_of, esperado):
    monkeypatch.setattr(market_engine, "datetime", _Relogio)
    assert MarketEngine.__new__(MarketEngine)._instante_da_coleta(as_of) == esperado


def test_motor_historico_mantem_o_relogio(monkeypatch):
    monkeypatch.setattr(market_engine, "datetime", _Relogio)
    assert MotorHistorico.__new__(MotorHistorico)._instante_da_coleta(AGORA) == DEPOIS


def test_cascata_que_passa_da_meia_noite_mantem_a_coleta_no_as_of(servico, monkeypatch):
    """Clique às 23:59:59 de 20/11 em São Paulo; o relógio vira o dia durante o yfinance."""
    clique = datetime(2026, 11, 21, 2, 59, 59, tzinfo=UTC)
    monkeypatch.setattr(_Relogio, "atual", clique + timedelta(milliseconds=500))

    class _TickerDaMeiaNoite(_Ticker):
        def history(self, *args, **kwargs):
            _Relogio.atual = clique + timedelta(seconds=3)  # 21/11, 00:00:02
            return super().history(*args, **kwargs)

    monkeypatch.setattr(market_engine.yf, "Ticker", _TickerDaMeiaNoite)
    dados = servico.analisar("ABEV3", clique, use_ai=False).raw
    assert "disponibilidade_por_publicacao" not in dados
    assert dados["proventos_b3"]["coleta"] == clique.isoformat()
    assert dados["ipca_serie"]["coleta"] == clique.isoformat()
    assert {n: dados["lentes"][n]["abstencao"] for n in ("Graham", "Bazin")} == {
        "Graham": None,
        "Bazin": None,
    }
    assert "_instante_coleta" not in dados


def test_etapa_chamada_direto_decide_o_instante_ela_mesma(monkeypatch):
    """Fora de `buscar_dados_ticker` (sem a marca da execução), a etapa usa a mesma regra."""
    monkeypatch.setattr(market_engine, "datetime", _Relogio)
    monkeypatch.setattr(_Relogio, "atual", DEPOIS)
    motor = MarketEngine.__new__(MarketEngine)
    assert motor._coleta_de({}, AGORA) == AGORA
    assert motor._coleta_de({}, None) == DEPOIS
    marcado = AGORA - timedelta(seconds=1)
    assert motor._coleta_de({"_instante_coleta": marcado}, AGORA) == marcado
