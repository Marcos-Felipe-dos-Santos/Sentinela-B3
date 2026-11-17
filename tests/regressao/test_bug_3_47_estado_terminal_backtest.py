"""BUG-3-47 (Gemini C4): último negócio na deslistagem e suspensão com prova.

Ficha §5: caixa ao CDI desde o último fechamento negociado; cotação ausente
não demonstra suspensão. O FCA sintético passa pela carga e leitura reais.
"""

import sqlite3
from contextlib import closing
from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest
from test_universo_pit import TSTE, _fca_sintetico

from backtesting.backtest_pit import BacktestPIT, retorno_total
from sentinela.data.store import migracoes

D, L, FIM_NEG, T = (
    date.fromisoformat(d)
    for d in ("2020-06-30", "2021-03-31", "2021-04-01", "2021-06-30")
)


@pytest.mark.parametrize("com_provento", [False, True])
def test_deslistada_sai_no_ultimo_negocio_e_capitaliza_cdi(com_provento: bool) -> None:
    proventos = (
        [
            {"data_ex": D, "valor": 9},
            {"data_ex": L, "valor": 1},
            {"data_ex": FIM_NEG, "valor": 10},
        ]
        if com_provento
        else []
    )
    saida = retorno_total(
        {D: 10, L: 11, date(2021, 4, 5): 99},
        proventos,
        inicio=D,
        fim=T,
        deslistagem=FIM_NEG,
        cdi={L: 1.0, FIM_NEG: 2.0, T: 99.0},
        pregoes=[D, L, FIM_NEG, T],
    )
    fator_acao = Fraction(6, 5) if com_provento else Fraction(11, 10)
    esperado = fator_acao * Fraction(101, 100) * Fraction(102, 100) - 1
    assert saida["abstencao"] is None
    assert saida["deslistada"] is True
    assert saida["suspensao"] is False
    assert saida["retorno"] == pytest.approx(float(esperado))


@pytest.mark.parametrize(
    "referencia,entrega,fim_negociacao",
    [
        ("2021-12-31", "2022-03-01", ""),
        ("2021-12-31", "2022-03-01", "2022-01-31"),
        ("2021-01-01", "2021-04-01", "2022-01-31"),
    ],
)
def test_fca_sem_prova_de_suspensao_nao_autoriza_preco_mantido(
    tmp_path: Path, referencia: str, entrega: str, fim_negociacao: str
) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        _fca_sintetico(
            conn,
            tmp_path,
            [(TSTE, referencia, "1", entrega)],
            [
                {
                    "CNPJ_Companhia": TSTE,
                    "Data_Referencia": referencia,
                    "Versao": "1",
                    "Codigo_Negociacao": "TSTE3",
                    "Valor_Mobiliario": "Ações Ordinárias",
                    "Data_Inicio_Negociacao": "2019-01-01",
                    "Data_Fim_Negociacao": fim_negociacao,
                }
            ],
            ano=int(referencia[:4]),
        )
        executor = BacktestPIT(
            conn, None, hoje=date(2026, 11, 17), cache_dir=tmp_path / "c"
        )
        estado = executor._estado_terminal(TSTE, "TSTE3", T, False)
    assert estado["suspensao_confirmada"] is False
    assert estado["deslistagem"] is None
    saida = retorno_total(
        {D: 10, L: 11},
        inicio=D,
        fim=T,
        pregoes=[D, L, T],
        **{k: estado[k] for k in ("deslistagem", "suspensao_confirmada")},
    )
    assert saida["retorno"] is None
    assert saida["abstencao"] == "estado terminal sem prova de suspensão ou deslistagem"


@pytest.mark.parametrize(
    "caso", ["dinheiro", "evento", "sem_prova", "com_no_ultimo", "evento_com_no_ultimo"]
)
def test_orquestracao_ignora_eventos_posteriores_a_saida(
    monkeypatch: pytest.MonkeyPatch, caso: str
) -> None:
    from datetime import timedelta

    from test_backtest_pit_retornos import EX as ultimo
    from test_backtest_pit_retornos import D as entrada
    from test_backtest_pit_retornos import T as horizonte
    from test_backtest_pit_retornos import _executar, _Fontes, _precos, _provento

    dinheiro = [_provento("ON", ultimo, "1,00")]
    eventos, sem_prova, eventos_sp = [], [], []
    if caso == "dinheiro":
        dinheiro.append(_provento("ON", horizonte, "9,00") | {"natureza": "OUTRA"})
    elif caso == "evento":
        eventos.append(
            {"isin": "BRABEVACNOR1", "data_ex": horizonte.isoformat(), "fator": None}
        )
    elif caso == "evento_com_no_ultimo":
        eventos_sp.append({"data_com": ultimo.isoformat()})
    else:
        com = ultimo if caso == "com_no_ultimo" else horizonte
        sem_prova.append({"especie": "ON", "data_com": com.isoformat()})
    _Fontes(
        monkeypatch,
        proventos=dinheiro,
        eventos=eventos,
        sem_prova=sem_prova,
        eventos_sp=eventos_sp,
    )
    estado = {
        "deslistagem": ultimo + timedelta(days=1),
        "suspensao_confirmada": False,
        "motivo_deslistagem": "fim comprovado",
    }
    retorno, *_ = _executar(
        monkeypatch,
        _precos((entrada, 10), (ultimo, 11), (horizonte, 99)),
        estado=estado,
        pregoes=[entrada, ultimo, horizonte],
        benchmarks={"IBOV": [], "CDI": [{"data": ultimo.isoformat(), "valor": 1.0}]},
    )
    assert retorno["abstencao"] is None
    assert retorno["deslistada"] is True
    assert retorno["retorno"] == pytest.approx(
        float(Fraction(6, 5) * Fraction(101, 100) - 1)
    )
