"""F3-3b-fix: conflitos da carga da CVM até o leitor (BUG-3-26, DD-57, DD-58) e o Informe de FII
no leiaute anterior à Resolução 175 (BUG-3-25), com a releitura de arquivo já registrado.

Fixtures oficiais recortadas: DFP de 2019 (00.776.574/0001-56, versões 1 e 2 entregues em
20 e 21/02/2020), Informe de FII de 2017 (00.332.266/0001-31, leiaute antigo) e o FCA
sintético de `test_universo_pit`.
"""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from test_carga_cvm import CIA, DFP, FUNDO, ITR, _copia
from test_universo_pit import (
    CADASTRO_TSTE,
    TSTE,
    _fca_sintetico,
    _negocio,
    _precos,
    _pregoes,
    _valor,
)

from sentinela.data.pit import carga_cvm, leitura
from sentinela.data.referencia import universo
from sentinela.data.store import migracoes

INFORME_2017 = (
    Path(__file__).parent / "fixtures" / "pit_cvm" / "inf_mensal_fii_2017.zip"
)
DRE = "dfp_cia_aberta_DRE_con_2019.csv"
COLETA = "2026-11-12T19:00:00+00:00"
DEPOIS = datetime(2026, 11, 12, 15, tzinfo=UTC)


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _carregar(conn, arquivo, tipo, **kw):
    return carga_cvm.carregar(
        conn, arquivo, tipo=tipo, fonte=f"cvm:{Path(arquivo).name}", coleta=COLETA, **kw
    )


def _receita_contraditoria(texto):
    linhas = texto.splitlines(keepends=True)
    receita = next(l for l in linhas if ";ÚLTIMO;" in l and ";3.01;" in l)
    return "".join(linhas) + receita.replace("6767982.0000000000", "6767983.0000000000")


def _conflito(conn, tabela, versao, documento="DFP", cnpj=CIA, dt_refer="2019-12-31",
              arquivo=("x",)):  # fmt: skip
    conn.execute(
        "INSERT INTO conflitos_carga VALUES (?, ?, ?, ?, ?, ?, '[]', ?, 'f', 'c', 'h')",
        (tabela, cnpj, documento, dt_refer, versao, f"{tabela}{versao}{documento}{cnpj}{dt_refer}", json.dumps(arquivo)),
    )  # fmt: skip


# --- Carga -----------------------------------------------------------------------------------


def test_conflito_gravado_com_os_dois_lados_e_a_proveniencia(conn, tmp_path):
    arquivo = _copia(DFP, tmp_path / "dfp.zip", {DRE: _receita_contraditoria})
    resumo = _carregar(conn, arquivo, "DFP")
    linhas = conn.execute(
        "SELECT tabela, cnpj, documento, dt_refer, versao, chave_json, gravado_json, "
        "arquivo_json, fonte, coleta, hash_sha256 FROM conflitos_carga"
    ).fetchall()
    assert resumo.total_conflitos == 1 and len(linhas) == 1
    (
        tabela,
        cnpj,
        documento,
        dt_refer,
        versao,
        chave,
        gravado,
        novo,
        fonte,
        coleta,
        hash_,
    ) = linhas[0]
    assert (tabela, cnpj, documento, dt_refer, versao) == (
        "demonstracoes", CIA, "DFP", "2019-12-31", 2,
    )  # fmt: skip
    assert json.loads(chave) == resumo.conflitos[0]["chave"]
    assert json.loads(chave)["conta"] == "3.01"
    assert chave == json.dumps(json.loads(chave), ensure_ascii=False, sort_keys=True)
    assert list(json.loads(chave)) == sorted(json.loads(chave))
    servicos = '"Receita de Venda de Bens e/ou Serviços"'  # sem escapar o acento
    assert gravado.startswith("[" + servicos) and novo.startswith("[" + servicos)
    assert json.loads(gravado)[1] == 6767982.0 and json.loads(novo)[1] == 6767983.0
    assert (fonte, coleta, hash_) == ("cvm:dfp.zip", COLETA, resumo.hash_sha256)


def test_releitura_nao_duplica_registro_nem_conflito(conn, tmp_path):
    arquivo = _copia(DFP, tmp_path / "dfp.zip", {DRE: _receita_contraditoria})
    primeira = _carregar(conn, arquivo, "DFP")
    assert _carregar(conn, arquivo, "DFP").ja_carregado
    relida = _carregar(conn, arquivo, "DFP", reler=True)
    assert relida.relido and not relida.ja_carregado
    assert dict(relida.inseridas) == {}
    assert sum(relida.repetidas.values()) == sum(primeira.inseridas.values())
    assert relida.total_conflitos == 1 and relida.so_ultima_versao is not None
    assert conn.execute("SELECT COUNT(*) FROM conflitos_carga").fetchone() == (1,)
    assert conn.execute("SELECT COUNT(*) FROM cargas_arquivo").fetchone() == (1,)
    assert not primeira.relido


