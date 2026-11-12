"""F3-3b: carga dos ZIPs abertos da CVM no banco único (`sentinela.data.pit.carga_cvm`).

As fixtures em `tests/fixtures/pit_cvm/` são os ZIPs oficiais da CVM recortados para uma
companhia (00.776.574/0001-56: ITR de 2020, DFP de 2019 e FCA de 2015) e um FII
(00.332.266/0001-31, Informe de 2023), com o mesmo leiaute e a mesma codificação; os
originais e os hashes estão em `data/fontes/l1/` (F3-L1).
"""

import csv
import io
import json
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path

import pytest

from sentinela.data.pit import carga_cvm
from sentinela.data.store import migracoes

FIXTURES = Path(__file__).parent / "fixtures" / "pit_cvm"
ITR = FIXTURES / "itr_cia_aberta_2020.zip"
DFP = FIXTURES / "dfp_cia_aberta_2019.zip"
FCA = FIXTURES / "fca_cia_aberta_2015.zip"
FII = FIXTURES / "inf_mensal_fii_2023.zip"
CIA = "00.776.574/0001-56"
FUNDO = "00.332.266/0001-31"
COLETA = "2026-11-11T12:00:00+00:00"


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _carregar(conn, arquivo, tipo, coleta=COLETA):
    return carga_cvm.carregar(
        conn, arquivo, tipo=tipo, fonte=f"cvm:{Path(arquivo).name}", coleta=coleta
    )


def _csv(arquivo, nome):
    texto = zipfile.ZipFile(arquivo).read(nome).decode("latin-1")
    return list(csv.DictReader(io.StringIO(texto), delimiter=";"))


def _copia(origem, destino, alterar=None, compressao=zipfile.ZIP_DEFLATED):
    """Cópia do ZIP com o texto de alguns membros alterado (`{nome: função(texto)}`)."""
    alterar = alterar or {}
    with zipfile.ZipFile(origem) as zi, zipfile.ZipFile(destino, "w", compressao) as zo:
        for nome in zi.namelist():
            texto = zi.read(nome).decode("latin-1")
            if nome in alterar:
                texto = alterar[nome](texto)
            zo.writestr(nome, texto.encode("latin-1"))
    return destino


def _contar(conn, tabela, onde="1", parametros=()):
    return conn.execute(
        f"SELECT COUNT(*) FROM {tabela} WHERE {onde}", parametros
    ).fetchone()[0]


# --- ITR -----------------------------------------------------------------------------------


def test_itr_grava_todas_as_versoes_do_indice_com_a_marca_do_conteudo(conn):
    resumo = _carregar(conn, ITR, "ITR")
    linhas = conn.execute(
        "SELECT dt_refer, versao, dt_receb, valores_na_fonte, id_documento FROM entregas "
        "WHERE cnpj = ? AND documento = 'ITR' ORDER BY dt_refer, versao",
        (CIA,),
    ).fetchall()
    assert linhas == [
        ("2020-03-31", 1, "2020-05-07", 0, "92819"),
        ("2020-03-31", 2, "2020-05-21", 1, "93342"),
        ("2020-06-30", 1, "2020-08-13", 1, "96062"),
        ("2020-09-30", 1, "2020-10-29", 1, "97955"),
    ]
    assert resumo.so_ultima_versao is True
    assert resumo.total_conflitos == 0
    assert resumo.total_recusadas == 0
    assert resumo.sem_entrega == []


def test_itr_grava_cada_linha_das_demonstracoes_sem_perder_nenhuma(conn):
    resumo = _carregar(conn, ITR, "ITR")
    nomes = [
        n for n in zipfile.ZipFile(ITR).namelist()
        if any(f"_{d}_" in n for d in ("BPA", "BPP", "DRE", "DRA", "DMPL", "DFC", "DVA"))
    ]  # fmt: skip
    esperado = sum(len(_csv(ITR, n)) for n in nomes)
    assert esperado > 6000
    assert _contar(conn, "demonstracoes") == esperado
    assert resumo.inseridas["demonstracoes"] == esperado
    assert resumo.repetidas.get("demonstracoes", 0) == 0
    assert resumo.ignorados == ["itr_cia_aberta_parecer_2020.csv"]


def test_itr_trimestre_isolado_e_acumulado_na_mesma_versao(conn):
    _carregar(conn, ITR, "ITR")
    linhas = conn.execute(
        "SELECT dt_ini_exerc, valor FROM demonstracoes WHERE dt_refer = '2020-06-30' AND "
        "demonstracao = 'DRE_con' AND ordem_exerc = 'ÚLTIMO' AND conta = '3.01' "
        "ORDER BY dt_ini_exerc"
    ).fetchall()
    origem = {
        r["DT_INI_EXERC"]: float(r["VL_CONTA"])
        for r in _csv(ITR, "itr_cia_aberta_DRE_con_2020.csv")
        if r["DT_REFER"] == "2020-06-30"
        and r["ORDEM_EXERC"] == "ÚLTIMO"
        and r["CD_CONTA"] == "3.01"
    }
    assert linhas == sorted(origem.items())
    assert [inicio for inicio, _ in linhas] == ["2020-01-01", "2020-04-01"]


def test_valor_como_declarado_com_a_escala_do_documento(conn):
    _carregar(conn, ITR, "ITR")
    origem = next(
        r for r in _csv(ITR, "itr_cia_aberta_BPA_con_2020.csv")
        if r["DT_REFER"] == "2020-03-31" and r["ORDEM_EXERC"] == "ÚLTIMO" and r["CD_CONTA"] == "1"
    )  # fmt: skip
    gravado = conn.execute(
        "SELECT valor, escala, moeda, dt_ini_exerc, coluna_df, versao, fonte, coleta, hash_sha256 "
        "FROM demonstracoes WHERE demonstracao = 'BPA_con' AND dt_refer = '2020-03-31' "
        "AND ordem_exerc = 'ÚLTIMO' AND conta = '1'"
    ).fetchone()
    assert gravado[:6] == (float(origem["VL_CONTA"]), "MIL", "REAL", "", "", 2)
    assert gravado[6:] == (
        "cvm:itr_cia_aberta_2020.zip",
        COLETA,
        carga_cvm.proveniencia.hash_sha256(ITR),
    )


