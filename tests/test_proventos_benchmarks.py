"""F3-7a: proventos em dinheiro e benchmarks por data no banco único.

Fixtures oficiais: as respostas do CompanyCall da Lojas Renner (contrato D18,
`b3_proventos_lren_2026.json`, 99 registros); as respostas inteiras do GetPortfolioDay do IBOV
de 2024 e 2025 (`b3_ibov_2024_2025.json`) e um recorte do SGS 12 de 11/2024 a 02/2025
(`bcb_sgs12_2024_2025.json`), coletados no L1. Pregões em registro 01 do COTAHIST.
"""

import dataclasses
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from test_eventos_societarios import COLETA, _obter, _precos

from sentinela.data import macro_por_data, proventos_b3
from sentinela.data.macro_por_data import Observacao
from sentinela.data.providers import b3_indices, b3_proventos, macro
from sentinela.data.store import migracoes

CONTRATOS = Path(__file__).parent / "fixtures" / "contratos"
COLETA_IBOV = datetime(2026, 11, 11, 14, 28, tzinfo=UTC)


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


@pytest.fixture
def relacao():
    return b3_proventos.coletar(8133, COLETA, _obter())


def _conferida(relacao, coleta=COLETA):
    """A mesma relação oficial com a identidade dada por conferida (o caso real é PN, DD-06)."""
    return dataclasses.replace(relacao, identidade=None, coleta=coleta.isoformat())


# --- Proventos ----------------------------------------------------------------------------


def test_relacao_oficial_gravada_com_a_pagina_e_a_coleta(conn, relacao):
    resumo = b3_proventos.gravar_proventos(conn, relacao, 8133)
    assert resumo == {"inseridos": 99, "repetidos": 0, "duplicados_na_coleta": 0}
    (coleta,) = conn.execute(
        "SELECT emissor, cd_cvm, nome_pregao, total, registros, identidade, fonte "
        "FROM proventos_coletas"
    ).fetchall()
    assert coleta[:5] == ("LREN", "8133", "LOJAS RENNER", 99, 99)
    assert (
        coleta[5] == relacao.identidade and coleta[5] is not None
    )  # PN sem ISIN (DD-06)
    assert "GetDetail" in coleta[6]
    jcp = conn.execute(
        "SELECT especie, natureza, data_com, aprovacao, valor_bruto, cotado_por, fonte, "
        "hash_sha256 FROM proventos WHERE data_com = '2026-09-22' AND especie = 'ON'"
    ).fetchone()
    assert jcp[:6] == (
        "ON",
        "JRS CAP PROPRIO",
        "2026-09-22",
        "2026-09-17",
        "0,240666",
        "1",
    )
    assert "GetListedCashDividends" in jcp[6] and jcp[7] == relacao.fontes[1]["sha256"]


def test_nova_coleta_repete_os_registros_e_grava_a_coleta(conn, relacao):
    b3_proventos.gravar_proventos(conn, relacao, 8133)
    depois = _conferida(relacao, datetime(2026, 10, 25, tzinfo=UTC))
    assert b3_proventos.gravar_proventos(conn, depois, 8133) == {
        "inseridos": 0,
        "repetidos": 99,
        "duplicados_na_coleta": 0,
    }
    assert conn.execute("SELECT COUNT(*) FROM proventos_coletas").fetchone() == (2,)
    assert conn.execute("SELECT COUNT(*) FROM proventos_vistos").fetchone() == (198,)
    with pytest.raises(
        sqlite3.IntegrityError, match="proventos_coletas é só de inserção"
    ):
        b3_proventos.gravar_proventos(conn, depois, 8133)
    assert conn.in_transaction is False or conn.execute(
        "SELECT COUNT(*) FROM proventos_coletas"
    ).fetchone() == (2,)


