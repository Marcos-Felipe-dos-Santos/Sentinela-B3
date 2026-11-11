"""BUG-3-19: linha duplicada no CSV do Tesouro derruba o `gravar_series` inteiro.

Auditoria externa do Gemini sobre 284165f..419f010, achado 2 (11/11/2026): o `_tesouro` grava
uma linha de `series_macro` por linha do CSV; duas linhas do mesmo título e data-base dão a
mesma chave (série, data, coleta), e o `sqlite3.IntegrityError` não é capturado por `familia`:
a gravação para antes da ANBIMA, do Focus, do IPCA e da Selic. Linha malformada de título fora
da cesta (que `tesouro.ler_csv` ignora) também derruba a família. Corrige: F3-A-F7.
"""

import sqlite3
from contextlib import closing

import pytest
from test_macro_por_data import _sgs_oficial
from test_taxa_real_data_passada import COLETA, JANELA, D, _provedor

from sentinela.data.providers import macro
from sentinela.data.store import migracoes

_ARQUIVO = ("macro", "tesouro", "precotaxatesourodireto.csv")


def _gravar_com(tmp_path, monkeypatch, alterar):
    provedor, _ = _provedor(tmp_path, monkeypatch, COLETA)
    original = provedor.baixar

    def baixar(url, instante):
        if "bcdata.sgs" in url:
            return macro.SnapshotMacro(
                _sgs_oficial(url).text, url, instante.isoformat(), "b" * 64
            )
        if "fer_nacionais/2025" in url:
            raise OSError("ANBIMA 2025 fora da fixture")
        return original(url, instante)

    monkeypatch.setattr(provedor, "baixar", baixar)
    caminho = tmp_path.joinpath(*_ARQUIVO)
    caminho.write_text(alterar(caminho.read_text(encoding="utf-8")), encoding="utf-8")
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        return macro.gravar_series(
            conn, provedor, coleta=COLETA, datas=[D.date()], janela=JANELA
        )


@pytest.mark.xfail(
    strict=True,
    raises=sqlite3.IntegrityError,
    reason="BUG-3-19 · linha duplicada do Tesouro derruba o gravar_series · corrige: F3-A-F7",
)
def test_linha_duplicada_nao_derruba_as_outras_familias(tmp_path, monkeypatch):
    def duplicar(texto):
        linhas = texto.splitlines(keepends=True)
        ntnb = next(
            l for l in linhas if l.startswith("Tesouro IPCA+ com Juros Semestrais")
        )
        return texto + ntnb

    resumo = _gravar_com(tmp_path, monkeypatch, duplicar)
    for familia in ("tesouro", "anbima", "focus", "ipca", "selic"):
        assert isinstance(resumo[familia], int), familia


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG-3-19 · título fora da cesta malformado derruba o Tesouro · corrige: F3-A-F7",
)
def test_titulo_fora_da_cesta_malformado_nao_derruba_o_tesouro(tmp_path, monkeypatch):
    def fora_da_cesta(texto):
        cabecalho = texto.splitlines()[0]
        colunas = cabecalho.split(";")
        campos = dict.fromkeys(colunas, "")
        campos.update(
            {
                "Tipo Titulo": "Tesouro Selic",
                "Data Vencimento": "01/03/2029",
                "Data Base": "lixo",
            }
        )
        return texto.rstrip("\n") + "\n" + ";".join(campos[c] for c in colunas) + "\n"

    resumo = _gravar_com(tmp_path, monkeypatch, fora_da_cesta)
    assert isinstance(resumo["tesouro"], int), resumo["tesouro"]
