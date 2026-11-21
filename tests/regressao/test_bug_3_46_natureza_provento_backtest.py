"""BUG-3-46: a ficha §5 só reinveste dividendos e JCP, com data ex em (D,T]."""

from datetime import date, timedelta

import pytest
from test_backtest_pit_retornos import BASE, EX, D, T, _executar, _Fontes, _provento

MOTIVO = "natureza de provento não prevista na ficha"


def _evento(natureza: str | None, data_ex: date = EX, especie: str = "ON") -> dict:
    return _provento(especie, data_ex, "1,00") | {"natureza": natureza}


@pytest.mark.parametrize("natureza", ["REST CAP DIN", "OUTRA", None])
def test_natureza_fora_da_ficha_abstem_na_janela(
    monkeypatch: pytest.MonkeyPatch, natureza: str | None
) -> None:
    _Fontes(monkeypatch, proventos=[_evento(natureza)])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["retorno"] is None
    assert retorno["abstencao"] == MOTIVO


@pytest.mark.parametrize("data_ex", [D, T + timedelta(days=1)])
def test_natureza_fora_da_janela_nao_abstem(
    monkeypatch: pytest.MonkeyPatch, data_ex: date
) -> None:
    _Fontes(monkeypatch, proventos=[_evento("REST CAP DIN", data_ex)])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.1)


@pytest.mark.parametrize("natureza", ["DIVIDENDO", "JRS CAP PROPRIO"])
def test_naturezas_da_ficha_reinvestem(
    monkeypatch: pytest.MonkeyPatch, natureza: str
) -> None:
    _Fontes(monkeypatch, proventos=[_evento(natureza)])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.21)


def test_natureza_de_outra_especie_nao_contamina(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _Fontes(
        monkeypatch,
        proventos=[_evento("DIVIDENDO"), _evento("REST CAP DIN", especie="PN")],
    )
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.21)
