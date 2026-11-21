"""BUG-3-38: a abstenção da inflação da janela da DFP chega ao Gordon e aos Bancos sem o motivo.

Com a taxa real registrada e a inflação abstida (por exemplo "IPCA ausente no banco", no motor
histórico do F3-8d), `gordon_cvm.entradas` comparava as datas de um dicionário sem datas e
mostrava "inflação incompatível com a janela da DFP", o mesmo defeito do BUG-2B-30 um nível
abaixo. Sonda do F3-8d (15/11/2026): 5 observações do Gordon com esse motivo.
"""

from datetime import UTC, datetime

import pytest
from apoio_bancos import enriquecer_bancos
from apoio_gordon import enriquecer_gordon

from sentinela.data import gordon_cvm

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)


@pytest.mark.parametrize("modelo", ["empresa", "banco"])
def test_gordon_e_bancos_mostram_o_motivo_da_inflacao(modelo):
    ativo = {
        "ticker": "TST3",
        "preco_atual": 100.0,
        "roe": 0.12,
        "pl": 10.0,
        "pvp": 1.0,
    }
    dados = (
        enriquecer_gordon(ativo) if modelo == "empresa" else enriquecer_bancos(ativo)
    )
    assert isinstance(
        gordon_cvm.entradas(dados, AS_OF, modelo=modelo), dict
    )  # controle
    dados["taxa_real"]["inflacao"] = {"abstencao": "IPCA ausente no banco"}
    entradas = gordon_cvm.entradas(dados, AS_OF, modelo=modelo)
    assert entradas == gordon_cvm.Abstencao(
        "inflação indisponível: IPCA ausente no banco"
    )
