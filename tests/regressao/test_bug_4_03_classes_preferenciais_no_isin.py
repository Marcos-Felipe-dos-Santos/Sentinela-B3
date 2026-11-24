"""BUG-4-03: os ISINs de PNC a PNH precisam conservar a classe nos consumidores B3."""

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest
from regressao.test_bug_3_45_especie_isin_backtest import (
    COLETA,
    COM,
    D,
    EX,
    T,
    _carregar,
)
from test_fatores_acoes_b3 import AS_OF, dados, documentos, evento

from backtesting.backtest_pit import BacktestPIT
from sentinela.data import proventos_b3
from sentinela.data.fatores_acoes_b3 import fatores_da_relacao
from sentinela.data.providers import b3_proventos
from sentinela.data.store import migracoes

pytestmark = pytest.mark.parametrize("sufixo", list("CDEFGH"))


def test_retorno_total_reinveste_o_provento_da_classe(
    tmp_path: Path, sufixo: str
) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        _carregar(conn, tmp_path, f"PN{sufixo}", f"ACNP{sufixo}")
        retorno, *_, evidencia = BacktestPIT(
            conn, None, hoje=COLETA.date(), cache_dir=tmp_path / "cache"
        )._retornos(
            "TSTA4", None, D, T, [D, COM, EX, T], {"IBOV": [], "CDI": []}, b3_proventos
        )
    assert evidencia["isin"] == f"BRTSTAACNP{sufixo}1"
    assert retorno["abstencao"] is None
    # R$ 1,00 reinvestido a R$ 10,00, com fechamento de R$ 11,00.
    assert retorno["retorno"] == pytest.approx(0.21)


def test_fator_reconhece_o_desdobramento_da_classe(sufixo: str) -> None:
    isin = f"BRTESTACNP{sufixo}0"
    entrada = dados([evento(isin=isin)])
    entrada["especie"] = f"PN{sufixo}"
    entrada["proventos_b3"]["isins_emissor"] = [isin]

    resultado = fatores_da_relacao(entrada, documentos(), AS_OF)

    assert resultado.get("abstencao") is None
    assert resultado["fatores"] == {
        "2021": 2,
        "2022": 2,
        "2023": 1,
        "2024": 1,
        "2025": 1,
    }


def test_janela_de_on_nao_abstem_por_evento_da_preferencial(sufixo: str) -> None:
    registros = [
        {
            "typeStock": "ON",
            "lastDatePriorEx": dia,
            "dateApproval": dia,
            "corporateAction": "DIVIDENDO",
            "quotedPerShares": "1",
            "valueCash": "1,50",
        }
        for dia in ("15/09/2025", "15/05/2026")
    ]
    janela = proventos_b3.serie_12_meses(
        registros,
        total=2,
        referencia=date(2026, 10, 19),
        dia_as_of=AS_OF.date(),
        especie="ON",
        eventos_acoes=[evento(isin=f"BRTESTACNP{sufixo}0", lastDatePrior="15/04/2026")],
    )

    assert not isinstance(janela, proventos_b3.Abstencao), janela
    assert janela["d_bruto_12m"] == pytest.approx(1.50)
