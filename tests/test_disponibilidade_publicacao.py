"""F3-3e, decisão 40 do Marcos (13/11/2026): numa data passada, a disponibilidade é a data de
publicação da fonte, não a data de coleta. Com as_of de hoje, nada muda.

- BPP do escopo (`valuation_engine._bpp_disponivel`) e DFP do Gordon
  (`CVMProvider.gordon_do_documento`): `DT_RECEB` antes do dia de D;
- Informe de FII (`rendimento_fii.entradas`): `Data_Entrega` de cada registro;
- proventos (`b3_proventos.proventos_ate`): aprovação e data com antes de D, na coleta mais
  recente;
- sem data de publicação legível, abstém; a coleta nunca a substitui.
"""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON
from test_proventos_benchmarks import _conferida, _precos, conn, relacao  # noqa: F401

import market_engine
from cvm_provider import CVMProvider
from sentinela.data import rendimento_fii as rf
from sentinela.data.providers import b3_proventos
from valuation_engine import _bpp_disponivel

D = datetime(2024, 6, 3, 15, tzinfo=UTC)  # meio-dia de 03/06/2024 em São Paulo


@pytest.mark.parametrize(
    ("entrega", "coleta", "publicacao", "esperado"),
    [
        (
            "2024-03-01",
            "2026-11-12T19:00:00+00:00",
            True,
            True,
        ),  # coletado hoje, entregue antes
        (
            "2024-03-01",
            "2026-11-12T19:00:00+00:00",
            False,
            False,
        ),  # hoje: a coleta conta
        ("2024-03-01", "2024-03-02T10:00:00+00:00", False, True),
        (
            "2024-06-03",
            "2024-06-01T10:00:00+00:00",
            True,
            False,
        ),  # entregue no dia de D
        (
            "2024-06-04",
            "2024-06-01T10:00:00+00:00",
            True,
            False,
        ),  # entregue depois de D
        (None, "2024-01-01T10:00:00+00:00", True, False),  # sem data de publicação
        ("ilegível", "2024-01-01T10:00:00+00:00", True, False),
        ("2024-03-01", None, True, True),  # a coleta não é critério na data passada
        ("2024-03-01", None, False, False),
    ],
)
def test_bpp_pela_entrega_na_data_passada(entrega, coleta, publicacao, esperado):
    prov = {"data_entrega": entrega, "data_coleta": coleta}
    assert _bpp_disponivel(prov, D, publicacao) is esperado
    assert _bpp_disponivel({}, D, publicacao) is False


@pytest.fixture
def documento(tmp_path, monkeypatch):
    fixture = json.loads(
        (
            Path(__file__).parent / "fixtures/contratos/dfp_2025_ambev_gordon.json"
        ).read_text()
    )  # DFP de 2025 entregue em 12/02/2026, coletada em 13/10/2026
    zip_path = tmp_path / "dfp_cia_aberta_2025.zip"
    with ZipFile(zip_path, "w") as z:
        for nome, texto in fixture["membros"].items():
            z.writestr(nome, texto.encode("latin-1"))
    instante = datetime.fromisoformat(fixture["data_coleta"]).timestamp()
    os.utime(zip_path, (instante, instante))
    p = CVMProvider(tmp_path / "cache")
    monkeypatch.setattr(p, "baixar_dfp", lambda ano: zip_path)
    ind = {"cvm_dt_refer": "2025-12-31", "cvm_versao": "1", "cnpj": "07.526.557/0001-00",
           "lucro_controladores": 15503400000.0}  # fmt: skip
    return p, ind


def test_gordon_pela_entrega_quando_coletado_depois_de_d(documento):
    p, ind = documento
    antes_da_coleta = datetime(
        2026, 3, 2, 15, tzinfo=UTC
    )  # entregue em 12/02, coletado em 13/10
    assert p.gordon_do_documento(23264, ind, antes_da_coleta) == {
        "abstencao": "disponibilidade histórica da DFP não demonstrada"
    }  # sem a marca da data passada, a coleta continua contando
    p.por_publicacao = True
    r = p.gordon_do_documento(23264, ind, antes_da_coleta)
    assert "abstencao" not in r and r["data_entrega"] == "2026-02-12"
    no_dia = p.gordon_do_documento(23264, ind, datetime(2026, 2, 12, 18, tzinfo=UTC))
    assert no_dia == {"abstencao": "disponibilidade histórica da DFP não demonstrada"}


def test_recorte_e_motor_historico_provam_pela_entrega():
    import cvm_provider
    from sentinela.services.historico import CVMProviderEm

    assert cvm_provider._Recorte.por_publicacao is True
    assert CVMProviderEm.por_publicacao is True
    assert getattr(CVMProvider, "por_publicacao", False) is False


