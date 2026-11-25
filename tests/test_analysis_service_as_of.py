"""Contrato F3-6a e decisão 16: corte temporal e persistência imutável por lente."""

import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest

from sentinela.data.store import migracoes, resultados
from sentinela.services.analyze_asset import AnalysisService

AGORA = datetime(2026, 11, 10, 15, tzinfo=UTC)


@pytest.fixture
def conn(tmp_path):
    with closing(sqlite3.connect(tmp_path / "resultados.db")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


@pytest.fixture
def conn_memoria():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def servico(conn, analise=None, dados=None, **opcoes):
    market = Mock()
    market.buscar_dados_ticker.return_value = dados or {
        "ticker": "TSTA3",
        "classe_ativo": "STOCK",
        "preco_atual": 10,
        "fonte_preco": "fonte oficial",
        "data_preco": "2026-11-09",
    }
    valuation = Mock()
    valuation.processar.return_value = (
        analise
        if analise is not None
        else {
            "apresentacao_versao": "1.0",
            "lentes": {"graham": {"valor": 20.0, "abstencao": None, "versao": "2.1.0"}},
        }
    )
    fii = Mock()
    fii.analisar.return_value = valuation.processar.return_value
    tech = Mock()
    tech.calcular_indicadores.return_value = {"rsi": 50}
    classe = Mock()
    classe.is_fii.return_value = (
        market.buscar_dados_ticker.return_value.get("classe_ativo") == "FII"
    )
    return (
        AnalysisService(
            market,
            valuation,
            fii,
            tech,
            asset_classifier=classe,
            hoje=AGORA.date(),
            conexao_resultados=conn,
            **opcoes,
        ),
        market,
        valuation,
        fii,
    )


def test_original_e_recalculo_preservam_resultado_e_proveniencia(conn):
    s, market, val, _ = servico(conn)
    a = s.analisar(" tsta3 ", AGORA)
    b = s.analisar("TSTA3", AGORA)
    market.buscar_dados_ticker.assert_called_with("TSTA3")
    assert val.processar.call_args.kwargs == {"as_of": AGORA}
    registros = resultados.buscar(
        conn, "TSTA3", metodo="graham", versao="2.1.0", as_of=AGORA
    )
    assert [r.tipo for r in registros] == ["original", "recalculo"]
    assert registros[0].resultado["valor"] == 20.0
    assert registros[0].proveniencia["fonte_preco"] == "fonte oficial"
    assert registros[0].proveniencia["data_preco"] == "2026-11-09"
    assert registros[0].proveniencia["lente"] == registros[0].resultado
    assert a.as_of == AGORA.isoformat()
    assert a.execucao_id != b.execucao_id
    assert [r.execucao_id for r in registros] == [a.execucao_id, b.execucao_id]
    assert a.raw["lentes"]["graham"]["valor"] == 20.0
    assert a.extra["analise_motor"] == {
        "apresentacao_versao": "1.0",
        "lentes": {"graham": {"valor": 20.0, "abstencao": None, "versao": "2.1.0"}},
    }


@pytest.mark.parametrize("dias,palavra", [(-1, "banco único"), (1, "futura")])
def test_recusa_data_fora_de_hoje_sem_consultar_fontes(conn, dias, palavra):
    """Futura: recusa. Passada (F3-3d): sem o banco único histórico, abstém com o motivo."""
    s, market, val, fii = servico(conn)
    instante = AGORA + timedelta(days=dias)
    r = s.analisar("TSTA3", instante)
    assert r.success is False
    assert r.raw == {"abstencao": r.error, "lentes": {}}
    assert palavra in r.error
    market.buscar_dados_ticker.assert_not_called()
    val.processar.assert_not_called()
    fii.analisar.assert_not_called()
    (registro,) = resultados.buscar(conn, "TSTA3", as_of=instante)
    assert registro.resultado is None
    assert registro.motivo_abstencao == r.error
    assert (registro.metodo, registro.versao) == ("analise", "1.0")


def test_corte_usa_dia_de_sao_paulo(conn):
    s, market, _, _ = servico(conn)
    r = s.analisar("TSTA3", datetime(2026, 11, 11, 1, tzinfo=UTC))
    assert r.success
    market.buscar_dados_ticker.assert_called_once()


@pytest.mark.parametrize("classe", ["FII", "STOCK", "ETF", "BDR", "UNKNOWN"])
def test_abstencao_global_preserva_motivo_sem_numero(conn, classe):
    motivo = "escopo não elegível"
    s, _, _, fii = servico(
        conn,
        {"abstencao": motivo, "lentes": {}},
        {"ticker": "TSTA3", "classe_ativo": classe, "preco_atual": 10},
    )
    r = s.analisar("TSTA3", AGORA)
    assert r.raw["abstencao"] == motivo
    (registro,) = resultados.buscar(conn, "TSTA3", as_of=AGORA)
    assert registro.resultado is None
    assert registro.motivo_abstencao == motivo
    assert "valor" not in r.raw
    assert fii.analisar.call_count == (classe == "FII")


def test_abstencao_por_lente_nao_vira_zero(conn):
    s, _, _, _ = servico(
        conn,
        {
            "lentes": {
                "bancos": {
                    "valor": None,
                    "abstencao": "sem cinco exercícios",
                    "versao": "1.1.0",
                }
            }
        },
    )
    s.analisar("TSTA3", AGORA)
    (r,) = resultados.buscar(conn, "TSTA3", metodo="bancos", versao="1.1.0")
    assert r.resultado is None
    assert r.motivo_abstencao == "sem cinco exercícios"


def test_dados_indisponiveis_tambem_sao_gravados(conn):
    s, market, _, _ = servico(conn)
    market.buscar_dados_ticker.return_value = {"erro": "fonte indisponível"}
    r = s.analisar("TSTA3", AGORA)
    assert not r.success
    (registro,) = resultados.buscar(conn, "TSTA3")
    assert registro.resultado is None
    assert registro.motivo_abstencao == r.error
    assert (registro.metodo, registro.versao) == ("analise", "1.0")


def test_sem_referencia_da_borda_recusa_configuracao(conn):
    s = AnalysisService(Mock(), Mock(), Mock(), Mock(), conexao_resultados=conn)
    with pytest.raises(ValueError, match="borda"):
        s.analisar("TSTA3", AGORA)


def test_datetime_sem_fuso_e_date_nao_fingem_instante(conn):
    s, market, _, _ = servico(conn)
    for instante in (datetime(2026, 11, 10, 12), date(2026, 11, 10)):  # noqa: DTZ001
        with pytest.raises(ValueError, match="fuso"):
            s.analisar("TSTA3", instante)
    market.buscar_dados_ticker.assert_not_called()


def test_fixture_b3_produtor_cascata_servico_motor_e_store(conn, monkeypatch):
    from tests.test_b3_identidade_emissor import _cascata
    from valuation_engine import ValuationEngine

    class MercadoOficial:
        def buscar_dados_ticker(self, ticker):
            assert ticker == "ABEV3"
            return _cascata(monkeypatch)

    s, _, _, _ = servico(conn)
    s.market_engine = MercadoOficial()
    s.valuation_engine = ValuationEngine()
    r = s.analisar("ABEV3", AGORA)
    assert r.raw["proventos_b3"]["proveniencia"]["nome_pregao"] == "AMBEV SA"
    assert r.raw["bazin_proventos"]["d_bruto_12m"] == pytest.approx(0.8464)
    assert r.raw["lentes"]["Bazin"]["valor"] == pytest.approx(0.8464 / 0.06)
    (gravado,) = resultados.buscar(conn, "ABEV3", metodo="Bazin", as_of=AGORA)
    assert gravado.resultado == r.raw["lentes"]["Bazin"]
    assert gravado.tipo == "original"
    assert (
        gravado.proveniencia["fontes"]["proventos_b3"]
        == r.raw["proventos_b3"]["proveniencia"]
    )


def _entrada_golden(caso):
    import copy

    from apoio_bancos import PL_INICIAL, enriquecer_bancos
    from apoio_bazin import enriquecer_bazin
    from apoio_fii import enriquecer_fii
    from apoio_gordon import enriquecer_gordon
    from golden_motores import ESCOPO_DA_CASCATA

    entrada = copy.deepcopy(caso["entrada"])
    if caso["motor"] == "acoes":
        entrada = {**ESCOPO_DA_CASCATA, **entrada}
        if "banco" in caso:
            lucro = caso["banco"]["roe"] * PL_INICIAL
            return enriquecer_bancos(
                entrada,
                lucro_controladores=lucro,
                proventos_controladores=caso["banco"]["payout"] * lucro,
                vpa=caso["banco"]["vpa"],
            )
        taxa = caso.get("taxa_real") or {"ntnb": 0.07, "inflacao": 0.055}
        entrada = enriquecer_bazin(
            enriquecer_gordon(
                entrada,
                ntnb=taxa["ntnb"],
                inflacao=taxa["inflacao"],
                teto=caso.get("teto_pib_cenario", 0.02),
            )
        )
        if "qualidade" in caso:
            # F4-C10: o mesmo gancho do `golden_motores.executar`.
            from apoio_qualidade import enriquecer_qualidade

            entrada = enriquecer_qualidade(entrada, caso["qualidade"])
        return entrada
    return (
        entrada
        if caso.get("sem_informe")
        else enriquecer_fii(entrada, ntnb=caso.get("taxa_real", {}).get("ntnb"))
    )


def test_casos_golden_preservam_saida_do_caminho_atual(conn_memoria, monkeypatch):
    from apoio_gordon import AS_OF_GORDON
    from golden_motores import DISTRESSED, executar, iguais, ler_golden

    from fii_engine import FIIEngine
    from valuation_engine import ValuationEngine

    monkeypatch.setattr("valuation_engine.DISTRESSED_TICKERS", DISTRESSED)
    conn = conn_memoria
    for caso in ler_golden():
        esperado = executar(caso)
        assert iguais(esperado, caso["saida"]), caso["id"]
        s, market, _, _ = servico(conn)
        s.hoje = AS_OF_GORDON.date()
        market.buscar_dados_ticker.return_value = _entrada_golden(caso)
        s.asset_classifier.is_fii.return_value = caso["motor"] == "fii"
        s.valuation_engine, s.fii_engine = ValuationEngine(), FIIEngine()
        monkeypatch.setattr("fii_engine.get_selic_atual", lambda c=caso: c["selic"])
        if isinstance(esperado, dict) and "__erro__" in esperado:
            with pytest.raises(Exception) as erro:
                s.analisar("TSTA3", AS_OF_GORDON, use_ai=False)
            assert type(erro.value).__name__ == esperado["__erro__"], caso["id"]
        else:
            r = s.analisar("TSTA3", AS_OF_GORDON, use_ai=False)
            if esperado is None:
                assert not r.success, caso["id"]
            else:
                assert iguais({k: r.raw[k] for k in esperado}, esperado), caso["id"]


def test_conexao_padrao_grava_e_e_fechada(conn, monkeypatch):
    caminho = conn.execute("PRAGMA database_list").fetchone()[2]
    propria = sqlite3.connect(caminho)
    abrir = Mock(return_value=propria)
    monkeypatch.setattr(
        "sentinela.services.analyze_asset.unico.caminho_padrao", lambda: caminho
    )
    monkeypatch.setattr("sentinela.services.analyze_asset.sqlite3.connect", abrir)
    s, _, _, _ = servico(None)
    r = s.analisar("TSTA3", AGORA)
    abrir.assert_called_once_with(caminho)
    assert resultados.buscar(conn, "TSTA3")[0].execucao_id == r.execucao_id
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        propria.execute("SELECT 1")


@pytest.mark.parametrize("usar_ia", [True, False])
def test_interface_nova_preserva_contexto_e_nao_grava_pelo_legado(conn, usar_ia):
    ai, peers, repo = Mock(), Mock(), Mock()
    ai.analisar.return_value = {
        "content": "contexto do estudo",
        "model": "modelo-teste",
    }
    peers.comparar.return_value = {"grupo": "teste"}
    s, market, _, _ = servico(conn, ai_engine=ai, peers_engine=peers, repository=repo)
    market.buscar_dados_ticker.return_value["fonte_fundamentos"] = "CVM"
    r = s.analisar("TSTA3", AGORA, use_ai=usar_ia)
    assert r.technical.rsi == 50
    assert r.raw["tech"] == {"rsi": 50}
    assert r.peers == {"grupo": "teste"}
    assert r.market.preco_atual == 10
    assert r.fundamentals.to_dict()["ticker"] == "TSTA3"
    assert r.ai_analysis == ("contexto do estudo" if usar_ia else None)
    assert ai.analisar.call_count == usar_ia
    assert r.extra.get("resposta_ia") == (ai.analisar.return_value if usar_ia else None)
    if usar_ia:
        assert ai.analisar.call_args.args == ("TSTA3", r.raw)
    repo.salvar_analise.assert_not_called()
    repo.save_run.assert_not_called()
    (gravado,) = resultados.buscar(conn, "TSTA3")
    assert gravado.proveniencia["fonte_fundamentos"] == "CVM"


def test_transporte_preserva_as_of_e_identificador(conn):
    from sentinela.domain.models import AnalysisResult

    s, _, _, _ = servico(conn)
    r = s.analisar("TSTA3", AGORA)
    transportado = AnalysisResult.from_dict(r.to_dict())
    assert transportado.as_of == AGORA.isoformat()
    assert transportado.execucao_id == r.execucao_id
