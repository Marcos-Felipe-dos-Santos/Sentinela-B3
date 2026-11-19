"""BUG-3-52 (Gemini A5): evento em ações aprovado em D ou depois não entra na relação em D.

`b3_proventos.relacao_ate` remontava os eventos em ações com todos os guardados do emissor,
sem o corte de publicação da decisão 40 que os registros em dinheiro já tinham. Um evento
aprovado depois de D, sem data com legível, abstinha o Bazin histórico por "evento em ações
na janela" (`proventos_b3._evento_de_acoes_na_janela`), com um evento que não existia em D.

Respostas oficiais da B3 da Lojas Renner (contrato D18), carga e leitor reais; o evento sem
data com é o mesmo JSON de um evento oficial, gravado pelo produtor real com outra aprovação.
"""

import dataclasses
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, date, datetime

import pytest
from test_bloco_bazin_historico import _dados, _gravar, _motor, _pregoes
from test_eventos_societarios import COLETA, _obter

from sentinela.data import proventos_b3
from sentinela.data.providers import b3_proventos
from sentinela.data.store import migracoes


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(":memory:")) as banco:
        migracoes.aplicar(banco)
        yield banco


@pytest.fixture
def relacao():
    return b3_proventos.coletar(8133, COLETA, _obter())


def _rotulos(bloco: dict) -> list[tuple[str, str]]:
    return sorted((e["label"], e["approvedOn"]) for e in bloco["eventos_acoes"])


def test_evento_aprovado_no_dia_de_d_fica_de_fora(conn, relacao, tmp_path):
    """A bonificação oficial de 11/12/2024 só conta depois do dia da aprovação."""
    _gravar(conn, relacao)
    _pregoes(conn, tmp_path, ["20241210"])
    em_d = b3_proventos.relacao_ate(conn, "LREN", date(2024, 12, 11), ticker="LREN4")
    depois = b3_proventos.relacao_ate(conn, "LREN", date(2024, 12, 12), ticker="LREN4")
    assert ("BONIFICACAO", "11/12/2024") in _rotulos(depois)
    assert ("BONIFICACAO", "11/12/2024") not in _rotulos(em_d)
    assert len(_rotulos(depois)) == len(_rotulos(em_d)) + 1


def _com_evento_sem_data_com(conn, relacao, aprovacao: str) -> None:
    """Grava pelo produtor real um evento em ações da PN sem data com, aprovado em `aprovacao`."""
    _gravar(conn, relacao)
    (modelo,) = [e for e in relacao.eventos_acoes if e["label"] == "DESDOBRAMENTO"]
    evento = {
        **modelo,
        "isinCode": "BRLRENACNPR8",
        "assetIssued": "BRLRENACNPR8",
        "approvedOn": aprovacao,
        "lastDatePrior": "",
    }
    b3_proventos.gravar_eventos(
        conn, dataclasses.replace(relacao, eventos_acoes=(evento,)), 8133
    )


def _bazin(conn, tmp_path):
    as_of = datetime(2026, 10, 19, 15, tzinfo=UTC)
    _pregoes(conn, tmp_path, ["20261015", "20261016"])
    motor = _motor(conn, tmp_path, as_of)
    dados = _dados()
    assert motor._buscar_yfinance("LREN4", dados)
    motor._buscar_proventos_b3("LREN4", dados)
    return proventos_b3.entradas(dados, as_of)


def test_evento_futuro_sem_data_com_nao_abstem_o_bazin_em_d(conn, relacao, tmp_path):
    _com_evento_sem_data_com(conn, relacao, "25/10/2026")  # depois de D = 19/10/2026
    obtido = _bazin(conn, tmp_path)
    assert not isinstance(obtido, proventos_b3.Abstencao), obtido


def test_evento_anterior_a_d_sem_data_com_segue_abstendo(conn, relacao, tmp_path):
    """Controle: o evento já aprovado em D, sem data com, mantém a abstenção conservadora."""
    _com_evento_sem_data_com(conn, relacao, "10/10/2026")
    obtido = _bazin(conn, tmp_path)
    assert isinstance(obtido, proventos_b3.Abstencao)
    assert obtido.motivo.startswith(proventos_b3.MOTIVO_EVENTO_ACOES)