def test_releitura_de_arquivo_nunca_carregado_registra(conn):
    resumo = _carregar(conn, DFP, "DFP", reler=True)
    assert not resumo.relido and sum(resumo.inseridas.values()) > 0
    assert conn.execute("SELECT COUNT(*) FROM cargas_arquivo").fetchone() == (1,)


def test_conflito_no_indice_do_fca_registra_documento_fca(conn, tmp_path):
    _fca_sintetico(conn, tmp_path, [(TSTE, "2026-01-01", "1", "2026-02-01")], [])
    _fca_sintetico(
        conn, tmp_path, [(TSTE, "2026-01-01", "1", "2026-04-01")], [], ano=2027
    )
    (linha,) = conn.execute(
        "SELECT documento, tabela, versao, arquivo_json FROM conflitos_carga"
    ).fetchall()
    assert (
        linha[:3] == ("FCA", "fca_entregas", 1)
        and json.loads(linha[3])[4] == "2026-04-01"
    )


def test_informe_antigo_gravado_pelo_cnpj_do_fundo(conn):
    resumo = _carregar(conn, INFORME_2017, "FII_INFORME")
    assert resumo.recusadas == [] and resumo.inseridas == {"fii_informe_linhas": 36}
    assert conn.execute("SELECT DISTINCT cnpj FROM fii_informe_linhas").fetchall() == [
        (FUNDO,)
    ]
    (texto,) = conn.execute(
        "SELECT linha_json FROM fii_informe_linhas WHERE parte = 'geral' LIMIT 1"
    ).fetchone()
    assert "CNPJ_Fundo" in json.loads(texto)  # guardada como o arquivo a traz
    linha = carga_cvm.linha_do_informe(texto)
    assert linha["CNPJ_Fundo_Classe"] == FUNDO and "CNPJ_Fundo" not in linha
    assert (
        linha["Nome_Fundo_Classe"].startswith("FUNDO DE INVESTIMENTO")
        and "Nome_Fundo" not in linha
    )
    assert linha["Codigo_ISIN"] == "BRFVPQCTF015"


@pytest.mark.parametrize(
    ("linha", "esperado"),
    [
        ({"CNPJ_Fundo": " 1 "}, "1"),
        ({"CNPJ_Fundo_Classe": "2"}, "2"),
        ({"CNPJ_Fundo": ""}, "CNPJ_Fundo vazio"),
        ({"CNPJ_Fundo_Classe": ""}, "CNPJ_Fundo_Classe vazio"),
        ({}, "CNPJ_Fundo_Classe vazio"),
        ({"CNPJ_Fundo": "1", "CNPJ_Fundo_Classe": "1"}, "CNPJ_Fundo e CNPJ_Fundo_Classe na mesma linha"),
    ],
)  # fmt: skip
def test_cnpj_do_fundo_nos_dois_leiautes(linha, esperado):
    if esperado.isdigit():
        assert carga_cvm._cnpj_do_fundo(linha) == esperado
    else:
        with pytest.raises(carga_cvm.LinhaRecusada, match=f"^{esperado}$"):
            carga_cvm._cnpj_do_fundo(linha)


def test_linha_do_informe_atual_fica_igual():
    linha = {"CNPJ_Fundo_Classe": "1", "Nome_Fundo_Classe": "N", "Versao": "1"}
    assert carga_cvm.linha_do_informe(json.dumps(linha)) == linha


def test_informe_antigo_lido_pelo_leitor_do_fundo(conn):
    _carregar(conn, INFORME_2017, "FII_INFORME")
    lido = leitura.informe_fii(conn, FUNDO, datetime(2018, 2, 15, 15, tzinfo=UTC))
    registros = lido.dados["registros"]
    assert len(registros) == 12 and lido.motivos == {}
    assert {r["CNPJ_Fundo_Classe"] for r in registros} == {FUNDO}
    assert all("CNPJ_Fundo" not in r for r in registros)


# --- Leitor das demonstrações (DD-57) -------------------------------------------------------


