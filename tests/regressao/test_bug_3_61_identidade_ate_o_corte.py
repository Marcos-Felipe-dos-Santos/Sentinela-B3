"""BUG-3-61 (Codex C3-02, checkpoint da Fase 3): divergência posterior ao corte na identidade.

A identidade do emissor (decisão 33) é conferida na coleta: todo provento em dinheiro do
complemento precisa estar na relação lida pelo nome. Numa data passada vale a coleta mais
recente (decisão 40), e a de 19/11/2026 trazia no complemento proventos anunciados de 13 a
17/11 que a relação ainda não listava: a identidade falhava e o retorno de horizontes já
encerrados (CURY3 em 30/06/2023, 12 meses) passava a abster por um dado de novembro de 2026.
Decisão 51 do Marcos (20/11/2026): a prova compara só os proventos do complemento anunciados
antes do corte (D na análise; T no retorno do horizonte, lido como o dia seguinte a T,
o mesmo corte dos proventos no `BacktestPIT._retornos`: o anunciado em T já era conhecido).
DD-90: os anunciados no corte ou depois ficam de fora da comparação, e ao menos um provento
do complemento precisa estar na relação (um homônimo, sem nenhum, segue sem identidade).

Fontes públicas da ABEV3 (`test_backtest_pit_e2e`): CVM, COTAHIST, macro e a coleta oficial
da B3, gravadas pelos produtores reais; a coleta posterior é a mesma resposta com um provento a
mais no complemento, gravada pelo `gravar_proventos`, e o retorno vem do `BacktestPIT`.
"""

import dataclasses
import json
from datetime import date, timedelta

import pandas as pd
import pytest
from test_backtest_pit_e2e import B3, COLETA, PASTA, D, T, banco_publico  # noqa: F401

from backtesting import backtest_pit
from sentinela.data import proventos_b3
from sentinela.data.providers import b3_proventos

POSTERIOR = COLETA + timedelta(days=7)


def _coleta_oficial():
    fixture = json.loads(B3.read_text())
    por_url = {f["url"]: f for f in fixture["fontes"]}

    def obter(url):
        nome = url.split("/CompanyCall/")[1].split("/")[0] + ".json"
        return json.loads(fixture["membros"][nome]), por_url[url]

    return b3_proventos.coletar(23264, COLETA, obter)


def _anexar_coleta_posterior(conn, *novos):
    """A coleta oficial de novo, uma semana depois, com `novos` no complemento."""
    oficial = _coleta_oficial()
    complemento = (*oficial.dinheiro_complemento, *novos)
    posterior = dataclasses.replace(
        oficial,
        coleta=POSTERIOR.isoformat(),
        dinheiro_complemento=complemento,
        identidade=proventos_b3.conferir_emissor(
            oficial.registros, complemento, oficial.isins
        ),
    )
    assert posterior.identidade is not None  # a coleta posterior falha na decisão 33
    b3_proventos.gravar_proventos(conn, posterior, 23264)


def _anuncio(aprovacao: str, data_com: str, valor="0,50000000000") -> dict:
    return {
        "assetIssued": "BRABEVACNOR1",
        "isinCode": "BRABEVACNOR1",
        "label": "DIVIDENDO",
        "approvedOn": aprovacao,
        "lastDatePrior": data_com,
        "rate": valor,
        "relatedTo": "",
        "paymentDate": "",
        "remarks": "",
    }


def _gordon(conn, tmp_path):
    cadastro = pd.read_csv(
        PASTA / "cad_cia_aberta_abev.csv", sep=";", encoding="latin-1", dtype=str
    )
    executor = backtest_pit.BacktestPIT(
        conn, cadastro, hoje=date(2026, 11, 20), cache_dir=tmp_path / "pit"
    )
    saida = executor.executar([D], horizontes=(12,), modo="estrito")
    return next(o for o in saida["observacoes"] if o["lente"] == "Gordon")


