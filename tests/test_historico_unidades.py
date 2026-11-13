"""F3-3d: unidades do motor histórico (`sentinela.services.historico`) e da remontagem.

Complementa o [e2e] de `test_servico_historico.py` nas bordas de cada etapa trocada.
"""

import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime
from unittest.mock import Mock

import pandas as pd
import pytest
from test_carga_cvm import CIA, DFP, FII, ITR
from test_servico_historico import CADASTRO, ISIN
from test_universo_pit import _negocio, _precos, _pregoes

import config
from sentinela.data.pit import carga_cvm, leitura, remontagem
from sentinela.data.store import migracoes
from sentinela.services import analyze_asset, historico

D = datetime(2020, 3, 2, 15, tzinfo=UTC)


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _motor(conn, tmp_path, **kw):
    return historico.MotorHistorico(conn, D, tmp_path / "pit", CADASTRO, **kw)


# --- remontagem: leiaute oficial ---------------------------------------------------------------


def test_cabecalhos_e_grupos_iguais_aos_do_arquivo_oficial():
    vistos = 0
    for original in (ITR, DFP):
        with zipfile.ZipFile(original) as z:
            for nome in z.namelist():
                dem = nome.split("_aberta_", 1)[1].rsplit("_", 1)[0]
                if dem.rsplit("_", 1)[-1] not in ("con", "ind"):
                    continue
                linhas = z.read(nome).decode("latin-1").splitlines()
                assert remontagem._cabecalho(dem) == linhas[0].split(";"), nome
                if len(linhas) > 1:
                    grupo = linhas[1].split(";")[5]
                    assert remontagem._grupo(dem) == grupo, nome
                vistos += 1
    assert vistos >= 28
    assert remontagem._grupo("DFC_MD_con") == (
        "DF Consolidado - Demonstração do Fluxo de Caixa (Método Direto)"
    )


@pytest.mark.parametrize(
    ("valor", "texto"),
    [(None, ""), (6767982.0, "6767982.0000000000"), (-0.5, "-0.5000000000")],
)
def test_numero_como_o_arquivo(valor, texto):
    assert remontagem._numero(valor) == texto


def test_csv_latin1_com_ponto_e_virgula_e_campos_a_mais_ignorados():
    bruto = remontagem._csv(["A", "B"], [{"A": "ação", "B": 1, "C": "x"}])
    assert bruto == "A;B\nação;1\n".encode("latin-1")


def test_composicao_csv_vazio_e_nan():
    linha = {"CNPJ_CIA": "1", "DT_REFER": "2020", "VERSAO": "2", "DENOM_CIA": "N",
             "QT_ACAO_ORDIN_CAP_INTEGR": 10.0, "QT_ACAO_PREF_CAP_INTEGR": float("nan"),
             "QT_ACAO_TOTAL_CAP_INTEGR": None}  # fmt: skip
    saida = remontagem._composicao_csv(linha)
    assert saida["QT_ACAO_ORDIN_CAP_INTEGR"] == "10"
    assert (
        saida["QT_ACAO_PREF_CAP_INTEGR"] == ""
        and saida["QT_ACAO_TOTAL_CAP_INTEGR"] == ""
    )
    assert saida["QT_ACAO_TOTAL_TESOURO"] == "" and saida["VERSAO"] == "2"


def test_composicao_so_no_ano_que_a_tem(conn, tmp_path):
    carga_cvm.carregar(
        conn, ITR, tipo="ITR", fonte="cvm", coleta="2026-11-11T12:00:00+00:00"
    )
    assert remontagem._tem_composicao(conn, "ITR", 2020)
    assert not remontagem._tem_composicao(conn, "ITR", 2019)
    assert not remontagem._tem_composicao(conn, "DFP", 2020)
    antes = datetime(
        2020, 1, 2, 15, tzinfo=UTC
    )  # nenhuma entrega ainda, mas o ano a tem
    caminho, _ = remontagem.zip_cia_em(conn, "ITR", 2020, antes, tmp_path)
    with zipfile.ZipFile(caminho) as z:
        assert "itr_cia_aberta_composicao_capital_2020.csv" in z.namelist()
        assert (
            len(z.read("itr_cia_aberta_composicao_capital_2020.csv").splitlines()) == 1
        )


