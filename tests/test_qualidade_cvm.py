"""BPP comparativo público de Ambev: PL inicial independe de DVA."""

import pytest

from tests.test_gordon_documento import documento as _documento


@pytest.fixture
def documento(tmp_path, monkeypatch):
    return _documento.__wrapped__(tmp_path, monkeypatch)


def ler(documento):
    p, ind = documento
    return p.pl_inicial_do_documento(
        p.baixar_dfp(2025),
        23264,
        ind["cvm_dt_refer"],
        ind["cvm_versao"],
        "2025-01-01",
        "empresa",
    )


def test_pl_inicial_qualidade_independe_dva(documento, monkeypatch):
    p, _ = documento
    original = p._read_raw

    def sem_dva(arquivo, tipo):
        assert tipo != "DVA_con"
        return original(arquivo, tipo)

    monkeypatch.setattr(p, "_read_raw", sem_dva)
    r = ler(documento)
    assert r["valor"] == 98642139000.0
    assert r["proveniencia"]["data_saldo"] == "2024-12-31"
    assert r["proveniencia"]["demonstrativo"] == "BPP_con PENÚLTIMO"


@pytest.mark.parametrize(
    "campo,valor", [("cvm_dt_refer", "2024-12-31"), ("cvm_versao", "99")]
)
def test_outro_documento_nao_serve(documento, campo, valor):
    documento[1][campo] = valor
    r = ler(documento)
    assert r["valor"] is None and r["motivo"]


def test_sem_bpp_comparativo_nao_usa_pl_final(documento, monkeypatch):
    p, _ = documento
    original = p._read_raw

    def sem_inicial(arquivo, tipo):
        df = original(arquivo, tipo)
        return df[df["ORDEM_EXERC"] != "PENÚLTIMO"] if tipo == "BPP_con" else df

    monkeypatch.setattr(p, "_read_raw", sem_inicial)
    assert ler(documento)["valor"] is None


def test_escala_comparativa_desconhecida(documento, monkeypatch):
    p, _ = documento
    original = p._read_raw

    def escala(arquivo, tipo):
        df = original(arquivo, tipo).copy()
        if tipo == "BPP_con":
            df["ESCALA_MOEDA"] = "desconhecida"
        return df

    monkeypatch.setattr(p, "_read_raw", escala)
    r = ler(documento)
    assert r["valor"] is None and "escala" in r["motivo"]
