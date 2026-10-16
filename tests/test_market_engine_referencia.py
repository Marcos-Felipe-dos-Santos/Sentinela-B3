"""A cascata lê o índice oficial (F2A-19): índice falso em memória, sem rede."""

import threading
from datetime import UTC, datetime, timedelta

import pytest

from ai_core import SentinelaAI
from sentinela.data.referencia import carga
from sentinela.data.referencia.registro import Excecao, Indice, Registro
from tests.test_market_engine import FakeCVM, _cvm_ind, _engine, _historico

FONTE_FCA = {"arquivo": "fca_cia_aberta_2026.zip", "data": "2026-10-08"}


class FakeReferencia:
    def __init__(self, indice):
        self._indice = indice
        self.instantes = []

    def indice(self, agora):
        self.instantes.append(agora)
        return self._indice


class CVMQueAnota(FakeCVM):
    def __init__(self, resultado=None):
        super().__init__(resultado)
        self.codigos = []

    def calcular_indicadores(self, cd_cvm, anos=1):
        self.codigos.append(cd_cvm)
        return super().calcular_indicadores(cd_cvm, anos)


def _registro(ticker="TSTA3", **campos):
    base = dict(
        ticker=ticker, classe="STOCK", regra="fca:codigo_ativo", fonte=FONTE_FCA,
        especie="ON", cnpj="11.111.111/0001-11", cd_cvm=999, nome="EMPRESA TESTE S.A.",
        setor="Energia Elétrica", controle_acionario="PRIVADO",
    )  # fmt: skip
    return Registro(**{**base, **campos})


def _indice(*registros, excecoes=()):
    return Indice(
        gerado_em="2026-10-08",
        fontes={},
        registros={r.ticker: r for r in registros},
        excecoes=list(excecoes),
    )


def _motor(monkeypatch, referencia, cvm=None):
    engine = _engine(
        monkeypatch,
        historico=_historico(20.0),
        info={"currentPrice": 20.0, "quoteType": "EQUITY", "trailingPE": 10.0,
              "priceToBook": 1.2, "returnOnEquity": 0.10, "dividendYield": 0.04},
        cvm=cvm if cvm is not None else CVMQueAnota(_cvm_ind()),
    )  # fmt: skip
    engine.referencia = referencia  # None: sem índice (F2A-31)
    return engine


# ── aceite ───────────────────────────────────────────────────────────────────


def test_ticker_fora_do_mapa_manual_recebe_cvm_pelo_indice(monkeypatch):
    cvm = CVMQueAnota(_cvm_ind(roe=0.21))
    engine = _motor(monkeypatch, FakeReferencia(_indice(_registro())), cvm)
    dados = engine.buscar_dados_ticker("TSTA3")
    assert cvm.codigos == [999]
    assert dados["cvm_disponivel"] is True
    assert dados["roe"] == pytest.approx(0.21)


def test_sem_indice_nao_usa_o_mapa_manual(monkeypatch):
    # F2A-31: antes, sem índice, o CD_CVM vinha de `cvm_ticker_map.py`.
    cvm = CVMQueAnota(_cvm_ind())
    engine = _motor(monkeypatch, FakeReferencia(None), cvm)
    dados = engine.buscar_dados_ticker("PETR4")
    assert cvm.codigos == []
    assert dados["cvm_disponivel"] is False
    # F2A-43: sem índice, a classe é a do classificador (não mais ausente).
    assert dados["classe_ativo"] == "STOCK"


def test_ticker_fora_da_cvm_tem_motivo_em_riscos_dados(monkeypatch):
    cvm = CVMQueAnota(_cvm_ind())
    engine = _motor(monkeypatch, FakeReferencia(_indice(_registro())), cvm)
    dados = engine.buscar_dados_ticker("ZZZZ3")
    assert cvm.codigos == []
    assert dados["cvm_disponivel"] is False
    assert "ticker fora da cobertura da CVM" in dados["riscos_dados"]


def test_registro_do_indice_entra_em_dados(monkeypatch):
    unit = _registro(
        "TSTA11", classe="UNIT", especie=None, acoes_por_unit={"ON": 1, "PN": 2}
    )
    engine = _motor(monkeypatch, FakeReferencia(_indice(unit)))
    dados = engine.buscar_dados_ticker("TSTA11")
    assert {
        k: dados[k]
        for k in (
            "classe_ativo", "especie", "cnpj", "cd_cvm", "setor", "segmento_fii",
            "controle_acionario", "acoes_por_unit",
        )
    } == {
        "classe_ativo": "UNIT", "especie": None, "cnpj": "11.111.111/0001-11",
        "cd_cvm": 999, "setor": "Energia Elétrica", "segmento_fii": None,
        "controle_acionario": "PRIVADO", "acoes_por_unit": {"ON": 1, "PN": 2},
    }  # fmt: skip
    assert dados["referencia_oficial"] == {
        "regra": "fca:codigo_ativo",
        "fonte": FONTE_FCA,
        "correcao": None,
        "gerado_em": "2026-10-08",
    }