def test_dmpl_grava_cada_coluna(conn):
    _carregar(conn, ITR, "ITR")
    colunas = {
        c
        for (c,) in conn.execute(
            "SELECT DISTINCT coluna_df FROM demonstracoes WHERE demonstracao = 'DMPL_con'"
        )
    }
    origem = {r["COLUNA_DF"] for r in _csv(ITR, "itr_cia_aberta_DMPL_con_2020.csv")}
    assert colunas == origem
    assert len(colunas) > 3


def test_composicao_do_capital_como_declarada(conn):
    _carregar(conn, ITR, "ITR")
    linhas = conn.execute(
        "SELECT dt_refer, versao, acoes_ordinarias, acoes_total, tesouraria_total "
        "FROM composicao_capital ORDER BY dt_refer"
    ).fetchall()
    origem = [
        (
            r["DT_REFER"],
            int(r["VERSAO"]),
            float(r["QT_ACAO_ORDIN_CAP_INTEGR"]),
            float(r["QT_ACAO_TOTAL_CAP_INTEGR"]),
            float(r["QT_ACAO_TOTAL_TESOURO"]),
        )
        for r in _csv(ITR, "itr_cia_aberta_composicao_capital_2020.csv")
    ]
    assert linhas == sorted(origem)
    assert len(linhas) == 3


# --- DFP, FCA e FII ------------------------------------------------------------------------


def test_dfp_reapresentada_grava_as_duas_entregas(conn):
    resumo = _carregar(conn, DFP, "DFP")
    assert conn.execute(
        "SELECT versao, dt_receb, valores_na_fonte FROM entregas WHERE documento = 'DFP' ORDER BY versao"
    ).fetchall() == [(1, "2020-02-20", 0), (2, "2020-02-21", 1)]
    versoes = {v for (v,) in conn.execute("SELECT DISTINCT versao FROM demonstracoes")}
    assert versoes == {2}
    assert resumo.so_ultima_versao is True
    assert _contar(conn, "composicao_capital") == 0


def test_fca_grava_o_indice_e_as_linhas_de_cada_parte(conn):
    resumo = _carregar(conn, FCA, "FCA")
    entregas = conn.execute(
        "SELECT versao, dt_receb, valores_na_fonte FROM fca_entregas ORDER BY versao"
    ).fetchall()
    versao_geral = _csv(FCA, "fca_cia_aberta_geral_2015.csv")[0]["Versao"]
    assert [(v, r) for v, r, _ in entregas] == [(1, "2015-01-16"), (2, "2015-08-17")]
    assert [m for v, _, m in entregas] == [
        int(str(v) == versao_geral) for v, _, _ in entregas
    ]
    partes = dict(
        conn.execute("SELECT parte, COUNT(*) FROM fca_linhas GROUP BY parte").fetchall()
    )
    nomes = [
        n for n in zipfile.ZipFile(FCA).namelist() if n != "fca_cia_aberta_2015.csv"
    ]
    assert partes == {
        n.removeprefix("fca_cia_aberta_").removesuffix("_2015.csv"): len(_csv(FCA, n))
        for n in nomes
    }
    mobiliario = json.loads(
        conn.execute(
            "SELECT linha_json FROM fca_linhas WHERE parte = 'valor_mobiliario'"
        ).fetchone()[0]
    )
    assert mobiliario == _csv(FCA, "fca_cia_aberta_valor_mobiliario_2015.csv")[0]
    assert resumo.so_ultima_versao is True


def test_informe_fii_grava_as_tres_partes_com_a_entrega_do_geral(conn):
    resumo = _carregar(conn, FII, "FII_INFORME")
    partes = dict(
        conn.execute(
            "SELECT parte, COUNT(*) FROM fii_informe_linhas GROUP BY parte"
        ).fetchall()
    )
    assert partes == {"geral": 12, "complemento": 12, "ativo_passivo": 12}
    entregas = conn.execute(
        "SELECT dt_refer, versao, data_entrega FROM fii_informe_linhas WHERE parte = 'geral' ORDER BY dt_refer"
    ).fetchall()
    origem = sorted(
        (r["Data_Referencia"], r["Versao"], r["Data_Entrega"])
        for r in _csv(FII, "inf_mensal_fii_geral_2023.csv")
    )
    assert entregas == origem
    assert (
        _contar(conn, "fii_informe_linhas", "parte != 'geral' AND data_entrega != ''")
        == 0
    )
    assert resumo.so_ultima_versao is True


def test_informe_fii_guarda_as_linhas_diferentes_da_mesma_versao(conn, tmp_path):
    """Conflito de mesma versão: as duas linhas ficam; a leitura abstém (ficha FII 1.3)."""

    def duplicar(texto):
        linhas = texto.splitlines(keepends=True)
        return texto + linhas[1].replace(";2800149;", ";2800150;")

    arquivo = _copia(
        FII, tmp_path / "fii.zip", {"inf_mensal_fii_geral_2023.csv": duplicar}
    )
    resumo = _carregar(conn, arquivo, "FII_INFORME")
    primeira = _csv(FII, "inf_mensal_fii_geral_2023.csv")[0]
    assert _contar(
        conn, "fii_informe_linhas", "parte = 'geral' AND dt_refer = ? AND versao = ?",
        (primeira["Data_Referencia"], primeira["Versao"]),
    ) == 2  # fmt: skip
    assert resumo.so_ultima_versao is True  # mesma versão: o conflito é de conteúdo


# --- Idempotência, versões novas e conflitos -----------------------------------------------


