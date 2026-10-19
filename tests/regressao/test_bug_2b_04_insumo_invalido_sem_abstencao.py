"""BUG-2B-04: insumo inválido vira número em vez de abstenção (ficha 1.1, seção 4, itens 10-12).

Pela ficha por ação, insumo inválido é abstenção com o motivo; zero, prejuízo e PL negativo
são dados. Funções que tratam insumo inválido como número:
- `cvm_provider.composicao_do_documento` sem a coluna de ações ON devolve ON = 0;
- `acoes_cvm.roe_dos_controladores` com lucro NaN devolve `(nan, None)` e com PL infinito
  `(0.0, None)`;
- `acoes_cvm.derivar_por_acao` com preço infinito devolve P/L e P/VP infinitos (a cascata já
  barra o preço não finito; a função não);
- `acoes_cvm.derivar_por_acao` aceita unit com quantidade fracionária de ações.
Origem: F2B-21, pergunta 8 (auditoria externa da 2A, correção 6).
"""

import math

import pandas as pd
import pytest

from cvm_provider import composicao_do_documento
from sentinela.data import acoes_cvm

BUG = pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-04 · insumo inválido vira número em vez de abstenção · corrige: a decidir no marcador",
)
CNPJ = "11.111.111/0001-11"
COMPOSICAO = acoes_cvm.Composicao(1000, 0, 0, 0, 0, "2025-12-31", "1")
DERIVAR = {
    "lucro_controladores": 1000.0, "pl_controladores": 10000.0, "composicao": COMPOSICAO,
    "motivo_composicao": None, "lpa_divulgado": 1.0, "preco": 10.0, "eh_unit": False,
    "acoes_por_unit": None,
}  # fmt: skip


@BUG
def test_composicao_sem_a_coluna_de_acoes_on_se_abstem():
    linha = {
        "CNPJ_CIA": CNPJ, "DT_REFER": "2025-12-31", "VERSAO": "1",
        "QT_ACAO_PREF_CAP_INTEGR": "0", "QT_ACAO_ORDIN_TESOURO": "0",
        "QT_ACAO_PREF_TESOURO": "0", "QT_ACAO_TOTAL_TESOURO": "0",
    }  # fmt: skip
    composicao, motivo = composicao_do_documento(
        pd.DataFrame([linha]), CNPJ, "2025-12-31", "1"
    )
    assert composicao is None
    assert motivo


@BUG
@pytest.mark.parametrize(("lucro", "pl"), [(math.nan, 10.0), (10.0, math.inf)])
def test_roe_com_insumo_nao_finito_se_abstem(lucro, pl):
    roe, motivo = acoes_cvm.roe_dos_controladores(lucro, pl)
    assert roe is None
    assert motivo


@BUG
def test_preco_infinito_nao_gera_multiplo_infinito():
    resultado = acoes_cvm.derivar_por_acao(**{**DERIVAR, "preco": math.inf})
    # A correção pode abster-se inteira ou devolver os múltiplos ausentes.
    assert isinstance(resultado, acoes_cvm.Abstencao) or (
        resultado.pl is None and resultado.pvp is None
    )


@BUG
def test_unit_com_quantidade_fracionaria_se_abstem():
    resultado = acoes_cvm.derivar_por_acao(
        **{**DERIVAR, "eh_unit": True, "acoes_por_unit": {"ON": 0.5, "PN": 1}}
    )
    assert isinstance(resultado, acoes_cvm.Abstencao)
