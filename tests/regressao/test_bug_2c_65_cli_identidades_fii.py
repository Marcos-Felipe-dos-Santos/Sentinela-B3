"""BUG-2C-65: entrada python -m deve enriquecer o mesmo índice da cascata."""

import runpy
import sys

import pytest

from sentinela.data.referencia import carregar_indice, fontes
from tests.regressao.test_bug_2b_21_fiis_fora_do_informe import _cotacao
from tests.test_referencia import FONTES, _cadastro, _fca, _sem_fii


def executar_cli(tmp_path, monkeypatch):
    lidas = fontes.Fontes(
        [(2026, _fca())],
        _cadastro(),
        _sem_fii(),
        [_cotacao(), _cotacao("TRPL11", "BRTRPLCTF015")],
        FONTES,
        "2026-10-26",
        [],
    )
    monkeypatch.setattr(fontes, "carregar_fontes", lambda *args: lidas)
    monkeypatch.setattr(sys, "argv", ["referencia", "--pasta", str(tmp_path)])
    # Simula a entrada de processo novo, mesmo quando a coleta importou a CLI.
    monkeypatch.delitem(sys.modules, "sentinela.data.referencia.__main__", raising=False)
    with pytest.raises(SystemExit) as encerramento:
        runpy.run_module("sentinela.data.referencia", run_name="__main__")
    assert encerramento.value.code == 0
    return carregar_indice(tmp_path / "referencia")


def test_modulo_cli_grava_fiis_com_identidade_oficial(tmp_path, monkeypatch):
    indice = executar_cli(tmp_path, monkeypatch)
    assert indice.registros["BTCI11"].classe == "FII"
    assert indice.registros["TRPL11"].classe == "FII"


@pytest.mark.parametrize("falha", ["ausente", "futura"])
def test_cli_sem_identidade_elegivel_nao_promove_fii(tmp_path, monkeypatch, falha):
    ler = fontes.ler_identidades_fii

    def indisponivel():
        if falha == "ausente":
            raise FileNotFoundError("snapshot ausente")
        return [{**i, "data": "2027-01-01"} for i in ler()]

    monkeypatch.setattr(fontes, "ler_identidades_fii", indisponivel)
    indice = executar_cli(tmp_path, monkeypatch)
    assert indice.registros["BTCI11"].classe == "UNKNOWN"
    assert indice.registros["TRPL11"].classe == "UNKNOWN"
