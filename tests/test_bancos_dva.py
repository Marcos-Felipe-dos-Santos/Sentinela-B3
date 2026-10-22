"""Perímetro bancário da DVA: pares públicos da DFP 2025, sem coleta."""

import pytest

from sentinela.data import contas_cvm as cc, gordon_cvm


def _linhas(participacao, descricao="Part. Não Controladores nos Lucros Retidos"):
    return [
        {
            "CD_CONTA": "7.09.04.01",
            "DS_CONTA": "Juros sobre o Capital Próprio",
            "VL_CONTA": 0,
        },
        {"CD_CONTA": "7.09.04.02", "DS_CONTA": "Dividendos", "VL_CONTA": 33704000},
        {"CD_CONTA": "7.09.04.04", "DS_CONTA": descricao, "VL_CONTA": participacao},
    ]


def _total(dva, *, minoritario=10575000):
    tabela = cc.tabela()

    def ler(campo):
        return cc.ler_conta(dva, campo, "banco", tabela)

    return gordon_cvm.proventos_da_dva(
        ler("dividendos"),
        ler("jcp"),
        ler("dva_nao_controladores"),
        cc.Leitura(992000, "3.09.02", "atribuido a socios nao controladores"),
        cc.Leitura(
            minoritario, "2.08.09", "participacao dos acionistas nao controladores"
        ),
    )


@pytest.mark.parametrize(
    "descricao",
    [
        "Part. Não Controladores nos Lucros Retidos",
        "Participação de Não Controladores nos Lucros Retidos",
    ],
)
def test_dva_com_nao_controladores_separados(descricao):
    assert _total(_linhas(992000, descricao)) == 33704000


def test_dva_ausente_zerada_nao_autoriza_minoritarios():
    assert isinstance(_total(_linhas(0)), gordon_cvm.Abstencao)
    assert isinstance(_total(_linhas(float("nan"))), gordon_cvm.Abstencao)


def test_reserva_sem_minoritarios_nao_aceita_correspondencia_invalida():
    ausente = cc.Abstencao(cc.MOTIVO_LINHA_AUSENTE, "ausente no documento")
    invalida = cc.Abstencao(cc.MOTIVO_SEM_CORRESPONDENCIA, "descrição divergente")
    valor = cc.Leitura(100, "7.09.04.02", "dividendos")
    zero = cc.Leitura(0, "7.09.04.04", "part. nao controladores nos lucros retidos")
    assert gordon_cvm.proventos_da_dva(valor, ausente, ausente, ausente, ausente) == 100
    assert gordon_cvm.proventos_da_dva(valor, ausente, zero, ausente, ausente) == 100
    assert isinstance(
        gordon_cvm.proventos_da_dva(valor, ausente, invalida, ausente, ausente),
        gordon_cvm.Abstencao,
    )
    assert isinstance(
        gordon_cvm.proventos_da_dva(valor, invalida, zero, ausente, ausente),
        gordon_cvm.Abstencao,
    )
