"""F3-5: universo ponto-no-tempo com as deslistadas.

Fixtures: o FCA oficial de 2015 recortado para a ALL - América Latina Logística (CNPJ
02.387.241/0001-60, deslistada em 2015 na incorporação pela Rumo: fim de negociação em
01/04/2015, entregue na versão 4 em 05/05/2015) e para a Americanas (fixture do F3-3b); o
Informe oficial de 2023 de um FII; e cotações pelo layout oficial do COTAHIST.
"""

import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from test_cotahist import _linha

import config
from sentinela.data.pit import carga_cvm
from sentinela.data.providers import b3_cotahist
from sentinela.data.referencia import universo
from sentinela.data.store import migracoes

FIXTURES = Path(__file__).parent / "fixtures" / "pit_cvm"
ALL = "02.387.241/0001-60"
AMER = "00.776.574/0001-56"
LIMIARES = {
    "presenca_min": config.MacroContext.LIQUIDEZ_PRESENCA_MIN,
    "volume_acoes_min": config.MacroContext.LIQUIDEZ_VOLUME_ACOES_MIN,
    "volume_fii_min": config.MacroContext.LIQUIDEZ_VOLUME_FII_MIN,
}


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _fca(conn, nome):
    caminho = FIXTURES / nome
    carga_cvm.carregar(
        conn,
        caminho,
        tipo="FCA",
        fonte=f"cvm:{nome}",
        coleta="2026-11-12T00:00:00+00:00",
    )


def _pregoes(inicio, quantos):
    dias, dia = [], inicio
    while len(dias) < quantos:
        if dia.weekday() < 5:
            dias.append(dia)
        dia += timedelta(days=1)
    return dias


def _precos(conn, tmp_path, linhas, nome="COTAHIST.ZIP"):
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("COTAHIST.TXT", "\n".join(linhas).encode("latin-1"))
    b3_cotahist.carregar(conn, caminho, fonte="b3", coleta="2026-11-12T00:00:00+00:00")


def _negocio(dia, codigo, isin, volume="000000000100000000"):
    return _linha(
        DATA=dia.strftime("%Y%m%d"), CODNEG=codigo, CODISI=isin, VOLTOT=volume
    )


# --- Companhias pelo FCA ------------------------------------------------------------------


def test_deslistada_conhecida_sai_depois_do_fim_de_negociacao(conn):
    _fca(conn, "fca_cia_aberta_2015_all.zip")
    depois = universo.companhias_em(conn, date(2015, 6, 1))
    assert depois == {
        "companhias": [],
        "sem_prova": [],
    }  # v4 entregue em 05/05: fim em 01/04
    linhas = conn.execute(
        "SELECT linha_json FROM fca_linhas WHERE parte = 'valor_mobiliario'"
    ).fetchall()
    acoes = [
        json.loads(t)
        for (t,) in linhas
        if json.loads(t)["Valor_Mobiliario"] == "Ações Ordinárias"
    ]
    assert acoes[0]["Data_Fim_Negociacao"] == "2015-04-01"


def test_antes_da_versao_com_linhas_a_companhia_fica_sem_prova(conn):
    _fca(conn, "fca_cia_aberta_2015_all.zip")
    antes = universo.companhias_em(
        conn, date(2015, 3, 1)
    )  # só a v1 (08/01) entregue; linhas da v4
    assert antes == {
        "companhias": [],
        "sem_prova": [{"cnpj": ALL, "referencia_fca": "2015-01-01"}],
    }


def test_companhia_listada_com_as_datas_do_fca(conn):
    _fca(conn, "fca_cia_aberta_2015.zip")
    lido = universo.companhias_em(
        conn, date(2015, 9, 1)
    )  # v2 da Americanas entregue em 17/08
    assert [c["cnpj"] for c in lido["companhias"]] == [AMER]
    (americanas,) = lido["companhias"]
    assert (
        americanas["valor_mobiliario"] == "Ações Ordinárias"
        and americanas["fim_negociacao"] is None
    )
    assert (
        americanas["inicio_negociacao"] < "2015-09-01"
        and americanas["referencia_fca"] == "2015-01-01"
    )