def test_mesmo_arquivo_nao_e_lido_de_novo(conn):
    primeiro = _carregar(conn, ITR, "ITR")
    antes = {
        t: _contar(conn, t) for t in ("entregas", "demonstracoes", "composicao_capital")
    }
    segundo = _carregar(conn, ITR, "ITR", coleta="2026-11-12T12:00:00+00:00")
    assert segundo.ja_carregado is True
    assert segundo.hash_sha256 == primeiro.hash_sha256
    assert not segundo.inseridas
    assert {t: _contar(conn, t) for t in antes} == antes
    registro = conn.execute(
        "SELECT tipo, arquivo, coleta, so_ultima_versao FROM cargas_arquivo"
    ).fetchall()
    assert registro == [("ITR", "itr_cia_aberta_2020.zip", COLETA, 1)]
    assert json.loads(
        conn.execute("SELECT resumo_json FROM cargas_arquivo").fetchone()[0]
    )["inseridas"] == dict(primeiro.inseridas)


def test_outro_arquivo_com_as_mesmas_linhas_so_conta_repetidas(conn, tmp_path):
    _carregar(conn, ITR, "ITR")
    antes = _contar(conn, "demonstracoes")
    copia = _copia(ITR, tmp_path / "itr.zip", compressao=zipfile.ZIP_STORED)
    resumo = _carregar(conn, copia, "ITR", coleta="2026-11-12T12:00:00+00:00")
    assert resumo.ja_carregado is False
    assert not resumo.inseridas
    assert resumo.repetidas["demonstracoes"] == antes
    assert resumo.repetidas["entregas"] == 4
    assert resumo.total_conflitos == 0
    assert _contar(conn, "demonstracoes") == antes
    assert _contar(conn, "cargas_arquivo") == 2


def test_versao_nova_entra_e_a_antiga_fica(conn, tmp_path):
    """Reapresentação depois da primeira coleta: a versão 3 entra sem apagar a 2."""
    _carregar(conn, ITR, "ITR")
    trimestre = ";2020-03-31;2;"

    def v3(texto):
        return texto.replace(trimestre, ";2020-03-31;3;")

    def indice(texto):
        linha = next(l for l in texto.splitlines(keepends=True) if trimestre in l)
        return texto + linha.replace(trimestre, ";2020-03-31;3;").replace(
            "2020-05-21", "2021-01-15"
        )

    alterar = {
        n: v3 for n in zipfile.ZipFile(ITR).namelist() if n != "itr_cia_aberta_2020.csv"
    }
    alterar["itr_cia_aberta_2020.csv"] = indice
    resumo = _carregar(
        conn,
        _copia(ITR, tmp_path / "itr_v3.zip", alterar),
        "ITR",
        coleta="2026-11-12T12:00:00+00:00",
    )
    versoes = conn.execute(
        "SELECT versao, COUNT(*) FROM demonstracoes WHERE dt_refer = '2020-03-31' GROUP BY versao"
    ).fetchall()
    assert (
        versoes[0][0] == 2 and versoes[1][0] == 3 and versoes[0][1] == versoes[1][1] > 0
    )
    marcas = conn.execute(
        "SELECT versao, dt_receb, valores_na_fonte FROM entregas WHERE dt_refer = '2020-03-31' ORDER BY versao"
    ).fetchall()
    # a marca da versão 2 é a da primeira coleta, que trazia os números dela
    assert marcas == [(1, "2020-05-07", 0), (2, "2020-05-21", 1), (3, "2021-01-15", 1)]
    assert resumo.inseridas["entregas"] == 1
    assert resumo.repetidas["entregas"] == 4  # a v1 e a v2 do 1º tri, o 2º e o 3º
    assert (
        resumo.total_conflitos == 0
    )  # a marca da v2 no arquivo novo é 0, sem conflito
    assert resumo.so_ultima_versao is True


def test_mesma_chave_com_valor_diferente_vira_conflito_e_fica_a_gravada(conn, tmp_path):
    _carregar(conn, ITR, "ITR")
    original = next(
        r for r in _csv(ITR, "itr_cia_aberta_BPA_con_2020.csv")
        if r["DT_REFER"] == "2020-03-31" and r["ORDEM_EXERC"] == "ÚLTIMO" and r["CD_CONTA"] == "1"
    )  # fmt: skip
    trecho = f";1;Ativo Total;{original['VL_CONTA']};"

    def mudar(texto):
        linha = next(
            l
            for l in texto.splitlines()
            if ";2020-03-31;" in l and ";ÚLTIMO;" in l and trecho in l
        )
        return texto.replace(
            linha, linha.replace(trecho, ";1;Ativo Total;1.0000000000;")
        )

    copia = _copia(
        ITR, tmp_path / "itr.zip", {"itr_cia_aberta_BPA_con_2020.csv": mudar}
    )
    resumo = _carregar(conn, copia, "ITR", coleta="2026-11-12T12:00:00+00:00")
    assert resumo.total_conflitos == 1
    conflito = resumo.conflitos[0]
    assert conflito["tabela"] == "demonstracoes"
    assert conflito["chave"]["conta"] == "1" and conflito["chave"]["versao"] == 2
    assert (
        conflito["gravado"][1] == float(original["VL_CONTA"])
        and conflito["arquivo"][1] == 1.0
    )
    valor = conn.execute(
        "SELECT valor FROM demonstracoes WHERE demonstracao = 'BPA_con' AND dt_refer = '2020-03-31' "
        "AND ordem_exerc = 'ÚLTIMO' AND conta = '1'"
    ).fetchone()
    assert valor == (float(original["VL_CONTA"]),)
    gravado = json.loads(
        conn.execute(
            "SELECT resumo_json FROM cargas_arquivo WHERE hash_sha256 = ?",
            (resumo.hash_sha256,),
        ).fetchone()[0]
    )
    assert gravado["total_conflitos"] == 1