@pytest.mark.parametrize("modo", leitura.MODOS)
def test_conflito_na_versao_escolhida_tira_o_documento_inteiro(conn, tmp_path, modo):
    _carregar(
        conn, _copia(DFP, tmp_path / "dfp.zip", {DRE: _receita_contraditoria}), "DFP"
    )
    motivo = {(CIA, "2019-12-31"): leitura.MOTIVO_CONFLITO_NA_FONTE}
    dre = leitura.demonstrativo(conn, "DFP", "DRE_con", DEPOIS, modo=modo)
    bpa = leitura.demonstrativo(conn, "DFP", "BPA_con", DEPOIS, modo=modo, cnpj=CIA)
    for lido in (dre, bpa):
        assert lido.motivos == motivo and len(lido.dados) == 0
    # a DFP de 2019 não tem composição: o motivo é o dela, sem versão escolhida em conflito
    composicao = leitura.composicao(conn, "DFP", DEPOIS, modo=modo)
    assert composicao.motivos == {(CIA, "2019-12-31"): leitura.MOTIVO_SEM_NUMEROS}


def test_conflito_nas_contas_tira_a_composicao_da_mesma_versao(conn):
    _carregar(conn, ITR, "ITR")
    escolhida = leitura.composicao(conn, "ITR", DEPOIS)
    assert len(escolhida.dados) > 0 and escolhida.motivos == {}
    cnpj, dt_refer, versao = escolhida.dados.iloc[0][["CNPJ_CIA", "DT_REFER", "VERSAO"]]
    _conflito(
        conn,
        "demonstracoes",
        int(versao),
        documento="ITR",
        cnpj=cnpj,
        dt_refer=dt_refer,
    )
    lido = leitura.composicao(conn, "ITR", DEPOIS)
    assert lido.motivos == {(cnpj, dt_refer): leitura.MOTIVO_CONFLITO_NA_FONTE}
    assert (lido.dados["DT_REFER"] != dt_refer).all()


def test_sem_conflito_o_documento_e_lido(conn):
    _carregar(conn, DFP, "DFP")
    lido = leitura.demonstrativo(conn, "DFP", "DRE_con", DEPOIS)
    assert lido.motivos == {} and len(lido.dados) > 0


@pytest.mark.parametrize(
    ("tabela", "versao", "fora"),
    [("demonstracoes", 1, False), ("composicao_capital", 1, False), ("entregas", 1, True),
     ("demonstracoes", 2, True), ("composicao_capital", 2, True), ("entregas", 2, True),
     ("entregas", 3, True)],
)  # fmt: skip
def test_conflito_conta_no_indice_em_qualquer_versao_e_nos_numeros_so_na_escolhida(
    conn, tabela, versao, fora
):
    _carregar(conn, DFP, "DFP")
    _conflito(conn, tabela, versao)
    lido = leitura.demonstrativo(conn, "DFP", "DRE_con", DEPOIS)
    assert (
        lido.motivos == {(CIA, "2019-12-31"): leitura.MOTIVO_CONFLITO_NA_FONTE}
    ) is fora
    assert (len(lido.dados) == 0) is fora


def test_conflito_de_outro_documento_tipo_ou_companhia_nao_tira(conn):
    _carregar(conn, DFP, "DFP")
    _conflito(conn, "entregas", 2, documento="ITR")
    _conflito(conn, "entregas", 2, cnpj="99.999.999/0001-99")
    _conflito(conn, "entregas", 2, dt_refer="2018-12-31")
    for cnpj in (None, CIA):
        lido = leitura.demonstrativo(conn, "DFP", "DRE_con", DEPOIS, cnpj=cnpj)
        assert lido.motivos == {} and len(lido.dados) > 0


def test_conflito_de_documento_que_nao_existia_em_d_fica_sem_motivo(conn):
    _carregar(conn, DFP, "DFP")
    _conflito(conn, "entregas", 2)
    antes = datetime(
        2020, 2, 20, 15, tzinfo=UTC
    )  # nenhuma versão entregue antes do dia
    lido = leitura.demonstrativo(conn, "DFP", "DRE_con", antes)
    assert lido.motivos == {} and len(lido.dados) == 0


def test_conflito_tira_documento_que_ja_tinha_outro_motivo(conn):
    _carregar(conn, DFP, "DFP")
    _conflito(conn, "entregas", 1)
    entre = datetime(
        2020, 2, 21, 15, tzinfo=UTC
    )  # só a versão 1, sem números, entregue
    lido = leitura.demonstrativo(conn, "DFP", "DRE_con", entre)
    assert lido.motivos == {(CIA, "2019-12-31"): leitura.MOTIVO_CONFLITO_NA_FONTE}


# --- Universo: entrega do FCA em conflito (DD-58) --------------------------------------------


def _fca_com_acao(conn, tmp_path, receb="2026-02-01"):
    acao = _valor(Valor_Mobiliario="Ações Ordinárias", Codigo_Negociacao="TSTE3",
                  Data_Inicio_Negociacao="2020-01-02")  # fmt: skip
    _fca_sintetico(conn, tmp_path, [(TSTE, "2026-01-01", "1", receb)], [acao])


