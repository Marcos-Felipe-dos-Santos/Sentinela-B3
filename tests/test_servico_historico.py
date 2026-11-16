"""F3-3d [e2e]: o serviço numa data passada só lê o histórico do banco único.

Banco em memória com a DFP oficial de 2019 (00.776.574/0001-56: versão 1 entregue em
20/02/2020, versão 2 em 21/02/2020), um FCA sintético com o código de negociação entregue em
01/02/2020 e o COTAHIST sintético dos pregões antes de D. As fontes correntes (yfinance,
brapi, índice de referência atual, cache de fundamentos e pares) são espiões que falham se
forem chamados. Valor corrente e histórico diferentes: o preço corrente do espião (99,00)
contra o do COTAHIST em D (20,50); a DFP vista hoje (versão 2) contra a vista em D.
"""

import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from unittest.mock import Mock

import pandas as pd
import pytest
from test_carga_cvm import CIA, DFP
from test_universo_pit import _fca_sintetico, _negocio, _precos, _pregoes, _valor

import market_engine
from backtesting.backtest_pit import BacktestPIT
from fii_engine import FIIEngine
from sentinela.data.pit import carga_cvm, remontagem
from sentinela.data.store import migracoes, resultados
from sentinela.services import historico
from sentinela.services.analyze_asset import MOTIVO_PARES, AnalysisService
from technical_engine import TechnicalEngine
from valuation_engine import MOTIVO_BPP_INDISPONIVEL, ValuationEngine

ISIN = "BRAMERACNOR6"
HOJE = date(2026, 11, 12)
CADASTRO = pd.DataFrame(
    [{"CNPJ_CIA": CIA, "DENOM_SOCIAL": "AMERICANAS S.A.", "SIT": "ATIVO", "CD_CVM": "20990",
      "SETOR_ATIV": "Comércio (Atacado e Varejo)", "CONTROLE_ACIONARIO": "PRIVADO",
      "DT_REG": "1977-01-01", "DT_CANCEL": ""}]
)  # fmt: skip


@pytest.fixture
def banco(tmp_path):
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        carga_cvm.carregar(
            conn, DFP, tipo="DFP", fonte="cvm", coleta="2026-11-11T12:00:00+00:00"
        )
        acao = _valor(CNPJ_Companhia=CIA, Data_Referencia="2020-01-01",
                      Valor_Mobiliario="Ações Ordinárias", Codigo_Negociacao="AMER3",
                      Data_Inicio_Negociacao="2010-01-04")  # fmt: skip
        _fca_sintetico(
            conn, tmp_path, [(CIA, "2020-01-01", "1", "2020-02-01")], [acao], ano=2020
        )
        dias = _pregoes(date(2019, 11, 1), 86)  # até 28/02/2020
        _precos(conn, tmp_path, [
            _negocio(d, "AMER3", ISIN) if d < date(2020, 2, 28)
            else _negocio(d, "AMER3", ISIN).replace("0000000012345", "0000000002050")
            for d in dias
        ])  # fmt: skip
        yield conn


@pytest.fixture
def espioes(monkeypatch):
    falha = Mock(side_effect=AssertionError("fonte corrente consultada"))
    monkeypatch.setattr(market_engine.yf, "Ticker", falha)
    monkeypatch.setattr(market_engine.BrapiProvider, "get_fundamentals", falha)
    monkeypatch.setattr(market_engine.REFERENCIA_OFICIAL, "indice", falha)
    monkeypatch.setattr(
        market_engine.DatabaseManager, "buscar_fundamentos_cache", falha
    )
    monkeypatch.setattr(
        market_engine.DatabaseManager, "salvar_fundamentos_cache", falha
    )
    return falha


def _servico(banco, tmp_path, resultados_conn):
    corrente = Mock()  # o motor corrente: nunca chamado com data passada
    corrente.buscar_dados_ticker.return_value = {"preco_atual": 99.0}
    corrente.buscar_dados_ticker_em.return_value = {"preco_atual": 99.0}
    pares = Mock()
    pares.comparar.side_effect = AssertionError("pares consultados com data passada")
    servico = AnalysisService(
        corrente, ValuationEngine(), FIIEngine(), TechnicalEngine(), pares,
        hoje=HOJE, conexao_resultados=resultados_conn,
        motor_historico=lambda as_of: historico.MotorHistorico(
            banco, as_of, tmp_path / "pit", CADASTRO
        ),
    )  # fmt: skip
    return servico, corrente, pares


@pytest.fixture
def resultados_conn():
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        yield conn