def test_divergencia_anunciada_depois_de_t_preserva_o_retorno(
    banco_publico,  # noqa: F811
    tmp_path,
):
    _anexar_coleta_posterior(banco_publico, _anuncio("13/11/2026", "17/11/2026"))
    gordon = _gordon(banco_publico, tmp_path)
    oracle = json.loads((PASTA / "retorno_esperado.json").read_text())
    assert gordon["fim"] == T.isoformat()
    assert gordon["abstencao_retorno"] is None, gordon
    assert gordon["retorno_total"] == pytest.approx(oracle["retorno_total"], abs=1e-12)


def test_divergencia_anunciada_ate_t_segue_abstendo(banco_publico, tmp_path):  # noqa: F811
    """Controle: o provento anunciado até T e ausente da relação ainda falha a decisão 33."""
    _anexar_coleta_posterior(banco_publico, _anuncio("15/03/2023", "20/03/2023"))
    motivo = _gordon(banco_publico, tmp_path)["abstencao_retorno"]
    assert motivo is not None and "20/03/2023 ausente da relação" in motivo


def test_relacao_sem_nenhum_provento_do_complemento_segue_sem_identidade():
    """DD-90: só anúncios posteriores ao corte e nenhum na relação não provam a identidade."""
    oficial = _coleta_oficial()
    motivo = proventos_b3.conferir_emissor(
        oficial.registros,
        [_anuncio("13/11/2026", "17/11/2026")],
        oficial.isins,
        corte=date(2023, 4, 1),
    )
    assert motivo == (
        "identidade do emissor não comprovada: nenhum provento do complemento na relação"
    )


def test_anuncio_no_dia_do_corte_fica_de_fora():
    """O anúncio no próprio dia do corte não era conhecido antes dele: fica de fora."""
    oficial = _coleta_oficial()
    novo = _anuncio("01/04/2023", "05/04/2023")
    complemento = [*oficial.dinheiro_complemento, novo]
    conferir = proventos_b3.conferir_emissor
    assert (
        conferir(oficial.registros, complemento, oficial.isins, corte=date(2023, 4, 1))
        is None
    )
    assert "05/04/2023 ausente" in conferir(
        oficial.registros, complemento, oficial.isins, corte=date(2023, 4, 2)
    )
    assert "05/04/2023 ausente" in conferir(
        oficial.registros, complemento, oficial.isins
    )


def test_anuncio_com_aprovacao_ilegivel_segue_comparado():
    oficial = _coleta_oficial()
    complemento = [*oficial.dinheiro_complemento, _anuncio("sem data", "05/04/2023")]
    motivo = proventos_b3.conferir_emissor(
        oficial.registros, complemento, oficial.isins, corte=date(2023, 4, 1)
    )
    assert "05/04/2023 ausente" in motivo


def test_coleta_sem_complemento_guardado_mantem_o_motivo_gravado(tmp_path):
    """Sem complemento e sem ISIN novo do pregão, não há como refazer a conferência: fica o
    motivo da coleta (coletas gravadas antes da tabela do complemento)."""
    import sqlite3
    from contextlib import closing

    from sentinela.data.store import migracoes

    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        conn.execute(
            "INSERT INTO proventos_coletas (emissor, coleta, cd_cvm, nome_pregao, total, "
            "registros, identidade, isins_json, fonte, hash_sha256) "
            "VALUES ('ABEV', ?, '23264', 'AMBEV SA', 0, 0, 'motivo gravado', "
            "'[\"BRABEVACNOR1\"]', 'u', 'h')",
            (COLETA.isoformat(),),
        )
        lido = b3_proventos.proventos_ate(
            conn, "ABEV", date(2023, 4, 1), por_publicacao=True, ticker="ABEV3"
        )
    assert lido == {
        "abstencao": f"{b3_proventos.MOTIVO_PROVENTO_IDENTIDADE}: motivo gravado"
    }