# ── demais regras do item ────────────────────────────────────────────────────


def test_cascata_consulta_o_indice_com_o_instante_atual_em_utc(monkeypatch):
    referencia = FakeReferencia(_indice(_registro()))
    antes = datetime.now(UTC)
    _motor(monkeypatch, referencia).buscar_dados_ticker("TSTA3")
    (instante,) = referencia.instantes
    assert instante.tzinfo == UTC
    assert antes <= instante <= datetime.now(UTC)


def test_ticker_fora_do_indice_tem_risco_com_o_motivo(monkeypatch):
    excecao = Excecao("TRXF11", "ticker repetido em CNPJs distintos", "1", "F")
    engine = _motor(monkeypatch, FakeReferencia(_indice(excecoes=[excecao])))
    dados = engine.buscar_dados_ticker("TRXF11")
    assert (
        "ticker fora da referência oficial (ticker repetido em CNPJs distintos)"
        in dados["riscos_dados"]
    )


def test_ticker_fora_do_indice_sem_motivo(monkeypatch):
    engine = _motor(monkeypatch, FakeReferencia(_indice(_registro())))
    dados = engine.buscar_dados_ticker("PETR4")
    assert "ticker fora da referência oficial" in dados["riscos_dados"]
    # F2A-43: fora do índice, a classe é a do classificador (não mais ausente).
    assert dados["classe_ativo"] == "STOCK"


def test_classe_do_indice_prevalece_sobre_o_classificador(monkeypatch):
    # F2A-43: só sem classe do índice a cascata grava a do classificador. "COTA" o
    # classificador converte em FII; a cascata guarda o valor do índice como veio.
    cota = _registro("TSTA11", classe="COTA", especie=None)
    dados = _motor(monkeypatch, FakeReferencia(_indice(cota))).buscar_dados_ticker("TSTA11")
    assert dados["classe_ativo"] == "COTA"
    assert dados["referencia_oficial"]["regra"] == "fca:codigo_ativo"


def test_ticker_fora_do_indice_nao_consulta_a_cvm(monkeypatch):
    # F2A-31: antes, caía no mapa manual (CD_CVM 9512).
    cvm = CVMQueAnota(_cvm_ind())
    engine = _motor(monkeypatch, FakeReferencia(_indice(_registro())), cvm)
    dados = engine.buscar_dados_ticker("PETR4")
    assert cvm.codigos == []
    assert "ticker fora da cobertura da CVM" in dados["riscos_dados"]


def test_cd_cvm_do_indice_prevalece_sobre_o_mapa_manual(monkeypatch):
    cvm = CVMQueAnota(_cvm_ind())
    registro = _registro("PETR4", cd_cvm=123)
    engine = _motor(monkeypatch, FakeReferencia(_indice(registro)), cvm)
    engine.buscar_dados_ticker("PETR4")
    assert cvm.codigos == [123]


def test_registro_sem_cd_cvm_nao_consulta_a_cvm(monkeypatch):
    # F2A-31: antes, caía no mapa manual (CD_CVM 9512) e não ganhava o risco de cobertura.
    cvm = CVMQueAnota(_cvm_ind())
    registro = _registro("PETR4", cd_cvm=None)
    engine = _motor(monkeypatch, FakeReferencia(_indice(registro)), cvm)
    dados = engine.buscar_dados_ticker("PETR4")
    assert cvm.codigos == []
    assert "ticker fora da cobertura da CVM" in dados["riscos_dados"]


def test_motor_sem_referencia_nao_consulta_a_cvm(monkeypatch):
    # F2A-31: sem a referência injetada, é o mesmo que sem índice.
    engine = _motor(monkeypatch, None)
    dados = engine.buscar_dados_ticker("PETR4")
    assert "referencia_oficial" not in dados
    assert dados["riscos_dados"] == [
        "referência oficial indisponível: dados da CVM não consultados"
    ]