def test_proventos_ate_com_a_data_ex_do_calendario(conn, relacao, tmp_path):
    b3_proventos.gravar_proventos(conn, _conferida(relacao), 8133)
    _precos(conn, tmp_path, "20260922", "20260923")
    lido = b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 21))
    assert lido["coleta"] == COLETA.isoformat()
    (jcp,) = [p for p in lido["proventos"] if p["data_com"] == "2026-09-22"]
    assert jcp["data_ex"] == "2026-09-23" and jcp["valor_bruto"] == "0,240666"
    sem = {p["data_com"] for p in lido["sem_prova"]}
    assert "2026-06-23" in sem  # sem pregões guardados em volta
    assert {p["motivo"] for p in lido["sem_prova"]} == {
        b3_proventos.MOTIVO_SEM_CALENDARIO
    }
    assert b3_proventos.proventos_ate(conn, "LREN", date(2026, 9, 23)) == {
        "abstencao": b3_proventos.MOTIVO_PROVENTO_SEM_COLETA
    }  # a coleta de 20/10 ainda não existia em 23/09


def test_aprovacao_e_data_com_em_d_ou_depois_ficam_de_fora(conn, relacao, tmp_path):
    b3_proventos.gravar_proventos(
        conn, _conferida(relacao, datetime(2026, 9, 1, tzinfo=UTC)), 8133
    )
    _precos(conn, tmp_path, "20260922", "20260923")

    def datas_com(dia):
        lido = b3_proventos.proventos_ate(conn, "LREN", dia)
        return {p["data_com"] for p in lido["proventos"] + lido["sem_prova"]}

    assert "2026-09-22" not in datas_com(date(2026, 9, 17))  # aprovado em 17/09
    assert "2026-09-22" not in datas_com(date(2026, 9, 22))  # data com em D
    no_dia = b3_proventos.proventos_ate(conn, "LREN", date(2026, 9, 23))
    (jcp,) = [p for p in no_dia["sem_prova"] if p["data_com"] == "2026-09-22"]
    assert jcp["motivo"] == b3_proventos.MOTIVO_SEM_CALENDARIO  # data ex é o próprio D
    depois = b3_proventos.proventos_ate(conn, "LREN", date(2026, 9, 24))
    (jcp,) = [p for p in depois["proventos"] if p["data_com"] == "2026-09-22"]
    assert jcp["data_ex"] == "2026-09-23"


def test_proventos_ate_abstem_sem_coleta_identidade_ou_completa(conn, relacao):
    assert b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 21)) == {
        "abstencao": b3_proventos.MOTIVO_PROVENTO_SEM_COLETA
    }
    b3_proventos.gravar_proventos(conn, relacao, 8133)
    lido = b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 21))
    assert lido == {
        "abstencao": f"{b3_proventos.MOTIVO_PROVENTO_IDENTIDADE}: {relacao.identidade}"
    }
    incompleta = dataclasses.replace(
        _conferida(relacao, datetime(2026, 10, 22, 12, tzinfo=UTC)), total=100
    )
    b3_proventos.gravar_proventos(conn, incompleta, 8133)
    assert b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 24)) == {
        "abstencao": b3_proventos.MOTIVO_PROVENTO_INCOMPLETA
    }
    # a coleta de 22/10 (9h em São Paulo) ainda não vale em 22/10: fica a de 20/10
    assert "abstencao" in b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 22))
    assert b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 22))[
        "abstencao"
    ].startswith(b3_proventos.MOTIVO_PROVENTO_IDENTIDADE)


def test_coleta_no_dia_de_d_em_sao_paulo_nao_vale(conn, relacao):
    tarde = datetime(2026, 10, 21, 2, 30, tzinfo=UTC)  # 20/10 23h30 em São Paulo
    b3_proventos.gravar_proventos(conn, _conferida(relacao, tarde), 8133)
    assert "proventos" in b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 21))
    assert b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 20)) == {
        "abstencao": b3_proventos.MOTIVO_PROVENTO_SEM_COLETA
    }


def test_registro_visto_so_em_coleta_posterior_fica_de_fora(conn, relacao):
    primeira = dataclasses.replace(
        _conferida(relacao), registros=relacao.registros[1:], total=98
    )
    b3_proventos.gravar_proventos(conn, primeira, 8133)
    segunda = _conferida(relacao, datetime(2026, 10, 25, tzinfo=UTC))
    b3_proventos.gravar_proventos(conn, segunda, 8133)
    novo = relacao.registros[0]["lastDatePriorEx"]  # 22/09/2026
    lido = b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 24))
    assert "2026-09-22" not in {p["data_com"] for p in lido["sem_prova"]}
    depois = b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 26))
    assert "2026-09-22" in {p["data_com"] for p in depois["sem_prova"]} and novo


