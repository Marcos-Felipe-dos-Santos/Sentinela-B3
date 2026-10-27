"""BUG-2C-09: formato inválido na leitura LPA/reserva sai da fronteira da escala.

Ficha por ação1.1 e F2C-31: CSV sem colunas do contrato não determina escala;
KeyError de campo da fonte deve produzir indeterminação, não queda da análise.
"""

import pandas as pd
import pytest

from cvm_provider import CVMProvider
from sentinela.data.acoes_cvm import Composicao


@pytest.mark.parametrize("coluna", ["CD_CONTA", "DS_CONTA"])
def test_formato_incompleto_abstem_escala(tmp_path, monkeypatch, coluna):
    p = CVMProvider(cache_dir=str(tmp_path / "cache"))
    linha = {
        "CNPJ_CIA": "00.000.000/0001-00",
        "DT_REFER": "2026-06-30",
        "VERSAO": "1",
        "ORDEM_EXERC": "ÚLTIMO",
        "DT_INI_EXERC": "2026-01-01",
        "VL_CONTA": "2",
        "ESCALA_MOEDA": "MIL",
        "CD_CONTA": "3.99.01.01",
        "DS_CONTA": "ON",
    }
    linha.pop(coluna)
    monkeypatch.setattr(p, "_read_raw", lambda *a: pd.DataFrame([linha]))
    composicao = Composicao(100, 0, 0, 0, 0, "2026-06-30", "1")
    assert (
        p._escala_da_composicao(
            tmp_path / "itr.zip", "00.000.000/0001-00", "2026-06-30", "1", composicao
        )
        is None
    )
