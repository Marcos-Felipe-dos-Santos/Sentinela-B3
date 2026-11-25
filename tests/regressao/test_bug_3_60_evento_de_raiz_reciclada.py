"""BUG-3-60 (Codex C3-03, checkpoint da Fase 3): evento de outro emissor com a mesma raiz.

O motor histórico remonta os eventos em ações pela raiz do ticker (`eventos_societarios`
por `emissor`), e `fatores_acoes_b3._fator_do_par` aceitava o evento pela espécie do ISIN,
sem provar que o ISIN era do papel analisado. Com a raiz reutilizada por outro emissor, um
desdobramento 1:2 desse outro emissor, da mesma espécie, reconciliava uma série cuja
quantidade dobrou por outra causa, e o LPA anterior era dividido por 2 em Graham e Lynch.
Decisão 51 do Marcos (20/11/2026): o evento só reconcilia se o ISIN dele estiver entre os
ISINs do próprio emissor (GetDetail das coletas pelo código CVM do ativo, ou o CODISI do
pregão). Esclarecimento do Marcos no mesmo dia (C3-03b): o evento com ISIN de outro emissor é
descartado, não abstém; só o evento que não pode ser atribuído (ISIN ausente ou ilegível)
faz a lente abster.

Respostas oficiais da B3 da Lojas Renner (contrato D18) e COTAHIST do LREN4, como em
`test_bloco_bazin_historico`, gravados pelos produtores reais (`gravar_proventos`,
`gravar_eventos`, `b3_cotahist.carregar`); o outro emissor é a mesma resposta com outro código
CVM, outro ISIN e o desdobramento; o bloco vem do motor histórico (`relacao_ate`).
"""

import dataclasses
from datetime import datetime, timedelta

import pytest
from test_bloco_bazin_historico import (
    AS_OF,
    ISIN_PN,
    _dados,
    _gravar,
    _motor,
    _pregoes,
    conn,  # noqa: F401
    relacao,  # noqa: F401
)
from test_fatores_acoes_b3 import AS_OF as AS_OF_SINTETICO
from test_fatores_acoes_b3 import dados as dados_sinteticos
from test_fatores_acoes_b3 import documentos

from sentinela.data.fatores_acoes_b3 import fatores_da_relacao
from sentinela.data.providers import b3_proventos

ISIN_DO_OUTRO = "BRLRE2ACNPR6"  # PN de outro emissor que usou a mesma raiz
CD_CVM_DO_OUTRO = 99990
SEM_EVENTO = "base incompatível sem evento oficial B3 no par documental"
FATORES = {"2021": 2, "2022": 2, "2023": 1, "2024": 1, "2025": 1}


def _desdobramento(isin: str) -> dict:
    """1:2 aprovado e com data com em 2023, entre os encerramentos de 100 e 200 ações."""
    return {
        "label": "DESDOBRAMENTO",
        "factor": "100,00000000000",
        "isinCode": isin,
        "assetIssued": isin,
        "approvedOn": "01/04/2023",
        "lastDatePrior": "15/04/2023",
    }


def _do_outro_emissor(conn, relacao):  # noqa: F811
    """A mesma raiz coletada antes pelo código CVM do outro emissor, com o evento dele."""
    outro = dataclasses.replace(
        relacao,
        isins=(ISIN_DO_OUTRO,),
        eventos_acoes=(_desdobramento(ISIN_DO_OUTRO),),
        coleta=(datetime.fromisoformat(relacao.coleta) - timedelta(days=1)).isoformat(),
    )
    # gravado com zero à esquerda, como o código CVM aparece em outras fontes
    b3_proventos.gravar_proventos(conn, outro, f"0{CD_CVM_DO_OUTRO}")
    b3_proventos.gravar_eventos(conn, outro, f"0{CD_CVM_DO_OUTRO}")


def _fatores(conn, tmp_path, isin_no_pregao=ISIN_PN):  # noqa: F811
    """Série PN 100 → 200 de 2022 para 2023, com o bloco remontado pelo motor em D."""
    _pregoes(conn, tmp_path, ["20261029", "20261030"], isin=isin_no_pregao)
    dados = {**_dados(), "cd_cvm": "8133"}
    motor = _motor(conn, tmp_path)
    assert motor._buscar_yfinance("LREN4", dados)
    motor._buscar_proventos_b3("LREN4", dados)
    assert "abstencao" not in dados["proventos_b3"], dados["proventos_b3"]
    return fatores_da_relacao(dados, documentos(), AS_OF)


def test_evento_de_outro_emissor_com_a_mesma_raiz_nao_reconcilia(
    conn,  # noqa: F811
    relacao,  # noqa: F811
    tmp_path,
):
    """Descartado o evento do outro emissor, a série 100 → 200 fica sem evento e abstém."""
    _gravar(conn, relacao)
    _do_outro_emissor(conn, relacao)
    assert _fatores(conn, tmp_path) == {"abstencao": SEM_EVENTO}