def test_informe_exploratorio_e_ano_sem_linhas(conn, tmp_path):
    carga_cvm.carregar(conn, FII, tipo="FII_INFORME", fonte="cvm", coleta="c")
    vazio = remontagem.zip_informe_em(conn, 2010, D, tmp_path / "a")
    with zipfile.ZipFile(vazio) as z:
        assert z.namelist() == []
    hoje = datetime(2026, 11, 12, 15, tzinfo=UTC)
    estrito = remontagem.zip_informe_em(conn, 2023, hoje, tmp_path / "b")
    explorado = remontagem.zip_informe_em(
        conn, 2023, hoje, tmp_path / "c", modo=leitura.EXPLORATORIO
    )
    with zipfile.ZipFile(estrito) as a, zipfile.ZipFile(explorado) as b:
        assert sorted(a.namelist()) == sorted(b.namelist()) == [
            "inf_mensal_fii_ativo_passivo_2023.csv", "inf_mensal_fii_complemento_2023.csv",
            "inf_mensal_fii_geral_2023.csv",
        ]  # fmt: skip


# --- motor histórico ------------------------------------------------------------------------


def test_dia_local_exige_fuso():
    assert historico.dia_local(datetime(2020, 3, 2, 2, 59, tzinfo=UTC)) == date(
        2020, 3, 1
    )
    with pytest.raises(ValueError, match="^as_of exige fuso horário$"):
        historico.dia_local(datetime(2020, 3, 2))  # noqa: DTZ001


def test_construcao_sem_fonte_corrente(conn, tmp_path):
    motor = _motor(conn, tmp_path)
    assert motor.dia == date(2020, 3, 2) and motor.modo == leitura.ESTRITO
    for nome in (
        "brapi",
        "ifdata",
        "cotahist",
        "b3_proventos",
        "b3_fundos",
        "database",
    ):
        assert getattr(motor, nome) is None
    assert motor.cvm.cache_dir == tmp_path / "pit" / "cache"
    assert motor.cvm_fii.cache_dir == tmp_path / "pit" / "cache_fii"
    assert motor.cvm.recorte_em(D) is motor.cvm and motor.cvm.motivos == {}
    assert motor.asset_classifier is not None
    assert motor._buscar_brapi("X", {}) is False
    assert motor._aplicar_cache_fundamentos("X", {}) is False
    assert motor._salvar_cache_se_valido("X", {}) is None


def test_provedores_lem_os_zips_remontados(conn, tmp_path):
    carga_cvm.carregar(conn, ITR, tipo="ITR", fonte="cvm", coleta="c")
    carga_cvm.carregar(conn, FII, tipo="FII_INFORME", fonte="cvm", coleta="c")
    hoje = datetime(2026, 11, 12, 15, tzinfo=UTC)
    motor = historico.MotorHistorico(conn, hoje, tmp_path / "pit", CADASTRO)
    itr = motor.cvm.baixar_itr(2020)
    assert itr == tmp_path / "pit" / "itr" / "itr_cia_aberta_2020.zip"
    assert motor.cvm.baixar_dfp(2019).parent == tmp_path / "pit" / "dfp"
    informe = motor.cvm_fii.baixar_informe(2023)
    assert informe == tmp_path / "pit" / "fii" / "inf_mensal_fii_2023.zip"
    carga_cvm.carregar(conn, DFP, tipo="DFP", fonte="cvm", coleta="c")
    entre = datetime(2020, 2, 21, 15, tzinfo=UTC)  # versão 1 da DFP entregue; a 2, não
    cedo = historico.MotorHistorico(conn, entre, tmp_path / "c", CADASTRO)
    cedo.cvm.baixar_dfp(2019)
    assert cedo.cvm.motivos == {(CIA, "2019-12-31"): leitura.MOTIVO_ENTREGA_POSTERIOR}