def test_registro_com_data_ilegivel_fica_sem_prova(conn, relacao):
    estranho = dict(relacao.registros[0], lastDatePriorEx="", dateApproval="31/02/2026")
    b3_proventos.gravar_proventos(
        conn,
        dataclasses.replace(_conferida(relacao), registros=(estranho,), total=1),
        8133,
    )
    lido = b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 21))
    assert [p["motivo"] for p in lido["sem_prova"]] == [
        b3_proventos.MOTIVO_PROVENTO_SEM_DATAS
    ]
    assert lido["proventos"] == []


def test_fonte_fora_das_paginas_recusa_sem_gravar(conn, relacao):
    torta = dataclasses.replace(relacao, fontes=(relacao.fontes[0], relacao.fontes[-1]))
    with pytest.raises(ValueError, match="as fontes da coleta não seguem as páginas"):
        b3_proventos.gravar_proventos(conn, torta, 8133)
    assert conn.execute("SELECT COUNT(*) FROM proventos_coletas").fetchone() == (0,)
    assert conn.in_transaction is False


def test_proventos_ate_recusa_instante(conn):
    with pytest.raises(
        TypeError, match=r"^proventos_ate recebe o dia local de D \(date\)"
    ):
        b3_proventos.proventos_ate(conn, "LREN", datetime(2026, 10, 21, tzinfo=UTC))


# --- Ibovespa -----------------------------------------------------------------------------


def _ibov():
    return json.loads(
        (CONTRATOS / "b3_ibov_2024_2025.json").read_text(encoding="utf-8")
    )


URLS_IBOV = {
    "GetPortfolioDay_2024.json": b3_indices.url(2024),
    "GetPortfolioDay_2025.json": b3_indices.url(2025),
}


def _obter_ibov(endereco):
    for nome, texto in _ibov()["membros"].items():
        if URLS_IBOV[nome] == endereco:
            corpo = texto.encode("utf-8")
            return json.loads(corpo), {
                "url": endereco, "bytes": len(corpo), "sha256": hashlib.sha256(corpo).hexdigest()
            }  # fmt: skip
    raise AssertionError(endereco)


def test_url_oficial_do_l1():
    assert b3_indices.url(2024) == _ibov()["fonte"]
    assert b3_indices.url(2025) in _ibov()["recorte"]


def test_fechamentos_oficiais_do_ano():
    fechamentos, fonte = b3_indices.coletar(2024, _obter_ibov)
    assert fonte["sha256"] == _ibov()["sha256_original"]
    assert len(fechamentos) == 251  # dias com fechamento no L1
    assert fechamentos[0][0] == date(2024, 1, 2) and fechamentos[-1][0] == date(
        2024, 12, 30
    )
    assert all(isinstance(t, str) and v > 0 for _, t, v in fechamentos)
    _, texto, valor = fechamentos[-1]
    assert valor == float(texto.replace(".", "").replace(",", "."))