def test_evento_de_outro_emissor_na_janela_e_descartado_e_o_proprio_reconcilia(
    conn,  # noqa: F811
    relacao,  # noqa: F811
    tmp_path,
):
    """C3-03b: com o evento próprio e o alheio na janela, vale só o próprio (fator 2, não 4)."""
    _gravar(
        conn, dataclasses.replace(relacao, eventos_acoes=(_desdobramento(ISIN_PN),))
    )
    _do_outro_emissor(conn, relacao)
    r = _fatores(conn, tmp_path)
    assert r.get("fatores") == FATORES, r
    (par,) = [e for e in r["evidencias"] if e["eventos"]]
    assert [e["isinCode"] for e in par["eventos"]] == [ISIN_PN]


@pytest.mark.parametrize("isin", [None, 123, "BRLREN", "BRLRENXXXXX9"])
def test_evento_sem_isin_atribuivel_abstem(isin):
    """C3-03b: ISIN ausente ou ilegível não permite atribuir o evento; a lente abstém."""
    d = dados_sinteticos([{**_desdobramento("BRTESTACNOR0"), "isinCode": isin}])
    assert fatores_da_relacao(d, documentos(), AS_OF_SINTETICO) == {
        "abstencao": "espécie do evento em ações não demonstrada"
    }


def test_isin_do_pregao_prova_o_vinculo(conn, relacao, tmp_path):  # noqa: F811
    """Controle: o mesmo evento com o CODISI do LREN4 antes de D (o GetDetail só traz a ON)."""
    _gravar(
        conn, dataclasses.replace(relacao, eventos_acoes=(_desdobramento(ISIN_PN),))
    )
    assert _fatores(conn, tmp_path)["fatores"] == FATORES


def test_isin_do_getdetail_pelo_codigo_cvm_prova_o_vinculo(conn, relacao, tmp_path):  # noqa: F811
    """Controle: o ISIN do evento no GetDetail da coleta do código CVM 8133, com outro CODISI."""
    proprio = dataclasses.replace(
        relacao,
        isins=(*relacao.isins, ISIN_PN),
        identidade=None,
        eventos_acoes=(_desdobramento(ISIN_PN),),
    )
    _gravar(conn, proprio)
    assert _fatores(conn, tmp_path, isin_no_pregao="BRLRENACNPR0")["fatores"] == FATORES


def test_isins_do_emissor_pelo_codigo_cvm_e_pelo_pregao(conn, relacao, tmp_path):  # noqa: F811
    """O código CVM com zeros à esquerda é o mesmo; sem código ou sem ticker, só a outra fonte."""
    from test_bloco_bazin_historico import DIA

    _gravar(conn, relacao)
    _do_outro_emissor(conn, relacao)
    _pregoes(conn, tmp_path, ["20261030"])
    lidos = b3_proventos.isins_do_emissor
    assert lidos(conn, "LREN", "008133", "LREN4", DIA) == ["BRLRENACNOR1", ISIN_PN]
    assert lidos(conn, "LREN", 8133, None, DIA) == ["BRLRENACNOR1"]
    assert lidos(conn, "LREN", None, "LREN4", DIA) == [ISIN_PN]
    assert lidos(conn, "LREN", CD_CVM_DO_OUTRO, None, DIA) == [ISIN_DO_OUTRO]
    bloco = b3_proventos.relacao_ate(conn, "LREN", DIA, ticker="LREN4", cd_cvm=8133)
    assert bloco["isins_emissor"] == ["BRLRENACNOR1", ISIN_PN]


@pytest.mark.parametrize("isins", [None, [], ["BRTESTACNOR0", None], "BRTESTACNOR0"])
def test_sem_isins_do_emissor_demonstrados_abstem(isins):
    d = dados_sinteticos()
    if isins is None:
        d["proventos_b3"].pop("isins_emissor")
    else:
        d["proventos_b3"]["isins_emissor"] = isins
    assert fatores_da_relacao(d, documentos(), AS_OF_SINTETICO) == {
        "abstencao": "ISINs do emissor não demonstrados para os eventos em ações"
    }


@pytest.mark.parametrize("isin_alheio", ["BRTAEECDAM10", "BRTSTAACNPZ7"])
def test_evento_alheio_com_isin_legivel_e_especie_sem_mapa_nao_abstem(
    isin_alheio: str,
) -> None:
    # CDAM de unit e código sintético ACNPZ com dígito correto (ISO 6166).
    proprio = _desdobramento("BRTESTACNOR0")
    alheio = _desdobramento(isin_alheio)
    entrada = dados_sinteticos([alheio, proprio])

    resultado = fatores_da_relacao(entrada, documentos(), AS_OF_SINTETICO)

    assert resultado.get("fatores") == FATORES, resultado
    (par,) = [e for e in resultado["evidencias"] if e["eventos"]]
    assert [e["isinCode"] for e in par["eventos"]] == ["BRTESTACNOR0"]


def test_evento_proprio_com_isin_legivel_e_especie_sem_mapa_abstem() -> None:
    isin_proprio = "BRTSTAACNPZ7"
    entrada = dados_sinteticos([_desdobramento(isin_proprio)])
    entrada["proventos_b3"]["isins_emissor"] = [isin_proprio]

    assert fatores_da_relacao(entrada, documentos(), AS_OF_SINTETICO) == {
        "abstencao": "espécie do evento em ações não demonstrada"
    }
