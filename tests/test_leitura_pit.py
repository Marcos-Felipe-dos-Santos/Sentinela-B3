"""F3-3c: leitura ponto-no-tempo das demonstrações e do Informe (`sentinela.data.pit.leitura`).

Ponta a ponta: ZIP oficial (fixtures do F3-3b) → `carga_cvm.carregar` → leitor por data →
consumidores da cascata (`cvm_provider`, `rendimento_fii`), chamando o leitor diretamente.
Com D = hoje, os insumos são os mesmos da cascata atual (equivalência).
"""

import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from test_carga_cvm import CIA, FII, FUNDO, ITR, _copia

import cvm_fii_provider
import cvm_provider
from sentinela.data import rendimento_fii
from sentinela.data.pit import carga_cvm, leitura
from sentinela.data.store import migracoes

HOJE = datetime(2026, 11, 11, 15, tzinfo=UTC)
ITR_CON = [
    "BPA_con",
    "BPP_con",
    "DRE_con",
    "DRA_con",
    "DMPL_con",
    "DFC_MI_con",
    "DVA_con",
]


def _sp(ano, mes, dia, hora=12):
    return datetime(ano, mes, dia, hora, tzinfo=ZoneInfo("America/Sao_Paulo"))


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _carregar(conn, arquivo, tipo, coleta="2026-11-11T12:00:00+00:00"):
    return carga_cvm.carregar(
        conn, arquivo, tipo=tipo, fonte=f"cvm:{Path(arquivo).name}", coleta=coleta
    )


# --- Equivalência com a cascata (D = hoje) ---------------------------------------------------


def _normalizar(frame):
    frame = frame.copy()
    frame["VERSAO"] = frame["VERSAO"].astype(int)
    frame["CD_CVM"] = frame["CD_CVM"].astype("Int64")
    for coluna in frame.columns:
        if coluna not in ("VL_CONTA", "VERSAO", "CD_CVM"):
            frame[coluna] = frame[coluna].astype(str)
    return frame.sort_values(list(frame.columns)).reset_index(drop=True)


@pytest.mark.parametrize("demonstracao", ITR_CON)
def test_demonstrativo_de_hoje_igual_ao_da_cascata(conn, tmp_path, demonstracao):
    _carregar(conn, ITR, "ITR")
    cascata = cvm_provider.CVMProvider(cache_dir=str(tmp_path)).parsear_demonstrativo(
        ITR,
        demonstracao,
        include_cd_cvm=True,
        include_versao=True,
        include_periodo=True,
    )
    lido = leitura.demonstrativo(conn, "ITR", demonstracao, HOJE)
    assert lido.modo == leitura.ESTRITO and lido.motivos == {} and lido.avisos == ()
    assert len(cascata) > 0
    pd.testing.assert_frame_equal(
        _normalizar(lido.dados), _normalizar(cascata[lido.dados.columns])
    )
    assert set(cascata.columns) == set(lido.dados.columns)


def test_composicao_e_entregas_de_hoje_iguais_as_da_cascata(conn, tmp_path):
    _carregar(conn, ITR, "ITR")
    provedor = cvm_provider.CVMProvider(cache_dir=str(tmp_path))
    bruto = provedor._read_raw(ITR, "composicao_capital")
    lido = leitura.composicao(conn, "ITR", HOJE).dados
    colunas = list(lido.columns)
    esperado = bruto[colunas].astype(str).sort_values(colunas).reset_index(drop=True)
    obtido = lido.assign(**{c: lido[c].map(lambda x: str(int(x))) for c in colunas[4:]})
    pd.testing.assert_frame_equal(
        obtido.astype(str).sort_values(colunas).reset_index(drop=True), esperado
    )
    indice = provedor._entregas(ITR)
    chaves = [
        "CNPJ_CIA",
        "DT_REFER",
        "VERSAO",
        "DENOM_CIA",
        "CD_CVM",
        "CATEG_DOC",
        "ID_DOC",
        "DT_RECEB",
    ]
    assert leitura.entregas(conn, "ITR", HOJE).dados == [
        {k: linha[k] for k in chaves} for linha in indice
    ]


def test_informe_de_hoje_igual_ao_da_cascata(conn, tmp_path, monkeypatch):
    _carregar(conn, FII, "FII_INFORME")
    provedor = cvm_fii_provider.CVMFIIProvider(cache_dir=str(tmp_path))
    monkeypatch.setattr(provedor, "baixar_informe", lambda ano: FII)
    _, registros, composicoes = provedor._linhas_do_fundo(FUNDO, 2023)
    lido = leitura.informe_fii(conn, FUNDO, HOJE)
    ordem = lambda linhas: sorted(
        linhas, key=lambda l: (l["Data_Referencia"], l["Versao"])
    )
    assert ordem(lido.dados["registros"]) == ordem(registros)
    assert ordem(lido.dados["composicoes"]) == ordem(composicoes)
    assert lido.motivos == {}


# --- Integração: ZIP → carga → leitor → consumidores da cascata ----------------------------


def _lpa_do_documento(frame, dt_refer):
    """Como a cascata (`_por_acao_cvm`): o documento, o período mais longo e as contas 3.99."""
    frame = frame[frame["DT_REFER"] == dt_refer]
    frame = frame[frame["DT_INI_EXERC"] == frame["DT_INI_EXERC"].min()]
    return frame[frame["CD_CONTA"].astype(str).str.startswith("3.99")]


