"""BUG-2A-19: os arquivos do IF.data não registram a proveniência da D16.

`IFDataProvider._buscar` grava a resposta em `data/ifdata/<hash>.json` sem o arquivo lateral
`.proveniencia.json` (data da coleta e hash; `sentinela/data/proveniencia.py`), e o `Capital`
devolvido não carrega proveniência. Origem: 2ª passada do Gemini (15/10/2026), conferida pelo
Claude no código em 18/10/2026.
"""

from datetime import date

import pytest

from sentinela.data import proveniencia
from sentinela.data.providers import ifdata
from tests.test_cvm_bancos import CADASTRO_BB, CAPITAL_BB


class _Resposta:
    def __init__(self, valor):
        self._valor = valor

    def raise_for_status(self):
        return None

    def json(self):
        return {"value": self._valor}


def _get_falso(url, timeout):
    return _Resposta(CAPITAL_BB if "IfDataValores" in url else CADASTRO_BB)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-19 · arquivos do IF.data sem a proveniência da D16, e o Capital sem ela "
        "· corrige: F2B-44"
    ),
)
def test_arquivo_do_ifdata_tem_registro_lateral_e_capital_a_carrega(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(ifdata.requests, "get", _get_falso)
    capital = ifdata.IFDataProvider(cache_dir=str(tmp_path)).capital(
        "00.000.000/0001-91", date(2026, 10, 13)
    )
    assert capital.basileia == pytest.approx(0.151297835513664)
    baixados = [
        p for p in tmp_path.iterdir() if not p.name.endswith(proveniencia.SUFIXO)
    ]
    assert baixados
    assert all(proveniencia.caminho_lateral(p).exists() for p in baixados)
    assert getattr(capital, "proveniencia", None) is not None
