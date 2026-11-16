"""F3-8h: o bloco do Bazin no motor histórico, pelo preço do COTAHIST de D.

A relação é a da coleta escolhida pelo `proventos_ate` (decisão 40 e decisão 43), remontada do
banco com os registros literais (`linha_json`), o total declarado, o complemento em dinheiro e
os eventos em ações guardados; o preço é o fechamento bruto do COTAHIST antes do dia de D. A
conta é a mesma da cascata (`proventos_b3.entradas`), sem regra nova (ficha Bazin 1.2).
Respostas oficiais da B3 da Lojas Renner (contrato D18), as do `test_identidade_isin_pregao`.
"""

import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime, timedelta

import pandas as pd
import pytest
from test_cotahist import _linha
from test_eventos_societarios import COLETA, _obter

from sentinela.data import proventos_b3
from sentinela.data.providers import b3_cotahist, b3_proventos
from sentinela.data.store import migracoes
from sentinela.services import historico

AS_OF = datetime(2026, 11, 2, 15, tzinfo=UTC)
DIA = date(2026, 11, 2)
ISIN_PN = "BRLRENACNPR8"


@pytest.fixture
def relacao():
    return b3_proventos.coletar(8133, COLETA, _obter())


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _pregoes(conn, tmp_path, dias, codigo="LREN4", isin=ISIN_PN, preco="0000000002000"):
    caminho = tmp_path / f"COTAHIST_{codigo}_{dias[0]}.ZIP"
    with zipfile.ZipFile(caminho, "w") as zf:
        linhas = [
            _linha(DATA=d, CODNEG=codigo, ESPECI="PN", CODISI=isin, PREULT=preco)
            for d in dias
        ]
        zf.writestr("COTAHIST.TXT", "\n".join(linhas).encode("latin-1"))
    b3_cotahist.carregar(conn, caminho, fonte="b3", coleta=COLETA.isoformat())


def _gravar(conn, relacao):
    b3_proventos.gravar_proventos(conn, relacao, 8133)
    b3_proventos.gravar_eventos(conn, relacao, 8133)


def _motor(conn, tmp_path, as_of=AS_OF):
    return historico.MotorHistorico(conn, as_of, tmp_path / "pit", pd.DataFrame())


def _dados():
    return {
        "classe_ativo": "STOCK",
        "modelo_bpp": "empresa",
        "especie": "PN",
        "disponibilidade_por_publicacao": True,
    }


def _ordenados(itens):
    return sorted(json.dumps(i, sort_keys=True, ensure_ascii=False) for i in itens)


def test_relacao_do_banco_e_a_da_coleta(conn, relacao, tmp_path):
    _gravar(conn, relacao)
    _pregoes(conn, tmp_path, ["20261030"])
    bloco = b3_proventos.relacao_ate(conn, "LREN", DIA, ticker="LREN4")
    assert "abstencao" not in bloco, bloco
    assert _ordenados(bloco["registros"]) == _ordenados(relacao.registros)
    assert bloco["total"] == relacao.total
    assert bloco["dinheiro_complemento"] == list(relacao.dinheiro_complemento)
    assert _ordenados(bloco["eventos_acoes"]) == _ordenados(relacao.eventos_acoes)
    assert bloco["coleta"] == relacao.coleta
    assert bloco["aprovacao_antes_de_d"] is True
    detalhe = relacao.fontes[0]
    assert bloco["proveniencia"] == {
        "fonte": "B3, relação de proventos em dinheiro (CompanyCall)",
        "nome_pregao": relacao.nome_pregao,
        "coleta": relacao.coleta,
        "detalhe": {"url": detalhe["url"], "sha256": detalhe["sha256"]},
        "banco": "proventos",
    }