def test_conteudo_com_duas_versoes_do_mesmo_documento_tira_a_marca(conn, tmp_path):
    def v1_tambem(texto):
        extra = [
            l.replace(";2020-06-30;1;", ";2020-06-30;0;")
            for l in texto.splitlines(keepends=True)
            if ";2020-06-30;1;" in l
        ]
        return texto + "".join(extra)

    copia = _copia(
        ITR, tmp_path / "itr.zip", {"itr_cia_aberta_DRE_con_2020.csv": v1_tambem}
    )
    resumo = _carregar(conn, copia, "ITR")
    assert resumo.so_ultima_versao is False
    assert conn.execute("SELECT so_ultima_versao FROM cargas_arquivo").fetchone() == (
        0,
    )


def test_conteudo_com_versao_menor_que_a_do_indice_tira_a_marca(conn, tmp_path):
    def so_v1(texto):
        return texto.replace(";2020-03-31;2;", ";2020-03-31;1;")

    alterar = {
        n: so_v1
        for n in zipfile.ZipFile(ITR).namelist()
        if n != "itr_cia_aberta_2020.csv"
    }
    resumo = _carregar(conn, _copia(ITR, tmp_path / "itr.zip", alterar), "ITR")
    assert resumo.so_ultima_versao is False
    assert conn.execute(
        "SELECT versao, valores_na_fonte FROM entregas WHERE dt_refer = '2020-03-31' ORDER BY versao"
    ).fetchall() == [(1, 1), (2, 0)]


# --- Linhas ilegíveis, vazio e atomicidade -------------------------------------------------


def test_valor_vazio_e_nulo_nunca_zero(conn, tmp_path):
    def esvaziar(texto):
        linhas = texto.splitlines(keepends=True)
        campos = linhas[1].split(";")
        campos[13] = ""
        return linhas[0] + ";".join(campos) + "".join(linhas[2:])

    copia = _copia(
        ITR, tmp_path / "itr.zip", {"itr_cia_aberta_DRE_con_2020.csv": esvaziar}
    )
    _carregar(conn, copia, "ITR")
    assert _contar(conn, "demonstracoes", "valor IS NULL") == 1
    assert _contar(conn, "demonstracoes", "valor = 0") == _contar_zeros_da_origem()


def _contar_zeros_da_origem():
    nomes = [n for n in zipfile.ZipFile(ITR).namelist() if "_con_" in n or "_ind_" in n]
    return sum(
        1 for n in nomes if "parecer" not in n for r in _csv(ITR, n)
        if r.get("VL_CONTA") not in (None, "") and float(r["VL_CONTA"]) == 0
    )  # fmt: skip


@pytest.mark.parametrize(
    ("coluna", "valor", "motivo"),
    [
        (8, "ANTERIOR", "ordem do exercício desconhecida"),
        (7, "MILHAO", "escala desconhecida"),
        (2, "2a", "versão ilegível"),
        (13, "abc", "VL_CONTA não numérico"),
        (13, "inf", "VL_CONTA não finito"),
        (11, "", "CD_CONTA vazio"),
    ],
)
def test_linha_ilegivel_e_recusada_com_o_motivo_e_o_resto_entra(
    conn, tmp_path, coluna, valor, motivo
):
    def estragar(texto):
        linhas = texto.splitlines(keepends=True)
        campos = linhas[1].split(";")
        campos[coluna] = valor
        return linhas[0] + ";".join(campos) + "".join(linhas[2:])

    copia = _copia(
        ITR, tmp_path / "itr.zip", {"itr_cia_aberta_DRE_con_2020.csv": estragar}
    )
    resumo = _carregar(conn, copia, "ITR")
    assert resumo.total_recusadas == 1
    assert resumo.recusadas[0]["arquivo"] == "itr_cia_aberta_DRE_con_2020.csv"
    assert resumo.recusadas[0]["linha"] == 2
    assert resumo.recusadas[0]["motivo"].startswith(motivo)
    assert (
        _contar(conn, "demonstracoes", "demonstracao = 'DRE_con'")
        == len(_csv(ITR, "itr_cia_aberta_DRE_con_2020.csv")) - 1
    )


def test_linha_com_colunas_a_mais_ou_a_menos_e_recusada(conn, tmp_path):
    def estragar(texto):
        linhas = texto.splitlines(keepends=True)
        return (
            linhas[0]
            + linhas[1].rstrip("\r\n")
            + ";extra\n"
            + linhas[2].split(";", 3)[0]
            + "\n"
            + "".join(linhas[3:])
        )

    copia = _copia(
        FII, tmp_path / "fii.zip", {"inf_mensal_fii_complemento_2023.csv": estragar}
    )
    resumo = _carregar(conn, copia, "FII_INFORME")
    assert resumo.total_recusadas == 2
    assert {r["linha"] for r in resumo.recusadas} == {2, 3}
    assert _contar(conn, "fii_informe_linhas", "parte = 'complemento'") == 10


def test_documento_do_conteudo_sem_entrega_no_indice_e_registrado(conn, tmp_path):
    def sem_q3(texto):
        return "".join(
            l for l in texto.splitlines(keepends=True) if ";2020-09-30;" not in l
        )

    copia = _copia(ITR, tmp_path / "itr.zip", {"itr_cia_aberta_2020.csv": sem_q3})
    resumo = _carregar(conn, copia, "ITR")
    assert resumo.sem_entrega == [[CIA, "2020-09-30"]]


def test_falha_no_meio_nao_deixa_linha_parcial(conn, monkeypatch):
    original = carga_cvm._carregar_indice

    def falhar(*args, **kwargs):
        raise OSError("disco")

    monkeypatch.setattr(carga_cvm, "_carregar_indice", falhar)
    with pytest.raises(OSError):
        _carregar(conn, ITR, "ITR")
    monkeypatch.setattr(carga_cvm, "_carregar_indice", original)
    for tabela in ("entregas", "demonstracoes", "composicao_capital", "cargas_arquivo"):
        assert _contar(conn, tabela) == 0
    assert _carregar(conn, ITR, "ITR").inseridas["entregas"] == 4