def test_data_passada_le_so_o_historico_do_banco(
    banco, espioes, tmp_path, resultados_conn
):
    servico, corrente, pares = _servico(banco, tmp_path, resultados_conn)
    d = datetime(2020, 3, 2, 15, tzinfo=UTC)
    r = servico.analisar("AMER3", d, use_ai=False)
    dados = r.raw
    assert dados["preco_atual"] == pytest.approx(20.50)  # corrente: 99,00
    assert dados["data_preco"] == "2020-02-28"
    assert dados["fonte_preco"] == historico.FONTE_PRECO
    assert dados["cnpj"] == CIA and dados["cd_cvm"] == 20990
    assert dados["modo_historico"] == "estrito"
    assert dados["cvm_disponivel"] is True
    assert dados["modelo_bpp_proveniencia"]["periodo_referencia"] == "2019-12-31"
    assert r.peers == {"abstencao": MOTIVO_PARES}
    pares.comparar.assert_not_called()
    corrente.buscar_dados_ticker.assert_not_called()
    corrente.buscar_dados_ticker_em.assert_not_called()
    espioes.assert_not_called()
    # o leitor histórico: o banco de teste não tem coleta da relação antes de D
    assert dados["proventos_b3"] == {
        "abstencao": "sem coleta da relação de proventos do emissor"
    }
    # macro: a semente corrente dos testes (NTN-B de 7%, `conftest`) não chega; chega o
    # registro do `series_macro` do banco em D, que não tem a série
    assert dados["taxa_real"] == {"abstencao": "series_macro sem NTN-B até a data"}
    assert resultados.buscar(resultados_conn, "AMER3", as_of=d)
    # decisão 40 (F3-3e): a DFP entregue antes de D vale, mesmo coletada hoje; as lentes
    # passam pelo escopo e respondem às regras dos próprios métodos (aqui, empresa em
    # situação especial), sem número
    lentes = dados["lentes"]
    assert set(lentes) == {"Graham", "Bazin", "Lynch", "Gordon", "Bancos"}
    motivos = {lente.get("abstencao") for lente in lentes.values()}
    assert MOTIVO_BPP_INDISPONIVEL not in motivos
    assert "Empresa em situação especial/distressed" in motivos
    # as janelas: a DFP de 2019 só, sem a Composição do Capital (anterior a 2020) e sem os
    # cinco exercícios; a passagem pela guarda de coleta é provada nos testes de unidade
    # (`test_disponibilidade_publicacao`, BUG-3-27)
    janelas = dados["janelas_fundamentais"]
    motivo = "ações do exercício 2015: sem Composição do Capital no documento do lucro"
    assert janelas["graham"]["abstencao"] == janelas["lynch"]["abstencao"] == motivo


def test_versao_entregue_depois_de_d_fica_fora_com_motivo(
    banco, espioes, tmp_path, resultados_conn
):
    servico, _, _ = _servico(banco, tmp_path, resultados_conn)
    d = datetime(2020, 2, 21, 15, tzinfo=UTC)  # a versão 2, lida hoje, saiu neste dia
    dados = servico.analisar("AMER3", d, use_ai=False).raw
    assert dados["preco_atual"] == pytest.approx(123.45)  # 20/02, antes do novo preço
    assert any(
        "documento da CVM de 2019-12-31 fora da leitura" in risco
        for risco in dados["riscos_dados"]
    )
    assert (
        dados.get("modelo_bpp_proveniencia", {}).get("periodo_referencia")
        != "2019-12-31"
    )
    espioes.assert_not_called()


def test_codigo_sem_pregao_antes_de_d_abstem_sem_fonte_corrente(
    banco, espioes, tmp_path, resultados_conn
):
    servico, _, _ = _servico(banco, tmp_path, resultados_conn)
    r = servico.analisar("AMER3", datetime(2019, 6, 3, 15, tzinfo=UTC), use_ai=False)
    assert r.success is False
    espioes.assert_not_called()


def test_motor_historico_so_responde_pela_sua_data(banco, tmp_path):
    motor = historico.MotorHistorico(
        banco, datetime(2020, 3, 2, 15, tzinfo=UTC), tmp_path, CADASTRO
    )
    with pytest.raises(ValueError, match="só responde pela data"):
        motor.buscar_dados_ticker_em("AMER3", datetime(2020, 3, 3, 15, tzinfo=UTC))
    with pytest.raises(ValueError, match="modo desconhecido"):
        historico.MotorHistorico(banco, datetime(2020, 3, 2, 15, tzinfo=UTC), tmp_path,
                                 CADASTRO, modo="outro")  # fmt: skip


# F3-8e: a remontagem da CVM de um dia é feita uma vez e reaproveitada; o resultado
# é o mesmo da análise que remonta tudo, e outro D remonta o seu.
D_F38E = datetime(2020, 3, 2, 15, tzinfo=UTC)


@pytest.fixture
def chamadas(monkeypatch):
    feitas = []
    original = remontagem.zip_cia_em

    def espiao(conn, documento, ano, as_of, destino, **kw):
        feitas.append((documento, ano, as_of))
        return original(conn, documento, ano, as_of, destino, **kw)

    monkeypatch.setattr(remontagem, "zip_cia_em", espiao)
    return feitas


