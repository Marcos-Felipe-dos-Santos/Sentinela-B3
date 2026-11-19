"""BUG-3-53 (Gemini B1): o fator B3 da relação histórica vale pela publicação numa data passada.

O bloco que `b3_proventos.relacao_ate` monta do banco (marca `aprovacao_antes_de_d`, eventos
aprovados antes de D) traz a coleta mais recente, posterior a D. O ramo da relação em
`fatores_acoes_b3.fatores_da_relacao` e a conferência de `janelas_fundamentais.fatores_da_base`
exigiam a coleta até o as_of, e Graham e Lynch abstinham em toda data passada com base
incompatível, mesmo com o desdobramento aprovado e com data com antes de D. Decisão 40: a
publicação antes de D decide, não a coleta; cada evento usado já é conferido por aprovação e
data com antes de D (`_fator_do_par`). A relação corrente e a reconciliação injetada mantêm a
guarda de coleta (DD-65).
"""

from copy import deepcopy

import pytest
from test_fatores_acoes_b3 import dados as relacao_sintetica
from test_fatores_acoes_b3 import documentos, evento
from test_janelas_fundamentais import AS_OF, dados_exemplo

from sentinela.data.fatores_acoes_b3 import fatores_da_relacao
from sentinela.data.janelas_fundamentais import entradas

COLETA_DEPOIS_DE_D = "2026-11-12T19:00:00+00:00"  # AS_OF = 20/10/2026


def _historico(eventos=None, marca=True, por_publicacao=True):
    """Série com desdobramento 1:2 em 2023 e o bloco da relação como o `relacao_ate` entrega."""
    d = dados_exemplo()
    d.pop("reconciliacao_serie")
    for registro, quantidade in zip(
        d["serie_cvm"]["exercicios"], (100, 100, 200, 200, 200), strict=True
    ):
        registro["acoes"] = quantidade
    bloco = deepcopy(relacao_sintetica(eventos)["proventos_b3"])
    bloco["coleta"] = COLETA_DEPOIS_DE_D
    if marca:
        bloco["aprovacao_antes_de_d"] = True
    d.update(classe_ativo="STOCK", especie="ON", proventos_b3=bloco)
    if por_publicacao:
        d["disponibilidade_por_publicacao"] = True
    return d


def test_fator_da_relacao_historica_vale_pela_publicacao():
    d = _historico()
    r = fatores_da_relacao(d, documentos(), AS_OF)
    assert r.get("fatores") == {
        "2021": 2,
        "2022": 2,
        "2023": 1,
        "2024": 1,
        "2025": 1,
    }, r
    assert r["coleta"] == COLETA_DEPOIS_DE_D


def test_graham_e_lynch_usam_o_fator_da_relacao_historica():
    r = entradas(_historico(), AS_OF)
    # LPA na base final: 1/2, 2/2, 3, 4, 5; corrigido pelo IPCA: 0,6 + 1,15 + 3,3 + 4,2 + 5
    assert r["graham"]["lpa"] == pytest.approx(14.25 / 5), r["graham"]
    assert r["lynch"]["crescimento_lpa"] == pytest.approx(10**0.25 - 1), r["lynch"]


@pytest.mark.parametrize(
    ("marca", "por_publicacao"), [(False, True), (True, False), (False, False)]
)
def test_sem_as_duas_marcas_a_relacao_mantem_a_guarda_de_coleta(marca, por_publicacao):
    """Controle (DD-65): a relação corrente, sem o bloco do banco ou fora da data passada."""
    d = _historico(marca=marca, por_publicacao=por_publicacao)
    assert fatores_da_relacao(d, documentos(), AS_OF) == {
        "abstencao": "coleta sem fuso ou posterior ao as_of"
    }
    assert entradas(d, AS_OF)["graham"]["abstencao"] == (
        "fator oficial B3 indisponível: coleta sem fuso ou posterior ao as_of"
    )


def test_reconciliacao_injetada_mantem_a_guarda_mesmo_com_as_marcas():
    """Controle (DD-65): só a reconciliação calculada do bloco do banco vale pela publicação."""
    d = _historico()
    d["reconciliacao_serie"] = {
        "fonte": "eventos oficiais sintéticos",
        "inicio": "2021-01-01",
        "fim": "2025-12-31",
        "coleta": COLETA_DEPOIS_DE_D,
        "fatores": {"2021": 2, "2022": 2, "2023": 1, "2024": 1, "2025": 1},
    }
    assert entradas(d, AS_OF)["graham"]["abstencao"] == (
        "coleta sem fuso ou posterior ao as_of"
    )


def test_evento_aprovado_depois_de_d_continua_fora_pela_publicacao():
    """Com as marcas, o evento usado ainda precisa de aprovação antes de D (o motivo era a
    coleta antes da correção)."""
    d = _historico([evento(approvedOn="21/10/2026")])
    assert fatores_da_relacao(d, documentos(), AS_OF) == {
        "abstencao": "aprovação ou data com do evento não elegível até o as_of"
    }