def test_debentures_e_balcao_ficam_fora(conn):
    _fca(conn, "fca_cia_aberta_2015_all.zip")
    linhas = conn.execute(
        "SELECT linha_json FROM fca_linhas WHERE parte = 'valor_mobiliario'"
    ).fetchall()
    assert {json.loads(t)["Valor_Mobiliario"] for (t,) in linhas} == {
        "Ações Ordinárias",
        "Debêntures",
    }
    assert universo.companhias_em(conn, date(2015, 6, 1))["companhias"] == []


# --- Tickers pelo COTAHIST ----------------------------------------------------------------


def test_ticker_deslistado_entra_antes_e_sai_depois(conn, tmp_path):
    dias = _pregoes(date(2015, 1, 2), 120)
    ultimo_all = dias[60]
    linhas = [_negocio(d, "VIVA3", "BRVIVAACNOR1") for d in dias]
    linhas += [_negocio(d, "ALLL3", "BRALLLACNOR4") for d in dias if d <= ultimo_all]
    _precos(conn, tmp_path, linhas)
    assert universo.gerar(conn, "2026-11-12T00:00:00+00:00") == 2
    durante = {t["ticker"] for t in universo.tickers_em(conn, dias[50])}
    assert durante == {"VIVA3", "ALLL3"}
    ainda = {
        t["ticker"] for t in universo.tickers_em(conn, dias[100])
    }  # parou há 39 pregões
    assert ainda == {"VIVA3", "ALLL3"}
    depois = {
        t["ticker"] for t in universo.tickers_em(conn, dias[119])
    }  # 58 pregões depois
    assert depois == {"VIVA3", "ALLL3"}
    _precos(
        conn,
        tmp_path,
        [
            _negocio(d, "VIVA3", "BRVIVAACNOR1")
            for d in _pregoes(dias[-1] + timedelta(days=1), 10)
        ],
        "b.ZIP",
    )
    universo.gerar(conn, "2026-11-13T00:00:00+00:00")
    fora = {t["ticker"] for t in universo.tickers_em(conn, date(2015, 8, 1))}
    assert fora == {"VIVA3"}  # a ALL parou de negociar há mais de 63 pregões
    (all3,) = [t for t in universo.tickers_em(conn, dias[50]) if t["ticker"] == "ALLL3"]
    assert (all3["primeiro_pregao"], all3["ultimo_pregao"]) == (
        dias[0].isoformat(),
        dias[49].isoformat(),  # nada depois de D: a deslistagem futura não aparece
    )
    (all3,) = [
        t for t in universo.tickers_em(conn, dias[100]) if t["ticker"] == "ALLL3"
    ]
    assert all3["ultimo_pregao"] == ultimo_all.isoformat()


def test_ticker_ainda_nao_negociado_fica_fora(conn, tmp_path):
    dias = _pregoes(date(2020, 1, 2), 30)
    _precos(
        conn,
        tmp_path,
        [_negocio(d, "VIVA3", "BRVIVAACNOR1") for d in dias]
        + [_negocio(dias[20], "NOVA3", "BRNOVAACNOR1")],
    )
    universo.gerar(conn, "g")
    assert {t["ticker"] for t in universo.tickers_em(conn, dias[10])} == {"VIVA3"}
    assert {t["ticker"] for t in universo.tickers_em(conn, dias[29])} == {
        "VIVA3",
        "NOVA3",
    }


def test_classes_pelo_isin_e_fii_so_com_informe(conn, tmp_path):
    dias = _pregoes(date(2024, 1, 2), 5)
    isins = {
        "TSTA3": "BRTSTAACNOR1", "TSTA11": "BRTSTACDAM12", "UNTS11": "BRUNTSUNT001",
        "FUND11": "BRFUNDCTF000", "VPQS11": "BRFVPQCTF015", "AAPL34": "BRAAPLBDR004",
    }  # fmt: skip
    _precos(conn, tmp_path, [_negocio(d, c, i) for d in dias for c, i in isins.items()])
    carga_cvm.carregar(
        conn,
        FIXTURES / "inf_mensal_fii_2023.zip",
        tipo="FII_INFORME",
        fonte="cvm",
        coleta="c",
    )
    universo.gerar(conn, "g")
    classes = {
        t["ticker"]: t["classe"]
        for t in universo.tickers_em(conn, dias[-1] + timedelta(days=1))
    }
    assert classes == {"TSTA3": "STOCK", "UNTS11": "UNIT", "VPQS11": "FII"}


