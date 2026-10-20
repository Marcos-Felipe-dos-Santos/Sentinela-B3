"""Gordon1.1: documento elegível selecionado pelo índice de entregas da CVM."""

import csv
import io
import os
from datetime import UTC, datetime
from zipfile import ZipFile

import pytest

from cvm_provider import CVMProvider

CNPJ = "11.111.111/0001-11"
ASOF = datetime(2026, 10, 20, 18, tzinfo=UTC)


def _csv(colunas, linhas):
    f = io.StringIO()
    w = csv.writer(f, delimiter=";")
    w.writerow(colunas)
    w.writerows(linhas)
    return f.getvalue().encode("latin-1")


@pytest.fixture
def fonte(tmp_path, monkeypatch):
    def arquivo(tipo, ano, documentos=(), composicoes=()):
        p = tmp_path / f"{tipo}_{ano}.zip"
        with ZipFile(p, "w") as z:
            z.writestr(
                f"{tipo}_cia_aberta_{ano}.csv",
                _csv(["CNPJ_CIA", "DT_REFER", "VERSAO", "DT_RECEB"], documentos),
            )
            z.writestr(
                f"{tipo}_cia_aberta_composicao_capital_{ano}.csv",
                _csv(
                    [
                        "CNPJ_CIA",
                        "DT_REFER",
                        "VERSAO",
                        "QT_ACAO_ORDIN_CAP_INTEGR",
                        "QT_ACAO_PREF_CAP_INTEGR",
                        "QT_ACAO_ORDIN_TESOURO",
                        "QT_ACAO_PREF_TESOURO",
                        "QT_ACAO_TOTAL_TESOURO",
                    ],
                    composicoes,
                ),
            )
        instante = datetime(2026, 10, 19, tzinfo=UTC).timestamp()
        os.utime(p, (instante, instante))
        return p

    caminhos = {(t, a): arquivo(t, a) for t in ("dfp", "itr") for a in (2025, 2026)}
    p = CVMProvider(tmp_path / "cache")
    monkeypatch.setattr(p, "baixar_dfp", lambda ano: caminhos["dfp", ano])
    monkeypatch.setattr(p, "baixar_itr", lambda ano: caminhos["itr", ano])
    caminhos["dfp", 2025] = arquivo(
        "dfp",
        2025,
        [(CNPJ, "2025-12-31", "1", "2026-02-12")],
        [(CNPJ, "2025-12-31", "1", 1000, 0, 0, 0, 0)],
    )
    return p, arquivo, caminhos


def test_ultima_referencia_e_maior_versao_entregue_antes_do_corte(fonte):
    p, arquivo, caminhos = fonte
    caminhos["itr", 2026] = arquivo(
        "itr",
        2026,
        [
            (CNPJ, "2026-06-30", "1", "2026-08-10"),
            (CNPJ, "2026-06-30", "2", "2026-10-20"),
            (CNPJ, "2026-09-30", "1", "2026-11-10"),
        ],
        [
            (CNPJ, "2026-06-30", "1", 1020, 0, 0, 0, 0),
            (CNPJ, "2026-06-30", "2", 2000, 0, 0, 0, 0),
        ],
    )
    r = p.composicao_mais_recente(CNPJ, ASOF, 2025)
    assert r["composicao"].total == 1020
    assert r["composicao"].dt_refer == "2026-06-30"
    assert r["proveniencia"]["documento"] == "ITR"
    assert r["proveniencia"]["data_entrega"] == "2026-08-10"
    assert r["proveniencia"]["versao"] == "1"
    assert "itr_cia_aberta_2026.zip" in r["proveniencia"]["fonte"]


def test_ultima_entrega_sem_composicao_abstem_sem_voltar_a_dfp(fonte):
    p, arquivo, caminhos = fonte
    caminhos["itr", 2026] = arquivo(
        "itr", 2026, [(CNPJ, "2026-06-30", "1", "2026-08-10")]
    )
    r = p.composicao_mais_recente(CNPJ, ASOF, 2025)
    assert "abstencao" in r
    assert r["proveniencia"]["periodo_referencia"] == "2026-06-30"


def test_so_dfp_elegivel_e_ausencia_de_identidade(fonte):
    p, _, _ = fonte
    r = p.composicao_mais_recente(CNPJ, ASOF, 2025)
    assert r["composicao"].total == 1000
    assert r["proveniencia"]["documento"] == "DFP"
    assert "abstencao" in p.composicao_mais_recente("22.222.222/0001-22", ASOF, 2025)


def test_falha_de_consulta_nao_certifica_ausencia_de_documento_recente(
    fonte, monkeypatch
):
    p, _, _ = fonte

    def indisponivel(ano):
        raise OSError("consulta indisponível")

    monkeypatch.setattr(p, "baixar_itr", indisponivel)
    r = p.composicao_mais_recente(CNPJ, ASOF, 2025)
    assert r == {"abstencao": "não foi possível conferir a composição mais recente"}