def test_lpa_e_composicao_do_documento_pelo_leitor(conn, tmp_path):
    """O LPA divulgado e a composição de cada documento, pelo leitor e pela leitura da cascata."""
    _carregar(conn, ITR, "ITR")
    dre = leitura.demonstrativo(
        conn, "ITR", "DRE_con", HOJE, aplicar_escala=False
    ).dados
    cc = leitura.composicao(conn, "ITR", HOJE).dados
    provedor = cvm_provider.CVMProvider(cache_dir=str(tmp_path))
    bruto_dre = provedor._read_raw(ITR, "DRE_con")
    bruto_dre = bruto_dre[bruto_dre["ORDEM_EXERC"] == "ÚLTIMO"]
    bruto_cc = provedor._read_raw(ITR, "composicao_capital")
    for dt_refer, versao in [
        ("2020-03-31", "2"),
        ("2020-06-30", "1"),
        ("2020-09-30", "1"),
    ]:
        do_leitor, do_zip = (
            _lpa_do_documento(dre, dt_refer),
            _lpa_do_documento(bruto_dre, dt_refer),
        )
        assert len(do_leitor) == len(do_zip) > 0
        assert cvm_provider.lpa_divulgado(do_leitor) == cvm_provider.lpa_divulgado(
            do_zip
        )
        assert cvm_provider.lpa_divulgado(do_leitor) is not None
        assert cvm_provider.composicao_do_documento(cc, CIA, dt_refer, versao) == (
            cvm_provider.composicao_do_documento(bruto_cc, CIA, dt_refer, versao)
        )


@pytest.mark.parametrize("demonstracao", [d for d in ITR_CON if d != "DMPL_con"])
def test_ordem_das_linhas_igual_a_do_arquivo(conn, tmp_path, demonstracao):
    _carregar(conn, ITR, "ITR")
    cascata = cvm_provider.CVMProvider(cache_dir=str(tmp_path)).parsear_demonstrativo(
        ITR, demonstracao, include_periodo=True
    )
    lido = leitura.demonstrativo(conn, "ITR", demonstracao, HOJE).dados
    assert lido["CD_CONTA"].tolist() == cascata["CD_CONTA"].tolist()
    assert lido["DT_REFER"].tolist() == cascata["DT_REFER"].tolist()
    if "DT_INI_EXERC" in cascata.columns:
        assert lido["DT_INI_EXERC"].tolist() == cascata["DT_INI_EXERC"].tolist()


def test_valor_declarado_sem_a_escala(conn):
    _carregar(conn, ITR, "ITR")
    com = leitura.demonstrativo(conn, "ITR", "BPA_con", HOJE).dados["VL_CONTA"]
    sem = leitura.demonstrativo(
        conn, "ITR", "BPA_con", HOJE, aplicar_escala=False
    ).dados["VL_CONTA"]
    assert (com == sem * 1000).all() and (sem != 0).any()


def test_rendimento_do_fii_pelo_leitor_igual_ao_da_cascata(conn, tmp_path, monkeypatch):
    _carregar(conn, FII, "FII_INFORME")
    provedor = cvm_fii_provider.CVMFIIProvider(cache_dir=str(tmp_path))
    monkeypatch.setattr(provedor, "baixar_informe", lambda ano: FII)
    _, registros, _ = provedor._linhas_do_fundo(FUNDO, 2023)
    lido = leitura.informe_fii(conn, FUNDO, HOJE).dados["registros"]
    assert rendimento_fii._por_mes(lido) == rendimento_fii._por_mes(registros)
    assert len(rendimento_fii._por_mes(lido)[0]) == 12
    resultado = rendimento_fii.rendimento_12_meses(lido, 90.0)
    assert resultado == rendimento_fii.rendimento_12_meses(registros, 90.0)


# --- Modo estrito ------------------------------------------------------------------------------


def _versoes(lido):
    return sorted(
        {
            (d, v)
            for d, v in zip(lido.dados["DT_REFER"], lido.dados["VERSAO"], strict=True)
        }
    )


def test_estrito_antes_da_reapresentacao_abstem_com_o_motivo(conn):
    _carregar(conn, ITR, "ITR")
    lido = leitura.demonstrativo(conn, "ITR", "DRE_con", _sp(2020, 5, 15))
    assert _versoes(lido) == []
    assert lido.motivos == {(CIA, "2020-03-31"): leitura.MOTIVO_ENTREGA_POSTERIOR}


def test_entrega_no_proprio_dia_ainda_nao_vale(conn):
    _carregar(conn, ITR, "ITR")
    assert (
        _versoes(leitura.demonstrativo(conn, "ITR", "DRE_con", _sp(2020, 5, 21, 23)))
        == []
    )
    assert _versoes(
        leitura.demonstrativo(conn, "ITR", "DRE_con", _sp(2020, 5, 22, 0))
    ) == [("2020-03-31", "2")]


def test_documento_ainda_nao_entregue_fica_fora_sem_motivo(conn):
    _carregar(conn, ITR, "ITR")
    lido = leitura.demonstrativo(conn, "ITR", "DRE_con", _sp(2020, 5, 7))
    assert _versoes(lido) == [] and lido.motivos == {}
    lido = leitura.demonstrativo(conn, "ITR", "DRE_con", _sp(2020, 9, 1))
    assert _versoes(lido) == [("2020-03-31", "2"), ("2020-06-30", "1")]