def test_informe_sem_guarda_de_coleta_na_data_passada():
    dados = enriquecer_fii({"ticker": "TST11", "preco_atual": 100.0, "dy": 0.12})
    dados["informe_fii"]["proveniencia"] = None
    assert rf.entradas(dados, AS_OF_GORDON) == rf.Abstencao(rf.MOTIVO_COLETA_INFORME)
    dados["disponibilidade_por_publicacao"] = True
    resultado = rf.entradas(dados, AS_OF_GORDON)
    assert resultado != rf.Abstencao(rf.MOTIVO_COLETA_INFORME)


def test_informe_com_entrega_depois_de_d_continua_fora():
    dados = enriquecer_fii({"ticker": "TST11", "preco_atual": 100.0, "dy": 0.12})
    dados["disponibilidade_por_publicacao"] = True
    for registro in dados["informe_fii"]["registros"]:
        registro["Data_Entrega"] = "2026-12-31"  # depois do as_of
    resultado = rf.entradas(dados, AS_OF_GORDON)
    assert isinstance(resultado, rf.Abstencao)
    assert resultado != rf.Abstencao(rf.MOTIVO_COLETA_INFORME)


def test_proventos_pela_aprovacao_na_coleta_mais_recente(conn, relacao, tmp_path):  # noqa: F811
    b3_proventos.gravar_proventos(
        conn, _conferida(relacao, datetime(2026, 11, 12, 19, tzinfo=UTC)), 8133
    )  # coletado hoje
    _precos(conn, tmp_path, "20260922", "20260923")
    d = date(2026, 9, 24)
    assert b3_proventos.proventos_ate(conn, "LREN", d) == {
        "abstencao": b3_proventos.MOTIVO_PROVENTO_SEM_COLETA
    }
    lido = b3_proventos.proventos_ate(conn, "LREN", d, por_publicacao=True)
    (jcp,) = [p for p in lido["proventos"] if p["data_com"] == "2026-09-22"]
    assert jcp["data_ex"] == "2026-09-23"
    aprovado_depois = b3_proventos.proventos_ate(
        conn, "LREN", date(2026, 9, 17), por_publicacao=True
    )
    assert "2026-09-22" not in {
        p["data_com"]
        for p in aprovado_depois["proventos"] + aprovado_depois["sem_prova"]
    }  # aprovado em 17/09: em D = 17/09 ainda não existia


@pytest.mark.parametrize(("dia", "marca"), [(12, True), (13, False)])
def test_cascata_marca_so_a_data_passada(monkeypatch, dia, marca):
    monkeypatch.setattr(market_engine, "_hoje_sp", lambda: date(2026, 10, 13))
    motor = market_engine.MarketEngine.__new__(market_engine.MarketEngine)
    vistos = {}

    def referencia(ticker, dados):
        vistos.update(dados)
        dados["_sem_referencia"] = True

    motor._aplicar_referencia = referencia
    motor.asset_classifier = Mock()
    motor.asset_classifier.classify.return_value.value = "STOCK"
    for nome in ("_buscar_yfinance", "_buscar_brapi", "_buscar_cvm"):
        setattr(motor, nome, Mock(return_value=False))
    motor.buscar_dados_ticker("PETR4", as_of=datetime(2026, 10, dia, 15, tzinfo=UTC))
    assert ("disponibilidade_por_publicacao" in vistos) is marca
    if marca:
        assert vistos["disponibilidade_por_publicacao"] is True


@pytest.fixture
def relogio_em_utc():
    import time

    antes = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    try:
        yield
    finally:
        if antes is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = antes
        time.tzset()


@pytest.mark.parametrize("publicacao", [True, False])
def test_dia_de_d_e_o_de_sao_paulo_com_o_relogio_em_utc(relogio_em_utc, publicacao):
    noite = datetime(2024, 6, 4, 2, tzinfo=UTC)  # 23h de 03/06 em São Paulo
    prov = {"data_entrega": "2024-06-03", "data_coleta": "2024-06-01T10:00:00+00:00"}
    assert (
        _bpp_disponivel(prov, noite, publicacao) is False
    )  # entregue no próprio dia de D


def test_coleta_no_proprio_instante_vale_hoje():
    prov = {"data_entrega": "2024-03-01", "data_coleta": D.isoformat()}
    assert _bpp_disponivel(prov, D, False) is True


def test_sem_a_marca_o_padrao_e_a_regra_de_hoje():
    prov = {"data_entrega": "2024-03-01", "data_coleta": "2026-11-12T19:00:00+00:00"}
    assert _bpp_disponivel(prov, D) is False  # coletado depois de D: só a marca libera