def test_relacao_abstem_com_o_motivo_do_leitor(conn, relacao, tmp_path):
    assert b3_proventos.relacao_ate(conn, "LREN", DIA, ticker="LREN4") == {
        "abstencao": b3_proventos.MOTIVO_PROVENTO_SEM_COLETA
    }
    _gravar(conn, relacao)
    _pregoes(conn, tmp_path, ["20261030"], codigo="LREN3", isin="BRLRENACNOR1")
    motivo = b3_proventos.relacao_ate(conn, "LREN", DIA, ticker="LREN3")["abstencao"]
    assert motivo.startswith(b3_proventos.MOTIVO_PROVENTO_IDENTIDADE)


def test_relacao_sem_complemento_guardado_abstem(conn, relacao, tmp_path):
    """Coleta com a identidade comprovada, anterior à migração 011 (sem o complemento)."""
    _gravar(conn, relacao)
    _pregoes(conn, tmp_path, ["20261030"])
    for (nome,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name IN "
        "('proventos_complemento', 'proventos_coletas')"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{nome}"')
    conn.execute("UPDATE proventos_coletas SET identidade = NULL")
    assert "abstencao" not in b3_proventos.relacao_ate(
        conn, "LREN", DIA, ticker="LREN4"
    )
    conn.execute("DELETE FROM proventos_complemento")
    assert b3_proventos.relacao_ate(conn, "LREN", DIA, ticker="LREN4") == {
        "abstencao": b3_proventos.MOTIVO_COMPLEMENTO_NAO_GUARDADO
    }


def test_motor_monta_o_bloco_igual_ao_da_cascata(conn, relacao, tmp_path):
    """[e2e] produtor real: coleta oficial e COTAHIST gravados, motor em D, DY da cascata."""
    _gravar(conn, relacao)
    _pregoes(conn, tmp_path, ["20261029", "20261030"])
    motor = _motor(conn, tmp_path)
    dados = _dados()
    assert motor._buscar_yfinance("LREN4", dados)
    motor._buscar_proventos_b3("LREN4", dados)
    bloco = dados["proventos_b3"]
    assert "abstencao" not in bloco, bloco
    assert bloco["fechamentos"] == {"2026-10-29": 20.0, "2026-10-30": 20.0}
    assert bloco["conferencia_yfinance"] is None
    da_cascata = {
        "registros": list(relacao.registros),
        "total": relacao.total,
        "eventos_acoes": list(relacao.eventos_acoes),
        "dinheiro_complemento": list(relacao.dinheiro_complemento),
        "fechamentos": {"2026-10-29": 20.0, "2026-10-30": 20.0},
        "pregoes": bloco["pregoes"],
        "conferencia_yfinance": None,
        "coleta": relacao.coleta,
    }
    esperado = proventos_b3.entradas({**dados, "proventos_b3": da_cascata}, AS_OF)
    obtido = proventos_b3.entradas(dados, AS_OF)
    assert obtido == esperado
    assert not isinstance(obtido, proventos_b3.Abstencao), obtido
    assert obtido["preco_referencia"] == 20.0
    assert obtido["dy"] == pytest.approx(obtido["serie"]["d_bruto_12m"] / 20.0)


def test_coleta_posterior_a_d_vale_pela_publicacao(conn, relacao, tmp_path):
    """Decisão 40: numa data passada, a coleta deixa de ser critério de disponibilidade."""
    _gravar(conn, relacao)
    _pregoes(conn, tmp_path, ["20261015", "20261016"])
    as_of = datetime(2026, 10, 19, 15, tzinfo=UTC)  # antes da coleta de 20/10
    motor = _motor(conn, tmp_path, as_of)
    dados = _dados()
    assert motor._buscar_yfinance("LREN4", dados)
    motor._buscar_proventos_b3("LREN4", dados)
    obtido = proventos_b3.entradas(dados, as_of)
    assert not isinstance(obtido, proventos_b3.Abstencao), obtido
    assert obtido["preco_referencia"] == 20.0
    sem_marca = {
        k: v for k, v in dados.items() if k != "disponibilidade_por_publicacao"
    }
    assert proventos_b3.entradas(sem_marca, as_of) == proventos_b3.Abstencao(
        proventos_b3.MOTIVO_COLETA
    )


def test_sem_preco_do_cotahist_abstem(conn, relacao, tmp_path):
    _gravar(conn, relacao)
    _pregoes(conn, tmp_path, ["20261030"])
    motor = _motor(conn, tmp_path)
    dados = _dados()
    motor._buscar_proventos_b3(
        "LREN4", dados
    )  # sem `_buscar_yfinance`: sem fechamentos
    assert dados["proventos_b3"] == {"abstencao": proventos_b3.MOTIVO_PRECO}
    outra_fonte = {
        **_dados(),
        "fonte_preco": "yfinance",
        "fechamentos_brutos": {"2026-10-30": 1.0},
    }
    motor._buscar_proventos_b3("LREN4", outra_fonte)
    assert outra_fonte["proventos_b3"] == {"abstencao": proventos_b3.MOTIVO_PRECO}
    so_em_d = {
        **_dados(),
        "fonte_preco": historico.FONTE_PRECO,
        "fechamentos_brutos": {"2026-11-02": 1.0},
    }
    motor._buscar_proventos_b3("LREN4", so_em_d)
    assert so_em_d["proventos_b3"] == {
        "abstencao": proventos_b3.MOTIVO_PRECO_NAO_ENCERRADO
    }


def test_pregoes_do_banco_so_quando_a_data_ex_depende(conn, tmp_path):
    referencia = date(2026, 10, 30)
    inicio = proventos_b3.inicio_da_janela(referencia)
    perto = inicio - proventos_b3.FOLGA_SEM_PREGAO + (proventos_b3.FOLGA_SEM_PREGAO / 2)
    longe = {"lastDatePriorEx": "01/06/2026"}
    assert b3_proventos.pregoes_da_data_ex(conn, [longe], referencia) is None
    _pregoes(conn, tmp_path, [perto.strftime("%Y%m%d")])
    registro = {"lastDatePriorEx": perto.strftime("%d/%m/%Y")}
    assert b3_proventos.pregoes_da_data_ex(
        conn, [longe, registro, None], referencia
    ) == [perto.isoformat()]


def test_pregoes_do_banco_nos_limites_dos_meses(conn, tmp_path):
    referencia = date(2026, 10, 30)
    inicio = proventos_b3.inicio_da_janela(referencia)
    limite = inicio - proventos_b3.FOLGA_SEM_PREGAO
    no_limite = {"lastDatePriorEx": limite.strftime("%d/%m/%Y")}
    assert b3_proventos.pregoes_da_data_ex(conn, [no_limite], referencia) is None
    primeiro = date(limite.year, limite.month, 1)
    ultimo = (pd.Timestamp(inicio) + pd.offsets.MonthEnd(0)).date()
    dias = [primeiro - timedelta(days=1), primeiro, ultimo, ultimo + timedelta(days=1)]
    _pregoes(conn, tmp_path, [d.strftime("%Y%m%d") for d in dias])
    dentro = {"lastDatePriorEx": (limite + timedelta(days=1)).strftime("%d/%m/%Y")}
    assert b3_proventos.pregoes_da_data_ex(conn, [dentro], referencia) == [
        primeiro.isoformat(),
        ultimo.isoformat(),
    ]


def test_coleta_sem_fuso_abstem_mesmo_pela_publicacao():
    dados = {**_dados(), "proventos_b3": {"coleta": "2026-10-20T20:40:00"}}
    assert proventos_b3.entradas(dados, AS_OF) == proventos_b3.Abstencao(
        proventos_b3.MOTIVO_COLETA
    )


def test_motor_unit_vazio_e_pregoes(conn, tmp_path, monkeypatch):
    motor = _motor(conn, tmp_path)
    unit = {"classe_ativo": "UNIT", "modelo_bpp": "empresa"}
    motor._buscar_proventos_b3("LREN11", unit)
    assert unit["proventos_b3"] == {"abstencao": proventos_b3.MOTIVO_PRECO}
    vazio = {**_dados(), "fonte_preco": historico.FONTE_PRECO, "fechamentos_brutos": {}}
    motor._buscar_proventos_b3("LREN4", vazio)
    assert vazio["proventos_b3"] == {"abstencao": proventos_b3.MOTIVO_PRECO}
    relacao = {
        "registros": [{"lastDatePriorEx": "01/01/2026"}],
        "total": 1,
        "coleta": "c",
    }
    monkeypatch.setattr(historico.b3_proventos, "relacao_ate", lambda *a, **k: relacao)
    chamadas = []

    def pregoes(*args):
        chamadas.append(args)
        return ["2025-10-31"]

    monkeypatch.setattr(historico.b3_proventos, "pregoes_da_data_ex", pregoes)
    dados = {
        **_dados(), "fonte_preco": historico.FONTE_PRECO,
        "fechamentos_brutos": {"2026-10-29": 9.0, "2026-10-30": 10.0, "2026-11-02": 11.0},
    }  # fmt: skip
    motor._buscar_proventos_b3("LREN4", dados)
    assert chamadas == [(conn, relacao["registros"], date(2026, 10, 30))]
    assert dados["proventos_b3"]["pregoes"] == ["2025-10-31"]


@pytest.mark.parametrize(
    ("modelo", "motivo"),
    [
        ("banco", "fora do escopo do Bazin: modelo banco"),
        (None, "modelo empresa não demonstrado no BPP consolidado"),
    ],
)
def test_motor_fora_do_modelo_empresa(conn, tmp_path, modelo, motivo):
    dados = {"classe_ativo": "STOCK", "modelo_bpp": modelo}
    _motor(conn, tmp_path)._buscar_proventos_b3("LREN4", dados)
    assert dados["proventos_b3"] == {"abstencao": motivo}


def test_aprovacao_no_dia_de_d_fica_de_fora(conn, relacao, tmp_path):
    """Decisão 40, como no `proventos_ate`: a aprovação de 17/09/2026 só conta depois dela."""
    _gravar(conn, relacao)
    _pregoes(conn, tmp_path, ["20260915"])
    em_d = b3_proventos.relacao_ate(conn, "LREN", date(2026, 9, 17), ticker="LREN4")
    depois = b3_proventos.relacao_ate(conn, "LREN", date(2026, 9, 18), ticker="LREN4")
    aprovados = [r["dateApproval"] for r in depois["registros"]]
    assert "17/09/2026" in aprovados and len(aprovados) == relacao.total == 99
    assert "17/09/2026" not in [r["dateApproval"] for r in em_d["registros"]]
    assert len(em_d["registros"]) == em_d["total"] == 98


def test_relacao_corrente_mantem_a_guarda_de_coleta(relacao):
    """DD-65: a cascata corrente com as_of passado liga a marca da decisão 40, mas a relação
    coletada agora (sem a marca do bloco do banco) continua abstendo pela coleta."""
    as_of = datetime(2026, 10, 19, 15, tzinfo=UTC)  # antes da coleta de 20/10
    corrente = {
        "registros": list(relacao.registros),
        "total": relacao.total,
        "eventos_acoes": list(relacao.eventos_acoes),
        "dinheiro_complemento": list(relacao.dinheiro_complemento),
        "fechamentos": {"2026-10-16": 20.0},
        "pregoes": None,
        "conferencia_yfinance": None,
        "coleta": relacao.coleta,
    }
    dados = {**_dados(), "proventos_b3": corrente}
    assert proventos_b3.entradas(dados, as_of) == proventos_b3.Abstencao(
        proventos_b3.MOTIVO_COLETA
    )
    marcado = {**corrente, "aprovacao_antes_de_d": "sim"}  # só `True` libera
    assert proventos_b3.entradas(
        {**dados, "proventos_b3": marcado}, as_of
    ) == proventos_b3.Abstencao(proventos_b3.MOTIVO_COLETA)