@pytest.mark.parametrize(
    ("corpo", "mensagem"),
    [([], "fora do leiaute"), ({"results": [{"day": "1"}]}, "dia ilegível"),
     ({"results": [{"day": 1, "rateValue1": 10}]}, "fechamento ilegível")],
)  # fmt: skip
def test_leiaute_fora_recusa(corpo, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        b3_indices.ler(corpo, 2024)


def test_ibovespa_gravado_e_lido_ate_d(conn):
    for ano in (2024, 2025):
        fechamentos, fonte = b3_indices.coletar(ano, _obter_ibov)
        resumo = b3_indices.gravar_ibovespa(conn, fechamentos, fonte, COLETA_IBOV)
        assert resumo["inseridos"] == len(fechamentos) and resumo["repetidos"] == 0
    fechamentos, fonte = b3_indices.coletar(2024, _obter_ibov)
    assert (
        b3_indices.gravar_ibovespa(conn, fechamentos, fonte, COLETA_IBOV)["repetidos"]
        == 251
    )
    lido = b3_indices.benchmarks_ate(conn, "IBOV", date(2025, 1, 2))
    assert lido[-1]["data"] == "2024-12-30"  # o pregão de D não conta
    assert (
        lido[-1]["fonte"] == b3_indices.url(2024)
        and lido[-1]["coleta"] == COLETA_IBOV.isoformat()
    )
    with pytest.raises(sqlite3.IntegrityError, match="benchmarks é só de inserção"):
        conn.execute("DELETE FROM benchmarks")


def test_mesma_data_de_coletas_diferentes_vale_a_mais_recente(conn):
    fonte_a = {"url": "a", "sha256": "1"}
    fonte_b = {"url": "b", "sha256": "2"}
    dia = date(2024, 12, 30)
    b3_indices.gravar_ibovespa(conn, [(dia, "1,00", 1.0)], fonte_b, COLETA_IBOV)
    b3_indices.gravar_ibovespa(
        conn, [(dia, "2,00", 2.0)], fonte_a, datetime(2026, 11, 11, 12, tzinfo=UTC)
    )
    (lido,) = b3_indices.benchmarks_ate(conn, "IBOV", date(2025, 1, 1))
    assert (lido["valor"], lido["fonte"]) == (1.0, "b")


def test_gravacao_exige_fuso_e_leitura_exige_dia(conn):
    with pytest.raises(ValueError, match="coleta exige fuso"):
        b3_indices.gravar_ibovespa(
            conn,
            [],
            {"url": "a", "sha256": "1"},
            datetime(2026, 1, 1),  # noqa: DTZ001
        )
    with pytest.raises(TypeError, match="dia local de D"):
        b3_indices.benchmarks_ate(conn, "IBOV", datetime(2026, 1, 1, tzinfo=UTC))


# --- CDI (SGS 12) e o fechamento mensal (DD-36) ---------------------------------------------


class _ProvedorSGS:
    def __init__(self, fonte=None):
        self.fx = json.loads(
            (CONTRATOS / "bcb_sgs12_2024_2025.json").read_text(encoding="utf-8")
        )
        self.fonte = fonte or self.fx["fonte"]
        self.pedidos = []

    def serie_sgs(self, serie, fim, instante):
        self.pedidos.append((serie, fim, instante))
        observacoes = macro_por_data.ler_sgs(self.fx["membros"]["sgs12_2024_2025.json"])
        return {
            "observacoes": observacoes,
            "coleta": instante.date(),
            "proveniencia": [
                {"fonte": self.fonte, "hash_sha256": self.fx["sha256_original"]}
            ],
        }


def test_cdi_gravado_com_a_janela_que_o_devolveu(conn):
    provedor = _ProvedorSGS()
    resumo = macro.gravar_cdi(conn, provedor, date(2025, 2, 28), COLETA_IBOV)
    assert resumo == {"inseridos": 82, "repetidos": 0}
    assert provedor.pedidos == [(12, date(2025, 2, 28), COLETA_IBOV)]
    linha = conn.execute(
        "SELECT valor, valor_texto, fonte, coleta, hash_sha256 FROM benchmarks "
        "WHERE serie = 'CDI' AND data = '2024-12-31'"
    ).fetchone()
    assert linha == (
        0.045513, "0.045513", provedor.fonte, COLETA_IBOV.isoformat(),
        provedor.fx["sha256_original"],
    )  # fmt: skip
    assert (
        macro.gravar_cdi(conn, provedor, date(2025, 2, 28), COLETA_IBOV)["repetidos"]
        == 82
    )


def test_cdi_fora_da_janela_ou_abstido_recusa(conn):
    fora = _ProvedorSGS(
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json"
        "&dataInicial=01/01/2025&dataFinal=28/02/2025"
    )
    with pytest.raises(
        ValueError, match="CDI: observação de 2024-11-01 sem janela única"
    ):
        macro.gravar_cdi(conn, fora, date(2025, 2, 28), COLETA_IBOV)
    assert conn.execute("SELECT COUNT(*) FROM benchmarks").fetchone() == (0,)

    class Abstido:
        def serie_sgs(self, *a):
            return {"abstencao": "fonte fora do ar"}

    with pytest.raises(ValueError, match="fonte fora do ar"):
        macro.gravar_cdi(conn, Abstido(), date(2025, 2, 28), COLETA_IBOV)
    with pytest.raises(ValueError, match="coleta exige fuso"):
        macro.gravar_cdi(conn, _ProvedorSGS(), date(2025, 2, 28), datetime(2026, 1, 1))  # noqa: DTZ001


def test_mensal_fecha_no_ultimo_pregao_e_acumula_o_cdi_ate_ele(conn):
    for ano in (2024, 2025):
        fechamentos, fonte = b3_indices.coletar(ano, _obter_ibov)
        b3_indices.gravar_ibovespa(conn, fechamentos, fonte, COLETA_IBOV)
    macro.gravar_cdi(conn, _ProvedorSGS(), date(2025, 2, 28), COLETA_IBOV)
    d = date(2025, 3, 1)
    ibov = [
        o
        for o in b3_indices.benchmarks_ate(conn, "IBOV", d)
        if o["data"] >= "2024-11-01"
    ]
    meses = b3_indices.mensal(ibov, b3_indices.benchmarks_ate(conn, "CDI", d))
    assert [(m["mes"], m["data"]) for m in meses] == [
        ("2024-11", "2024-11-29"), ("2024-12", "2024-12-30"), ("2025-01", "2025-01-31"),
        ("2025-02", "2025-02-28"),
    ]  # fmt: skip
    assert "fator_cdi" not in meses[0]  # ponto de partida
    cdi = {o["data"]: o["valor"] for o in b3_indices.benchmarks_ate(conn, "CDI", d)}
    # Fator DI: do fechamento anterior, inclusive, ao do mês, exclusive (DD-55)
    dezembro = [v for k, v in cdi.items() if "2024-11-29" <= k < "2024-12-30"]
    janeiro = [v for k, v in cdi.items() if "2024-12-30" <= k < "2025-01-31"]
    assert "2024-12-31" in cdi  # o dia útil sem pregão fica no período de janeiro
    produto = 1.0
    for v in dezembro:
        produto *= 1 + v / 100
    assert meses[1]["fator_cdi"] == pytest.approx(produto, rel=1e-15)
    produto = 1.0
    for v in janeiro:
        produto *= 1 + v / 100
    assert meses[2]["fator_cdi"] == pytest.approx(produto, rel=1e-15)
    assert (
        len(janeiro) == len([k for k in cdi if "2025-01-01" <= k <= "2025-01-31"]) + 1
    )


def test_mes_sem_cdi_ou_com_pregao_sem_cdi_fica_sem_fator():
    ibov = [
        {"data": "2024-11-29", "valor": 1.0},
        {"data": "2024-12-02", "valor": 1.5},
        {"data": "2024-12-30", "valor": 2.0},
    ]
    (_, sem) = b3_indices.mensal(ibov, [{"data": "2024-12-30", "valor": 0.04}])
    assert (
        sem["motivo_cdi"] == b3_indices.MOTIVO_CDI_SEM_IBOV and "fator_cdi" not in sem
    )
    (_, falta) = b3_indices.mensal(ibov, [{"data": "2024-11-29", "valor": 0.04}])
    assert (
        falta["motivo_cdi"] == b3_indices.MOTIVO_CDI_INCOMPLETO
        and "fator_cdi" not in falta
    )
    cdi = [{"data": d, "valor": 0.04} for d in ("2024-11-29", "2024-12-02")]
    (_, ok) = b3_indices.mensal(
        list(reversed(ibov)), cdi
    )  # a ordem da entrada não importa
    assert (
        ok["fator_cdi"] == pytest.approx(1.0004**2, rel=1e-15)
        and ok["data"] == "2024-12-30"
    )


# --- Bordas (mutação) ---------------------------------------------------------------------


def test_registro_da_segunda_pagina_leva_a_fonte_dela(conn, relacao):
    muitos = tuple(dict(relacao.registros[0], valueCash=f"{i},00") for i in range(121))
    paginas = (
        relacao.fontes[0],
        {"url": "GetListedCashDividends/p1", "sha256": "p1"},
        {"url": "GetListedCashDividends/p2", "sha256": "p2"},
        relacao.fontes[-1],
    )
    longa = dataclasses.replace(
        _conferida(relacao), registros=muitos, total=None, fontes=paginas
    )
    assert b3_proventos.gravar_proventos(conn, longa, 8133)["inseridos"] == 121
    fontes = conn.execute(
        "SELECT valor_bruto, fonte, hash_sha256, cd_cvm FROM proventos "
        "WHERE valor_bruto IN ('0,00', '119,00', '120,00') ORDER BY valor_bruto"
    ).fetchall()
    assert fontes == [
        ("0,00", "GetListedCashDividends/p1", "p1", "8133"),
        ("119,00", "GetListedCashDividends/p1", "p1", "8133"),
        ("120,00", "GetListedCashDividends/p2", "p2", "8133"),
    ]
    assert conn.execute("SELECT total, isins_json FROM proventos_coletas").fetchone() == (
        None, json.dumps(list(relacao.isins)),
    )  # fmt: skip
    texto = json.dumps(muitos[0], ensure_ascii=False, sort_keys=True)
    assert conn.execute(
        "SELECT linha_sha256, linha_json FROM proventos WHERE valor_bruto = '0,00'"
    ).fetchone() == (hashlib.sha256(texto.encode("utf-8")).hexdigest(), texto)


def test_fonte_fora_das_paginas_mensagem_inteira(conn, relacao):
    torta = dataclasses.replace(relacao, fontes=(relacao.fontes[0], relacao.fontes[-1]))
    with pytest.raises(
        ValueError, match=r"^as fontes da coleta não seguem as páginas da relação$"
    ):
        b3_proventos.gravar_proventos(conn, torta, 8133)


def test_coleta_mais_recente_pelo_instante_e_nao_pelo_texto(conn, relacao):
    conferida = _conferida(relacao)
    b3_proventos.gravar_proventos(
        conn, dataclasses.replace(conferida, coleta="2026-10-20T23:00:00-03:00"), 8133
    )  # 21/10 02h UTC: a mais recente
    incompleta = dataclasses.replace(
        conferida, coleta="2026-10-21T01:00:00+00:00", total=100
    )
    b3_proventos.gravar_proventos(conn, incompleta, 8133)
    assert "proventos" in b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 22))


