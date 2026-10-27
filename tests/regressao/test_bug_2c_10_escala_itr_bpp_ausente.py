"""BUG-2C-10: escala do ITR reserva lucro total sem BPP efetivamente lido.

D20, ficha por ação1.1 e F2C-29: ausência do arquivo não demonstra ausência de
minoritários. Ler controlador explícito continua independente do BPP da reserva.
"""

from pathlib import Path

import pandas as pd
import pytest

from cvm_provider import CVMProvider
from sentinela.data.acoes_cvm import Composicao


def fonte_do_itr(tmp_path, monkeypatch, controladora=0, falha_bpp=FileNotFoundError):
    base = {
        "CNPJ_CIA": "00.000.000/0001-00",
        "DT_REFER": "2026-06-30",
        "VERSAO": "1",
        "ORDEM_EXERC": "ÚLTIMO",
        "DT_INI_EXERC": "2026-01-01",
        "ESCALA_MOEDA": "MIL",
    }
    contas = [
        ("3.11", "Lucro/Prejuízo Consolidado do Período", 100),
        ("3.11.01", "Atribuído a Sócios da Empresa Controladora", controladora),
        ("3.11.02", "Atribuído a Sócios Não Controladores", 0),
        ("3.99.01.01", "ON", 2),
    ]
    dre = pd.DataFrame(
        [{**base, "CD_CONTA": c, "DS_CONTA": d, "VL_CONTA": v} for c, d, v in contas]
    )
    p = CVMProvider(cache_dir=str(tmp_path / "cache"))

    def ler(caminho, tipo):
        if tipo == "BPP_con":
            raise falha_bpp("BPP ausente ou ilegível")
        return dre.copy()

    monkeypatch.setattr(p, "_read_raw", ler)
    composicao = Composicao(40_000, 0, 0, 0, 0, "2026-06-30", "1")
    return p, (
        Path(tmp_path) / "itr.zip",
        "00.000.000/0001-00",
        "2026-06-30",
        "1",
        composicao,
    )


def test_escala_sem_bpp_nao_reserva_o_lucro_total(tmp_path, monkeypatch):
    p, args = fonte_do_itr(tmp_path, monkeypatch)
    assert p._escala_da_composicao(*args) is None


def test_escala_com_lucro_direto_independe_do_bpp_da_reserva(tmp_path, monkeypatch):
    p, args = fonte_do_itr(tmp_path, monkeypatch, 80)
    assert p._escala_da_composicao(*args) is not None


@pytest.mark.parametrize("falha_bpp", [OSError, KeyError, ValueError])
def test_falha_bpp_nao_apaga_lucro_direto(tmp_path, monkeypatch, falha_bpp):
    p, args = fonte_do_itr(tmp_path, monkeypatch, 80, falha_bpp)
    assert p._escala_da_composicao(*args) is not None