def _com_precos(conn, tmp_path, codigo="AMER3", quantos=70):
    dias = _pregoes(date(2019, 11, 1), quantos)
    _precos(conn, tmp_path, [_negocio(d, codigo, ISIN) for d in dias]
            + [_negocio(d, "OUTR3", "BROUTRACNOR1") for d in dias])  # fmt: skip
    return dias


def test_preco_e_historico_do_ultimo_pregao_antes_de_d(conn, tmp_path):
    dias = _com_precos(conn, tmp_path)
    motor = _motor(conn, tmp_path)
    dados = {}
    assert motor._buscar_yfinance("AMER3", dados) is True
    assert dados["preco_atual"] == pytest.approx(123.45)
    assert dados["data_preco"] == dias[-1].isoformat()
    assert dados["fonte_preco"] == historico.FONTE_PRECO
    assert list(dados["fechamentos_brutos"]) == [d.isoformat() for d in dias]
    historico_df = dados["historico"]
    assert list(historico_df.columns) == ["Close"] and len(historico_df) == len(dias)
    assert historico_df.index[-1] == pd.Timestamp(dias[-1])
    assert "riscos_dados" not in dados


def test_sem_pregao_ou_sem_isin(conn, tmp_path):
    motor = _motor(conn, tmp_path)
    dados = {}
    assert motor._buscar_yfinance("AMER3", dados) is False
    assert dados["riscos_dados"] == [f"{historico.MOTIVO_SEM_PRECO} (AMER3)"]
    assert "preco_atual" not in dados


def test_serie_ajustada_com_bloqueio_fica_so_com_o_trecho_final(
    conn, tmp_path, monkeypatch
):
    _com_precos(conn, tmp_path)
    serie = [{"data": "2020-01-02", "ajustado": None}, {"data": "2020-01-03", "ajustado": 1.0},
             {"data": "2020-01-06", "ajustado": 2.0}]  # fmt: skip
    chamada = Mock(return_value={"serie": serie, "motivo": "sem prova"})
    monkeypatch.setattr(historico.serie_ajustada, "serie_do_banco", chamada)
    dados = {}
    _motor(conn, tmp_path)._buscar_yfinance("AMER3", dados)
    assert list(dados["historico"]["Close"]) == [1.0, 2.0]
    assert dados["riscos_dados"] == ["série ajustada indisponível: sem prova"]
    args = chamada.call_args.args
    assert args[1:] == (
        "AMER3",
        "AMER",
        date(2020, 3, 2),
        historico.PREGOES_DO_HISTORICO,
    )
    chamada.return_value = {"serie": [{"data": "2020-01-02", "ajustado": None}]}
    dados = {}
    _motor(conn, tmp_path)._buscar_yfinance("AMER3", dados)
    assert dados["historico"].empty and "riscos_dados" not in dados


def test_liquidez_pelos_pregoes_antes_de_d(conn, tmp_path):
    _com_precos(conn, tmp_path, quantos=70)
    motor = _motor(conn, tmp_path)
    dados = {}
    motor._buscar_liquidez("AMER3", dados)
    assert dados["liquidez"]["data_final"] == "2020-02-06"  # o último dos 70 pregões
    assert dados["liquidez"]["janelas"]["63"]["pregoes"] == 63
    assert dados["liquidez"]["janelas"]["63"]["volume_mediano"] == 1_000_000.0
    dados = {}
    motor._buscar_liquidez("NADA3", dados)
    assert "abstencao" in dados["liquidez"]


def test_ifdata_so_avisa_banco(conn, tmp_path):
    motor = _motor(conn, tmp_path)
    banco, empresa = {"modelo_bpp": "banco"}, {"modelo_bpp": "empresa"}
    motor._buscar_ifdata(banco, as_of=D)
    motor._buscar_ifdata(empresa, as_of=D)
    assert (
        banco["riscos_dados"] == [historico.RISCO_IFDATA]
        and "riscos_dados" not in empresa
    )


