"""BUG-3-45: C1 Gemini — reinvestimento usa a espécie provada pelo CODISI.

COTAHIST e respostas B3 sintéticos entram pelos produtores reais, sem substituir
proventos_ate ou _retornos. Pela ficha §5: 10→11 e R$ 1 reinvestido a 10 = 21%.
"""

import hashlib
import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from test_cotahist import _linha

from backtesting.backtest_pit import BacktestPIT
from sentinela.data.providers import b3_cotahist, b3_proventos
from sentinela.data.store import migracoes

D, COM, EX, T = (
    date.fromisoformat(d)
    for d in ("2022-06-30", "2022-12-29", "2022-12-30", "2023-06-30")
)
COLETA = datetime(2026, 11, 17, tzinfo=UTC)


def _carregar(
    conn: sqlite3.Connection, tmp_path: Path, especie: str, codigo_isin: str
) -> None:
    isin = f"BRTSTA{codigo_isin}1"
    registros = [
        {
            "typeStock": e,
            "corporateAction": "DIVIDENDO",
            "valueCash": v,
            "quotedPerShares": "1",
            "dateApproval": "20/12/2022",
            "lastDatePriorEx": "29/12/2022",
        }
        for e, v in ((especie, "1,00"), ("ON", "9,00"))
    ]
    respostas = {
        "GetDetail": {
            "tradingName": "TESTE SA",
            "issuingCompany": "TSTA",
            "otherCodes": [{"isin": isin}, {"isin": "BRTSTAACNOR1"}],
        },
        "GetListedCashDividends": {
            "page": {"totalRecords": 2, "totalPages": 1},
            "results": registros,
        },
        "GetListedSupplementCompany": [
            {
                "stockDividends": [],
                "cashDividends": [
                    {"lastDatePrior": "29/12/2022", "rate": "1,00"},
                    {"lastDatePrior": "29/12/2022", "rate": "9,00"},
                ],
            }
        ],
    }

    def obter(url: str) -> tuple[dict | list, dict]:
        metodo = url.rsplit("/", 2)[-2]
        corpo = respostas[metodo]
        return corpo, {
            "url": url,
            "sha256": hashlib.sha256(json.dumps(corpo).encode()).hexdigest(),
        }

    relacao = b3_proventos.coletar(999999, COLETA, obter)
    assert relacao.identidade is None
    b3_proventos.gravar_proventos(conn, relacao, 999999)
    caminho = tmp_path / "COTAHIST.ZIP"
    linhas = [
        _linha(
            DATA=dia.strftime("%Y%m%d"),
            CODNEG="TSTA4",
            CODISI=isin,
            ESPECI=especie,
            PREULT=str(preco),
        )
        for dia, preco in (
            (date(2022, 6, 29), 1000),
            (D, 1000),
            (COM, 1000),
            (EX, 1000),
            (T, 1100),
        )
    ]
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("COTAHIST.TXT", "\n".join(linhas).encode("latin-1"))
    b3_cotahist.carregar(
        conn, caminho, fonte="fixture sintética B3", coleta=COLETA.isoformat()
    )
    conn.commit()


@pytest.mark.parametrize("especie,codigo_isin", [("PNA", "ACNPA"), ("PNB", "ACNPB")])
def test_retorno_reinveste_especie_comprovada_pelo_isin(
    tmp_path: Path, especie: str, codigo_isin: str
) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        _carregar(conn, tmp_path, especie, codigo_isin)
        prova = b3_proventos.proventos_ate(
            conn, "TSTA", date(2023, 7, 1), por_publicacao=True, ticker="TSTA4"
        )
        assert len(prova["proventos"]) == 2
        retorno, *_, evidencia = BacktestPIT(
            conn, None, hoje=COLETA.date(), cache_dir=tmp_path / "cache"
        )._retornos(
            "TSTA4", None, D, T, [D, COM, EX, T], {"IBOV": [], "CDI": []}, b3_proventos
        )
    assert evidencia["isin"] == f"BRTSTA{codigo_isin}1"
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.21)
