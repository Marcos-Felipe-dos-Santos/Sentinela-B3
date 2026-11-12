"""F3-P14b: calendário anual de pregões para a regularidade de proventos (qualidade 1.0 §9).

Contrato em `docs/decisoes/calendario-proventos-3.md`. Os arquivos anuais do COTAHIST são
montados no leiaute oficial: o cabeçalho é o da fixture oficial (`cotahist_m092026_petrobras`),
com o nome e a data de geração trocados; os pregões são registros 01 de um papel sintético.
"""

import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

import pytest
from test_cotahist import _linha
from test_qualidade import AS_OF
from test_qualidade_inputs import dados as dados_qualidade

import config
from market_engine import MarketEngine
from sentinela.data import proventos_b3
from sentinela.data.providers import b3_cotahist
from sentinela.data.qualidade_inputs import entradas
from sentinela.data.store import migracoes
from sentinela.methods.qualidade import Qualidade

FIXTURE = (
    Path(__file__).parent / "fixtures" / "contratos" / "cotahist_m092026_petrobras.json"
)
COLETA = "2026-03-02T12:00:00+00:00"


def _cabecalho(ano: int, geracao: date) -> str:
    oficial = json.loads(FIXTURE.read_text(encoding="utf-8"))["membros"]
    linha = oficial["COTAHIST_M092026.TXT"].splitlines()[0]
    linha = linha[:2] + f"COTAHIST.{ano}" + linha[15:]
    return linha[:23] + geracao.strftime("%Y%m%d") + linha[31:]


def _dias_uteis(inicio: date, fim: date) -> list[date]:
    return [
        inicio + timedelta(days=n)
        for n in range((fim - inicio).days + 1)
        if (inicio + timedelta(days=n)).weekday() < 5
    ]


def _anual(pasta: Path, ano: int, geracao: date, ate: date | None = None) -> Path:
    fim = min(date(ano, 12, 31), ate or date(ano, 12, 31))
    linhas = [_cabecalho(ano, geracao)] + [
        _linha(DATA=d.strftime("%Y%m%d"), CODNEG="TSTA3", CODISI="BRTSTAACNOR1")
        for d in _dias_uteis(date(ano, 1, 1), fim)
    ]
    caminho = pasta / f"COTAHIST_A{ano}.ZIP"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr(
            f"COTAHIST_A{ano}.TXT", ("\n".join(linhas) + "\n").encode("latin-1")
        )
    return caminho


def _banco(caminho_db: Path, pasta: Path, anos=range(2020, 2026), parcial=None):
    with closing(sqlite3.connect(caminho_db)) as conn:
        migracoes.aplicar(conn)
        for ano in anos:
            arquivo = _anual(pasta, ano, date(ano + 1, 1, 2))
            b3_cotahist.carregar(
                conn, arquivo, fonte=f"b3:{arquivo.name}", coleta=COLETA
            )
        if parcial is not None:
            arquivo = _anual(pasta, parcial.year, parcial, ate=parcial)
            b3_cotahist.carregar(
                conn, arquivo, fonte=f"b3:{arquivo.name}", coleta=COLETA
            )
        conn.commit()


# --- Produtor puro ------------------------------------------------------------------------


def _carga(ano, geracao, coleta=COLETA, arquivo=None):
    return {
        "arquivo": f"COTAHIST_A{ano}.ZIP" if arquivo is None else arquivo,
        "data_geracao": geracao,
        "coleta": coleta,
        "hash_sha256": f"h{ano}",
    }


def test_calendario_com_os_anos_cobertos():
    pregoes = [date(2024, 12, 30), date(2025, 1, 2), date(2025, 6, 2), date(2026, 1, 5)]
    cargas = [
        _carga(2024, "2025-01-02", coleta="2026-01-01T00:00:00+00:00"),
        _carga(2025, "2026-01-02"),
        _carga(
            2025, "2025-07-01", coleta="2027-01-01T00:00:00+00:00"
        ),  # mais velha: perde
        _carga(2025, "2026-01-05", arquivo="COTAHIST_M012025.ZIP"),  # mensal: ignorada
    ]
    lido = proventos_b3.calendario_anual(
        pregoes, cargas, date(2024, 12, 25), date(2025, 12, 31)
    )
    assert lido == {
        "fonte": "B3, COTAHIST anual: COTAHIST_A2024.ZIP (sha256 h2024); "
        "COTAHIST_A2025.ZIP (sha256 h2025)",
        "coleta": COLETA,
        "inicio": "2024-12-25",
        "fim": "2025-12-31",
        "pregoes": ["2024-12-30", "2025-01-02", "2025-06-02"],
    }


