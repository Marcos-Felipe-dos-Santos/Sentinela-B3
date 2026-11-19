"""BUG-3-55 (Gemini B2): as correções e identidades oficiais chegam ao índice em D.

`universo.indice_em` aceita a tabela de correções e as identidades complementares de FII,
mas o motor histórico (`ReferenciaEm`) e o backtest (`universo_backtest`) não as passavam:
o índice em D ficava sem elas, e os defeitos de fonte já documentados (o código "4030" da
CSN no FCA, a espécie da MGLU3) voltavam no histórico. Corte temporal: a linha vale em D
quando as datas da sua evidência (`data` e, quando há, `ligacao_data`) são anteriores a D.

Tabelas reais (`correcoes.csv`, `identidades_fii.csv`); FCA sintético no layout oficial
com os códigos defeituosos da tabela, pela carga e pela montagem reais.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date

import pandas as pd
import pytest
from test_universo_pit import _fca_sintetico, _valor

from sentinela.data.referencia import universo
from sentinela.data.store import migracoes
from sentinela.services.historico import ReferenciaEm

CSN = "33.042.730/0001-04"
MGLU = "47.960.950/0001-21"
CADASTRO = pd.DataFrame(
    [{"CNPJ_CIA": c, "DENOM_SOCIAL": n, "SIT": "ATIVO", "CD_CVM": cd,
      "SETOR_ATIV": None, "CONTROLE_ACIONARIO": None}
     for c, n, cd in ((CSN, "CSN", "4030"), (MGLU, "MAGAZINE LUIZA", "22470"))]
)  # fmt: skip
ANTES_DA_MGLU, DEPOIS_DA_MGLU = date(2025, 6, 30), date(2026, 3, 2)


@pytest.fixture
def conn(tmp_path) -> Iterator[sqlite3.Connection]:
    """FCA 2025 com os defeitos da tabela: CSN com "4030" e MGLU3 como PNA."""
    with closing(sqlite3.connect(":memory:")) as banco:
        migracoes.aplicar(banco)
        _fca_sintetico(
            banco,
            tmp_path,
            [(CSN, "2025-01-01", "1", "2025-02-01"), (MGLU, "2025-01-01", "1", "2025-02-01")],
            [
                _valor(CNPJ_Companhia=CSN, Data_Referencia="2025-01-01",
                       Valor_Mobiliario="Ações Ordinárias", Codigo_Negociacao="4030",
                       Data_Inicio_Negociacao="2000-01-03"),
                _valor(CNPJ_Companhia=MGLU, Data_Referencia="2025-01-01",
                       Valor_Mobiliario="Ações Preferenciais",
                       Sigla_Classe_Acao_Preferencial="PNA", Codigo_Negociacao="MGLU3",
                       Data_Inicio_Negociacao="2011-05-02"),
            ],
            ano=2025,
        )  # fmt: skip
        yield banco


def test_referencia_do_motor_historico_aplica_a_correcao_vigente_em_d(conn):
    registros = ReferenciaEm(conn, ANTES_DA_MGLU, CADASTRO).indice(None).registros
    assert registros["CSNA3"].cnpj == CSN  # data da evidência 2025-01-01 < D


def test_correcao_de_especie_vale_so_depois_da_evidencia(conn):
    antes = universo.indice_em(conn, ANTES_DA_MGLU, CADASTRO).registros
    depois = universo.indice_em(conn, DEPOIS_DA_MGLU, CADASTRO).registros
    # a `data` da linha (2025-12-31, referência da DFP 2025) é posterior a D
    assert antes["MGLU3"].especie == "PN"
    assert depois["MGLU3"].especie == "ON"


def test_universo_do_backtest_identifica_pela_correcao(conn):
    lido = universo.universo_em(conn, ANTES_DA_MGLU, CADASTRO)
    assert "CSNA3" in {t["ticker"] for t in lido["universo"]}


def test_tabelas_explicitamente_vazias_seguem_sem_correcao(conn):
    """Controle: quem passa as tabelas (vazias) continua decidindo o que entra."""
    registros = universo.indice_em(
        conn, DEPOIS_DA_MGLU, CADASTRO, correcoes=(), identidades_fii=()
    ).registros
    assert "CSNA3" not in registros
    assert registros["MGLU3"].especie == "PN"
    # só as correções passadas: as identidades oficiais valem, as correções não
    so_correcoes = universo.indice_em(conn, DEPOIS_DA_MGLU, CADASTRO, correcoes=())
    assert "CSNA3" not in so_correcoes.registros


def test_corte_temporal_das_tabelas_oficiais():
    """A linha vale em D com `data` (e `ligacao_data`, quando há) anterior a D."""

    def tickers(dia):
        tabelas = universo.referencias_em(dia)
        return (
            sorted(c.ticker for c in tabelas["correcoes"]),
            sorted(i["ticker"] for i in tabelas["identidades_fii"]),
        )

    assert tickers(date(2025, 1, 1)) == ([], [])  # CSNA3 só a partir do dia seguinte
    assert tickers(date(2025, 1, 2)) == (["CSNA3"], [])
    # BPAC11: defeito de 2026-01-01, ligação conferida em 2026-10-19
    assert tickers(date(2026, 10, 19)) == (["CSNA3", "MGLU3", "TRXF11"], [])
    assert tickers(date(2026, 10, 26))[1] == []  # documento do mesmo dia de D: fora
    assert tickers(date(2026, 10, 27)) == (
        ["BPAC11", "CSNA3", "MGLU3", "TRXF11"],
        ["BTCI11", "TRPL11"],
    )


def test_data_fora_do_formato_iso_falha_em_vez_de_cortar(monkeypatch):
    """Data registrada fora de AAAA-MM-DD não pode ser comparada como texto."""
    from dataclasses import replace

    (csn,) = [c for c in universo.ler_correcoes() if c.ticker == "CSNA3"]
    monkeypatch.setattr(
        universo, "ler_correcoes", lambda: [replace(csn, data="01/01/2025")]
    )
    with pytest.raises(ValueError):
        universo.referencias_em(date(2025, 6, 30))
