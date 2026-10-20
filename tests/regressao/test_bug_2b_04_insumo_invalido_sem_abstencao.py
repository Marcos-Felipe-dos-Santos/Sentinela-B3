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

CNPJ = "11.111.111/0001-11"
COMPOSICAO = acoes_cvm.Composicao(1000, 0, 0, 0, 0, "2025-12-31", "1")
DERIVAR = {
    "lucro_controladores": 1000.0, "pl_controladores": 10000.0, "composicao": COMPOSICAO,
    "motivo_composicao": None, "lpa_divulgado": 1.0, "preco": 10.0, "eh_unit": False,
    "acoes_por_unit": None,
}  # fmt: skip


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


@pytest.mark.parametrize(("lucro", "pl"), [(math.nan, 10.0), (10.0, math.inf)])
def test_roe_com_insumo_nao_finito_se_abstem(lucro, pl):
    roe, motivo = acoes_cvm.roe_dos_controladores(lucro, pl)
    assert roe is None
    assert motivo


def test_preco_infinito_nao_gera_multiplo_infinito():
    resultado = acoes_cvm.derivar_por_acao(**{**DERIVAR, "preco": math.inf})
    # A correção pode abster-se inteira ou devolver os múltiplos ausentes.
    assert isinstance(resultado, acoes_cvm.Abstencao) or (
        resultado.pl is None and resultado.pvp is None
    )


def test_unit_com_quantidade_fracionaria_se_abstem():
    resultado = acoes_cvm.derivar_por_acao(
        **{**DERIVAR, "eh_unit": True, "acoes_por_unit": {"ON": 0.5, "PN": 1}}
    )
    assert isinstance(resultado, acoes_cvm.Abstencao)


def test_tesouraria_maior_que_a_especie_invalida_composicao():
    from dataclasses import replace

    composicao = replace(
        COMPOSICAO, on=100, pn=100, tesouraria_on=101, tesouraria_total=101
    )
    assert isinstance(
        acoes_cvm.derivar_por_acao(
            **{**DERIVAR, "composicao": composicao, "lucro_controladores": 99.0}
        ),
        acoes_cvm.Abstencao,
    )


@pytest.mark.parametrize("preco", [math.inf, math.nan])
def test_preco_nao_finito_preserva_lpa_vpa(preco):
    resultado = acoes_cvm.derivar_por_acao(**{**DERIVAR, "preco": preco})
    assert isinstance(resultado, acoes_cvm.PorAcao)
    assert resultado.lpa == 1.0 and resultado.vpa == 10.0
    assert resultado.pl is None and resultado.pvp is None


def test_lpa_invalido_na_coleta_abstem_especie_sem_descartar_outra():
    from cvm_provider import lpa_basico_por_classe

    linhas = pd.DataFrame(
        [
            {"CD_CONTA": "3.99.01.01", "DS_CONTA": "ON", "VL_CONTA": 1.0},
            {"CD_CONTA": "3.99.01.01", "DS_CONTA": "ON", "VL_CONTA": "ilegível"},
            {"CD_CONTA": "3.99.01.02", "DS_CONTA": "PN", "VL_CONTA": 2.0},
        ]
    )
    lidos = lpa_basico_por_classe(linhas)
    resultado = acoes_cvm.divulgados_coerentes(lidos, 10.0, 10.0)
    assert isinstance(resultado["ON"], acoes_cvm.Abstencao)
    assert "inválido" in resultado["ON"].motivo
    assert resultado["PN"].valor == 2.0


def test_lpa_agregado_invalido_nao_autoriza_reserva():
    from cvm_provider import lpa_basico_agregado

    linhas = pd.DataFrame(
        [
            {"CD_CONTA": "3.99.01", "VL_CONTA": "ilegível"},
            {"CD_CONTA": "3.99", "VL_CONTA": 2.0},
        ]
    )
    por_classe, _ = acoes_cvm.linhas_da_especie_unica(
        {},
        lpa_basico_agregado(linhas),
        ["ON"],
        lucro_controladores=2000.0,
        acoes=1000.0,
    )
    resultado = acoes_cvm.divulgados_coerentes(por_classe, 2000.0, 2000.0)
    assert isinstance(resultado["ON"], acoes_cvm.Abstencao)