def test_todos_os_registros_conhecidos_saem_inteiros(conn, relacao, tmp_path):
    b3_proventos.gravar_proventos(conn, _conferida(relacao), 8133)
    _precos(conn, tmp_path, "20260922", "20260923")
    lido = b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 21))
    esperados = [
        r for r in relacao.registros
        if (com := proventos_b3.ler_data(r.get("lastDatePriorEx")))
        and (apr := proventos_b3.ler_data(r.get("dateApproval")))
        and com < date(2026, 10, 21) and apr < date(2026, 10, 21)
    ]  # fmt: skip
    assert len(lido["proventos"]) + len(lido["sem_prova"]) == len(esperados) > 2
    (jcp,) = [p for p in lido["proventos"] if p["data_com"] == "2026-09-22"]
    texto = json.dumps(relacao.registros[0], ensure_ascii=False, sort_keys=True)
    assert jcp == {
        "especie": "ON", "natureza": "JRS CAP PROPRIO", "data_com": "2026-09-22",
        "aprovacao": "2026-09-17", "valor_bruto": "0,240666", "cotado_por": "1",
        "fonte": relacao.fontes[1]["url"], "hash_sha256": relacao.fontes[1]["sha256"],
        "linha_sha256": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
        "data_ex": "2026-09-23",
    }  # fmt: skip


