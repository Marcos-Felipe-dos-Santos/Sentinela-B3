"""Índice oficial de ativos (F2A-1): arquivos sintéticos montados pelo layout da CVM, sem rede."""

from datetime import date

import pandas as pd
import pytest

from sentinela.data.providers.b3_cotahist import Cotacao
from sentinela.data.referencia import carregar_indice, salvar_indice
from sentinela.data.referencia.cobertura import cobertura
from sentinela.data.referencia.montagem import (
    MOTIVO_COMPANHIA,
    MOTIVO_REPETIDO,
    MOTIVO_RESERVA,
    cd_cvm_por_cnpj,
    fca_mais_recente,
    montar_indice,
    parsear_acoes_por_unit,
)

FONTES = {
    "fca": {
        "2026": {"arquivo": "fca_cia_aberta_2026.zip", "data": "2026-10-08"},
        "2025": {"arquivo": "fca_cia_aberta_2025.zip", "data": "2026-10-01"},
    },
    "cadastro": {"arquivo": "cad.csv", "data": "2026-10-08"},
    "informe_fii": {"arquivo": "inf.zip", "data": "2026-10-08"},
    "cotahist": {"arquivo": "cot.zip", "data": "2026-10-08"},
}
CNPJ_A = "11.111.111/0001-11"
CNPJ_B = "22.222.222/0001-22"


def _fca(*linhas):
    colunas = [
        "CNPJ_Companhia", "Data_Referencia", "Versao", "Nome_Empresarial", "Valor_Mobiliario",
        "Codigo_Negociacao", "Composicao_BDR_Unit", "Mercado", "Data_Fim_Negociacao",
    ]  # fmt: skip
    base = {
        "CNPJ_Companhia": CNPJ_A, "Data_Referencia": "2026-01-01", "Versao": "1",
        "Nome_Empresarial": "EMPRESA A S.A.", "Valor_Mobiliario": "Ações Ordinárias",
        "Codigo_Negociacao": "TSTA3", "Composicao_BDR_Unit": None, "Mercado": "Bolsa",
        "Data_Fim_Negociacao": None,
    }  # fmt: skip
    return pd.DataFrame(
        [{**base, **linha} for linha in linhas or ({},)], columns=colunas
    )


def _cadastro(*linhas):
    base = {
        "CNPJ_CIA": CNPJ_A,
        "CD_CVM": "100",
        "SIT": "ATIVO",
        "DENOM_SOCIAL": "EMPRESA A S.A.",
    }
    return pd.DataFrame([{**base, **linha} for linha in linhas or ({},)])


def _informe(*linhas):
    base = {
        "CNPJ_Fundo_Classe": "33.333.333/0001-33", "Data_Referencia": "2026-01-01",
        "Versao": "1", "Nome_Fundo_Classe": "FUNDO TESTE FII", "Codigo_ISIN": "BRTSTFCTF001",
        "Mercado_Negociacao_Bolsa": "S",
    }  # fmt: skip
    colunas = list(base)
    return pd.DataFrame(
        [{**base, **linha} for linha in linhas or ({},)], columns=colunas
    )


def _cot(codigo, codbdi="02", especi="ON", isin="BRXXXXACNOR0"):
    return Cotacao(
        data=date(2026, 9, 30), codigo_negociacao=codigo, codbdi=codbdi, tipo_mercado="010",
        especificacao=especi, isin=isin, fechamento=1.0, volume_financeiro=1.0,
        quantidade=1, negocios=1, fator_cotacao=1,
    )  # fmt: skip


def _indice(fca=None, cadastro=None, informe=None, cotacoes=(), fca_anterior=None):
    fcas = []
    if fca_anterior is not None:
        fcas.append((2025, fca_anterior))
    fcas.append((2026, fca if fca is not None else _fca()))
    return montar_indice(
        fcas,
        cadastro if cadastro is not None else _cadastro(),
        informe if informe is not None else _informe(),
        list(cotacoes),
        FONTES,
        "2026-10-08",
    )


def _sem_fii():
    return _informe(*[]).iloc[0:0]


# ── companhias ───────────────────────────────────────────────────────────────


def test_codigo_ativo_no_fca_mais_recente_entra():
    indice = _indice(informe=_sem_fii())
    r = indice.registros["TSTA3"]
    assert (r.classe, r.especie, r.cnpj, r.cd_cvm) == ("STOCK", "ON", CNPJ_A, 100)
    assert r.nome == "EMPRESA A S.A."
    assert r.regra == "fca:codigo_ativo"
    assert r.fonte == FONTES["fca"]["2026"]


