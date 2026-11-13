"""BUG-3-27: numa data passada, a guarda de coleta abstém todas as lentes de ação.

Achado C1 da revisão do F3-3d (12/11/2026): `valuation_engine._bpp_disponivel` exigia a coleta
do arquivo até o as_of. No histórico, todo dado foi coletado depois de D (backfill de
12/11/2026), e Graham, Bazin, Lynch, Gordon e Bancos saíam com "disponibilidade do BPP
consolidado não demonstrada até o as_of", mesmo com a DFP entregue antes de D. Correto
(decisão 40 do Marcos, 13/11/2026): numa data passada, a prova é a data de publicação
(`DT_RECEB` antes do dia de D); a coleta fica na proveniência. Corrige: F3-3e.
"""

from datetime import UTC, datetime

import pytest
import test_servico_historico as base

from valuation_engine import MOTIVO_BPP_INDISPONIVEL

banco, espioes, resultados_conn = base.banco, base.espioes, base.resultados_conn


@pytest.mark.usefixtures("espioes")
def test_bug_3_27_dfp_entregue_antes_de_d_e_coletada_hoje_passa_pelo_escopo(
    banco, tmp_path, resultados_conn
):
    servico, _, _ = base._servico(banco, tmp_path, resultados_conn)
    dados = servico.analisar(
        "AMER3", datetime(2020, 3, 2, 15, tzinfo=UTC), use_ai=False
    ).raw
    motivos = {lente.get("abstencao") for lente in dados["lentes"].values()}
    assert MOTIVO_BPP_INDISPONIVEL not in motivos
    assert dados["modelo_bpp_proveniencia"]["data_entrega"] == "2020-02-21"
    assert dados["disponibilidade_por_publicacao"] is True


def test_bug_3_27_gordon_e_janelas_pela_entrega_quando_coletados_depois():
    """As guardas da fronteira do Gordon e das janelas de Graham e Lynch (revisão do F3-3e)."""
    from test_gordon_cvm import _dados
    from test_janelas_fundamentais import AS_OF, dados_exemplo

    from sentinela.data import gordon_cvm
    from sentinela.data.janelas_fundamentais import entradas

    gordon = _dados()
    for prov in (
        gordon["gordon_cvm"]["proveniencia"],
        gordon["base_acionaria_gordon"]["proveniencia"],
    ):
        prov["data_coleta"] = "2026-11-12T19:00:00+00:00"
    gordon["disponibilidade_por_publicacao"] = True
    assert isinstance(
        gordon_cvm.entradas(gordon, datetime(2026, 10, 20, 18, tzinfo=UTC)), dict
    )
    janelas = dados_exemplo()
    janelas.pop("reconciliacao_serie")  # o caminho de produção: o fator pelos documentos
    for e in janelas["serie_cvm"]["exercicios"]:
        e["acoes"] = 100
        e["proveniencia"]["data_coleta"] = "2026-11-12T19:00:00+00:00"
    janelas["disponibilidade_por_publicacao"] = True
    assert "abstencao" not in entradas(janelas, AS_OF)["graham"]