def test_aprovacao_no_dia_de_d_e_data_com_parcial(conn, relacao, tmp_path):
    base = relacao.registros[0]
    registros = (
        dict(base, dateApproval="21/10/2026", lastDatePriorEx="22/09/2026"),
        dict(base, dateApproval="17/09/2026", lastDatePriorEx="", valueCash="9,9"),
        dict(base, dateApproval="xx", lastDatePriorEx="22/09/2026", valueCash="8,8"),
        dict(base, valueCash="7,7"),
    )
    b3_proventos.gravar_proventos(
        conn,
        dataclasses.replace(_conferida(relacao), registros=registros, total=4),
        8133,
    )
    _precos(conn, tmp_path, "20260922", "20260923")
    lido = b3_proventos.proventos_ate(conn, "LREN", date(2026, 10, 21))
    assert sorted(p["valor_bruto"] for p in lido["sem_prova"]) == ["8,8", "9,9"]
    assert [p["valor_bruto"] for p in lido["proventos"]] == [
        "7,7"
    ]  # o de 21/10 fica fora


def test_janelas_do_sgs_nas_bordas_e_url_ilegivel(conn):
    base = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json"

    class Duas(_ProvedorSGS):
        def serie_sgs(self, serie, fim, instante):
            dados = super().serie_sgs(serie, fim, instante)
            dados["proveniencia"] = [
                {"fonte": f"{base}&dataInicial=01/11/2024&dataFinal=31/12/2024", "hash_sha256": "a"},
                {"fonte": f"{base}&dataInicial=01/01/2025&dataFinal=28/02/2025", "hash_sha256": "b"},
            ]  # fmt: skip
            return dados

    macro.gravar_cdi(conn, Duas(), date(2025, 2, 28), COLETA_IBOV)
    donos = dict(
        conn.execute("SELECT data, hash_sha256 FROM benchmarks WHERE serie = 'CDI'")
    )
    assert (donos["2024-11-01"], donos["2024-12-31"], donos["2025-01-02"]) == (
        "a",
        "a",
        "b",
    )
    assert donos["2025-02-28"] == "b"
    inteira = _ProvedorSGS(base)  # sem janela: a série inteira numa chamada
    assert (
        macro.gravar_cdi(conn, inteira, date(2025, 2, 28), COLETA_IBOV)["inseridos"]
        == 82
    )
    for meia in (f"{base}&dataInicial=01/11/2024", f"{base}&dataFinal=28/02/2025"):
        with pytest.raises(
            ValueError,
            match=rf"^CDI: janela ilegível na fonte {meia}$".replace("?", r"\?"),
        ):
            macro.gravar_cdi(conn, _ProvedorSGS(meia), date(2025, 2, 28), COLETA_IBOV)

    class SemProv(_ProvedorSGS):
        def serie_sgs(self, *a):
            return super().serie_sgs(*a) | {"proveniencia": []}

    with pytest.raises(ValueError, match=r"^CDI sem proveniência da coleta$"):
        macro.gravar_cdi(conn, SemProv(), date(2025, 2, 28), COLETA_IBOV)
    with pytest.raises(ValueError, match=r"^coleta exige fuso horário$"):
        macro.gravar_cdi(conn, _ProvedorSGS(), date(2025, 2, 28), datetime(2026, 1, 1))  # noqa: DTZ001


