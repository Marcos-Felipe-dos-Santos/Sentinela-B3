"""BUG-4-07: pendências de outra espécie não bloqueiam o retorno de ITUB3."""

import pytest
from test_backtest_pit_retornos import BASE, MEIO, _executar, _Fontes

ON = "BRITUBACNOR4"
PN = "BRITUBACNPR1"
MOTIVOS = {
    "provento": "relação de proventos contém registros sem prova no horizonte",
    "evento_sem_prova": "evento em ações sem prova no horizonte",
    "evento_sem_ex": "evento em ações sem data ex demonstrada no horizonte",
}


def _retorno(
    monkeypatch: pytest.MonkeyPatch,
    origem: str,
    especie: str | None,
    isin: str | None,
    *,
    isin_ticker: str | None = ON,
) -> dict:
    data_com = MEIO.isoformat()
    campos_evento = {"data_com": data_com, "isin": isin}
    _Fontes(
        monkeypatch,
        sem_prova=[{"data_com": data_com, "especie": especie}]
        if origem == "provento"
        else (),
        eventos_sp=[campos_evento] if origem == "evento_sem_prova" else (),
        eventos=[campos_evento | {"data_ex": None}]
        if origem == "evento_sem_ex"
        else (),
    )
    retorno, *_ = _executar(monkeypatch, BASE, ticker="ITUB3", isin=isin_ticker)
    return retorno


@pytest.mark.parametrize("origem", MOTIVOS)
def test_pendencia_da_pn_nao_bloqueia_a_on(
    monkeypatch: pytest.MonkeyPatch, origem: str
) -> None:
    retorno = _retorno(monkeypatch, origem, "PN", PN)

    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.10)


@pytest.mark.parametrize("origem", MOTIVOS)
@pytest.mark.parametrize(
    ("especie", "isin"),
    [
        ("ON", ON),
        (None, None),
        ("", ""),
        ("  ", "  "),
        (" ON ", f" {ON} "),
    ],
)
def test_pendencia_da_on_ou_identidade_ausente_bloqueia(
    monkeypatch: pytest.MonkeyPatch,
    origem: str,
    especie: str | None,
    isin: str | None,
) -> None:
    retorno = _retorno(monkeypatch, origem, especie, isin)

    assert retorno["abstencao"] == MOTIVOS[origem]


@pytest.mark.parametrize("origem", MOTIVOS)
def test_pendencia_bloqueia_se_a_especie_do_ticker_nao_esta_demonstrada(
    monkeypatch: pytest.MonkeyPatch, origem: str
) -> None:
    retorno = _retorno(monkeypatch, origem, "PN", PN, isin_ticker=None)

    assert retorno["abstencao"] == MOTIVOS[origem]