# --- as outras guardas de coleta (revisão rodada 1 do F3-3e) --------------------------------


def test_gordon_entradas_pela_entrega_quando_coletado_depois():
    from test_gordon_cvm import _dados

    from sentinela.data import gordon_cvm

    d = _dados()
    for prov in (
        d["gordon_cvm"]["proveniencia"],
        d["base_acionaria_gordon"]["proveniencia"],
    ):
        prov["data_coleta"] = "2026-11-12T19:00:00+00:00"  # coletado depois do as_of
    instante = datetime(2026, 10, 20, 18, tzinfo=UTC)
    assert gordon_cvm.entradas(d, instante) == gordon_cvm.Abstencao(
        "evidência da DFP posterior ao as_of"
    )
    assert gordon_cvm.entradas(d, date(2026, 10, 20)) == gordon_cvm.Abstencao(
        "evidência da DFP posterior ao as_of"
    )
    d["disponibilidade_por_publicacao"] = True
    assert isinstance(gordon_cvm.entradas(d, instante), dict)
    assert isinstance(gordon_cvm.entradas(d, date(2026, 10, 20)), dict)
    d["gordon_cvm"]["proveniencia"]["data_entrega"] = (
        "2026-10-20"  # entregue no dia de D
    )
    assert gordon_cvm.entradas(d, instante) == gordon_cvm.Abstencao(
        "evidência da DFP posterior ao as_of"
    )


def test_janelas_pela_entrega_quando_coletado_depois():
    from test_janelas_fundamentais import AS_OF, dados_exemplo

    from sentinela.data.janelas_fundamentais import entradas

    d = dados_exemplo()
    for e in d["serie_cvm"]["exercicios"]:
        e["proveniencia"]["data_coleta"] = "2026-11-12T19:00:00+00:00"
    d["ipca_serie"]["coleta"] = "2026-11-12T19:00:00+00:00"
    assert "abstencao" in entradas(d, AS_OF)["graham"]
    d["disponibilidade_por_publicacao"] = True
    assert "abstencao" not in entradas(d, AS_OF)["graham"]
    d["serie_cvm"]["exercicios"][-1]["proveniencia"]["data_coleta"] = (
        "2026-03-01T12:00:00"
    )
    assert (
        "abstencao" in entradas(d, AS_OF)["graham"]
    )  # coleta sem fuso continua recusada


def _janelas_sem_reconciliacao(coleta):
    """O caminho de produção: sem `reconciliacao_serie`, o fator vem de `fatores_da_relacao`."""
    from test_janelas_fundamentais import dados_exemplo

    d = dados_exemplo()
    d.pop("reconciliacao_serie")
    for e in d["serie_cvm"]["exercicios"]:
        e["acoes"] = 100
        e["proveniencia"]["data_coleta"] = coleta
    return d


def test_janelas_pelo_ramo_documental_quando_coletado_depois():
    from test_janelas_fundamentais import AS_OF

    from sentinela.data.janelas_fundamentais import entradas

    d = _janelas_sem_reconciliacao("2026-11-12T19:00:00+00:00")
    assert entradas(d, AS_OF)["graham"]["abstencao"] == (
        "fator oficial B3 indisponível: coleta sem fuso ou posterior ao as_of"
    )
    d["disponibilidade_por_publicacao"] = True
    assert entradas(d, AS_OF)["graham"]["lpa"] == pytest.approx(3.2)
    d["serie_cvm"]["exercicios"][0]["proveniencia"]["data_coleta"] = (
        "2026-03-01T12:00:00"
    )
    assert "sem fuso" in entradas(d, AS_OF)["graham"]["abstencao"]


def test_fator_da_relacao_b3_mantem_a_guarda_de_coleta():
    """DD-65: a reconciliação da relação corrente da B3 traria eventos posteriores a D."""
    from test_janelas_fundamentais import AS_OF, dados_exemplo

    from sentinela.data.janelas_fundamentais import entradas

    d = dados_exemplo()
    d["serie_cvm"]["exercicios"][0]["acoes"] = 50  # base incompatível: exige o fator B3
    d["reconciliacao_serie"]["coleta"] = "2026-11-12T19:00:00+00:00"
    d["disponibilidade_por_publicacao"] = True
    assert (
        entradas(d, AS_OF)["graham"]["abstencao"]
        == "coleta sem fuso ou posterior ao as_of"
    )