def test_falha_no_meio_da_carga_nao_deixa_linha(conn):
    class Quebrado(_ProvedorSGS):
        def serie_sgs(self, *a):
            dados = super().serie_sgs(*a)
            dados["observacoes"] = (
                *dados["observacoes"][:3],
                Observacao(date(2025, 3, 3), None),
            )
            return dados

    with pytest.raises(sqlite3.IntegrityError):
        macro.gravar_cdi(conn, Quebrado(), date(2025, 3, 3), COLETA_IBOV)
    assert conn.in_transaction is False
    assert conn.execute("SELECT COUNT(*) FROM benchmarks").fetchone() == (0,)
    fonte = {"url": "u", "sha256": "h"}
    fechamentos = [(date(2024, 1, 2), "1,0", 1.0), (date(2024, 1, 3), "x", None)]
    with pytest.raises(sqlite3.IntegrityError):
        b3_indices.gravar_ibovespa(conn, fechamentos, fonte, COLETA_IBOV)
    assert conn.in_transaction is False
    assert conn.execute("SELECT COUNT(*) FROM benchmarks").fetchone() == (0,)
    with pytest.raises(ValueError, match=r"^coleta exige fuso horário$"):
        b3_indices.gravar_ibovespa(conn, [], fonte, datetime(2026, 1, 1))  # noqa: DTZ001