def test_estrito_usa_a_versao_antiga_guardada_por_carga_anterior(conn, tmp_path):
    """A v2 carregada antes da reapresentação (v3) continua valendo nas datas entre as duas."""
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
    _carregar(
        conn,
        _copia(ITR, tmp_path / "v3.zip", alterar),
        "ITR",
        coleta="2026-11-12T12:00:00+00:00",
    )
    entre = _sp(2020, 12, 1)
    assert ("2020-03-31", "2") in _versoes(
        leitura.demonstrativo(conn, "ITR", "DRE_con", entre)
    )
    assert ("2020-03-31", "3") in _versoes(
        leitura.demonstrativo(conn, "ITR", "DRE_con", _sp(2021, 2, 1))
    )
    explorado = leitura.demonstrativo(
        conn, "ITR", "DRE_con", entre, modo=leitura.EXPLORATORIO
    )
    assert ("2020-03-31", "3") in _versoes(explorado)
    assert explorado.avisos == (leitura.AVISO_EXPLORATORIO,)


def test_versao_so_no_indice_sem_numeros_tem_motivo_proprio(conn, tmp_path):
    def sem_q3(texto):
        return "".join(
            l for l in texto.splitlines(keepends=True) if ";2020-09-30;" not in l
        )

    alterar = {
        n: sem_q3
        for n in zipfile.ZipFile(ITR).namelist()
        if n != "itr_cia_aberta_2020.csv"
    }
    _carregar(conn, _copia(ITR, tmp_path / "x.zip", alterar), "ITR")
    for modo in leitura.MODOS:
        lido = leitura.demonstrativo(conn, "ITR", "DRE_con", HOJE, modo=modo)
        assert lido.motivos == {(CIA, "2020-09-30"): leitura.MOTIVO_SEM_NUMEROS}


def test_entregas_estritas_so_ate_d_e_exploratorias_com_a_posterior(conn):
    _carregar(conn, ITR, "ITR")
    d = _sp(2020, 5, 15)
    estrito = leitura.entregas(conn, "ITR", d).dados
    assert [(l["DT_REFER"], l["VERSAO"]) for l in estrito] == [("2020-03-31", "1")]
    explorado = leitura.entregas(conn, "ITR", d, modo=leitura.EXPLORATORIO)
    assert [(l["DT_REFER"], l["VERSAO"]) for l in explorado.dados] == [
        ("2020-03-31", "1"),
        ("2020-03-31", "2"),
    ]
    assert explorado.avisos == (leitura.AVISO_EXPLORATORIO,)


def test_composicao_estrita_e_exploratoria(conn):
    _carregar(conn, ITR, "ITR")
    d = _sp(2020, 5, 15)
    estrito = leitura.composicao(conn, "ITR", d)
    assert estrito.dados.empty and estrito.motivos == {
        (CIA, "2020-03-31"): leitura.MOTIVO_ENTREGA_POSTERIOR
    }
    explorado = leitura.composicao(conn, "ITR", d, modo=leitura.EXPLORATORIO)
    assert explorado.dados["VERSAO"].tolist() == ["2"]
    assert explorado.proveniencia == (
        (
            f"cvm:{ITR.name}",
            "2026-11-11T12:00:00+00:00",
            carga_cvm.proveniencia.hash_sha256(ITR),
        ),
    )


def test_filtro_por_cnpj(conn):
    _carregar(conn, ITR, "ITR")
    assert leitura.demonstrativo(
        conn, "ITR", "DRE_con", HOJE, cnpj="11.111.111/0001-11"
    ).dados.empty
    assert not leitura.demonstrativo(conn, "ITR", "DRE_con", HOJE, cnpj=CIA).dados.empty


# --- Informe de FII (contrato F3-P12, §2) ------------------------------------------------------


def _meses(lido):
    return sorted(
        {(r["Data_Referencia"], r["Versao"]) for r in lido.dados["registros"]}
    )


def test_informe_estrito_so_com_entrega_anterior_ao_dia(conn):
    _carregar(conn, FII, "FII_INFORME")
    lido = leitura.informe_fii(conn, FUNDO, _sp(2023, 3, 15))
    assert _meses(lido) == [
        ("2023-01-01", "1")
    ]  # fevereiro entregue em 15/03: ainda não
    assert _meses(leitura.informe_fii(conn, FUNDO, _sp(2023, 3, 16, 0))) == [
        ("2023-01-01", "1"),
        ("2023-02-01", "1"),
    ]
    assert {(c["Data_Referencia"]) for c in lido.dados["composicoes"]} == {"2023-01-01"}


def test_informe_reapresentado_depois_de_d_abstem_o_mes(conn):
    """Julho/2023 só na versão 2, entregue em 08/09: em 01/09 a vigente não está na fonte."""
    _carregar(conn, FII, "FII_INFORME")
    lido = leitura.informe_fii(conn, FUNDO, _sp(2023, 9, 1))
    assert ("2023-07-01", "2") not in _meses(lido)
    assert lido.motivos == {(FUNDO, "2023-07-01"): leitura.MOTIVO_ENTREGA_POSTERIOR}
    explorado = leitura.informe_fii(
        conn, FUNDO, _sp(2023, 9, 1), modo=leitura.EXPLORATORIO
    )
    assert ("2023-07-01", "2") in _meses(explorado)
    assert ("2023-09-01", "1") not in _meses(explorado)  # referência depois de D
    assert explorado.avisos == (leitura.AVISO_EXPLORATORIO,)