def test_qualidade_pela_entrega_quando_coletado_depois():
    from test_qualidade import AS_OF, documentos

    from sentinela.methods.qualidade import Qualidade

    docs = documentos()
    for e in docs:
        e["proveniencia"]["data_coleta"] = "2026-11-12T19:00:00+00:00"
        if isinstance(e.get("distribuicao"), dict):
            e["distribuicao"]["coleta"] = "2026-11-12T19:00:00+00:00"
    hoje = Qualidade().calcular(docs, as_of=AS_OF, classe="STOCK", modelo="empresa")
    passado = Qualidade().calcular(
        docs, as_of=AS_OF, classe="STOCK", modelo="empresa", por_publicacao=True
    )
    assert hoje["lucros"]["observados"] == 0 and hoje["proventos"]["observados"] == 0
    assert (
        passado["lucros"]["observados"] == 5 and passado["proventos"]["observados"] == 5
    )
    assert passado["cobertura"] == {"observados": 5, "esperados": 5, "completa": True}
    # a distribuição vem da relação corrente da B3 e mantém a guarda de coleta (DD-65)
    for e in docs:
        e["proventos_b3"]["coleta"] = "2026-11-12T19:00:00+00:00"
    sem_distribuicao = Qualidade().calcular(
        docs, as_of=AS_OF, classe="STOCK", modelo="empresa", por_publicacao=True
    )
    assert sem_distribuicao["proventos"]["observados"] == 0
    assert sem_distribuicao["lucros"]["observados"] == 5


def test_composicao_recente_pela_entrega_quando_coletada_depois(tmp_path, monkeypatch):
    cnpj = "11.111.111/0001-11"
    p = CVMProvider(tmp_path / "cache")
    arquivo = tmp_path / "dfp_2025.zip"
    with ZipFile(arquivo, "w") as z:
        z.writestr(
            "dfp_cia_aberta_2025.csv",
            f"CNPJ_CIA;DT_REFER;VERSAO;DT_RECEB\n{cnpj};2025-12-31;1;2026-02-12\n",
        )
        z.writestr("dfp_cia_aberta_composicao_capital_2025.csv",
                   "CNPJ_CIA;DT_REFER;VERSAO;QT_ACAO_ORDIN_CAP_INTEGR;QT_ACAO_PREF_CAP_INTEGR;"
                   "QT_ACAO_TOTAL_CAP_INTEGR;QT_ACAO_ORDIN_TESOURO;QT_ACAO_PREF_TESOURO;"
                   f"QT_ACAO_TOTAL_TESOURO\n{cnpj};2025-12-31;1;1000;0;1000;0;0;0\n")  # fmt: skip
    coletado_hoje = datetime(2026, 11, 12, 19, tzinfo=UTC).timestamp()
    os.utime(arquivo, (coletado_hoje, coletado_hoje))
    monkeypatch.setattr(p, "baixar_dfp", lambda ano: arquivo)
    itr = tmp_path / "itr_vazio.zip"
    with ZipFile(itr, "w") as z:  # ITR do ano sem entrega da companhia
        z.writestr("itr_cia_aberta_2026.csv", "CNPJ_CIA;DT_REFER;VERSAO;DT_RECEB\n")
    os.utime(itr, (coletado_hoje, coletado_hoje))
    monkeypatch.setattr(p, "baixar_itr", lambda ano: itr)
    as_of = datetime(2026, 10, 20, 18, tzinfo=UTC)
    assert p.composicao_mais_recente(cnpj, as_of, 2025) == {
        "abstencao": "composição recente com coleta posterior ao as_of"
    }
    p.por_publicacao = True
    r = p.composicao_mais_recente(cnpj, as_of, 2025)
    assert (
        r["composicao"].total == 1000
        and r["proveniencia"]["data_entrega"] == "2026-02-12"
    )


def test_janelas_sem_a_marca_recusam_com_o_motivo():
    from test_janelas_fundamentais import AS_OF, dados_exemplo

    from sentinela.data import janelas_fundamentais as jf

    d = dados_exemplo()
    for e in d["serie_cvm"]["exercicios"]:
        e["proveniencia"]["data_coleta"] = "2026-11-12T19:00:00+00:00"
    assert (
        jf.entradas(d, AS_OF)["graham"]["abstencao"]
        == "coleta sem fuso ou posterior ao as_of"
    )
    registro = {"fonte": "B3", "coleta": "2026-11-12T19:00:00+00:00"}
    with pytest.raises(ValueError, match="^coleta sem fuso ou posterior ao as_of$"):
        jf._fonte(registro, AS_OF)  # o padrão é a regra de hoje
    jf._fonte(registro, AS_OF, por_publicacao=True)
    exercicios = [{"acoes": 100}, {"acoes": 50}]
    reconciliacao = {"fonte": "B3", "coleta": "2026-11-12T19:00:00+00:00"}
    with pytest.raises(ValueError, match="^coleta sem fuso ou posterior ao as_of$"):
        jf.fatores_da_base(
            exercicios, reconciliacao, AS_OF
        )  # o padrão é a regra de hoje
