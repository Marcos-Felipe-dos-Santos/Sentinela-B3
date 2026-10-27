"""BUG-2C-23: abstenção documental não deve aparecer como datas None."""

import pytest
from apoio_bancos import enriquecer_bancos

from tests.test_rastreabilidade import _contexto
from tests.test_valuation_bancos import BANCO


def test_documento_bancario_ausente_mostra_motivo():
    dados = enriquecer_bancos(BANCO)
    dados["gordon_cvm"] = {"abstencao": "DFP anual indisponível: arquivo ausente"}
    fonte = dict(_contexto(dados)["fontes"])["DFP da lente de bancos"]
    assert "None" not in fonte
    assert "DFP anual indisponível: arquivo ausente" in fonte


@pytest.mark.parametrize("fato", [None, {}])
def test_registro_bancario_ausente_tambem_explica_documento(fato):
    dados = enriquecer_bancos(BANCO)
    dados["gordon_cvm"] = fato
    fonte = dict(_contexto(dados)["fontes"])["DFP da lente de bancos"]
    assert "None" not in fonte
    assert dados["bancos_diagnostico"] in fonte