def test_informe_versao_1_entregue_depois_de_d_nao_tem_motivo(conn):
    _carregar(conn, FII, "FII_INFORME")
    lido = leitura.informe_fii(conn, FUNDO, _sp(2023, 9, 1))
    assert (
        FUNDO,
        "2023-08-01",
    ) not in lido.motivos  # v1 entregue em 15/09: ainda não existia


def test_informe_complemento_sem_geral_fica_fora_com_motivo(conn, tmp_path):
    def sem_janeiro(texto):
        return "".join(
            l for l in texto.splitlines(keepends=True) if ";2023-01-01;" not in l
        )

    _carregar(
        conn,
        _copia(FII, tmp_path / "f.zip", {"inf_mensal_fii_geral_2023.csv": sem_janeiro}),
        "FII_INFORME",
    )
    for modo in leitura.MODOS:
        lido = leitura.informe_fii(conn, FUNDO, HOJE, modo=modo)
        assert lido.motivos[(FUNDO, "2023-01-01")] == leitura.MOTIVO_SEM_GERAL
        assert ("2023-01-01", "1") not in _meses(lido)


def test_informe_geral_em_conflito_abstem_a_referencia(conn, tmp_path):
    def duplicar(texto):
        linhas = texto.splitlines(keepends=True)
        return texto + linhas[1].replace(";2023-02-15;", ";2023-02-16;")

    _carregar(
        conn,
        _copia(FII, tmp_path / "f.zip", {"inf_mensal_fii_geral_2023.csv": duplicar}),
        "FII_INFORME",
    )
    lido = leitura.informe_fii(conn, FUNDO, HOJE)
    assert lido.motivos[(FUNDO, "2023-01-01")] == leitura.MOTIVO_GERAL_EM_CONFLITO
    assert ("2023-01-01", "1") not in _meses(lido)


def test_informe_antes_de_2016_indisponivel(conn):
    _carregar(conn, FII, "FII_INFORME")
    lido = leitura.informe_fii(conn, FUNDO, _sp(2015, 12, 31))
    assert lido.motivos == {(FUNDO, ""): leitura.MOTIVO_INFORME_INDISPONIVEL}
    assert lido.dados == {"registros": [], "composicoes": []}


# --- Modos e parâmetros ------------------------------------------------------------------------


def test_modos_nunca_se_misturam(conn):
    _carregar(conn, ITR, "ITR")
    _carregar(conn, FII, "FII_INFORME")
    estrito = [
        leitura.demonstrativo(conn, "ITR", "DRE_con", HOJE),
        leitura.composicao(conn, "ITR", HOJE),
        leitura.informe_fii(conn, FUNDO, HOJE),
        leitura.entregas(conn, "ITR", HOJE),
    ]
    assert leitura.modo_unico(estrito) == leitura.ESTRITO
    assert (
        leitura.entregas(conn, "ITR", HOJE, modo=leitura.EXPLORATORIO).modo
        == leitura.EXPLORATORIO
    )
    explorado = leitura.demonstrativo(
        conn, "ITR", "BPA_con", HOJE, modo=leitura.EXPLORATORIO
    )
    assert leitura.modo_unico([explorado]) == leitura.EXPLORATORIO
    with pytest.raises(leitura.ModosMisturados, match="modos diferentes"):
        leitura.modo_unico([*estrito, explorado])
    with pytest.raises(leitura.ModosMisturados):
        leitura.modo_unico([])


@pytest.mark.parametrize(
    ("as_of", "modo", "mensagem"),
    [
        (datetime(2026, 1, 1), leitura.ESTRITO, "as_of exige fuso horário"),  # noqa: DTZ001
        (HOJE, "misto", "modo desconhecido: 'misto'"),
    ],
)
def test_parametros_invalidos(conn, as_of, modo, mensagem):
    for chamada in (
        lambda: leitura.demonstrativo(conn, "ITR", "DRE_con", as_of, modo=modo),
        lambda: leitura.composicao(conn, "ITR", as_of, modo=modo),
        lambda: leitura.entregas(conn, "ITR", as_of, modo=modo),
        lambda: leitura.informe_fii(conn, FUNDO, as_of, modo=modo),
    ):
        with pytest.raises(ValueError, match=f"^{mensagem}$"):
            chamada()


def test_dia_e_o_de_sao_paulo(conn):
    lido = leitura.entregas(conn, "ITR", datetime(2020, 5, 22, 2, tzinfo=UTC))
    assert lido.dia == date(2020, 5, 21)