@pytest.mark.parametrize(
    ("arquivo", "tipo"),
    [(DFP, "ITR"), (ITR, "FCA"), (FCA, "FII_INFORME"), (FII, "DFP")],
)
def test_zip_de_outro_tipo_e_recusado_sem_gravar(conn, arquivo, tipo):
    with pytest.raises(carga_cvm.ArquivoInvalido):
        _carregar(conn, arquivo, tipo)
    assert _contar(conn, "cargas_arquivo") == 0
    assert _contar(conn, "demonstracoes") == 0


def test_migracao_005_aplicada_sobre_o_banco_da_004_sem_perda(tmp_path):
    import shutil

    ate_004, ate_005 = tmp_path / "ate_004", tmp_path / "ate_005"
    ate_004.mkdir()
    ate_005.mkdir()
    for _, arquivo in migracoes.listar():
        if arquivo.name < "005":
            shutil.copy(arquivo, ate_004 / arquivo.name)
        if arquivo.name < "006":
            shutil.copy(arquivo, ate_005 / arquivo.name)
    banco = tmp_path / "banco.db"
    with closing(sqlite3.connect(banco)) as c:
        assert migracoes.aplicar(c, ate_004) == [1, 2, 3, 4]
        _carregar_sem_registro(c)
        antes = {
            t: c.execute(f'SELECT * FROM "{t}"').fetchall()
            for t in ("entregas", "demonstracoes", "carteira_real")
        }
    with closing(sqlite3.connect(banco)) as c:
        assert migracoes.aplicar(c, ate_005) == [5]
        assert {t: c.execute(f'SELECT * FROM "{t}"').fetchall() for t in antes} == antes


def _carregar_sem_registro(c):
    c.execute("INSERT INTO carteira_real VALUES ('TST3', 10, 9.5, '2026-01-02')")
    c.execute(
        "INSERT INTO entregas (cnpj, documento, dt_refer, versao, dt_receb, valores_na_fonte, fonte, "
        "coleta, hash_sha256) VALUES (?, 'ITR', '2020-03-31', 2, '2020-05-21', 1, 'f', 'c', 'h')",
        (CIA,),
    )
    c.commit()


@pytest.mark.parametrize(
    "tabela", ["cargas_arquivo", "fca_entregas", "fca_linhas", "fii_informe_linhas"]
)
def test_tabelas_da_005_sao_so_de_insercao(conn, tabela):
    _carregar(conn, FCA, "FCA")
    _carregar(conn, FII, "FII_INFORME")
    antes = conn.execute(f"SELECT * FROM {tabela}").fetchall()
    assert antes
    for sql in (f"UPDATE {tabela} SET fonte = 'x'", f"DELETE FROM {tabela}"):
        with pytest.raises(sqlite3.IntegrityError, match=f"{tabela} é só de inserção"):
            conn.execute(sql)
    colunas = [c[1] for c in conn.execute(f"PRAGMA table_info({tabela})")]
    with pytest.raises(sqlite3.IntegrityError, match=f"{tabela} é só de inserção"):
        conn.execute(
            f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})",
            antes[0],
        )
    assert conn.execute(f"SELECT * FROM {tabela}").fetchall() == antes


# --- Campos obrigatórios, recusas e resumo -------------------------------------------------


def _esvaziar(membro, coluna, valor="", linha=1):
    """Troca o valor de `coluna` (pelo cabeçalho) na `linha`-ésima linha de dados do membro."""

    def alterar(texto):
        linhas = texto.splitlines(keepends=True)
        indice = linhas[0].rstrip("\r\n").split(";").index(coluna)
        campos = linhas[linha].split(";")
        campos[indice] = valor
        linhas[linha] = ";".join(campos)
        return "".join(linhas)

    return {membro: alterar}


_INDICE_ITR = "itr_cia_aberta_2020.csv"
_COMPOSICAO_ITR = "itr_cia_aberta_composicao_capital_2020.csv"
_DRE_ITR = "itr_cia_aberta_DRE_con_2020.csv"


@pytest.mark.parametrize(
    ("arquivo", "tipo", "membro", "coluna", "valor", "motivo", "tabela"),
    [
        (ITR, "ITR", _DRE_ITR, "CNPJ_CIA", "", "CNPJ_CIA vazio", "demonstracoes"),
        (ITR, "ITR", _DRE_ITR, "DT_REFER", "", "DT_REFER vazio", "demonstracoes"),
        (ITR, "ITR", _DRE_ITR, "ORDEM_EXERC", "", "ORDEM_EXERC vazio", "demonstracoes"),
        (ITR, "ITR", _DRE_ITR, "ESCALA_MOEDA", "", "ESCALA_MOEDA vazio", "demonstracoes"),
        (ITR, "ITR", _DRE_ITR, "DT_FIM_EXERC", "", "DT_FIM_EXERC vazio", "demonstracoes"),
        (ITR, "ITR", _DRE_ITR, "VERSAO", "", "VERSAO vazio", "demonstracoes"),
        (ITR, "ITR", _COMPOSICAO_ITR, "CNPJ_CIA", "", "CNPJ_CIA vazio", "composicao_capital"),
        (ITR, "ITR", _COMPOSICAO_ITR, "DT_REFER", "", "DT_REFER vazio", "composicao_capital"),
        (ITR, "ITR", _COMPOSICAO_ITR, "VERSAO", "x", "versão ilegível: 'x'", "composicao_capital"),
        (
            ITR, "ITR", _COMPOSICAO_ITR, "QT_ACAO_ORDIN_CAP_INTEGR", "mil",
            "QT_ACAO_ORDIN_CAP_INTEGR não numérico: 'mil'", "composicao_capital",
        ),
        (ITR, "ITR", _INDICE_ITR, "CNPJ_CIA", "", "CNPJ_CIA vazio", "entregas"),
        (ITR, "ITR", _INDICE_ITR, "DT_REFER", "", "DT_REFER vazio", "entregas"),
        (ITR, "ITR", _INDICE_ITR, "DT_RECEB", "", "DT_RECEB vazio", "entregas"),
        (ITR, "ITR", _INDICE_ITR, "VERSAO", "2.0", "versão ilegível: '2.0'", "entregas"),
        (FCA, "FCA", "fca_cia_aberta_endereco_2015.csv", "CNPJ_Companhia", "", "CNPJ_Companhia vazio", "fca_linhas"),
        (FCA, "FCA", "fca_cia_aberta_endereco_2015.csv", "Data_Referencia", "", "Data_Referencia vazio", "fca_linhas"),
        (FCA, "FCA", "fca_cia_aberta_endereco_2015.csv", "Versao", "", "Versao vazio", "fca_linhas"),
        (FCA, "FCA", "fca_cia_aberta_2015.csv", "DT_RECEB", "", "DT_RECEB vazio", "fca_entregas"),
        (FII, "FII_INFORME", "inf_mensal_fii_geral_2023.csv", "CNPJ_Fundo_Classe", "", "CNPJ_Fundo_Classe vazio", "fii_informe_linhas"),
        (FII, "FII_INFORME", "inf_mensal_fii_geral_2023.csv", "Data_Referencia", "", "Data_Referencia vazio", "fii_informe_linhas"),
    ],
)  # fmt: skip
def test_campo_obrigatorio_ilegivel_recusa_so_a_linha(
    conn, tmp_path, arquivo, tipo, membro, coluna, valor, motivo, tabela
):
    referencia = sqlite3.connect(":memory:")
    migracoes.aplicar(referencia)
    _carregar(referencia, arquivo, tipo)
    completo = _contar(referencia, tabela)
    referencia.close()
    resumo = _carregar(
        conn,
        _copia(arquivo, tmp_path / "x.zip", _esvaziar(membro, coluna, valor)),
        tipo,
    )
    assert resumo.total_recusadas == 1
    assert resumo.recusadas == [{"arquivo": membro, "linha": 2, "motivo": motivo}]
    assert _contar(conn, tabela) == completo - 1
    gravado = json.loads(
        conn.execute("SELECT resumo_json FROM cargas_arquivo").fetchone()[0]
    )
    assert gravado["recusadas"] == resumo.recusadas
    assert gravado["total_recusadas"] == 1