def test_ticker_sem_cvm_injetada_nao_ganha_risco_de_cobertura(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(20.0),
        info={"currentPrice": 20.0, "quoteType": "EQUITY"},
    )
    dados = engine.buscar_dados_ticker("ZZZZ3")
    assert "ticker fora da cobertura da CVM" not in dados["riscos_dados"]


def test_correcao_marca_a_proveniencia_dos_campos_da_cvm(monkeypatch):
    correcao = {"ticker": "CSNA3", "codigo_na_fonte": "4030", "motivo": "m"}
    registro = _registro("CSNA3", regra="correcao", correcao=correcao)
    engine = _motor(monkeypatch, FakeReferencia(_indice(registro)))
    dados = engine.buscar_dados_ticker("CSNA3")
    assert dados["referencia_oficial"]["correcao"] == correcao
    prov = dados["field_provenance"]["roe"]["provenance"]
    assert prov["source"] == "CVM"
    assert "cvm_code_from_correction_table" in prov["warnings"]
    preco = dados["field_provenance"]["preco_atual"]["provenance"]
    assert "cvm_code_from_correction_table" not in preco["warnings"]


def test_sem_correcao_nao_ha_aviso_de_tabela(monkeypatch):
    engine = _motor(monkeypatch, FakeReferencia(_indice(_registro())))
    dados = engine.buscar_dados_ticker("TSTA3")
    avisos = dados["field_provenance"]["roe"]["provenance"]["warnings"]
    assert "cvm_code_from_correction_table" not in avisos


def test_blocos_estruturados_da_referencia_ficam_fora_do_prompt():
    texto = SentinelaAI.__new__(SentinelaAI)._formatar_dados(
        {
            "ticker": "TSTA11",
            "setor": "Bancos",
            "acoes_por_unit": {"ON": 1, "PN": 2},
            "referencia_oficial": {"regra": "fca:codigo_ativo"},
        }
    )
    assert "setor: Bancos" in texto
    assert "acoes_por_unit" not in texto
    assert "referencia_oficial" not in texto


# ── carga uma vez por processo ───────────────────────────────────────────────

AGORA = datetime(2026, 10, 8, 12, tzinfo=UTC)


@pytest.fixture
def obter_contado(monkeypatch):
    chamadas = []

    def obter(agora, pasta):
        chamadas.append(agora)
        return _indice(_registro())

    monkeypatch.setattr(carga, "obter_indice", obter)
    return chamadas


def test_carga_uma_vez_dentro_do_ttl(obter_contado, tmp_path):
    ref = carga.ReferenciaOficial(tmp_path)
    primeiro = ref.indice(AGORA)
    assert ref.indice(AGORA + timedelta(days=6)) is primeiro
    assert len(obter_contado) == 1


def test_carga_recarrega_quando_o_ttl_vence(obter_contado, tmp_path):
    ref = carga.ReferenciaOficial(tmp_path)
    ref.indice(AGORA)
    ref.indice(AGORA + timedelta(days=7, seconds=1))
    assert len(obter_contado) == 2


def test_carga_em_threads_monta_uma_vez(monkeypatch, tmp_path):
    chamadas = []
    liberar = threading.Event()

    def obter_lento(agora, pasta):
        chamadas.append(agora)
        liberar.wait(1)
        return _indice(_registro())

    monkeypatch.setattr(carga, "obter_indice", obter_lento)
    ref = carga.ReferenciaOficial(tmp_path)
    resultados = []
    threads = [
        threading.Thread(target=lambda: resultados.append(ref.indice(AGORA)))
        for _ in range(5)
    ]
    for t in threads:
        t.start()
    liberar.set()
    for t in threads:
        t.join()
    assert len(chamadas) == 1
    assert len({id(r) for r in resultados}) == 1


@pytest.mark.parametrize(
    "erro",
    [OSError("sem rede"), ValueError("csv"), carga.CorrecaoInvalida("sem evidência")],
)
def test_carga_sem_indice_devolve_none_e_espera_para_tentar_de_novo(
    monkeypatch, tmp_path, caplog, erro
):
    chamadas = []

    def falha(agora, pasta):
        chamadas.append(agora)
        raise erro

    monkeypatch.setattr(carga, "obter_indice", falha)
    ref = carga.ReferenciaOficial(tmp_path)
    with caplog.at_level("WARNING"):
        assert ref.indice(AGORA) is None
    assert "indisponível" in caplog.text
    assert ref.indice(AGORA + timedelta(minutes=59)) is None
    assert len(chamadas) == 1
    assert ref.indice(AGORA + timedelta(hours=1)) is None
    assert len(chamadas) == 2