def _analisar(banco, conn_resultados, diretorio, as_of, remontagens=None):
    servico = AnalysisService(
        None,
        ValuationEngine(),
        FIIEngine(),
        TechnicalEngine(),
        hoje=HOJE,
        conexao_resultados=conn_resultados,
        motor_historico=lambda instante: historico.MotorHistorico(
            banco, instante, diretorio, CADASTRO, remontagens=remontagens
        ),
    )
    raw = servico.analisar("AMER3", as_of, use_ai=False).raw
    dados = dict(raw)
    # o que `executar` leva ao hash dos insumos: o raw sem histórico e fontes e sem a
    # proveniência instável (o instante da remontagem, `data_coleta`)
    dados.pop("historico", None)
    dados.pop("fontes", None)
    return BacktestPIT._hash(BacktestPIT._sem_proveniencia_instavel(dados)), raw


def test_compartilhada_da_o_mesmo_resultado_e_remonta_uma_vez(
    banco, espioes, resultados_conn, tmp_path, chamadas
):
    sozinha, _ = _analisar(banco, resultados_conn, tmp_path / "a", D_F38E)
    por_analise = len(chamadas)
    assert por_analise > 0
    assert len(set(chamadas)) == por_analise  # sem memória: um ZIP por documento e ano

    memoria = {}
    primeira, _ = _analisar(banco, resultados_conn, tmp_path / "b", D_F38E, memoria)
    segunda, _ = _analisar(banco, resultados_conn, tmp_path / "b", D_F38E, memoria)
    assert primeira == sozinha and segunda == sozinha
    assert len(chamadas) == 2 * por_analise  # a segunda análise não remontou nada
    espioes.assert_not_called()


def test_outro_dia_com_a_mesma_memoria_remonta_o_seu(
    banco, espioes, resultados_conn, tmp_path, chamadas
):
    memoria = {}
    _analisar(banco, resultados_conn, tmp_path / "c", D_F38E, memoria)
    antes = len(chamadas)
    outro = datetime(2020, 2, 21, 15, tzinfo=UTC)
    _, dados = _analisar(banco, resultados_conn, tmp_path / "c", outro, memoria)
    assert len(chamadas) == 2 * antes
    assert {as_of for _, _, as_of in chamadas[antes:]} == {outro}
    # a versão 2 da DFP saiu em 21/02: a remontagem desse dia não a herda de 02/03
    assert any(
        "documento da CVM de 2019-12-31 fora da leitura" in risco
        for risco in dados["riscos_dados"]
    )


def test_bloco_compartilhado_divide_as_remontagens_so_dentro_dele(
    banco, espioes, resultados_conn, tmp_path, chamadas
):
    with historico.remontagens_compartilhadas():
        _analisar(banco, resultados_conn, tmp_path / "d", D_F38E)
        por_analise = len(chamadas)
        _analisar(banco, resultados_conn, tmp_path / "d", D_F38E)
        assert len(chamadas) == por_analise
    _analisar(banco, resultados_conn, tmp_path / "d", D_F38E)
    assert len(chamadas) == 2 * por_analise  # fora do bloco, cada análise remonta


def test_executar_do_backtest_roda_dentro_do_bloco_compartilhado(monkeypatch):
    vistas = []

    def _executar(self, datas, *, horizontes, modo):
        vistas.append(historico._REMONTAGENS.get())
        return {"modo": modo, "horizontes": horizontes}

    monkeypatch.setattr(BacktestPIT, "_executar", _executar)
    executor = BacktestPIT(None, None, hoje=HOJE, cache_dir="c")
    assert executor.executar([date(2020, 3, 2)]) == {
        "modo": "estrito",
        "horizontes": (12, 24, 36),
    }
    assert vistas == [{}]  # a memória do bloco, vazia no início
    assert historico._REMONTAGENS.get() is None  # e só dentro dele


def test_informe_e_dfp_compartilhados_por_ano_e_com_o_modo(monkeypatch, tmp_path):
    feitas = []

    def informe(conn, ano, as_of, destino, *, modo):
        feitas.append(("fii", ano, modo))
        return destino / f"inf_{ano}.zip"

    def cia(conn, documento, ano, as_of, destino, *, modo):
        feitas.append((documento, ano, modo))
        return destino / f"{documento}_{ano}.zip", {}

    monkeypatch.setattr(remontagem, "zip_informe_em", informe)
    monkeypatch.setattr(remontagem, "zip_cia_em", cia)
    memoria = {}
    motores = [
        historico.MotorHistorico(
            None, D_F38E, tmp_path, CADASTRO, modo="exploratorio", remontagens=memoria
        )
        for _ in range(2)
    ]
    for motor in motores:
        assert motor.cvm_fii.baixar_informe(2019).name == "inf_2019.zip"
        assert motor.cvm_fii.baixar_informe(2020).name == "inf_2020.zip"
        assert motor.cvm.baixar_dfp(2019).name == "DFP_2019.zip"
    # uma remontagem por fonte e ano para os dois motores, sempre no modo do motor
    assert feitas == [
        ("fii", 2019, "exploratorio"),
        ("fii", 2020, "exploratorio"),
        ("DFP", 2019, "exploratorio"),
    ]