def test_colunas_fora_dos_meses_ignoradas_e_mensagens_inteiras():
    corpo = {
        "results": [
            {"day": 2, "rateValue0": "x", "rateValue13": "y", "rateValue1": "1,5"}
        ]
    }
    assert b3_indices.ler(corpo, 2024) == [(date(2024, 1, 2), "1,5", 1.5)]
    for corpo, mensagem in (
        ([], "série do índice da B3 fora do leiaute"),
        ({"results": [{"day": "1"}]}, "série do índice da B3 com dia ilegível"),
        (
            {"results": [{"day": 1, "rateValue1": 10}]},
            "série do índice da B3 com fechamento ilegível",
        ),
    ):
        with pytest.raises(ValueError, match=rf"^{mensagem}$"):
            b3_indices.ler(corpo, 2024)
    with pytest.raises(
        TypeError,
        match=r"^benchmarks_ate recebe o dia local de D \(date\), não um instante$",
    ):
        b3_indices.benchmarks_ate(None, "IBOV", datetime(2026, 1, 1, tzinfo=UTC))


def test_mais_recente_vence_mesmo_quando_vem_por_ultimo_e_saida_inteira(conn):
    dia = date(2024, 12, 30)
    b3_indices.gravar_ibovespa(
        conn, [(dia, "1,00", 1.0)], {"url": "b", "sha256": "1"}, COLETA_IBOV
    )
    antiga = datetime(2026, 11, 11, 12, tzinfo=UTC)
    b3_indices.gravar_ibovespa(
        conn, [(dia, "2,00", 2.0)], {"url": "a", "sha256": "2"}, antiga
    )
    assert b3_indices.benchmarks_ate(conn, "IBOV", date(2025, 1, 1)) == [
        {"data": "2024-12-30", "valor": 1.0, "fonte": "b", "coleta": COLETA_IBOV.isoformat(),
         "hash_sha256": "1"}
    ]  # fmt: skip
    (mes,) = b3_indices.mensal(
        b3_indices.benchmarks_ate(conn, "IBOV", date(2025, 1, 1)), []
    )
    assert mes == {"mes": "2024-12", "data": "2024-12-30", "ibov": 1.0}


def test_relacao_da_coleta_escolhida_sem_versao_antiga_nem_duplicado(conn, relacao):
    base = relacao.registros[0]
    antiga = dict(base, valueCash="0,999999")  # valor corrigido depois pela B3
    primeira = dataclasses.replace(
        _conferida(relacao), registros=(antiga, antiga), total=2
    )
    assert b3_proventos.gravar_proventos(conn, primeira, 8133) == {
        "inseridos": 1, "repetidos": 0, "duplicados_na_coleta": 1,
    }  # fmt: skip
    segunda = dataclasses.replace(
        _conferida(relacao, datetime(2026, 10, 25, tzinfo=UTC)),
        registros=(base,),
        total=1,
    )
    b3_proventos.gravar_proventos(conn, segunda, 8133)

    def valores(dia):
        lido = b3_proventos.proventos_ate(conn, "LREN", dia)
        return [p["valor_bruto"] for p in lido["proventos"] + lido["sem_prova"]]

    assert valores(date(2026, 10, 24)) == ["0,999999"]
    assert valores(date(2026, 10, 26)) == ["0,240666"]  # só a versão corrigida


def test_coleta_sem_fuso_recusada(conn, relacao):
    sem_fuso = dataclasses.replace(relacao, coleta="2026-10-20T20:40:00")
    with pytest.raises(ValueError, match=r"^coleta exige fuso horário$"):
        b3_proventos.gravar_proventos(conn, sem_fuso, 8133)