@pytest.mark.parametrize(
    ("isin", "classe"),
    [("BRTSTAACNOR1", "STOCK"), ("BRUNTSUNT001", "UNIT"), ("BRFUNDCTF000", "FUNDO"),
     ("BRAAPLBDR004", "BDR"), ("BRTSTACDAM12", "OUTRO"), ("CURTO", "OUTRO")],
)  # fmt: skip
def test_classe_do_isin(isin, classe):
    assert universo.classe_do_isin(isin) == classe


def test_sem_pregao_antes_de_d_nao_ha_universo(conn, tmp_path):
    assert universo.tickers_em(conn, date(2024, 1, 1)) == []
    _precos(conn, tmp_path, [_negocio(date(2024, 1, 2), "TSTA3", "BRTSTAACNOR1")])
    assert universo.tickers_em(conn, date(2024, 1, 2)) == []  # o pregão de D não conta
    assert [t["ticker"] for t in universo.tickers_em(conn, date(2024, 1, 3))] == [
        "TSTA3"
    ]


# --- Universo do backtest -----------------------------------------------------------------


def test_universo_do_backtest_filtra_pela_liquidez_da_propria_data(conn, tmp_path):
    _fca(conn, "fca_cia_aberta_2026_amer.zip")  # AMER3, entregue em 10/06/2026
    carga_cvm.carregar(
        conn,
        FIXTURES / "inf_mensal_fii_2023.zip",
        tipo="FII_INFORME",
        fonte="cvm",
        coleta="c",
    )
    dias = _pregoes(date(2026, 6, 12), 70)
    linhas = []
    for d in dias:
        linhas.append(_negocio(d, "AMER3", "BRAMERACNOR4"))  # R$ 1 milhão por pregão
        linhas.append(
            _negocio(d, "VPQS11", "BRFVPQCTF015", volume="000000000005000000")
        )
        linhas.append(_negocio(d, "POUC3", "BRPOUCACNOR1"))  # sem código no FCA
    _precos(conn, tmp_path, linhas)
    universo.gerar(conn, "g")
    lido = universo.universo_backtest(
        conn, dias[-1] + timedelta(days=1), CADASTRO, **LIMIARES
    )
    assert [t["ticker"] for t in lido["elegiveis"]] == ["AMER3"]
    (fii,) = lido["fora"]  # R$ 50 mil por pregão, abaixo dos R$ 100 mil do FII
    assert (fii["ticker"], fii["classe"]) == ("VPQS11", "FII")
    assert fii["motivo"].startswith("liquidez abaixo do mínimo")
    assert [t["ticker"] for t in lido["sem_identificacao"]] == ["POUC3"]
    cedo = universo.universo_backtest(conn, dias[10], CADASTRO, **LIMIARES)
    assert cedo["elegiveis"] == [] and [f["ticker"] for f in cedo["fora"]] == [
        "AMER3",
        "VPQS11",
    ]
    assert {f["motivo"] for f in cedo["fora"]} == {
        "liquidez não medida: janela incompleta"
    }


def test_universo_recusa_instante(conn):
    for chamada in (universo.tickers_em, universo.companhias_em):
        with pytest.raises(
            TypeError,
            match=r"^o universo recebe o dia local de D \(date\), não um instante$",
        ):
            chamada(conn, datetime(2024, 1, 1, tzinfo=UTC))


def test_geracao_so_insercao_e_falha_sem_linha_parcial(conn, tmp_path):
    _precos(conn, tmp_path, [_negocio(date(2024, 1, 2), "TSTA3", "BRTSTAACNOR1")])
    universo.gerar(conn, "g")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError, match="universo é só de inserção"):
        universo.gerar(conn, "g")
    assert conn.in_transaction is False  # o SAVEPOINT desfeito e liberado
    assert conn.execute("SELECT COUNT(*) FROM universo").fetchone() == (1,)
    for sql in ("UPDATE universo SET classe = 'BDR'", "DELETE FROM universo"):
        with pytest.raises(sqlite3.IntegrityError, match="universo é só de inserção"):
            conn.execute(sql)


# --- Universo montado em D (índice em D + complemento do COTAHIST) ------------------------