def test_valor_vazio_vira_nan_e_balanco_sem_inicio(conn, tmp_path):
    def esvaziar(texto):
        linhas = texto.splitlines(keepends=True)
        posicao = next(n for n, l in enumerate(linhas) if ";ÚLTIMO;" in l)
        campos = linhas[posicao].split(";")
        campos[linhas[0].split(";").index("VL_CONTA")] = ""
        linhas[posicao] = ";".join(campos)
        return "".join(linhas)

    copia = _copia(
        ITR, tmp_path / "x.zip", {"itr_cia_aberta_BPA_con_2020.csv": esvaziar}
    )
    _carregar(conn, copia, "ITR")
    lido = leitura.demonstrativo(
        conn, "ITR", "BPA_con", HOJE, modo=leitura.EXPLORATORIO
    ).dados
    assert "DT_INI_EXERC" not in lido.columns
    assert lido["VL_CONTA"].isna().sum() == 1


# --- Lacunas da mutação -------------------------------------------------------------------------

OUTRA = "99.999.999/0001-99"


def _duas_companhias(conn, tmp_path):
    """A fixture do ITR e uma cópia com outro CNPJ, entregue um dia depois."""
    _carregar(conn, ITR, "ITR")

    def outra(texto):
        return texto.replace(CIA, OUTRA).replace(";2020-05-21;", ";2020-05-22;")

    alterar = {n: outra for n in zipfile.ZipFile(ITR).namelist()}
    _carregar(conn, _copia(ITR, tmp_path / "outra.zip", alterar), "ITR")


def test_filtro_por_cnpj_com_duas_companhias(conn, tmp_path):
    _duas_companhias(conn, tmp_path)
    d = _sp(2020, 5, 22)
    for funcao, args in (
        (leitura.demonstrativo, ("ITR", "DRE_con", d)),
        (leitura.composicao, ("ITR", d)),
    ):
        todas = funcao(conn, *args)
        so_cia = funcao(conn, *args, cnpj=CIA)
        assert set(todas.dados["CNPJ_CIA"]) == {CIA}  # a outra só tem a v2 em 22/05
        assert todas.motivos == {
            (OUTRA, "2020-03-31"): leitura.MOTIVO_ENTREGA_POSTERIOR
        }
        assert so_cia.motivos == {} and set(so_cia.dados["CNPJ_CIA"]) == {CIA}
        so_outra = funcao(conn, *args, cnpj=OUTRA)
        assert so_outra.dados.empty and set(so_outra.motivos) == {(OUTRA, "2020-03-31")}
    entregas = leitura.entregas(conn, "ITR", d, cnpj=OUTRA).dados
    assert {l["CNPJ_CIA"] for l in entregas} == {OUTRA} and len(entregas) == 1
    assert {l["CNPJ_CIA"] for l in leitura.entregas(conn, "ITR", d).dados} == {
        CIA,
        OUTRA,
    }
    explorado = leitura.entregas(
        conn, "ITR", d, modo=leitura.EXPLORATORIO, cnpj=OUTRA
    ).dados
    assert [l["VERSAO"] for l in explorado] == ["1", "2"]


def test_ordem_da_conta_por_segmento_numerico():
    contas = ["3.10", "3.2", "3.01.01", "3.01", "3.99.01.A", "3.99.01.1"]
    assert sorted(contas, key=leitura._ordem_da_conta) == [
        "3.01", "3.01.01", "3.2", "3.10", "3.99.01.1", "3.99.01.A",
    ]  # fmt: skip


@pytest.mark.parametrize(("texto", "esperado"), [("020990", 20990), (" 1023 ", 1023)])
def test_codigo_cvm(texto, esperado):
    assert leitura._codigo_cvm(texto) == esperado


@pytest.mark.parametrize("texto", ["", None, "ab"])
def test_codigo_cvm_ausente(texto):
    assert leitura._codigo_cvm(texto) is pd.NA


@pytest.mark.parametrize(
    ("dt_refer", "dia", "esperado"),
    [
        ("2023-12-01", date(2024, 1, 1), True),
        ("2023-12-01", date(2023, 12, 31), False),
        ("2023-11-01", date(2023, 12, 1), True),
        ("2023-11-01", date(2023, 11, 30), False),
        ("lixo", date(2030, 1, 1), False),
    ],
)
def test_mes_encerrado(dt_refer, dia, esperado):
    assert leitura._mes_encerrado(dt_refer, dia) is esperado


def test_data_so_os_dez_primeiros_caracteres():
    assert leitura._data("2023-02-15T10:00") == date(2023, 2, 15)
    assert leitura._data("2023-02-155") == date(2023, 2, 15)
    assert leitura._data(None) is None


def test_informe_exploratorio_so_com_documento_que_ja_existia(conn):
    """Dezembro/2023 (v1 entregue em 15/01/2024): fora em 01/01/2024, dentro em 16/01."""
    _carregar(conn, FII, "FII_INFORME")
    antes = leitura.informe_fii(conn, FUNDO, _sp(2024, 1, 1), modo=leitura.EXPLORATORIO)
    depois = leitura.informe_fii(
        conn, FUNDO, _sp(2024, 1, 16), modo=leitura.EXPLORATORIO
    )
    assert ("2023-12-01", "1") not in _meses(antes)
    assert ("2023-12-01", "1") in _meses(depois)
    assert len(_meses(depois)) == 12 and len(depois.dados["composicoes"]) == 12
    agosto = leitura.informe_fii(
        conn, FUNDO, _sp(2023, 9, 1), modo=leitura.EXPLORATORIO
    )
    assert ("2023-08-01", "1") not in _meses(agosto)  # v1 entregue em 15/09
    assert ("2023-07-01", "2") in _meses(agosto)  # reapresentação: a v1 existiu


