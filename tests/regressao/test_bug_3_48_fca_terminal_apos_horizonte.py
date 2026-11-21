"""BUG-3-48 (Gemini A3): só entregas até T decidem o FCA terminal.

FCA sintético no layout CVM passa por carga e leitor reais; nenhum intermediário
é substituído. O mesmo executor deve preservar o recorte de cada horizonte.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest
from test_universo_pit import TSTE, _fca_sintetico

from backtesting.backtest_pit import BacktestPIT
from sentinela.data.store import migracoes

T1, T2, F1, F2 = (
    date.fromisoformat(d)
    for d in ("2021-06-30", "2022-06-30", "2021-03-31", "2021-09-30")
)


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(":memory:")) as banco:
        migracoes.aplicar(banco)
        yield banco


def _carregar(
    conn: sqlite3.Connection, tmp_path: Path, documentos: list[tuple[str, str, str]]
) -> BacktestPIT:
    por_ano: dict[int, list[tuple[str, str, str]]] = {}
    for documento in documentos:
        por_ano.setdefault(int(documento[0][:4]), []).append(documento)
    for ano, docs in por_ano.items():
        _fca_sintetico(
            conn,
            tmp_path,
            [(TSTE, ref, "1", entrega) for ref, entrega, _ in docs],
            [
                {
                    "CNPJ_Companhia": TSTE,
                    "Data_Referencia": ref,
                    "Versao": "1",
                    "Codigo_Negociacao": "TSTE3",
                    "Valor_Mobiliario": "Ações Ordinárias",
                    "Data_Inicio_Negociacao": "2010-01-01",
                    "Data_Fim_Negociacao": fim,
                }
                for ref, _, fim in docs
            ],
            ano=ano,
        )
    return BacktestPIT(
        conn, None, hoje=date(2026, 11, 17), cache_dir=tmp_path / "cache"
    )


def test_entrega_apos_t_nao_apaga_deslistagem_ja_conhecida(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    executor = _carregar(
        conn,
        tmp_path,
        [
            ("2021-01-01", "2021-04-15", F1.isoformat()),
            ("2021-06-01", "2021-07-01", ""),
        ],
    )
    estado = executor._estado_terminal(TSTE, "TSTE3", T1, False)
    assert estado["deslistagem"] == F1
    assert estado["suspensao_confirmada"] is False


def test_fim_passado_publicado_depois_de_t_nao_antecipa_estado(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    executor = _carregar(
        conn,
        tmp_path,
        [
            ("2021-01-01", "2021-04-15", ""),
            ("2021-06-01", "2021-07-01", F1.isoformat()),
        ],
    )
    estado = executor._estado_terminal(TSTE, "TSTE3", T1, False)
    assert estado["deslistagem"] is None
    assert estado["suspensao_confirmada"] is False


@pytest.mark.parametrize("ordem", [(T1, T2), (T2, T1)])
def test_mesmo_executor_preserva_estado_de_cada_horizonte(
    conn: sqlite3.Connection, tmp_path: Path, ordem: tuple[date, date]
) -> None:
    executor = _carregar(
        conn,
        tmp_path,
        [
            ("2021-01-01", "2021-04-15", F1.isoformat()),
            ("2022-01-01", "2022-04-01", F2.isoformat()),
        ],
    )
    esperados = {T1: F1, T2: F2}
    for horizonte in ordem:
        estado = executor._estado_terminal(TSTE, "TSTE3", horizonte, False)
        assert estado["deslistagem"] == esperados[horizonte]
        assert estado["suspensao_confirmada"] is False


@pytest.mark.parametrize("entrega", ["2021-06-30", "2021-06-30 14:00:00"])
def test_entrega_no_dia_t_e_incluida(
    conn: sqlite3.Connection, tmp_path: Path, entrega: str
) -> None:
    executor = _carregar(conn, tmp_path, [("2021-01-01", entrega, F1.isoformat())])
    assert executor._estado_terminal(TSTE, "TSTE3", T1, False)["deslistagem"] == F1