CADASTRO = pd.DataFrame(
    [
        {"CNPJ_CIA": AMER, "DENOM_SOCIAL": "AMERICANAS S.A.", "SIT": "ATIVO", "CD_CVM": "20990",
         "SETOR_ATIV": "Comércio", "CONTROLE_ACIONARIO": "PRIVADO"},
        {"CNPJ_CIA": ALL, "DENOM_SOCIAL": "RUMO S.A.", "SIT": "ATIVO", "CD_CVM": "17450",
         "SETOR_ATIV": "Logística", "CONTROLE_ACIONARIO": "PRIVADO"},
    ]
)  # fmt: skip


def test_deslistada_sem_codigo_no_fca_fica_sem_identificacao_e_sai_depois(
    conn, tmp_path
):
    _fca(conn, "fca_cia_aberta_2015_all.zip")
    dias = _pregoes(date(2015, 1, 2), 150)
    linhas = [_negocio(d, "VIVA3", "BRVIVAACNOR1") for d in dias]
    linhas += [
        _negocio(d, "ALLL3", "BRALLLACNOR4") for d in dias if d <= date(2015, 3, 31)
    ]
    _precos(conn, tmp_path, linhas)
    universo.gerar(conn, "g")
    durante = universo.universo_em(conn, date(2015, 3, 2), CADASTRO)
    assert durante["universo"] == []  # o FCA de 2015 não traz o código de negociação
    assert [
        (t["ticker"], t["classe"], t["motivo"]) for t in durante["sem_identificacao"]
    ] == [
        ("ALLL3", "STOCK", universo.MOTIVO_SEM_IDENTIFICACAO),
        ("VIVA3", "STOCK", universo.MOTIVO_SEM_IDENTIFICACAO),
    ]
    assert (
        durante["sem_identificacao"][0]["ultimo_pregao"] == "2015-02-27"
    )  # o último antes de D
    depois = universo.universo_em(conn, dias[-1], CADASTRO)
    assert [t["ticker"] for t in depois["sem_identificacao"]] == ["VIVA3"]


def test_codigo_do_fca_entra_pelo_indice_em_d(conn, tmp_path):
    _fca(conn, "fca_cia_aberta_2026_amer.zip")  # v1 entregue em 10/06/2026, AMER3
    dias = _pregoes(date(2026, 5, 4), 40)
    _precos(conn, tmp_path, [_negocio(d, "AMER3", "BRAMERACNOR4") for d in dias])
    universo.gerar(conn, "g")
    antes = universo.universo_em(conn, date(2026, 6, 10), CADASTRO)  # FCA não entregue
    assert antes["universo"] == []
    assert [t["ticker"] for t in antes["sem_identificacao"]] == ["AMER3"]
    depois = universo.universo_em(conn, date(2026, 6, 11), CADASTRO)
    assert depois == {
        "universo": [
            {"ticker": "AMER3", "classe": "STOCK", "regra": "fca:codigo_ativo", "cnpj": AMER,
             "primeiro_pregao": "2026-05-04", "ultimo_pregao": "2026-06-10"}
        ],
        "sem_identificacao": [],
    }  # fmt: skip


def test_indice_em_so_usa_o_entregue_antes_de_d(conn):
    _fca(conn, "fca_cia_aberta_2026_amer.zip")
    assert (
        "AMER3" not in universo.indice_em(conn, date(2026, 6, 10), CADASTRO).registros
    )
    registro = universo.indice_em(conn, date(2026, 6, 11), CADASTRO).registros["AMER3"]
    assert (registro.cnpj, registro.cd_cvm, registro.classe) == (AMER, 20990, "STOCK")


# --- Bordas (FCA sintético no layout oficial, com os cabeçalhos da fixture de 2026) ----------

CAB_ENTREGAS = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;CATEG_DOC;ID_DOC;DT_RECEB;LINK_DOC"
)
CAB_VALORES = (
    "CNPJ_Companhia;Data_Referencia;Versao;ID_Documento;Nome_Empresarial;Valor_Mobiliario;"
    "Sigla_Classe_Acao_Preferencial;Classe_Acao_Preferencial;Codigo_Negociacao;"
    "Composicao_BDR_Unit;Mercado;Sigla_Entidade_Administradora;Entidade_Administradora;"
    "Data_Inicio_Negociacao;Data_Fim_Negociacao;Segmento;Data_Inicio_Listagem;Data_Fim_Listagem"
)
TSTE = "11.111.111/0001-11"