@pytest.mark.parametrize(
    ("dados", "esperado"),
    [({"classe_ativo": "FII"}, None),
     ({"classe_ativo": "STOCK", "modelo_bpp": "banco"}, "fora do escopo do Bazin: modelo banco"),
     ({"classe_ativo": "UNIT"}, "modelo empresa não demonstrado no BPP consolidado")],
)  # fmt: skip
def test_proventos_com_o_escopo_da_cascata(conn, tmp_path, dados, esperado):
    _motor(conn, tmp_path)._buscar_proventos_b3("AMER3", dados)
    assert (dados.get("proventos_b3") or {}).get("abstencao") == esperado


def test_proventos_pelo_leitor_historico(conn, tmp_path, monkeypatch):
    sem_coleta = historico.b3_proventos.MOTIVO_PROVENTO_SEM_COLETA
    lido = Mock(return_value={"abstencao": sem_coleta})
    monkeypatch.setattr(historico.b3_proventos, "proventos_ate", lido)
    motor = _motor(conn, tmp_path)
    dados = {"classe_ativo": "STOCK", "modelo_bpp": "empresa"}
    motor._buscar_proventos_b3("AMER3", dados)
    assert lido.call_args.args == (conn, "AMER", date(2020, 3, 2))
    assert dados["proventos_b3"] == {"abstencao": sem_coleta}
    registros = {"proventos": [{"valor": 1.0}], "sem_prova": []}
    lido.return_value = registros
    motor._buscar_proventos_b3("AMER3", dados)
    assert dados["proventos_b3"] == {
        "abstencao": historico.MOTIVO_PROVENTOS_MONTAGEM, "historicos": registros
    }  # fmt: skip


def test_taxa_real_do_banco_do_motor(conn, tmp_path, monkeypatch):
    chamada = Mock(return_value={"abstencao": "sem linha"})
    monkeypatch.setattr(historico.macro, "registro_do_banco", chamada)
    motor = _motor(conn, tmp_path)
    dados = {"janela_contabil_cvm": (date(2019, 1, 1), date(2019, 12, 31))}
    motor._buscar_taxa_real(dados, as_of=D)
    assert dados["taxa_real"] == {"abstencao": "sem linha"}
    assert chamada.call_args.args == (conn, D, (date(2019, 1, 1), date(2019, 12, 31)))
    chamada.side_effect = sqlite3.OperationalError("no such table: series_macro")
    motor._buscar_taxa_real(dados, as_of=D)
    assert dados["taxa_real"] == {
        "abstencao": "series_macro indisponível: no such table: series_macro"
    }