def test_preferencial_tem_especie_pn():
    fca = _fca(
        {"Valor_Mobiliario": "Ações Preferenciais", "Codigo_Negociacao": "TSTA4"}
    )
    assert _indice(fca, informe=_sem_fii()).registros["TSTA4"].especie == "PN"


def test_codigo_com_data_de_fim_sai():
    fca = _fca({}, {"Codigo_Negociacao": "TSTA4", "Data_Fim_Negociacao": "2025-09-22"})
    indice = _indice(fca, informe=_sem_fii())
    assert "TSTA3" in indice.registros
    assert "TSTA4" not in indice.registros


def test_valor_mobiliario_que_nao_e_acao_nem_unit_nao_entra():
    fca = _fca({"Valor_Mobiliario": "Debêntures", "Codigo_Negociacao": "TSTD12"})
    assert "TSTD12" not in _indice(fca, informe=_sem_fii()).registros


def test_balcao_nao_organizado_nao_entra():
    fca = _fca(
        {"Mercado": "Balcão Não-Organizado"},
        {"Mercado": "Balcão Organizado", "Codigo_Negociacao": "TSTB3"},
    )
    indice = _indice(fca, informe=_sem_fii())
    assert "TSTA3" not in indice.registros
    assert "TSTB3" in indice.registros


def test_fca_do_ano_anterior_vale_se_o_atual_nao_foi_entregue():
    anterior = _fca(
        {
            "CNPJ_Companhia": CNPJ_B,
            "Codigo_Negociacao": "TSTB3",
            "Data_Referencia": "2025-01-01",
        },
        {},
    )
    atual = _fca({})  # só a companhia A entregou o FCA de 2026
    indice = _indice(atual, fca_anterior=anterior, informe=_sem_fii())
    assert indice.registros["TSTB3"].cnpj == CNPJ_B
    assert indice.registros["TSTA3"].cnpj == CNPJ_A


def test_fca_atual_substitui_o_anterior_da_mesma_companhia():
    anterior = _fca({"Codigo_Negociacao": "OLDA3", "Data_Referencia": "2025-01-01"})
    atual = _fca({"Codigo_Negociacao": "NEWA3"})
    indice = _indice(atual, fca_anterior=anterior, informe=_sem_fii())
    assert "NEWA3" in indice.registros
    assert "OLDA3" not in indice.registros


def test_maior_versao_do_mesmo_fca_vale():
    fca = _fca(
        {"Versao": "2", "Codigo_Negociacao": "V2AA3"},
        {"Versao": "10", "Codigo_Negociacao": "V10A3"},
    )
    recente = fca_mais_recente([(2026, fca)])
    assert list(recente["Codigo_Negociacao"]) == ["V10A3"]


def test_fca_vazio_nao_quebra():
    assert fca_mais_recente([(2026, _fca().iloc[0:0])]).empty
    assert _indice(_fca().iloc[0:0], informe=_sem_fii()).registros == {}


def test_cd_cvm_prefere_registro_ativo():
    cadastro = _cadastro(
        {"CD_CVM": "1", "SIT": "CANCELADA"},
        {"CD_CVM": "2", "SIT": "ATIVO"},
        {"CD_CVM": "3", "SIT": "CANCELADA"},
    )
    assert cd_cvm_por_cnpj(cadastro)[CNPJ_A][0] == 2


def test_cd_cvm_sem_ativo_usa_o_primeiro():
    cadastro = _cadastro(
        {"CD_CVM": "7", "SIT": "CANCELADA"}, {"CD_CVM": "8", "SIT": "SUSPENSO"}
    )
    assert cd_cvm_por_cnpj(cadastro)[CNPJ_A][0] == 7


def test_companhia_fora_do_cadastro_fica_sem_cd_cvm():
    indice = _indice(cadastro=_cadastro({"CNPJ_CIA": CNPJ_B}), informe=_sem_fii())
    r = indice.registros["TSTA3"]
    assert r.cd_cvm is None
    assert r.nome == "EMPRESA A S.A."


