"""BUG-2B-33: o fechamento ajustado do yfinance decide o gate do Bazin, que exige preço bruto.

Achado da 2ª auditoria FASE do Codex (20/10/2026): `_buscar_yfinance` lê o `history` com o
ajuste padrão (`auto_adjust=True`), e `_buscar_proventos_b3` usa esse `Close` como preço do
DY da B3. Com D = 4,99 e preço bruto 100, o DY é 4,99% (sem Bazin); pelo preço ajustado 99,
5,04% (Bazin calcula). A ficha Bazin, §2, pede o fechamento bruto da referência.
"""

from datetime import UTC, datetime
from typing import ClassVar

import pandas as pd
import pytest

import market_engine
from market_engine import MarketEngine
from sentinela.data import proventos_b3
from sentinela.data.providers import b3_proventos

AGORA = datetime(2026, 10, 20, 15, tzinfo=UTC)
INDICE = pd.DatetimeIndex(pd.to_datetime(["2026-10-16", "2026-10-19"])).tz_localize(
    "America/Sao_Paulo"
)
AJUSTADO = pd.DataFrame({"Close": [98.0, 99.0], "Dividends": [0.0, 0.0]}, index=INDICE)
BRUTO = pd.DataFrame({"Close": [99.0, 100.0], "Dividends": [0.0, 0.0]}, index=INDICE)


class _Ticker:
    info: ClassVar[dict] = {}

    def history(self, *args, auto_adjust=True, **kwargs):
        return AJUSTADO if auto_adjust else BRUTO


class _Relogio(datetime):
    @classmethod
    def now(cls, tz=None):
        return AGORA if tz is None else AGORA.astimezone(tz)


class _Provedor:
    def coletar(self, cd_cvm, agora):
        return b3_proventos.Relacao(
            nome_pregao="TESTE SA",
            emissor="TSTE",
            registros=(
                {
                    "typeStock": "ON",
                    "corporateAction": "DIVIDENDO",
                    "valueCash": "4,99",
                    "lastDatePriorEx": "10/06/2026",
                    "dateApproval": "01/06/2026",
                    "quotedPerShares": "1",
                },
                {
                    "typeStock": "ON",
                    "corporateAction": "DIVIDENDO",
                    "valueCash": "1,0",
                    "lastDatePriorEx": "10/06/2020",
                    "dateApproval": "01/06/2020",
                    "quotedPerShares": "1",
                },
            ),
            total=2,
            eventos_acoes=(),
            dinheiro_complemento=(),
            fontes=(),
            coleta="2026-10-20T14:00:00+00:00",
        )


def test_dy_da_b3_usa_o_fechamento_bruto(monkeypatch):
    monkeypatch.setattr(market_engine, "datetime", _Relogio)
    monkeypatch.setattr(market_engine.yf, "Ticker", lambda ticker: _Ticker())
    engine = MarketEngine.__new__(MarketEngine)
    engine.b3_proventos = _Provedor()
    dados = {
        "classe_ativo": "STOCK",
        "modelo_bpp": "empresa",
        "cd_cvm": 1,
        "especie": "ON",
    }
    assert engine._buscar_yfinance("TSTE3", dados)
    engine._buscar_proventos_b3("TSTE3", dados)
    entradas = proventos_b3.entradas(dados, AGORA)
    assert entradas["preco_referencia"] == 100.0
    assert entradas["dy"] == pytest.approx(0.0499)