def test_ipca_das_janelas_abstem_sem_apagar_o_existente(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(
        historico.MarketEngine, "_contexto_janelas", lambda self, d, i, **k: None
    )
    motor = _motor(conn, tmp_path)
    com_serie = {"serie_cvm": {"exercicios": [{}] * 5}}
    motor._contexto_janelas(com_serie, D)
    assert com_serie["ipca_serie"] == {
        "abstencao": f"IPCA do SIDRA: {historico.MOTIVO_FONTE_CORRENTE}"
    }
    for quantos in (0, 4, 6):  # a cascata só pede o IPCA com os cinco exercícios
        outro = {"serie_cvm": {"exercicios": [{}] * quantos}}
        motor._contexto_janelas(outro, D)
        assert "ipca_serie" not in outro
    ja = {"serie_cvm": {"exercicios": [{}] * 5}, "ipca_serie": {"valor": 1}}
    motor._contexto_janelas(ja, D)
    assert ja["ipca_serie"] == {"valor": 1}


def test_riscos_dos_documentos_fora_e_aviso_do_exploratorio(
    conn, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        historico.MarketEngine, "buscar_dados_ticker",
        lambda self, t, as_of=None: {"cnpj": "1", "riscos_dados": []},
    )  # fmt: skip
    motor = _motor(conn, tmp_path, modo=leitura.EXPLORATORIO)
    motor.cvm.motivos = {
        ("2", "2019-12-31"): "x",
        ("1", "2019-12-31"): "y",
        ("1", "2018-12-31"): "z",
    }
    dados = motor.buscar_dados_ticker_em("AMER3", D)
    assert dados["modo_historico"] == leitura.EXPLORATORIO
    assert dados["riscos_dados"] == [
        leitura.AVISO_EXPLORATORIO,
        "documento da CVM de 2018-12-31 fora da leitura: z",
        "documento da CVM de 2019-12-31 fora da leitura: y",
    ]
    monkeypatch.setattr(
        historico.MarketEngine, "buscar_dados_ticker", lambda self, t, as_of=None: None
    )
    assert motor.buscar_dados_ticker_em("AMER3", D) is None


def test_motor_do_banco_com_e_sem_cadastro(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(historico, "DIRETORIO", tmp_path / "h")
    monkeypatch.setattr(historico, "CADASTRO", tmp_path / "nao.csv")
    motor = historico.motor_do_banco(conn, D)
    assert motor.cvm.cache_dir == tmp_path / "h" / "2020-03-02" / "cache"
    assert motor.conn is conn
    assert list(motor.referencia._cadastro.columns) == [
        "CNPJ_CIA", "DENOM_SOCIAL", "SIT", "CD_CVM", "SETOR_ATIV", "CONTROLE_ACIONARIO"
    ]  # fmt: skip
    assert motor.referencia._cadastro.empty
    cad = tmp_path / "cad.csv"
    cad.write_text(
        "CNPJ_CIA;CD_CVM;DENOM_SOCIAL\n1;020990;CONSTRUÇÃO S.A.\n", encoding="latin-1"
    )
    monkeypatch.setattr(historico, "CADASTRO", cad)
    lido = historico.motor_do_banco(conn, D).referencia._cadastro.iloc[0]
    assert (lido["CD_CVM"], lido["DENOM_SOCIAL"]) == ("020990", "CONSTRUÇÃO S.A.")


def test_servico_abre_o_banco_pela_conexao_da_serie_macro(conn, tmp_path, monkeypatch):
    aberto = sqlite3.connect(":memory:")
    monkeypatch.setattr(config, "_conexao_series_macro", lambda: aberto)
    criado = {}

    def fabrica(banco, as_of):
        criado["banco"], criado["as_of"] = banco, as_of
        motor = Mock()
        motor.buscar_dados_ticker_em.return_value = None
        motor.buscar_dados_ticker.return_value = None
        return motor

    monkeypatch.setattr(historico, "motor_do_banco", fabrica)
    servico = analyze_asset.AnalysisService(
        Mock(), Mock(), Mock(), Mock(), hoje=date(2026, 11, 12), conexao_resultados=conn
    )
    r = servico.analisar("AMER3", D, use_ai=False)
    assert criado == {"banco": aberto, "as_of": D} and r.error == "DADOS INSUFICIENTES"
    with pytest.raises(sqlite3.ProgrammingError):
        aberto.execute("SELECT 1")  # fechado depois da análise


def test_liquidez_ticker_ausente_marca_cobertura(conn, tmp_path):
    _com_precos(conn, tmp_path, quantos=40)  # menos que os 63 pregões da janela
    dados = {}
    _motor(conn, tmp_path)._buscar_liquidez("NADA3", dados)
    assert (
        dados["liquidez"]["incompleta"] is True
        and dados["liquidez"]["meses_ausentes"] == []
    )
    cheio = sqlite3.connect(":memory:")
    migracoes.aplicar(cheio)
    _com_precos(cheio, tmp_path, quantos=70)
    dados = {}
    _motor(cheio, tmp_path)._buscar_liquidez("NADA3", dados)
    assert dados["liquidez"]["incompleta"] is False
    cheio.close()


def test_complemento_do_fundo_abstem_so_para_fii_com_cnpj(conn, tmp_path, monkeypatch):
    cascata = Mock(return_value=None)
    monkeypatch.setattr(historico.MarketEngine, "_buscar_rendimento_fii", cascata)
    motor = _motor(conn, tmp_path)
    monkeypatch.setattr(
        motor, "_is_fii_ticker", lambda t, d: d.get("classe_ativo") == "FII"
    )
    fii, sem_cnpj, acao = {"classe_ativo": "FII", "cnpj": "1"}, {"classe_ativo": "FII"}, {
        "classe_ativo": "STOCK", "cnpj": "2"}  # fmt: skip
    for dados in (fii, sem_cnpj, acao):
        motor._buscar_rendimento_fii("X", dados, as_of=D)
    assert fii["b3_fundo"] == {
        "abstencao": f"complemento da B3 do fundo: {historico.MOTIVO_FONTE_CORRENTE}"
    }
    primeira = cascata.call_args_list[0]
    assert primeira.args == ("X", fii) and primeira.kwargs == {"as_of": D}
    assert "b3_fundo" not in sem_cnpj and "b3_fundo" not in acao


def test_zip_remontado_uma_vez_por_documento_e_ano(conn, tmp_path, monkeypatch):
    chamada = Mock(return_value=(tmp_path / "z.zip", {("1", "2019-12-31"): "m"}))
    monkeypatch.setattr(historico.remontagem, "zip_cia_em", chamada)
    motor = _motor(conn, tmp_path)
    assert (
        motor.cvm.baixar_dfp(2019) == motor.cvm.baixar_dfp(2019) == tmp_path / "z.zip"
    )
    motor.cvm.baixar_itr(2019)
    assert [c.args[1:3] for c in chamada.call_args_list] == [
        ("DFP", 2019),
        ("ITR", 2019),
    ]
    assert motor.cvm.motivos == {("1", "2019-12-31"): "m"}


def test_aviso_quando_o_codigo_nao_negociou_no_ultimo_pregao(conn, tmp_path):
    dias = _pregoes(date(2019, 11, 1), 70)
    _precos(conn, tmp_path, [_negocio(d, "AMER3", ISIN) for d in dias[:-3]]
            + [_negocio(d, "OUTR3", "BROUTRACNOR1") for d in dias])  # fmt: skip
    dados = {}
    _motor(conn, tmp_path)._buscar_yfinance("AMER3", dados)
    assert dados["data_preco"] == dias[-4].isoformat()
    assert dados["riscos_dados"] == [
        (
            f"último negócio de AMER3 em {dias[-4].isoformat()}, antes do último pregão "
            f"anterior à data ({dias[-1].isoformat()})"
        )
    ]
    assert historico.b3_cotahist.ultimo_pregao_antes(conn, dias[0]) is None
    assert historico.b3_cotahist.ultimo_pregao_antes(conn, dias[1]) == dias[0]
    with pytest.raises(
        TypeError,
        match=r"^ultimo_pregao_antes recebe o dia local de D \(date\), não um instante$",
    ):
        historico.b3_cotahist.ultimo_pregao_antes(conn, D)
    so = historico.b3_cotahist.cotacoes_do_codigo_ate(
        conn, "OUTR3", date(2020, 3, 2), 5
    )
    assert {c.codigo_negociacao for c in so} == {"OUTR3"} and len(so) == 5


def test_ia_desligada_na_data_passada(conn, tmp_path):
    ia = Mock()
    motor = Mock()
    motor.buscar_dados_ticker.return_value = {
        "ticker": "AMER3",
        "classe_ativo": "STOCK",
    }
    valuation = Mock()
    valuation.processar.return_value = {"lentes": {}}
    tecnico = Mock()
    tecnico.calcular_indicadores.return_value = {}
    servico = analyze_asset.AnalysisService(
        Mock(), valuation, Mock(), tecnico, None, ia, hoje=date(2026, 11, 12),
        conexao_resultados=conn, motor_historico=lambda as_of: motor,
    )  # fmt: skip
    servico.analisar("AMER3", D, use_ai=True)
    ia.analisar.assert_not_called()
