"""BUG-2B-42: reserva antiga do COTAHIST ocultava falha de download do gate."""

import os
import zipfile
from datetime import UTC, date, datetime, timedelta

import requests

from sentinela.data import liquidez
from sentinela.data.providers import b3_cotahist as cot
from tests.test_cotahist import _linha


def test_cache_antigo_apos_falha_nao_aplica_o_gate(tmp_path, monkeypatch):
    for mes in (7, 8, 9, 10):
        linhas = []
        dia = date(2026, mes, 1)
        while dia.month == mes:
            if dia.weekday() < 5 and mes != 10:
                linhas.append(
                    _linha(
                        DATA=dia.strftime("%Y%m%d"),
                        CODNEG="TSTC3",
                        VOLTOT="000000000000010000",
                    )
                )
            dia += timedelta(days=1)
        caminho = tmp_path / f"COTAHIST_M{mes:02d}2026.ZIP"
        with zipfile.ZipFile(caminho, "w") as z:
            z.writestr("COTAHIST.TXT", "\n".join(linhas))
        coleta = datetime(2026, 10, 1 if mes == 10 else 10, 12, tzinfo=UTC).timestamp()
        os.utime(caminho, (coleta, coleta))

    def falhar(*args, **kwargs):
        raise requests.ConnectionError("fonte indisponível")

    monkeypatch.setattr(cot, "baixar_arquivo", falhar)
    coleta = cot.HistoricoRecente(tmp_path, meses=4).coletar(
        datetime(2026, 10, 21, 12, tzinfo=UTC)
    )
    assert "10/2026" in coleta.meses_ausentes
    bloco = liquidez.metricas(
        coleta.cotacoes, "TSTC3", meses_ausentes=coleta.meses_ausentes
    )
    assert bloco["janelas"]["63"]["incompleta"] is False
    resultado = liquidez.avaliar(bloco, janela=63, presenca_min=0.8, volume_min=500000)
    assert "aviso" in resultado
    assert "abstencao" not in resultado
    assert (tmp_path / "COTAHIST_M102026.ZIP").exists()