def test_indice_sem_conteudo_do_documento_marca_zero(conn, tmp_path):
    def sem_q3(texto):
        return "".join(
            l for l in texto.splitlines(keepends=True) if ";2020-09-30;" not in l
        )

    alterar = {n: sem_q3 for n in zipfile.ZipFile(ITR).namelist() if n != _INDICE_ITR}
    _carregar(conn, _copia(ITR, tmp_path / "itr.zip", alterar), "ITR")
    assert conn.execute(
        "SELECT valores_na_fonte FROM entregas WHERE dt_refer = '2020-09-30'"
    ).fetchone() == (0,)


def test_campos_descritivos_gravados_como_na_fonte(conn):
    _carregar(conn, ITR, "ITR")
    indice = next(r for r in _csv(ITR, _INDICE_ITR) if r["VERSAO"] == "2")
    assert conn.execute(
        "SELECT cd_cvm, denominacao, categoria, id_documento FROM entregas WHERE versao = 2"
    ).fetchone() == (
        indice["CD_CVM"],
        indice["DENOM_CIA"],
        indice["CATEG_DOC"],
        indice["ID_DOC"],
    )
    origem = _csv(ITR, _DRE_ITR)[0]
    assert conn.execute(
        "SELECT descricao, conta_fixa FROM demonstracoes WHERE demonstracao = 'DRE_con' AND dt_refer = ? "
        "AND versao = ? AND ordem_exerc = ? AND dt_ini_exerc = ? AND conta = ?",
        (
            origem["DT_REFER"],
            int(origem["VERSAO"]),
            origem["ORDEM_EXERC"],
            origem["DT_INI_EXERC"],
            origem["CD_CONTA"],
        ),
    ).fetchone() == (origem["DS_CONTA"], origem["ST_CONTA_FIXA"])


def test_descricao_vazia_vira_nula(conn, tmp_path):
    _carregar(
        conn, _copia(ITR, tmp_path / "itr.zip", _esvaziar(_DRE_ITR, "DS_CONTA")), "ITR"
    )
    assert _contar(conn, "demonstracoes", "descricao IS NULL") == 1