def test_informe_no_primeiro_dia_de_2016_nao_tem_o_motivo(conn):
    lido = leitura.informe_fii(conn, FUNDO, _sp(2016, 1, 1))
    assert lido.motivos == {}


def test_leituras_levam_dia_e_proveniencia(conn):
    _carregar(conn, ITR, "ITR")
    _carregar(conn, FII, "FII_INFORME")
    itr = (
        f"cvm:{ITR.name}",
        "2026-11-11T12:00:00+00:00",
        carga_cvm.proveniencia.hash_sha256(ITR),
    )
    fii = (
        f"cvm:{FII.name}",
        "2026-11-11T12:00:00+00:00",
        carga_cvm.proveniencia.hash_sha256(FII),
    )
    for lido in (
        leitura.demonstrativo(conn, "ITR", "DRE_con", HOJE),
        leitura.composicao(conn, "ITR", HOJE),
        leitura.entregas(conn, "ITR", HOJE),
    ):
        assert lido.dia == date(2026, 11, 11) and lido.proveniencia == (itr,)
    informe = leitura.informe_fii(conn, FUNDO, HOJE)
    assert informe.dia == date(2026, 11, 11) and informe.proveniencia == (fii,)
    assert leitura.entregas(conn, "ITR", HOJE).motivos == {}


def test_composicao_vazia_mantem_as_colunas_e_o_aviso(conn):
    _carregar(conn, ITR, "ITR")
    vazia = leitura.composicao(conn, "ITR", _sp(2020, 5, 1), modo=leitura.EXPLORATORIO)
    assert vazia.dados.empty
    assert list(vazia.dados.columns) == [
        "CNPJ_CIA", "DT_REFER", "VERSAO", "DENOM_CIA", *leitura._COMPOSICAO,
    ]  # fmt: skip
    assert vazia.avisos == (leitura.AVISO_EXPLORATORIO,)


def test_cd_cvm_inteiro_anulavel(conn):
    _carregar(conn, ITR, "ITR")
    lido = leitura.demonstrativo(conn, "ITR", "DRE_con", HOJE).dados
    assert str(lido["CD_CVM"].dtype) == "Int64" and set(lido["CD_CVM"]) == {20990}


def _v1_e_v3_sem_a_v2(conn, tmp_path):
    """Carga antiga com a v1 do 1º tri; carga nova com a v3 (entregue em 2021); a v2 nunca vista."""
    trimestre = ";2020-03-31;2;"

    def v1(texto):
        return texto.replace(trimestre, ";2020-03-31;1;")

    def indice_v1(texto):
        return "".join(l for l in texto.splitlines(keepends=True) if trimestre not in l)

    alterar = {
        n: v1 for n in zipfile.ZipFile(ITR).namelist() if n != "itr_cia_aberta_2020.csv"
    }
    alterar["itr_cia_aberta_2020.csv"] = indice_v1
    _carregar(conn, _copia(ITR, tmp_path / "v1.zip", alterar), "ITR")

    def v3(texto):
        return texto.replace(trimestre, ";2020-03-31;3;")

    def indice_v3(texto):
        sem = [
            l
            for l in texto.splitlines(keepends=True)
            if trimestre not in l and ";2020-03-31;1;" not in l
        ]
        linha = next(l for l in texto.splitlines(keepends=True) if trimestre in l)
        return "".join(sem) + linha.replace(trimestre, ";2020-03-31;3;").replace(
            "2020-05-21", "2021-01-15"
        )

    alterar = {
        n: v3 for n in zipfile.ZipFile(ITR).namelist() if n != "itr_cia_aberta_2020.csv"
    }
    alterar["itr_cia_aberta_2020.csv"] = indice_v3
    _carregar(
        conn,
        _copia(ITR, tmp_path / "v3.zip", alterar),
        "ITR",
        coleta="2026-11-12T12:00:00+00:00",
    )


def test_estrito_abstem_com_versao_intermediaria_nao_vista(conn, tmp_path):
    _v1_e_v3_sem_a_v2(conn, tmp_path)
    d = _sp(2020, 12, 1)  # v1 entregue antes, v3 depois, v2 de data desconhecida
    for funcao, args in (
        (leitura.demonstrativo, ("ITR", "DRE_con", d)),
        (leitura.composicao, ("ITR", d)),
    ):
        lido = funcao(conn, *args)
        assert lido.motivos[(CIA, "2020-03-31")] == leitura.MOTIVO_VERSAO_NAO_VISTA
        assert "2020-03-31" not in set(lido.dados["DT_REFER"])
    explorado = leitura.demonstrativo(
        conn, "ITR", "DRE_con", d, modo=leitura.EXPLORATORIO
    )
    assert ("2020-03-31", "3") in _versoes(explorado)


def test_estrito_com_versoes_seguidas_nao_abstem(conn):
    _carregar(conn, ITR, "ITR")
    lido = leitura.demonstrativo(conn, "ITR", "DRE_con", _sp(2020, 5, 22))
    assert lido.motivos == {} and ("2020-03-31", "2") in _versoes(lido)


def _informe_alterado(conn, tmp_path, alterar_geral, outras=None):
    alterar = {"inf_mensal_fii_geral_2023.csv": alterar_geral, **(outras or {})}
    _carregar(conn, _copia(FII, tmp_path / "f.zip", alterar), "FII_INFORME")