def _fca_sintetico(conn, tmp_path, entregas, valores, ano=2026):
    """entregas: (cnpj, referência, versão, recebimento); valores: dicts sobre uma linha base."""
    base = dict.fromkeys(CAB_VALORES.split(";"), "")
    linhas_v = []
    for v in valores:
        linha = base | {"Nome_Empresarial": "TESTE S.A.", "Mercado": "Bolsa"} | v
        linhas_v.append(";".join(linha[c] for c in CAB_VALORES.split(";")))
    linhas_e = [
        f"{c};{r};{v};TESTE S.A.;099999;FCA;{v};{d};x" for c, r, v, d in entregas
    ]
    caminho = tmp_path / f"fca_cia_aberta_{ano}.zip"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr(
            f"fca_cia_aberta_{ano}.csv",
            "\n".join([CAB_ENTREGAS, *linhas_e]).encode("latin-1"),
        )
        zf.writestr(
            f"fca_cia_aberta_valor_mobiliario_{ano}.csv",
            "\n".join([CAB_VALORES, *linhas_v]).encode("latin-1"),
        )
    carga_cvm.carregar(conn, caminho, tipo="FCA", fonte="sintetico", coleta="c")


CADASTRO_TSTE = pd.DataFrame(
    [{"CNPJ_CIA": TSTE, "DENOM_SOCIAL": "TESTE S.A.", "SIT": "ATIVO", "CD_CVM": "99999",
      "SETOR_ATIV": None, "CONTROLE_ACIONARIO": None}]
)  # fmt: skip


def _valor(**campos):
    return {
        "CNPJ_Companhia": TSTE,
        "Data_Referencia": "2026-01-01",
        "Versao": "1",
    } | campos


def test_bordas_de_inicio_e_fim_de_negociacao(conn, tmp_path):
    _fca_sintetico(
        conn,
        tmp_path,
        [(TSTE, "2026-01-01", "1", "2026-02-01")],
        [
            _valor(Valor_Mobiliario="Ações Ordinárias", Codigo_Negociacao="TSTE3",
                   Data_Inicio_Negociacao="2026-03-10"),
            _valor(Valor_Mobiliario="Ações Preferenciais", Codigo_Negociacao="TSTE4",
                   Data_Inicio_Negociacao="2020-01-02", Data_Fim_Negociacao="2026-03-10"),
            _valor(Valor_Mobiliario="Debêntures", Codigo_Negociacao="TSTE11",
                   Data_Inicio_Negociacao="2020-01-02"),
            _valor(Valor_Mobiliario="Ações Ordinárias", Mercado="Balcão Não Organizado",
                   Codigo_Negociacao="TSTE5", Data_Inicio_Negociacao="2020-01-02"),
            _valor(Valor_Mobiliario="", Codigo_Negociacao="TSTE6", Data_Inicio_Negociacao="2020-01-02"),
            _valor(Valor_Mobiliario="Ações Ordinárias", Codigo_Negociacao="TSTE7"),
        ],
    )  # fmt: skip
    no_dia = universo.companhias_em(conn, date(2026, 3, 10))
    assert no_dia == {
        "companhias": [
            {"cnpj": TSTE, "nome": "TESTE S.A.", "valor_mobiliario": "Ações Preferenciais",
             "codigo": "TSTE4", "inicio_negociacao": "2020-01-02",
             "fim_negociacao": "2026-03-10", "referencia_fca": "2026-01-01"}
        ],
        "sem_prova": [],
    }  # fmt: skip
    seguinte = universo.companhias_em(conn, date(2026, 3, 11))["companhias"]
    assert [(c["codigo"], c["fim_negociacao"]) for c in seguinte] == [("TSTE3", None)]
    assert set(
        universo.indice_em(conn, date(2026, 3, 10), CADASTRO_TSTE).registros
    ) == {"TSTE4"}
    assert set(
        universo.indice_em(conn, date(2026, 3, 11), CADASTRO_TSTE).registros
    ) == {"TSTE3"}