def test_carga_que_falha_no_recarregamento_mantem_o_indice_em_memoria(
    monkeypatch, tmp_path
):
    respostas = [_indice(_registro()), OSError("sem rede"), _indice(_registro("NOVA3"))]

    def obter(agora, pasta):
        resposta = respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    monkeypatch.setattr(carga, "obter_indice", obter)
    ref = carga.ReferenciaOficial(tmp_path)
    antigo = ref.indice(AGORA)
    vencido = AGORA + timedelta(days=8)
    assert ref.indice(vencido) is antigo
    assert ref.indice(vencido + timedelta(minutes=30)) is antigo
    novo = ref.indice(vencido + timedelta(hours=1))
    assert "NOVA3" in novo.registros


def test_carga_passa_o_instante_e_a_pasta_de_dados(monkeypatch, tmp_path):
    chamadas = []
    monkeypatch.setattr(
        carga,
        "obter_indice",
        lambda agora, pasta: chamadas.append((agora, pasta)) or None,
    )
    carga.ReferenciaOficial(tmp_path).indice(AGORA)
    assert chamadas == [(AGORA, tmp_path)]


def test_carga_recarrega_exatamente_no_fim_do_ttl(obter_contado, tmp_path):
    ref = carga.ReferenciaOficial(tmp_path)
    ref.indice(AGORA)
    ref.indice(AGORA + timedelta(days=7))
    assert len(obter_contado) == 2


# ── relatório do F1-12 ───────────────────────────────────────────────────────


def _fontes_do_relatorio(referencia):
    from tests.test_rastreabilidade import _acao, _contexto

    return dict(_contexto(_acao(referencia_oficial=referencia))["fontes"])


def test_relatorio_mostra_que_o_codigo_veio_da_tabela_de_correcoes():
    correcao = {
        "ticker": "CSNA3", "codigo_na_fonte": "4030", "arquivo": "fca_2026.csv",
        "coluna": "Codigo_Negociacao", "data": "2025-01-01",
    }  # fmt: skip
    fontes = _fontes_do_relatorio(
        {"regra": "correcao", "gerado_em": "2026-10-08", "correcao": correcao}
    )
    assert fontes["Referência oficial"] == (
        "correcao (índice de 2026-10-08); código da tabela de correções, não do arquivo "
        "da fonte: 4030 → CSNA3 (evidência: fca_2026.csv, Codigo_Negociacao, 2025-01-01)"
    )


def test_relatorio_sem_correcao_mostra_so_a_regra():
    fontes = _fontes_do_relatorio(
        {"regra": "fca:codigo_ativo", "gerado_em": "2026-10-08", "correcao": None}
    )
    assert fontes["Referência oficial"] == "fca:codigo_ativo (índice de 2026-10-08)"


def test_relatorio_sem_referencia_nao_tem_a_linha():
    assert "Referência oficial" not in _fontes_do_relatorio(None)


# ── F2A-31: dados da CVM só pela referência oficial ──────────────────────────


def test_sem_indice_a_cvm_nao_e_consultada_e_o_motivo_aparece(monkeypatch):
    cvm = CVMQueAnota(_cvm_ind())
    engine = _motor(monkeypatch, FakeReferencia(None), cvm)
    dados = engine.buscar_dados_ticker("PETR4")  # está em `cvm_ticker_map.py`
    assert cvm.codigos == []
    assert (
        "referência oficial indisponível: dados da CVM não consultados"
        in dados["riscos_dados"]
    )
    assert "ticker fora da cobertura da CVM" not in dados["riscos_dados"]
    assert dados["preco_atual"] == 20.0  # as outras fontes seguem
    assert "_sem_referencia" not in dados


def test_fii_sem_indice_nao_consulta_o_informe(monkeypatch):
    class _Informe:
        def __init__(self):
            self.cnpjs = []

        def obter_dados_fii(self, cnpj):
            self.cnpjs.append(cnpj)
            return {"valor_cota": 100.0}

    informe = _Informe()
    engine = _engine(
        monkeypatch,
        historico=_historico(90.0),
        info={"currentPrice": 90.0, "priceToBook": 1.5, "dividendYield": 9.0},
    )
    engine.cvm_fii = informe
    engine.referencia = FakeReferencia(None)
    dados = engine.buscar_dados_ticker("HGLG11")  # está em `cvm_fii_map.py`
    assert informe.cnpjs == []
    assert dados["pvp"] == 1.5
    assert "vpa" not in dados