@pytest.mark.parametrize(
    ("cargas", "fim", "motivo"),
    [
        ([_carga(2025, "2026-01-02")], date(2025, 12, 31),
         "calendário anual B3 sem a carga do COTAHIST anual de 2024"),
        ([_carga(2024, "2024-12-30"), _carga(2025, "2026-01-02")], date(2025, 12, 31),
         "calendário anual B3: COTAHIST anual de 2024 gerado em 2024-12-30, antes de 2024-12-31"),
        ([_carga(2024, "2025-01-02"), _carga(2025, "2025-06-01")], date(2025, 6, 2),
         "calendário anual B3: COTAHIST anual de 2025 gerado em 2025-06-01, antes de 2025-06-02"),
    ],
)  # fmt: skip
def test_ano_sem_carga_anual_encerrada_abstem(cargas, fim, motivo):
    lido = proventos_b3.calendario_anual(
        [date(2025, 1, 2)], cargas, date(2024, 12, 25), fim
    )
    assert lido == proventos_b3.Abstencao(motivo)


def test_ano_corrente_coberto_ate_a_geracao_e_sem_pregao_abstem():
    cargas = [_carga(2026, "2026-06-01")]
    ok = proventos_b3.calendario_anual(
        [date(2026, 5, 4)], cargas, date(2026, 1, 1), date(2026, 6, 1)
    )
    assert ok["pregoes"] == ["2026-05-04"]
    vazio = proventos_b3.calendario_anual(
        [date(2025, 5, 4)], cargas, date(2026, 1, 1), date(2026, 6, 1)
    )
    assert vazio == proventos_b3.Abstencao(proventos_b3.MOTIVO_CALENDARIO_VAZIO)


@pytest.mark.parametrize(
    "nome",
    [
        "COTAHIST_A24.ZIP",
        "COTAHIST_AXXXX.ZIP",
        "OUTRO_A2024.ZIP",
        "",
        "COTAHIST_A2024.TXT",
        "XXXXXXXXXX2024.ZIP",
    ],
)
def test_nome_fora_do_arquivo_anual_nao_cobre(nome):
    lido = proventos_b3.calendario_anual(
        [date(2024, 6, 3)], [_carga(2024, "2025-01-02", arquivo=nome)], date(2024, 6, 1),
        date(2024, 6, 30),
    )  # fmt: skip
    assert lido == proventos_b3.Abstencao(
        proventos_b3.MOTIVO_CALENDARIO_SEM_ANO.format(ano=2024)
    )


def test_calendario_do_banco_sem_conexao():
    lido = proventos_b3.calendario_do_banco(None, date(2024, 1, 1), date(2024, 2, 1))
    assert lido == proventos_b3.Abstencao(proventos_b3.MOTIVO_CALENDARIO_BANCO)


# --- Banco único com os arquivos anuais no leiaute oficial ---------------------------------


def test_calendario_do_banco_pelos_arquivos_anuais(tmp_path):
    _banco(tmp_path / "s.db", tmp_path, anos=(2024, 2025), parcial=date(2026, 1, 9))
    with closing(sqlite3.connect(tmp_path / "s.db")) as conn:
        lido = proventos_b3.calendario_do_banco(
            conn, date(2024, 12, 25), date(2026, 1, 7)
        )
        assert (
            lido["pregoes"][0] == "2024-12-25" and lido["pregoes"][-1] == "2026-01-07"
        )
        assert lido["pregoes"] == [
            d.isoformat() for d in _dias_uteis(date(2024, 12, 25), date(2026, 1, 7))
        ]
        assert lido["coleta"] == COLETA and "COTAHIST_A2026.ZIP" in lido["fonte"]
        alem = proventos_b3.calendario_do_banco(
            conn, date(2024, 12, 25), date(2026, 1, 12)
        )
        assert alem.motivo.startswith(
            "calendário anual B3: COTAHIST anual de 2026 gerado em"
        )