def test_codigo_fora_do_formato_vai_para_excecoes():
    fca = _fca(
        {"Codigo_Negociacao": "4030"},
        {"Codigo_Negociacao": "1545-8"},
        {"Codigo_Negociacao": ""},
        {"Codigo_Negociacao": None},
    )
    indice = _indice(fca, informe=_sem_fii())
    assert indice.registros == {}
    motivos = {(e.codigo, e.motivo) for e in indice.excecoes}
    assert ("4030", "código fora do formato de ticker") in motivos
    assert ("1545-8", "código fora do formato de ticker") in motivos
    assert ("", "sem código de negociação") in motivos
    assert len(indice.excecoes) == 4
    assert all(e.cnpj == CNPJ_A and e.nome == "EMPRESA A S.A." for e in indice.excecoes)


def test_codigo_em_minusculas_e_normalizado():
    fca = _fca({"Codigo_Negociacao": " tgma3 "})
    assert "TGMA3" in _indice(fca, informe=_sem_fii()).registros


def test_ticker_repetido_em_cnpjs_distintos_sai_do_indice():
    fca = _fca(
        {},
        {"CNPJ_Companhia": CNPJ_B, "Nome_Empresarial": "EMPRESA B"},
        {"CNPJ_Companhia": CNPJ_B, "Codigo_Negociacao": "TSTB3"},
    )
    indice = _indice(fca, informe=_sem_fii())
    assert "TSTA3" not in indice.registros
    assert "TSTB3" in indice.registros
    repetidos = [
        e for e in indice.excecoes if e.motivo == "ticker repetido em CNPJs distintos"
    ]
    assert sorted(e.cnpj for e in repetidos) == [CNPJ_A, CNPJ_B]


def test_linha_duplicada_do_mesmo_cnpj_nao_e_excecao():
    fca = _fca({}, {})
    indice = _indice(fca, informe=_sem_fii())
    assert indice.excecoes == []
    assert "TSTA3" in indice.registros


# ── units ────────────────────────────────────────────────────────────────────


def test_unit_tem_classe_unit():
    fca = _fca(
        {
            "Valor_Mobiliario": "Units",
            "Codigo_Negociacao": "TSTA11",
            "Composicao_BDR_Unit": "1 ON / 2 PN",
        }
    )
    r = _indice(fca, informe=_sem_fii()).registros["TSTA11"]
    assert r.classe == "UNIT"
    assert r.especie is None
    assert r.acoes_por_unit == {"ON": 1, "PN": 2}


