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


def _com_dre(caminho, linhas_dre):
    with ZipFile(caminho, "a") as z:
        z.writestr(
            "itr_cia_aberta_DRE_con_2026.csv",
            _csv(
                [
                    "CNPJ_CIA",
                    "DT_REFER",
                    "VERSAO",
                    "ORDEM_EXERC",
                    "DT_INI_EXERC",
                    "ESCALA_MOEDA",
                    "CD_CONTA",
                    "DS_CONTA",
                    "VL_CONTA",
                ],
                [(CNPJ, "2026-06-30", "1", "ÚLTIMO", *linha) for linha in linhas_dre],
            ),
        )
    instante = datetime(2026, 10, 19, tzinfo=UTC).timestamp()
    os.utime(caminho, (instante, instante))


DRE_SEMESTRE = [
    # trimestre e acumulado do exercício: vale o acumulado (menor DT_INI_EXERC)
    (
        "2026-04-01",
        "MIL",
        "3.11.01",
        "Atribuído a Sócios da Empresa Controladora",
        "500",
    ),
    ("2026-04-01", "MIL", "3.99.01.01", "ON", "0.25"),
    (
        "2026-01-01",
        "MIL",
        "3.11.01",
        "Atribuído a Sócios da Empresa Controladora",
        "2040",
    ),
    ("2026-01-01", "MIL", "3.99.01.01", "ON", "2.00"),
]


@pytest.mark.parametrize("acoes,escala", [(1020, "MIL"), (1_020_000, "UNIDADE")])
def test_escala_do_documento_recente_pela_regra_da_dfp(fonte, acoes, escala):
    # F2B-54 (auditoria D30 do F2B-1): lucro do acumulado ÷ ações contra o LPA divulgado.
    p, arquivo, caminhos = fonte
    caminhos["itr", 2026] = arquivo(
        "itr",
        2026,
        [(CNPJ, "2026-06-30", "1", "2026-08-10")],
        [(CNPJ, "2026-06-30", "1", acoes, 0, 0, 0, 0)],
    )
    _com_dre(caminhos["itr", 2026], DRE_SEMESTRE)
    r = p.composicao_mais_recente(CNPJ, ASOF, 2025)
    assert r["escala"] == escala


def test_escala_do_documento_recente_indeterminada(fonte):
    p, arquivo, caminhos = fonte
    caminhos["itr", 2026] = arquivo(
        "itr",
        2026,
        [(CNPJ, "2026-06-30", "1", "2026-08-10")],
        [(CNPJ, "2026-06-30", "1", 1020, 0, 0, 0, 0)],
    )
    r = p.composicao_mais_recente(CNPJ, ASOF, 2025)
    assert r["composicao"].total == 1020
    assert r["escala"] is None


def test_escala_sem_lucro_dos_controladores_separado_fica_indeterminada(fonte):
    # Revisão do F2B-54: lucro pela regra da DFP (D20). Sem a linha dos controladores e
    # com minoritários no PL, o consolidado não serve; a escala fica indeterminada.
    p, arquivo, caminhos = fonte
    caminhos["itr", 2026] = arquivo(
        "itr",
        2026,
        [(CNPJ, "2026-06-30", "1", "2026-08-10")],
        [(CNPJ, "2026-06-30", "1", 1020, 0, 0, 0, 0)],
    )
    _com_dre(
        caminhos["itr", 2026],
        [
            (
                "2026-01-01",
                "MIL",
                "3.11",
                "Lucro/Prejuízo Consolidado do Período",
                "2040",
            ),
            ("2026-01-01", "MIL", "3.99.01.01", "ON", "2.00"),
        ],
    )
    with ZipFile(caminhos["itr", 2026], "a") as z:
        z.writestr(
            "itr_cia_aberta_BPP_con_2026.csv",
            _csv(
                [
                    "CNPJ_CIA",
                    "DT_REFER",
                    "VERSAO",
                    "ORDEM_EXERC",
                    "ESCALA_MOEDA",
                    "CD_CONTA",
                    "DS_CONTA",
                    "VL_CONTA",
                ],
                [
                    (
                        CNPJ,
                        "2026-06-30",
                        "1",
                        "ÚLTIMO",
                        "MIL",
                        "2.03.09",
                        "Participação dos Acionistas Não Controladores",
                        "500",
                    )
                ],
            ),
        )
    instante = datetime(2026, 10, 19, tzinfo=UTC).timestamp()
    os.utime(caminhos["itr", 2026], (instante, instante))
    assert p.composicao_mais_recente(CNPJ, ASOF, 2025)["escala"] is None


def test_escala_com_controladores_zerados_sem_minoritarios_usa_o_consolidado(fonte):
    # KLBN11 e BRBI11 no ITR de 30/06/2026: 3.11.01 zerada e sem não controladores; a
    # reserva da D20 é o consolidado, como na DFP.
    p, arquivo, caminhos = fonte
    caminhos["itr", 2026] = arquivo(
        "itr",
        2026,
        [(CNPJ, "2026-06-30", "1", "2026-08-10")],
        [(CNPJ, "2026-06-30", "1", 1020, 0, 0, 0, 0)],
    )
    _com_dre(
        caminhos["itr", 2026],
        [
            (
                "2026-01-01",
                "MIL",
                "3.11",
                "Lucro/Prejuízo Consolidado do Período",
                "2040",
            ),
            (
                "2026-01-01",
                "MIL",
                "3.11.01",
                "Atribuído a Sócios da Empresa Controladora",
                "0",
            ),
            (
                "2026-01-01",
                "MIL",
                "3.11.02",
                "Atribuído a Sócios Não Controladores",
                "0",
            ),
            ("2026-01-01", "MIL", "3.99.01.01", "ON", "2.00"),
        ],
    )
    assert p.composicao_mais_recente(CNPJ, ASOF, 2025)["escala"] == "MIL"


def test_escala_com_moeda_em_unidade(fonte):
    p, arquivo, caminhos = fonte
    caminhos["itr", 2026] = arquivo(
        "itr",
        2026,
        [(CNPJ, "2026-06-30", "1", "2026-08-10")],
        [(CNPJ, "2026-06-30", "1", 1020, 0, 0, 0, 0)],
    )
    _com_dre(
        caminhos["itr", 2026],
        [
            (
                "2026-01-01",
                "UNIDADE",
                "3.11.01",
                "Atribuído a Sócios da Empresa Controladora",
                "2040000",
            ),
            ("2026-01-01", "UNIDADE", "3.99.01.01", "ON", "2.00"),
        ],
    )
    assert p.composicao_mais_recente(CNPJ, ASOF, 2025)["escala"] == "MIL"