def test_referencia_mais_recente_prevalece_e_sem_linhas_nao_volta_para_a_antiga(
    conn, tmp_path
):
    antiga = _valor(Data_Referencia="2025-01-01", Valor_Mobiliario="Ações Ordinárias",
                    Codigo_Negociacao="VELH3", Data_Inicio_Negociacao="2020-01-02")  # fmt: skip
    _fca_sintetico(
        conn, tmp_path, [(TSTE, "2025-01-01", "1", "2025-02-01")], [antiga], ano=2025
    )
    nova = _valor(Versao="2", Valor_Mobiliario="Ações Ordinárias", Codigo_Negociacao="NOVA3",
                  Data_Inicio_Negociacao="2020-01-02")  # fmt: skip
    _fca_sintetico(
        conn,
        tmp_path,
        [
            (TSTE, "2026-01-01", "1", "2026-02-01"),
            (TSTE, "2026-01-01", "2", "2026-05-01"),
        ],
        [nova],
    )
    entre = date(
        2026, 3, 1
    )  # só a v1 de 2026 entregue, e as linhas guardadas são da v2
    assert universo.companhias_em(conn, entre) == {
        "companhias": [],
        "sem_prova": [{"cnpj": TSTE, "referencia_fca": "2026-01-01"}],
    }
    # o índice em D segue o índice atual e volta à referência de 2025 (BUG-3-24)
    assert set(universo.indice_em(conn, entre, CADASTRO_TSTE).registros) == {"VELH3"}
    assert [
        c["codigo"]
        for c in universo.companhias_em(conn, date(2025, 6, 1))["companhias"]
    ] == ["VELH3"]
    depois = date(2026, 6, 1)
    assert [
        c["codigo"] for c in universo.companhias_em(conn, depois)["companhias"]
    ] == ["NOVA3"]
    registro = universo.indice_em(conn, depois, CADASTRO_TSTE).registros["NOVA3"]
    assert registro.fonte == {"arquivo": "banco único", "data": "2026-06-01"}


def test_janela_de_listagem_nas_bordas(conn, tmp_path):
    dias = _pregoes(date(2024, 1, 2), 80)
    d = dias[-1] + timedelta(days=1)
    janela = dias[-63:]
    linhas = [_negocio(x, "BASE3", "BRBASEACNOR1") for x in dias]
    linhas.append(
        _negocio(dias[-1], "ESTR3", "BRESTRACNOR1")
    )  # estreia no último pregão
    linhas += [_negocio(x, "LIMI3", "BRLIMIACNOR1") for x in dias if x <= janela[0]]
    linhas += [_negocio(x, "ANTE3", "BRANTEACNOR1") for x in dias if x < janela[0]]
    _precos(conn, tmp_path, linhas)
    universo.gerar(conn, "g")
    lido = {t["ticker"]: t for t in universo.tickers_em(conn, d)}
    assert set(lido) == {"BASE3", "ESTR3", "LIMI3"}
    assert lido["LIMI3"] == {
        "ticker": "LIMI3", "isin": "BRLIMIACNOR1", "classe": "STOCK",
        "primeiro_pregao": dias[0].isoformat(), "ultimo_pregao": janela[0].isoformat(),
    }  # fmt: skip