def test_unit_sem_composicao_oficial_fica_sem_acoes_por_unit():
    fca = _fca({"Valor_Mobiliario": "Units", "Codigo_Negociacao": "TSTA11"})
    r = _indice(fca, informe=_sem_fii()).registros["TSTA11"]
    assert r.classe == "UNIT"
    assert r.acoes_por_unit is None


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("1 ação ordinária e 4 ações preferenciais", {"ON": 1, "PN": 4}),
        ("1 ON / 2 PN", {"ON": 1, "PN": 2}),
        ("1 ON E 2 PN", {"ON": 1, "PN": 2}),
        ("1 ON E 2 PNA", {"ON": 1, "PNA": 2}),  # F2B-12: a sigla da classe fica
        ("1 ON + 2 PNA + 1 PNA", {"ON": 1, "PNA": 3}),
        ("2 ações preferenciais e 1 ação ordinária", {"PN": 2, "ON": 1}),
        ("1 ON e 2PNs", {"ON": 1, "PN": 2}),
        ("1 KLBN3 + 4 KLBN4", {"ON": 1, "PN": 4}),
        ("1 ON + 1 PN", {"ON": 1, "PN": 1}),
        ("1 PN + 3 Recibos de Subscrição", None),
        ("1 XXXX1", None),
        ("1 XXXX9", None),
        ("1 XXXX8 + 2 XXXX3", {"PN": 1, "ON": 2}),
        ("0,555556", None),
        ("Class A Shares", None),
        ("", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_parser_de_acoes_por_unit(texto, esperado):
    assert parsear_acoes_por_unit(texto) == esperado


# ── FIIs ─────────────────────────────────────────────────────────────────────


def test_fii_pelo_isin_do_cotahist():
    cotacoes = [_cot("TSTF11", codbdi="12", especi="CI", isin="BRTSTFCTF001")]
    r = _indice(informe=_informe(), cotacoes=cotacoes, fca=_fca().iloc[0:0]).registros[
        "TSTF11"
    ]
    assert (r.classe, r.regra, r.cnpj) == (
        "FII",
        "fii:informe+cotahist_isin",
        "33.333.333/0001-33",
    )
    assert r.nome == "FUNDO TESTE FII"
    assert r.fonte == FONTES["informe_fii"]


def test_fii_pela_reserva_do_isin_fica_marcado():
    r = _indice(informe=_informe(), fca=_fca().iloc[0:0]).registros["TSTF11"]
    assert r.regra == "fii:reserva_isin"
    assert r.classe == "FII"


def test_ticker_do_cotahist_prevalece_sobre_a_reserva():
    cotacoes = [_cot("TSTF12", codbdi="12", especi="CI", isin="BRTSTFCTF001")]
    indice = _indice(informe=_informe(), cotacoes=cotacoes, fca=_fca().iloc[0:0])
    assert "TSTF12" in indice.registros
    assert "TSTF11" not in indice.registros


def test_isin_com_codbdi_12_prevalece_sobre_outro_codigo():
    cotacoes = [
        _cot("TSTF13", codbdi="14", especi="CI", isin="BRTSTFCTF001"),
        _cot("TSTF11", codbdi="12", especi="CI", isin="BRTSTFCTF001"),
    ]
    indice = _indice(informe=_informe(), cotacoes=cotacoes, fca=_fca().iloc[0:0])
    assert "TSTF11" in indice.registros


def test_fii_fora_de_bolsa_nao_entra():
    informe = _informe({"Mercado_Negociacao_Bolsa": "N"})
    assert _indice(informe=informe, fca=_fca().iloc[0:0]).registros == {}


def test_fii_sem_isin_valido_vai_para_excecoes():
    informe = _informe(
        {"Codigo_ISIN": None},
        {"CNPJ_Fundo_Classe": "44.444.444/0001-44", "Codigo_ISIN": "CURTO"},
    )
    indice = _indice(informe=informe, fca=_fca().iloc[0:0])
    assert indice.registros == {}
    assert [e.motivo for e in indice.excecoes] == ["FII em bolsa sem ISIN válido"] * 2


def test_informe_usa_a_versao_mais_recente_do_fundo():
    informe = _informe(
        {"Versao": "2", "Codigo_ISIN": "BRAAAACTF001"},
        {"Versao": "10", "Codigo_ISIN": "BRBBBBCTF001"},
        {
            "Data_Referencia": "2025-12-01",
            "Versao": "99",
            "Codigo_ISIN": "BRCCCCCTF001",
        },
    )
    indice = _indice(informe=informe, fca=_fca().iloc[0:0])
    assert sorted(indice.registros) == ["BBBB11"]


def test_informe_vazio_nao_quebra():
    assert _indice(informe=_sem_fii(), fca=_fca().iloc[0:0]).registros == {}


# ── BDR e cotas de fundo ─────────────────────────────────────────────────────


def test_cota_de_fundo_sem_informe_vira_unknown():
    cotacoes = [_cot("BOVA11", codbdi="14", especi="CI", isin="BRBOVACTF003")]
    r = _indice(cotacoes=cotacoes, informe=_sem_fii(), fca=_fca().iloc[0:0]).registros[
        "BOVA11"
    ]
    assert r.classe == "UNKNOWN"
    assert r.regra == "cotahist:cota_de_fundo"
    assert "ETF" in r.motivo
    assert r.fonte == FONTES["cotahist"]


def test_bdr_pelo_codbdi_e_especificacao():
    cotacoes = [
        _cot("AAPL34", codbdi="34", especi="DRN"),
        _cot("BEWJ39", codbdi="36", especi="DRE ED"),
    ]
    indice = _indice(cotacoes=cotacoes, informe=_sem_fii(), fca=_fca().iloc[0:0])
    assert indice.registros["AAPL34"].classe == "BDR"
    assert indice.registros["AAPL34"].regra == "cotahist:bdr"
    assert indice.registros["BEWJ39"].classe == "BDR"


def test_sufixo_sozinho_nao_define_classe():
    cotacoes = [
        _cot("ZZZZ11", codbdi="02", especi="ON"),
        _cot("YYYY34", codbdi="02", especi="ON"),
    ]
    indice = _indice(cotacoes=cotacoes, informe=_sem_fii(), fca=_fca().iloc[0:0])
    assert indice.registros == {}


def test_cota_de_fundo_ja_indexada_como_fii_nao_vira_unknown():
    cotacoes = [_cot("TSTF11", codbdi="12", especi="CI", isin="BRTSTFCTF001")]
    indice = _indice(informe=_informe(), cotacoes=cotacoes, fca=_fca().iloc[0:0])
    assert indice.registros["TSTF11"].classe == "FII"


def test_ticker_da_companhia_nao_vira_bdr_nem_unknown():
    cotacoes = [_cot("TSTA3", codbdi="34", especi="DRN")]
    indice = _indice(cotacoes=cotacoes, informe=_sem_fii())
    assert indice.registros["TSTA3"].classe == "STOCK"


def test_papel_repetido_no_cotahist_entra_uma_vez():
    cotacoes = [
        _cot("AAPL34", codbdi="34", especi="DRN"),
        _cot("AAPL34", codbdi="34", especi="DRN"),
    ]
    indice = _indice(cotacoes=cotacoes, informe=_sem_fii(), fca=_fca().iloc[0:0])
    assert list(indice.registros) == ["AAPL34"]


# ── persistência ─────────────────────────────────────────────────────────────


def test_indice_grava_e_le_igual(tmp_path):
    fca = _fca(
        {},
        {
            "Valor_Mobiliario": "Units",
            "Codigo_Negociacao": "TSTA11",
            "Composicao_BDR_Unit": "1 ON / 2 PN",
        },
        {"Codigo_Negociacao": "4030"},
    )
    cotacoes = [_cot("BOVA11", codbdi="14", especi="CI")]
    indice = _indice(fca, informe=_informe(), cotacoes=cotacoes)
    salvar_indice(indice, tmp_path / "referencia")
    lido = carregar_indice(tmp_path / "referencia")
    assert lido == indice
    assert lido.buscar("tsta3").ticker == "TSTA3"
    assert lido.buscar(None) is None
    assert lido.buscar("NADA3") is None


def test_carregar_sem_arquivo_devolve_none(tmp_path):
    assert carregar_indice(tmp_path) is None


def test_salvar_nao_deixa_arquivo_temporario(tmp_path):
    salvar_indice(_indice(informe=_sem_fii()), tmp_path / "ref")
    assert sorted(p.name for p in (tmp_path / "ref").iterdir()) == ["indice.json"]


# ── cobertura ────────────────────────────────────────────────────────────────


def test_cobertura_conta_mapeaveis_e_mapeados():
    fca = _fca({}, {"Codigo_Negociacao": "4030"})
    cotacoes = [
        _cot("BOVA11", codbdi="14", especi="CI"),
        _cot("AAPL34", codbdi="34", especi="DRN"),
    ]
    informe = _informe()
    indice = _indice(fca, informe=informe, cotacoes=cotacoes)
    c = cobertura(indice, [(2026, fca)], informe)
    assert c["companhias"] == {"codigos_ativos_no_fca": 2, "mapeados": 1}
    assert c["fiis"] == {
        "listados_em_bolsa": 1,
        "mapeados_pela_juncao": 0,
        "mapeados_pela_reserva": 1,
    }
    assert c["outros"] == {"bdr": 1, "unknown": 1}
    assert c["excecoes_por_motivo"] == {"código fora do formato de ticker": 1}


def test_arquivo_do_indice_tem_a_estrutura_documentada(tmp_path):
    import json

    indice = _indice(
        _fca({}, {"Codigo_Negociacao": "ABCD3"}),
        cadastro=_cadastro({"DENOM_SOCIAL": "AÇÃO S.A."}),
        informe=_sem_fii(),
    )
    caminho = salvar_indice(indice, tmp_path / "a" / "b")
    texto = caminho.read_text(encoding="utf-8")
    assert "AÇÃO S.A." in texto  # sem escape de ASCII
    bruto = json.loads(texto)
    assert sorted(bruto) == ["excecoes", "fontes", "gerado_em", "registros"]
    assert list(bruto["registros"]) == ["ABCD3", "TSTA3"]
    assert bruto["gerado_em"] == "2026-10-08"
    assert bruto["fontes"] == FONTES
    assert caminho == tmp_path / "a" / "b" / "indice.json"


def test_normalizar_codigo():
    from sentinela.data.referencia.montagem import normalizar_codigo

    assert normalizar_codigo("  abc3 ") == "ABC3"
    assert normalizar_codigo(None) == ""
    assert normalizar_codigo(float("nan")) == ""
    assert normalizar_codigo(" ") == ""


def test_indice_buscar_normaliza_o_ticker():
    indice = _indice(informe=_sem_fii())
    assert indice.buscar("  tsta3 ").ticker == "TSTA3"


def test_reserva_colide_com_ticker_da_juncao_e_perde():
    informe = _informe(
        {"CNPJ_Fundo_Classe": "44.444.444/0001-44", "Codigo_ISIN": "BRTSTFCTF001"},
        {"CNPJ_Fundo_Classe": "55.555.555/0001-55", "Codigo_ISIN": "BRTSTFCTF002"},
    )
    cotacoes = [_cot("TSTF11", codbdi="12", especi="CI", isin="BRTSTFCTF001")]
    indice = _indice(informe=informe, cotacoes=cotacoes, fca=_fca().iloc[0:0])
    assert indice.registros["TSTF11"].cnpj == "44.444.444/0001-44"
    assert indice.registros["TSTF11"].regra == "fii:informe+cotahist_isin"
    perdedores = [e for e in indice.excecoes if e.motivo == MOTIVO_RESERVA]
    assert [(e.codigo, e.cnpj) for e in perdedores] == [
        ("TSTF11", "55.555.555/0001-55")
    ]


def test_duas_reservas_iguais_saem_ambas():
    informe = _informe(
        {"CNPJ_Fundo_Classe": "44.444.444/0001-44", "Codigo_ISIN": "BRTSTFCTF001"},
        {"CNPJ_Fundo_Classe": "55.555.555/0001-55", "Codigo_ISIN": "BRTSTFCTF002"},
    )
    indice = _indice(informe=informe, fca=_fca().iloc[0:0])
    assert indice.registros == {}
    assert {e.motivo for e in indice.excecoes} == {MOTIVO_REPETIDO}
    assert len(indice.excecoes) == 2


def test_companhia_vence_a_reserva_de_fii():
    informe = _informe({"Codigo_ISIN": "BRTSTACTF001"})  # reserva: TSTA11
    fca = _fca({"Valor_Mobiliario": "Units", "Codigo_Negociacao": "TSTA11"})
    indice = _indice(fca, informe=informe)
    assert indice.registros["TSTA11"].classe == "UNIT"
    assert [e.motivo for e in indice.excecoes] == [MOTIVO_RESERVA]


def test_ticker_repetido_nao_vira_bdr_nem_unknown():
    informe = _informe(
        {"CNPJ_Fundo_Classe": "44.444.444/0001-44", "Codigo_ISIN": "BRTSTFCTF001"},
        {"CNPJ_Fundo_Classe": "55.555.555/0001-55", "Codigo_ISIN": "BRTSTFCTF002"},
    )
    cotacoes = [_cot("TSTF11", codbdi="14", especi="CI", isin="BRQQQQCTF001")]
    indice = _indice(informe=informe, cotacoes=cotacoes, fca=_fca().iloc[0:0])
    assert "TSTF11" not in indice.registros


def test_companhia_do_ano_anterior_leva_a_fonte_do_ano_anterior():
    anterior = _fca(
        {
            "CNPJ_Companhia": CNPJ_B,
            "Codigo_Negociacao": "TSTB3",
            "Data_Referencia": "2025-01-01",
        }
    )
    indice = _indice(_fca({}), fca_anterior=anterior, informe=_sem_fii())
    assert indice.registros["TSTB3"].fonte == FONTES["fca"]["2025"]
    assert indice.registros["TSTA3"].fonte == FONTES["fca"]["2026"]


def test_cobertura_conta_codigos_e_nao_linhas_repetidas():
    fca = _fca({}, {}, {})  # a mesma linha três vezes
    indice = _indice(fca, informe=_sem_fii())
    c = cobertura(indice, [(2026, fca)], _sem_fii())
    assert c["companhias"] == {"codigos_ativos_no_fca": 1, "mapeados": 1}


def test_isin_com_dois_codigos_vale_o_mais_recente():
    antigo = _cot("OLDF11", codbdi="12", especi="CI", isin="BRTSTFCTF001")
    novo = _cot("NEWF11", codbdi="12", especi="CI", isin="BRTSTFCTF001")
    novo = Cotacao(**{**novo.__dict__, "data": date(2026, 9, 30)})
    antigo = Cotacao(**{**antigo.__dict__, "data": date(2026, 8, 3)})
    for ordem in ([antigo, novo], [novo, antigo]):
        indice = _indice(informe=_informe(), cotacoes=ordem, fca=_fca().iloc[0:0])
        assert list(indice.registros) == ["NEWF11"]


def test_fii_da_juncao_perde_para_companhia_com_motivo_proprio():
    informe = _informe({"Codigo_ISIN": "BRTSTACTF001"})
    cotacoes = [_cot("TSTA11", codbdi="12", especi="CI", isin="BRTSTACTF001")]
    fca = _fca({"Valor_Mobiliario": "Units", "Codigo_Negociacao": "TSTA11"})
    indice = _indice(fca, informe=informe, cotacoes=cotacoes)
    assert indice.registros["TSTA11"].classe == "UNIT"
    assert [e.motivo for e in indice.excecoes] == [MOTIVO_COMPANHIA]


def test_situacao_inativa_nao_conta_como_ativa():
    cadastro = _cadastro(
        {"CD_CVM": "1", "SIT": "INATIVO"}, {"CD_CVM": "2", "SIT": " ativo "}
    )
    assert cd_cvm_por_cnpj(cadastro)[CNPJ_A][0] == 2


def test_fca_com_data_de_referencia_vazia_nao_perde_a_companhia():
    fca = _fca({"Data_Referencia": None})
    assert "TSTA3" in _indice(fca, informe=_sem_fii()).registros


def test_fca_mais_recente_mantem_a_data_de_referencia_vazia_como_nan():
    resultado = fca_mais_recente([(2026, _fca({"Data_Referencia": None}))])
    assert resultado["Data_Referencia"].isna().all()
    assert "_referencia" not in resultado.columns


def test_mercado_e_valor_mobiliario_do_fca_com_espaco_contam():
    fca = _fca(
        {"Mercado": " Bolsa ", "Valor_Mobiliario": "Ações Preferenciais "},
        {
            "Codigo_Negociacao": "TSTA11",
            "Mercado": "Balcão Organizado ",
            "Valor_Mobiliario": " Units",
            "Composicao_BDR_Unit": "1 ON + 2 PN",
        },
    )
    registros = _indice(fca, informe=_sem_fii()).registros
    assert registros["TSTA3"].especie == "PN"
    assert registros["TSTA11"].classe == "UNIT"
    assert registros["TSTA11"].acoes_por_unit == {"ON": 1, "PN": 2}


def test_informe_sem_nenhuma_data_valida_avisa_e_nao_tem_fii(caplog):
    informe = _informe(
        {"Data_Referencia": "data ruim"},
        {"CNPJ_Fundo_Classe": "44.444.444/0001-44", "Data_Referencia": None},
    )
    with caplog.at_level("WARNING"):
        indice = _indice(informe=informe, fca=_fca().iloc[0:0])
    assert indice.registros == {}
    assert "nenhuma data de referência válida" in caplog.text


def test_mercado_de_bolsa_com_espaco_conta_como_bolsa():
    informe = _informe(
        {"Mercado_Negociacao_Bolsa": " S "},
        {"CNPJ_Fundo_Classe": "44.444.444/0001-44", "Mercado_Negociacao_Bolsa": None},
    )
    assert list(_indice(informe=informe, fca=_fca().iloc[0:0]).registros) == ["TSTF11"]


def test_fundo_que_nao_informa_ha_mais_de_seis_meses_sai():
    informe = _informe(
        {
            "CNPJ_Fundo_Classe": "44.444.444/0001-44",
            "Data_Referencia": "2026-08-01",
            "Codigo_ISIN": "BRAAAACTF001",
        },
        {
            "CNPJ_Fundo_Classe": "55.555.555/0001-55",
            "Data_Referencia": "2026-02-01",
            "Codigo_ISIN": "BRBBBBCTF001",
        },
        {
            "CNPJ_Fundo_Classe": "66.666.666/0001-66",
            "Data_Referencia": "2026-01-31",
            "Codigo_ISIN": "BRCCCCCTF001",
        },
        {
            "CNPJ_Fundo_Classe": "77.777.777/0001-77",
            "Data_Referencia": "2025-12-01",
            "Codigo_ISIN": "BRDDDDCTF001",
        },
    )
    indice = _indice(informe=informe, fca=_fca().iloc[0:0])
    assert sorted(indice.registros) == ["AAAA11", "BBBB11"]