@pytest.mark.parametrize(
    ("outra_entrega", "dia", "presente"),
    [("2026-04-01", date(2026, 3, 1), False), ("2026-04-01", date(2026, 4, 1), False),
     ("2026-04-01", date(2026, 4, 2), True), ("2026-01-15", date(2026, 3, 1), True),
     ("", date(2026, 12, 1), False), (None, date(2026, 12, 1), False)],
)  # fmt: skip
def test_versao_do_fca_vale_pela_entrega_mais_tardia(
    conn, tmp_path, outra_entrega, dia, presente
):
    _fca_com_acao(conn, tmp_path)
    _conflito(conn, "fca_entregas", 1, documento="FCA", cnpj=TSTE, dt_refer="2026-01-01",
              arquivo=["099999", "TESTE S.A.", "FCA", "2", outra_entrega])  # fmt: skip
    companhias = universo.companhias_em(conn, dia)
    assert bool(companhias["companhias"]) is presente
    assert universo._entregas_vigentes(conn, dia.isoformat()) == (
        {(TSTE, "2026-01-01"): True} if presente else {}
    )


def test_conflito_das_contas_ou_de_outra_versao_nao_muda_o_fca(conn, tmp_path):
    _fca_com_acao(conn, tmp_path)
    tarde = ["099999", "TESTE S.A.", "FCA", "2", "2026-04-01"]
    _conflito(conn, "demonstracoes", 1, documento="DFP", cnpj=TSTE, dt_refer="2026-01-01",
              arquivo=tarde)  # fmt: skip
    _conflito(conn, "fca_entregas", 2, documento="FCA", cnpj=TSTE, dt_refer="2026-01-01",
              arquivo=tarde)  # fmt: skip
    _conflito(conn, "fca_linhas", 1, documento="FCA", cnpj=TSTE, dt_refer="2026-01-01",
              arquivo=tarde)  # fmt: skip
    assert universo.companhias_em(conn, date(2026, 3, 1))["companhias"]


def test_fii_do_informe_antigo_entra_no_indice_em_d(conn, tmp_path):
    dias = _pregoes(date(2018, 1, 2), 5)
    _precos(conn, tmp_path, [_negocio(d, "FVPQ11", "BRFVPQCTF015") for d in dias])
    _carregar(conn, INFORME_2017, "FII_INFORME")
    indice = universo.indice_em(conn, dias[-1] + timedelta(days=1), CADASTRO_TSTE)
    registro = indice.registros["FVPQ11"]
    assert registro.classe == "FII" and registro.cnpj == FUNDO
    assert registro.nome.startswith("FUNDO DE INVESTIMENTO IMOBILI")


def test_conflito_de_documento_fora_de_d_nao_interrompe_os_seguintes(conn):
    _carregar(conn, DFP, "DFP")
    _conflito(conn, "entregas", 2, dt_refer="2018-12-31")  # documento que não existe
    _conflito(conn, "entregas", 2)
    lido = leitura.demonstrativo(conn, "DFP", "DRE_con", DEPOIS)
    assert lido.motivos == {(CIA, "2019-12-31"): leitura.MOTIVO_CONFLITO_NA_FONTE}


def test_entrega_em_conflito_nao_interrompe_as_seguintes(conn, tmp_path):
    outra = "22.222.222/0001-22"
    _fca_sintetico(
        conn, tmp_path,
        [(TSTE, "2026-01-01", "1", "2026-02-01"), (outra, "2026-01-01", "1", "2026-02-01")],
        [],
    )  # fmt: skip
    _conflito(conn, "fca_entregas", 1, documento="FCA", cnpj=TSTE, dt_refer="2026-01-01",
              arquivo=["099999", "TESTE S.A.", "FCA", "2", "2026-04-01"])  # fmt: skip
    assert universo._entregas_vigentes(conn, "2026-03-01") == {
        (outra, "2026-01-01"): False
    }


def test_versao_vigente_e_a_maior_qualquer_que_seja_a_ordem_do_indice(conn, tmp_path):
    acao = _valor(Versao="1", Valor_Mobiliario="Ações Ordinárias", Codigo_Negociacao="TSTE3",
                  Data_Inicio_Negociacao="2020-01-02")  # fmt: skip
    _fca_sintetico(
        conn,
        tmp_path,
        [
            (TSTE, "2026-01-01", "2", "2026-02-02"),
            (TSTE, "2026-01-01", "1", "2026-02-01"),
        ],
        [acao],
    )  # fmt: skip  (a versão 2, sem conteúdo no arquivo, vem antes no índice)
    assert universo._entregas_vigentes(conn, "2026-03-01") == {
        (TSTE, "2026-01-01"): False
    }