def test_universo_com_fii_sem_pregao_unit_sem_codigo_e_identidade(conn, tmp_path):
    from sentinela.data.referencia.correcoes import ler_identidades_fii

    carga_cvm.carregar(
        conn,
        FIXTURES / "inf_mensal_fii_2023.zip",
        tipo="FII_INFORME",
        fonte="cvm",
        coleta="c",
    )
    (btci,) = [i for i in ler_identidades_fii() if i["ticker"] == "BTCI11"]
    dias = _pregoes(date(2026, 6, 1), 5)
    linhas = [_negocio(x, "UNTS11", "BRUNTSUNT001") for x in dias]
    linhas += [
        _linha(DATA=x.strftime("%Y%m%d"), CODNEG="BTCI11", CODISI=btci["isin"],
               CODBDI="12", ESPECI="CI")
        for x in dias
    ]  # fmt: skip
    _precos(conn, tmp_path, linhas)
    universo.gerar(conn, "g")
    d = dias[-1] + timedelta(days=1)
    sem = universo.universo_em(conn, d, CADASTRO)
    com = universo.universo_em(conn, d, CADASTRO, identidades_fii=[btci])
    assert [t["ticker"] for t in sem["sem_identificacao"]] == ["UNTS11"]
    assert sem["sem_identificacao"][0]["classe"] == "UNIT"
    fiis = {t["ticker"]: t for t in sem["universo"]}
    (vpq,) = [t for t in fiis.values() if t["classe"] == "FII"]
    assert (vpq["primeiro_pregao"], vpq["ultimo_pregao"]) == (
        None,
        None,
    )  # sem pregão guardado
    assert "BTCI11" not in fiis
    lido = universo.universo_backtest(conn, d, CADASTRO, **LIMIARES)
    (fora,) = [t for t in lido["fora"] if t["classe"] == "FII"]
    assert fora["motivo"] == "liquidez não medida: janela incompleta"  # 5 pregões
    (btci11,) = [t for t in com["universo"] if t["ticker"] == "BTCI11"]
    assert (btci11["classe"], btci11["primeiro_pregao"]) == ("FII", dias[0].isoformat())


def test_backtest_usa_o_limiar_do_fii_e_o_motivo_da_abstencao(conn, tmp_path):
    _fca(conn, "fca_cia_aberta_2026_amer.zip")
    carga_cvm.carregar(
        conn,
        FIXTURES / "inf_mensal_fii_2023.zip",
        tipo="FII_INFORME",
        fonte="cvm",
        coleta="c",
    )
    dias = _pregoes(date(2026, 6, 12), 70)
    linhas = [
        _negocio(x, "VPQS11", "BRFVPQCTF015", volume="000000000020000000") for x in dias
    ]
    linhas += [
        _negocio(x, "AMER3", "BRAMERACNOR4", volume="000000000020000000") for x in dias
    ]
    _precos(conn, tmp_path, linhas)  # R$ 200 mil por pregão: passa no FII, não na ação
    universo.gerar(conn, "g")
    lido = universo.universo_backtest(
        conn, dias[-1] + timedelta(days=1), CADASTRO, **LIMIARES
    )
    assert [t["ticker"] for t in lido["elegiveis"]] == ["VPQS11"]
    assert {t["ticker"]: t["motivo"][:25] for t in lido["fora"]}[
        "AMER3"
    ] == "liquidez abaixo do mínimo"


def test_backtest_ticker_sem_negocio_na_janela_coberta_tem_volume_zero(conn, tmp_path):
    _fca(conn, "fca_cia_aberta_2026_amer.zip")
    dias = _pregoes(date(2026, 6, 12), 63)
    _precos(conn, tmp_path, [_negocio(x, "BASE3", "BRBASEACNOR1") for x in dias])
    universo.gerar(conn, "g")
    lido = universo.universo_backtest(
        conn, dias[-1] + timedelta(days=1), CADASTRO, **LIMIARES
    )
    (amer,) = lido["fora"]  # no índice pelo FCA, sem negócio nos 63 pregões cobertos
    assert amer["ticker"] == "AMER3"
    assert amer["motivo"].startswith(
        "liquidez abaixo do mínimo para análise: presença de 0"
    )
    curto = universo.universo_backtest(conn, dias[-2], CADASTRO, **LIMIARES)
    assert [t["motivo"] for t in curto["fora"]] == [
        "liquidez não medida: janela incompleta"
    ]


def test_codigo_em_excecao_do_indice_leva_o_motivo_da_excecao(conn, tmp_path):
    _fca_sintetico(
        conn,
        tmp_path,
        [(TSTE, "2026-01-01", "1", "2026-02-01")],
        [_valor(Valor_Mobiliario="Ações Ordinárias", Codigo_Negociacao="TST3B",
                Data_Inicio_Negociacao="2020-01-02")],
    )  # fmt: skip
    _precos(conn, tmp_path, [_negocio(date(2026, 3, 2), "TST3B", "BRTSTEACNOR1")])
    lido = universo.universo_em(conn, date(2026, 3, 3), CADASTRO_TSTE)
    assert lido["universo"] == []
    assert [(t["ticker"], t["motivo"]) for t in lido["sem_identificacao"]] == [
        ("TST3B", "código fora do formato de ticker")
    ]