# --- Produtor real → qualidade_inputs → motor ----------------------------------------------


def _dados_sem_calendario():
    d = dados_qualidade()
    d.pop("calendario_proventos_b3")
    return d


def test_produtor_real_ate_o_motor(tmp_path, monkeypatch):
    _banco(tmp_path / "s.db", tmp_path, parcial=date(2026, 1, 9))
    monkeypatch.setattr(
        config, "_conexao_series_macro", lambda: sqlite3.connect(tmp_path / "s.db")
    )
    d = _dados_sem_calendario()
    MarketEngine._calendario_proventos_b3("TSTA3", d)
    calendario = d["calendario_proventos_b3"]
    assert (calendario["inicio"], calendario["fim"]) == ("2020-12-25", "2026-01-07")
    assert "calendario_proventos_b3_motivo" not in d
    registros = entradas(d, AS_OF)
    assert [r["proventos_b3"]["valor"] for r in registros] == [0, 1.0, 0, 0, 0]
    assert all(r["proventos_b3"]["cobertura_integral"] for r in registros)
    quadro = Qualidade().calcular(
        registros, as_of=AS_OF, classe="STOCK", modelo="empresa"
    )
    assert (quadro["proventos"]["positivos"], quadro["proventos"]["observados"]) == (
        1,
        5,
    )


def test_ano_sem_cobertura_tem_motivo_e_nao_zero(tmp_path, monkeypatch):
    _banco(
        tmp_path / "s.db",
        tmp_path,
        anos=(2020, 2021, 2023, 2024, 2025),
        parcial=date(2026, 1, 9),
    )
    monkeypatch.setattr(
        config, "_conexao_series_macro", lambda: sqlite3.connect(tmp_path / "s.db")
    )
    d = _dados_sem_calendario()
    MarketEngine._calendario_proventos_b3("TSTA3", d)
    assert "calendario_proventos_b3" not in d
    assert d[
        "calendario_proventos_b3_motivo"
    ] == proventos_b3.MOTIVO_CALENDARIO_SEM_ANO.format(ano=2022)
    registros = entradas(d, AS_OF)
    assert all(r["proventos_b3"]["valor"] is None for r in registros)
    assert all("calendário" in r["proventos_b3"]["motivo"] for r in registros)


def test_sem_banco_ou_sem_serie_a_chave_fica_ausente(monkeypatch):
    d = _dados_sem_calendario()
    MarketEngine._calendario_proventos_b3(
        "TSTA3", d
    )  # conftest: banco único indisponível
    assert "calendario_proventos_b3" not in d
    assert d["calendario_proventos_b3_motivo"] == proventos_b3.MOTIVO_CALENDARIO_BANCO
    chamadas = []
    monkeypatch.setattr(config, "_conexao_series_macro", lambda: chamadas.append(1))
    for serie in (None, {"exercicios": []}, {"exercicios": [{"inicio": "x"}]}):
        sem = {"serie_cvm": serie}
        MarketEngine._calendario_proventos_b3("TSTA3", sem)
        assert sem == {"serie_cvm": serie}
    assert chamadas == []


def test_erro_do_banco_vira_motivo(monkeypatch):
    class Quebrada:
        def execute(self, *a):
            raise sqlite3.OperationalError("no such table: precos")

        def close(self):
            Quebrada.fechada = True

    monkeypatch.setattr(config, "_conexao_series_macro", lambda: Quebrada())
    d = _dados_sem_calendario()
    MarketEngine._calendario_proventos_b3("TSTA3", d)
    assert d["calendario_proventos_b3_motivo"] == (
        "calendário anual B3 indisponível: no such table: precos"
    )
    assert Quebrada.fechada is True


def test_carga_sem_data_de_geracao_nao_cobre():
    lido = proventos_b3.calendario_anual(
        [date(2024, 6, 3)], [_carga(2024, None)], date(2024, 6, 1), date(2024, 6, 30)
    )
    assert lido == proventos_b3.Abstencao(
        proventos_b3.MOTIVO_CALENDARIO_SEM_ANO.format(ano=2024)
    )