def test_listas_do_resumo_limitadas_e_totais_completos(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(carga_cvm, "LIMITE_REGISTROS", 2)
    _carregar(conn, ITR, "ITR")

    def tres(coluna, valor):
        def alterar(texto):
            linhas = texto.splitlines(keepends=True)
            indice = linhas[0].split(";").index(coluna)
            for i in (1, 2, 3):
                campos = linhas[i].split(";")
                campos[indice] = valor
                linhas[i] = ";".join(campos)
            return "".join(linhas)

        return alterar

    def sem_indice(texto):
        return texto.splitlines(keepends=True)[0]

    alterar = {
        "itr_cia_aberta_BPA_con_2020.csv": tres("VL_CONTA", "-1.0"),
        _DRE_ITR: tres("ORDEM_EXERC", "X"),
        _INDICE_ITR: sem_indice,
    }
    resumo = _carregar(conn, _copia(ITR, tmp_path / "itr.zip", alterar), "ITR")
    assert resumo.total_conflitos == 3 and len(resumo.conflitos) == 2
    assert resumo.total_recusadas == 3 and len(resumo.recusadas) == 2
    assert len(resumo.sem_entrega) == 2  # três documentos sem entrega, lista limitada


def test_resumo_gravado_com_todos_os_campos(conn, tmp_path):
    alterar = _esvaziar(_DRE_ITR, "VERSAO", "v")
    resumo = _carregar(conn, _copia(ITR, tmp_path / "itr.zip", alterar), "ITR")
    texto = conn.execute("SELECT resumo_json FROM cargas_arquivo").fetchone()[0]
    assert "versão ilegível" in texto  # legível, sem escape
    gravado = json.loads(texto)
    assert set(gravado) == {
        "inseridas", "repetidas", "total_conflitos", "conflitos", "total_recusadas",
        "recusadas", "sem_entrega", "ignorados",
    }  # fmt: skip
    assert (
        gravado["inseridas"] == dict(resumo.inseridas)
        and gravado["inseridas"]["entregas"] == 4
    )
    assert gravado["repetidas"] == {}
    assert gravado["ignorados"] == ["itr_cia_aberta_parecer_2020.csv"]
    assert (
        gravado["sem_entrega"] == []
        and gravado["conflitos"] == []
        and gravado["total_conflitos"] == 0
    )
    assert resumo.tipo == "ITR"


def test_fca_com_versao_menor_que_a_do_indice_tira_a_marca(conn, tmp_path):
    versao = _csv(FCA, "fca_cia_aberta_geral_2015.csv")[0]["Versao"]
    assert versao == "2"

    def v1(texto):
        return texto.replace(";2015-01-01;2;", ";2015-01-01;1;")

    alterar = {
        n: v1 for n in zipfile.ZipFile(FCA).namelist() if n != "fca_cia_aberta_2015.csv"
    }
    resumo = _carregar(conn, _copia(FCA, tmp_path / "fca.zip", alterar), "FCA")
    assert resumo.so_ultima_versao is False
    assert conn.execute(
        "SELECT versao, valores_na_fonte FROM fca_entregas ORDER BY versao"
    ).fetchall() == [(1, 1), (2, 0)]


def test_fca_e_fii_ignoram_membros_fora_do_leiaute_e_seguem(conn, tmp_path):
    def com_extra(origem, destino):
        with zipfile.ZipFile(origem) as zi, zipfile.ZipFile(destino, "w") as zo:
            zo.writestr("aaa_leiame.txt", "x")
            for nome in zi.namelist():
                zo.writestr(nome, zi.read(nome))
        return destino

    fca = _carregar(conn, com_extra(FCA, tmp_path / "fca.zip"), "FCA")
    fii = _carregar(conn, com_extra(FII, tmp_path / "fii.zip"), "FII_INFORME")
    assert fca.ignorados == ["aaa_leiame.txt"]
    assert fii.ignorados == ["aaa_leiame.txt"]
    assert fca.inseridas["fca_entregas"] == 2 and fca.inseridas["fca_linhas"] > 10
    assert fii.inseridas["fii_informe_linhas"] == 36


def test_informe_com_duas_versoes_no_geral_tira_a_marca(conn, tmp_path):
    def v2(texto):
        linhas = texto.splitlines(keepends=True)
        campos = linhas[1].split(";")
        campos[3] = "2"
        return texto + ";".join(campos)

    resumo = _carregar(
        conn,
        _copia(FII, tmp_path / "fii.zip", {"inf_mensal_fii_geral_2023.csv": v2}),
        "FII_INFORME",
    )
    assert resumo.so_ultima_versao is False


def test_linha_fca_identificada_pelo_conteudo_mesmo_com_colunas_reordenadas(
    conn, tmp_path
):
    _carregar(conn, FCA, "FCA")

    def inverter(texto):
        return "".join(
            ";".join(reversed(l.rstrip("\r\n").split(";"))) + "\n"
            for l in texto.splitlines()
        )

    alterar = {
        n: inverter
        for n in zipfile.ZipFile(FCA).namelist()
        if n != "fca_cia_aberta_2015.csv"
    }
    resumo = _carregar(conn, _copia(FCA, tmp_path / "fca.zip", alterar), "FCA")
    assert not resumo.inseridas
    assert resumo.repetidas["fca_linhas"] == _contar(conn, "fca_linhas")
    texto, hash_linha = conn.execute(
        "SELECT linha_json, linha_sha256 FROM fca_linhas WHERE parte = 'geral'"
    ).fetchone()
    assert "Comércio" in texto  # legível, sem escape
    assert hash_linha == __import__("hashlib").sha256(texto.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    ("tipo", "fonte", "coleta", "mensagem"),
    [
        ("CAD", "f", "c", "tipo desconhecido: 'CAD'"),
        ("ITR", "", "c", "fonte e coleta são obrigatórias"),
        ("ITR", "f", "", "fonte e coleta são obrigatórias"),
    ],
)
def test_mensagens_dos_parametros(conn, tipo, fonte, coleta, mensagem):
    with pytest.raises(ValueError, match=f"^{mensagem}$"):
        carga_cvm.carregar(conn, ITR, tipo=tipo, fonte=fonte, coleta=coleta)


def test_zip_sem_indice_explica_o_que_falta(conn):
    with pytest.raises(
        carga_cvm.ArquivoInvalido,
        match=r"esperado um arquivo .*itr_cia_aberta.*, encontrados 0",
    ):
        _carregar(conn, DFP, "ITR")


def test_colunas_a_mais_tem_motivo_proprio(conn, tmp_path):
    def extra(texto):
        linhas = texto.splitlines(keepends=True)
        linhas[1] = linhas[1].rstrip("\r\n") + ";a mais\n"
        return "".join(linhas)

    resumo = _carregar(
        conn, _copia(ITR, tmp_path / "itr.zip", {_DRE_ITR: extra}), "ITR"
    )
    assert (
        resumo.recusadas[0]["motivo"]
        == "linha com número de colunas diferente do cabeçalho"
    )


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO cargas_arquivo VALUES ('h', 'CAD', 'a', 'f', 'c', 1, '{}')",
        "INSERT INTO cargas_arquivo VALUES ('h', 'ITR', 'a', 'f', 'c', 2, '{}')",
        (
            "INSERT INTO fca_entregas (cnpj, dt_refer, versao, dt_receb, valores_na_fonte, fonte, "
            "coleta, hash_sha256) VALUES ('c', 'd', 1, 'r', 2, 'f', 'c', 'h')"
        ),
        (
            "INSERT INTO fii_informe_linhas (cnpj, dt_refer, versao, parte, linha_sha256, linha_json, "
            "fonte, coleta, hash_sha256) VALUES ('c', 'd', '1', 'cotistas', 'l', '{}', 'f', 'c', 'h')"
        ),
    ],
)
def test_dominios_da_005(conn, sql):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(sql)


