"""Marcador 2B §2.2: fuso local e data sem horário após o fim do dia."""

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from sentinela.data import proveniencia
from sentinela.data.providers import tesouro


@pytest.mark.xfail(
    strict=True, reason="BUG-2B-16 · corte local do Tesouro · corrige: F2B-47"
)
@pytest.mark.parametrize(
    "caso", ["publicacao_so_com_data", "referencia_futura_no_fuso_local"]
)
def test_tesouro_respeita_corte_local_e_fim_do_dia(tmp_path, caso):
    instante = datetime(2026, 10, 19, 18, tzinfo=UTC)
    base = "15/10/2026"
    if caso == "referencia_futura_no_fuso_local":
        instante = datetime(2026, 10, 20, 2, tzinfo=UTC)  # ainda 19/10 em São Paulo
        base = "20/10/2026"
    texto = (
        "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha\n"
        f"Tesouro IPCA+;15/05/2035;{base};6,84;6,96\n"
    )
    arquivo = tmp_path / "precotaxatesourodireto.csv"
    arquivo.write_text(texto)
    coleta = (instante - timedelta(hours=2)).timestamp()
    os.utime(arquivo, (coleta, coleta))
    registro = proveniencia.registrar_arquivo(
        arquivo, tesouro.URL, "Tesouro Direto", None
    )
    if caso == "publicacao_so_com_data":
        registro = replace(registro, data_entrega="2026-10-19", motivo_sem_entrega=None)
    with pytest.raises(ValueError):
        tesouro.ler_snapshot(tesouro.ArquivoTesouro(arquivo, registro), as_of=instante)
