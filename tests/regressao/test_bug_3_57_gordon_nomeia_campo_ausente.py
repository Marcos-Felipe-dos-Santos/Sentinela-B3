"""BUG-3-57 (Codex B-1): campo ausente no Gordon produz abstenção que nomeia o campo.

Na sonda do F3-8j-uni, seis pares abstiveram o Gordon com "insumo ausente ou inválido do
Gordon: must be real number, not NoneType": `gordon_cvm.entradas` chamava `math.isfinite`
em campos que podiam vir `None`, e o `TypeError` virava abstenção genérica, sem dizer qual
insumo faltou. A abstenção já protegia a saída; o defeito é o motivo.

Os insumos do Gordon de `test_gordon_cvm.py` (DFP 2025 sintética) pela fronteira real.
"""

from datetime import date

import pytest
from test_gordon_cvm import _dados

from sentinela.data import gordon_cvm

AS_OF = date(2026, 10, 20)


def _sem(d, caminho):
    alvo = d
    for chave in caminho[:-1]:
        alvo = alvo[chave]
    alvo[caminho[-1]] = None
    return gordon_cvm.entradas(d, AS_OF)


@pytest.mark.parametrize(
    "caminho",
    [
        ("gordon_cvm", "lucro_controladores"),
        ("gordon_cvm", "pl_inicial_controladores"),
        ("gordon_cvm", "lpa"),
        ("gordon_cvm", "fator_unit"),
        ("taxa_real", "custo_capital_real"),
        ("taxa_real", "inflacao", "valor"),
        ("taxa_real", "pib", "valor"),
    ],
    ids=lambda c: ".".join(c[1:]),
)
def test_campo_ausente_nomeia_o_campo(caminho):
    obtido = _sem(_dados(), caminho)
    assert obtido == gordon_cvm.Abstencao(
        f"insumo ausente do Gordon: {'.'.join(caminho[1:])}"
    )


@pytest.mark.parametrize(
    ("caminho", "motivo"),
    [
        (("gordon_cvm", "acoes_base"), "ações da DFP não positivas ou inválidas"),
        (("gordon_cvm", "proventos_controladores"), "provento DVA inválido"),
    ],
)
def test_campos_que_ja_nomeavam_seguem_iguais(caminho, motivo):
    """Controle: os campos com guarda própria mantêm o motivo."""
    assert _sem(_dados(), caminho) == gordon_cvm.Abstencao(motivo)