@pytest.mark.parametrize("tabela", ["fca_linhas", "fii_informe_linhas"])
def test_mesma_linha_em_outra_parte_e_outra_linha(conn, tabela):
    sql = (
        f"INSERT INTO {tabela} (cnpj, dt_refer, versao, parte, linha_sha256, linha_json, fonte, coleta, "
        "hash_sha256) VALUES ('c', 'd', '1', ?, 'l', '{}', 'f', 'c', 'h')"
    )
    conn.execute(sql, ("geral",))
    conn.execute(sql, ("complemento",))
    assert _contar(conn, tabela) == 2


def test_indice_so_e_depois_o_conteudo_sem_conflito(conn, tmp_path):
    """Entrega registrada sem números (marca 0) e depois um arquivo com eles: entram as contas."""

    def sem_q3(texto):
        return "".join(
            l for l in texto.splitlines(keepends=True) if ";2020-09-30;" not in l
        )

    alterar = {n: sem_q3 for n in zipfile.ZipFile(ITR).namelist() if n != _INDICE_ITR}
    _carregar(conn, _copia(ITR, tmp_path / "itr.zip", alterar), "ITR")
    assert _contar(conn, "demonstracoes", "dt_refer = '2020-09-30'") == 0
    resumo = _carregar(conn, ITR, "ITR", coleta="2026-11-12T12:00:00+00:00")
    assert resumo.total_conflitos == 0
    assert (
        resumo.inseridas["demonstracoes"]
        == _contar(conn, "demonstracoes", "dt_refer = '2020-09-30'")
        > 0
    )
    # a marca é a da primeira observação; as contas da versão estão em `demonstracoes`
    assert conn.execute(
        "SELECT valores_na_fonte FROM entregas WHERE dt_refer = '2020-09-30'"
    ).fetchone() == (0,)


def test_entrega_com_data_diferente_e_conflito(conn, tmp_path):
    _carregar(conn, ITR, "ITR")
    copia = _copia(
        ITR,
        tmp_path / "itr.zip",
        {_INDICE_ITR: lambda t: t.replace(";2020-08-13;", ";2020-08-14;")},
    )
    resumo = _carregar(conn, copia, "ITR", coleta="2026-11-12T12:00:00+00:00")
    assert resumo.total_conflitos == 1
    conflito = resumo.conflitos[0]
    assert conflito["tabela"] == "entregas"
    assert (
        conflito["gravado"][4] == "2020-08-13"
        and conflito["arquivo"][4] == "2020-08-14"
    )
    assert len(conflito["gravado"]) == 5  # a marca fica fora da conferência


def _falhar_no_indice(monkeypatch):
    def falhar(*args, **kwargs):
        raise OSError("disco")

    monkeypatch.setattr(carga_cvm, "_carregar_indice", falhar)


def test_falha_desfaz_tambem_com_autocommit(tmp_path, monkeypatch):
    with closing(sqlite3.connect(tmp_path / "b.db", autocommit=True)) as c:
        migracoes.aplicar(c)
        _falhar_no_indice(monkeypatch)
        with pytest.raises(OSError):
            _carregar(c, ITR, "ITR")
        assert c.in_transaction is False
        for tabela in (
            "entregas",
            "demonstracoes",
            "composicao_capital",
            "cargas_arquivo",
        ):
            assert _contar(c, tabela) == 0
        monkeypatch.undo()
        assert _carregar(c, ITR, "ITR").inseridas["entregas"] == 4
    with closing(sqlite3.connect(tmp_path / "b.db")) as c:
        assert (
            _contar(c, "entregas") == 4
        )  # gravado sem transação aberta por quem chama


def test_dentro_da_transacao_de_quem_chama_a_gravacao_fica_com_ela(conn):
    conn.execute("BEGIN")
    _carregar(conn, FCA, "FCA")
    assert conn.in_transaction
    conn.rollback()
    assert _contar(conn, "fca_entregas") == 0
    assert _contar(conn, "cargas_arquivo") == 0


def test_carga_sem_transacao_aberta_termina_gravada(tmp_path):
    with closing(sqlite3.connect(tmp_path / "b.db")) as c:
        migracoes.aplicar(c)
        _carregar(c, FII, "FII_INFORME")
        assert c.in_transaction is False
    with closing(sqlite3.connect(tmp_path / "b.db")) as c:
        assert _contar(c, "fii_informe_linhas") == 36


@pytest.mark.parametrize("versao", ["²", "1²"])
def test_versao_com_digito_nao_ascii_e_recusada_sem_derrubar(conn, tmp_path, versao):
    alterar = _esvaziar(_DRE_ITR, "VERSAO", versao)
    resumo = _carregar(conn, _copia(ITR, tmp_path / "itr.zip", alterar), "ITR")
    assert resumo.recusadas == [
        {"arquivo": _DRE_ITR, "linha": 2, "motivo": f"versão ilegível: {versao!r}"}
    ]


def test_versao_nao_ascii_no_fca_fica_como_texto_e_fora_da_marca(conn, tmp_path):
    copia = _copia(
        FCA,
        tmp_path / "fca.zip",
        _esvaziar("fca_cia_aberta_endereco_2015.csv", "Versao", "²"),
    )
    resumo = _carregar(conn, copia, "FCA")
    assert resumo.total_recusadas == 0
    assert _contar(conn, "fca_linhas", "versao = '²'") == 1


def test_falha_depois_de_o_sqlite_desfazer_tudo_preserva_o_erro_original(
    conn, monkeypatch
):
    def desfazer_e_falhar(conn_, *args, **kwargs):
        conn_.execute("ROLLBACK")  # como o SQLite faz sozinho em disco cheio
        raise OSError("disco cheio")

    monkeypatch.setattr(carga_cvm, "_carregar_arquivo", desfazer_e_falhar)
    with pytest.raises(OSError, match="disco cheio"):
        _carregar(conn, ITR, "ITR")
    assert conn.in_transaction is False