def test_informe_estrito_abstem_com_versao_intermediaria_nao_vista(conn, tmp_path):
    """Março/2023 com a v1 (entregue em 14/04) e uma v3 entregue em 20/06, sem a v2."""

    def v3(texto):
        linha = next(
            l for l in texto.splitlines(keepends=True) if ";2023-03-01;1;" in l
        )
        return texto + linha.replace(
            ";2023-03-01;1;2023-04-14;", ";2023-03-01;3;2023-06-20;"
        )

    _informe_alterado(conn, tmp_path, v3)
    lido = leitura.informe_fii(conn, FUNDO, _sp(2023, 6, 1))
    assert lido.motivos[(FUNDO, "2023-03-01")] == leitura.MOTIVO_VERSAO_NAO_VISTA
    assert all(r["Data_Referencia"] != "2023-03-01" for r in lido.dados["registros"])


def test_informe_conflito_de_entrega_depois_de_d_nao_derruba_o_passado(conn, tmp_path):
    def segunda_entrega(texto):
        linha = next(
            l for l in texto.splitlines(keepends=True) if ";2023-01-01;1;" in l
        )
        return texto + linha.replace(";2023-02-15;", ";2023-08-01;")

    _informe_alterado(conn, tmp_path, segunda_entrega)
    em_marco = leitura.informe_fii(conn, FUNDO, _sp(2023, 3, 1))
    assert ("2023-01-01", "1") in _meses(em_marco) and em_marco.motivos == {}
    hoje = leitura.informe_fii(conn, FUNDO, HOJE)
    assert hoje.motivos[(FUNDO, "2023-01-01")] == leitura.MOTIVO_GERAL_EM_CONFLITO
    explorado = leitura.informe_fii(
        conn, FUNDO, _sp(2023, 3, 1), modo=leitura.EXPLORATORIO
    )
    assert explorado.motivos[(FUNDO, "2023-01-01")] == leitura.MOTIVO_GERAL_EM_CONFLITO


def test_informe_conflito_numa_versao_abstem_a_referencia_inteira(conn, tmp_path):
    def conflito_na_v1_e_v2_valida(texto):
        linha = next(
            l for l in texto.splitlines(keepends=True) if ";2023-01-01;1;" in l
        )
        return (
            texto
            + linha.replace(";2023-02-15;", ";2023-02-16;")
            + linha.replace(";2023-01-01;1;2023-02-15;", ";2023-01-01;2;2023-02-20;")
        )

    def v2_no_complemento(texto):
        linha = next(
            l for l in texto.splitlines(keepends=True) if ";2023-01-01;1;" in l
        )
        return texto + linha.replace(";2023-01-01;1;", ";2023-01-01;2;")

    _informe_alterado(
        conn,
        tmp_path,
        conflito_na_v1_e_v2_valida,
        {"inf_mensal_fii_complemento_2023.csv": v2_no_complemento},
    )
    for modo in leitura.MODOS:
        lido = leitura.informe_fii(conn, FUNDO, HOJE, modo=modo)
        assert lido.motivos[(FUNDO, "2023-01-01")] == leitura.MOTIVO_GERAL_EM_CONFLITO
        assert all(
            r["Data_Referencia"] != "2023-01-01" for r in lido.dados["registros"]
        )


def test_informe_motivos_so_de_referencias_que_ja_existiam(conn, tmp_path):
    def sem_julho(texto):
        return "".join(
            l for l in texto.splitlines(keepends=True) if ";2023-07-01;" not in l
        )

    _informe_alterado(conn, tmp_path, sem_julho)
    assert (FUNDO, "2023-07-01") not in leitura.informe_fii(
        conn, FUNDO, _sp(2023, 3, 1)
    ).motivos
    assert (
        leitura.informe_fii(conn, FUNDO, HOJE).motivos[(FUNDO, "2023-07-01")]
        == leitura.MOTIVO_SEM_GERAL
    )


def test_informe_ativo_sem_geral_fica_fora_com_motivo(conn, tmp_path):
    def ativo_v2(texto):
        linha = next(
            l for l in texto.splitlines(keepends=True) if ";2023-02-01;1;" in l
        )
        return texto + linha.replace(";2023-02-01;1;", ";2023-02-01;2;")

    _informe_alterado(
        conn, tmp_path, lambda t: t, {"inf_mensal_fii_ativo_passivo_2023.csv": ativo_v2}
    )
    lido = leitura.informe_fii(conn, FUNDO, HOJE)
    assert lido.motivos == {(FUNDO, "2023-02-01"): leitura.MOTIVO_SEM_GERAL}
    assert len(lido.dados["composicoes"]) == 11  # a referência inteira fica fora
    assert all(r["Data_Referencia"] != "2023-02-01" for r in lido.dados["registros"])


def test_demonstrativo_vazio_mantem_o_periodo_menos_nos_balancos(conn):
    _carregar(conn, ITR, "ITR")
    d = _sp(2020, 5, 1)
    assert (
        "DT_INI_EXERC" in leitura.demonstrativo(conn, "ITR", "DRE_con", d).dados.columns
    )
    assert (
        "DT_INI_EXERC"
        not in leitura.demonstrativo(conn, "ITR", "BPP_con", d).dados.columns
    )


def _versao_extra(referencia, de, para, entrega_nova):
    """Geral e complemento com mais uma versão da referência, entregue em `entrega_nova`."""

    def geral(texto):
        linha = next(
            l for l in texto.splitlines(keepends=True) if f";{referencia};{de};" in l
        )
        campos = linha.split(";")
        campos[3], campos[4] = para, entrega_nova
        return texto + ";".join(campos)

    def complemento(texto):
        linha = next(
            l for l in texto.splitlines(keepends=True) if f";{referencia};{de};" in l
        )
        return texto + linha.replace(f";{referencia};{de};", f";{referencia};{para};")

    return geral, {"inf_mensal_fii_complemento_2023.csv": complemento}


def test_informe_versoes_seguidas_usa_a_vigente(conn, tmp_path):
    """Março/2023: v1 entregue em 14/04 e v2 em 20/06; em 01/06 vale a v1, sem motivo."""
    geral, outras = _versao_extra("2023-03-01", "1", "2", "2023-06-20")
    _informe_alterado(conn, tmp_path, geral, outras)
    lido = leitura.informe_fii(conn, FUNDO, _sp(2023, 6, 1))
    assert lido.motivos == {}
    assert ("2023-03-01", "1") in _meses(lido) and ("2023-03-01", "2") not in _meses(
        lido
    )
    assert ("2023-03-01", "2") in _meses(
        leitura.informe_fii(conn, FUNDO, _sp(2023, 6, 21))
    )


@pytest.mark.parametrize("versao", ["x", "²"])
def test_informe_versao_ilegivel_passa_para_a_guarda_do_rendimento(
    conn, tmp_path, versao
):
    """Versão ilegível entregue antes de D vai ao `rendimento_fii`, que tem a guarda dela."""
    geral, outras = _versao_extra("2023-03-01", "1", versao, "2023-04-20")
    _informe_alterado(conn, tmp_path, geral, outras)
    lido = leitura.informe_fii(conn, FUNDO, _sp(2023, 6, 1))
    assert lido.motivos == {}
    assert ("2023-03-01", versao) in _meses(lido)


def test_informe_versao_ilegivel_antes_e_reapresentacao_depois(conn, tmp_path):
    """Com só uma versão ilegível entregue antes de D, não há vigente numérica para comparar."""

    def so_ilegivel(texto):
        return texto.replace(";2023-03-01;1;", ";2023-03-01;x;")

    geral_v3, outras = _versao_extra("2023-03-01", "x", "3", "2023-07-01")
    _informe_alterado(
        conn,
        tmp_path,
        lambda t: geral_v3(so_ilegivel(t)),
        {
            "inf_mensal_fii_complemento_2023.csv": lambda t: outras[
                "inf_mensal_fii_complemento_2023.csv"
            ](so_ilegivel(t)),
            "inf_mensal_fii_ativo_passivo_2023.csv": so_ilegivel,
        },
    )
    lido = leitura.informe_fii(conn, FUNDO, _sp(2023, 6, 1))
    assert lido.motivos == {}
    assert ("2023-03-01", "x") in _meses(lido) and ("2023-03-01", "3") not in _meses(
        lido
    )


def test_estrito_abstem_com_entrega_ilegivel_de_versao_posterior(conn, tmp_path):
    """1º tri: v1 entregue antes de D e v2 com DT_RECEB fora do formato: a v1 não fica provada."""
    _carregar(
        conn,
        _copia(
            ITR,
            tmp_path / "x.zip",
            {
                "itr_cia_aberta_2020.csv": lambda t: t.replace(
                    ";2020-05-21;", ";21/05/2020;"
                )
            },
        ),
        "ITR",
    )
    lido = leitura.demonstrativo(conn, "ITR", "DRE_con", _sp(2020, 6, 1))
    assert lido.motivos[(CIA, "2020-03-31")] == leitura.MOTIVO_ENTREGA_ILEGIVEL


def test_informe_estrito_abstem_com_entrega_ilegivel_de_versao_posterior(
    conn, tmp_path
):
    geral, outras = _versao_extra("2023-03-01", "1", "2", "")
    _informe_alterado(conn, tmp_path, geral, outras)
    lido = leitura.informe_fii(conn, FUNDO, _sp(2023, 6, 1))
    assert lido.motivos == {(FUNDO, "2023-03-01"): leitura.MOTIVO_ENTREGA_ILEGIVEL}
    assert all(r["Data_Referencia"] != "2023-03-01" for r in lido.dados["registros"])


def test_informe_versao_so_no_complemento_tira_a_referencia(conn, tmp_path):
    def complemento_v2(texto):
        linha = next(
            l for l in texto.splitlines(keepends=True) if ";2023-04-01;1;" in l
        )
        return texto + linha.replace(";2023-04-01;1;", ";2023-04-01;2;")

    _informe_alterado(
        conn,
        tmp_path,
        lambda t: t,
        {"inf_mensal_fii_complemento_2023.csv": complemento_v2},
    )
    lido = leitura.informe_fii(conn, FUNDO, HOJE)
    assert lido.motivos == {(FUNDO, "2023-04-01"): leitura.MOTIVO_SEM_GERAL}
    assert len(lido.dados["composicoes"]) == 11
