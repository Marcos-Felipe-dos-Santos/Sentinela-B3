"""Tabela de correções de fonte (F2A-19, [CORREÇÕES]): tabelas sintéticas em `tmp_path`, sem rede."""

import pytest

from sentinela.data.referencia.cobertura import cobertura
from sentinela.data.referencia.correcoes import (
    CAMINHO_PADRAO,
    Correcao,
    CorrecaoInvalida,
    ler_correcoes,
    validar_correcoes,
)
from sentinela.data.referencia.montagem import MOTIVO_CORRECAO, montar_indice
from tests.test_referencia import (
    CNPJ_A,
    FONTES,
    _cadastro,
    _cot,
    _fca,
    _informe,
    _sem_fii,
)

CABECALHO = "ticker;cnpj;codigo_na_fonte;motivo;arquivo;coluna;data"
LINHA_CSN = (
    f"TSTC3;{CNPJ_A};4030;código fora do formato;fca_cia_aberta_valor_mobiliario_2026.csv;"
    "Codigo_Negociacao;2026-01-01"
)


def _tabela(tmp_path, *linhas, cabecalho=CABECALHO):
    caminho = tmp_path / "correcoes.csv"
    caminho.write_text("\n".join([cabecalho, *linhas]) + "\n", encoding="utf-8")
    return caminho


def _correcao(**campos):
    base = dict(
        ticker="TSTC3", cnpj=CNPJ_A, codigo_na_fonte="4030", motivo="código fora do formato",
        arquivo="fca_cia_aberta_valor_mobiliario_2026.csv", coluna="Codigo_Negociacao",
        data="2026-01-01",
    )  # fmt: skip
    return Correcao(**{**base, **campos})


def _montar(fca=None, informe=None, cotacoes=(), correcoes=()):
    return montar_indice(
        [(2026, fca if fca is not None else _fca({"Codigo_Negociacao": "4030"}))],
        _cadastro(),
        informe if informe is not None else _sem_fii(),
        list(cotacoes),
        FONTES,
        "2026-10-08",
        correcoes,
    )


# ── aceite ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("campo", ["arquivo", "coluna", "data"])
def test_correcao_sem_evidencia_e_rejeitada(tmp_path, campo):
    valores = dict(zip(CABECALHO.split(";"), LINHA_CSN.split(";"), strict=True))
    valores[campo] = "  "
    caminho = _tabela(tmp_path, ";".join(valores.values()))
    with pytest.raises(CorrecaoInvalida, match=campo):
        ler_correcoes(caminho)
    with pytest.raises(CorrecaoInvalida, match=campo):
        _montar(correcoes=[_correcao(**{campo: ""})])


def test_correcao_aparece_na_proveniencia(tmp_path):
    correcoes = ler_correcoes(_tabela(tmp_path, LINHA_CSN))
    indice = _montar(correcoes=correcoes)
    registro = indice.registros["TSTC3"]
    assert registro.regra == "correcao"
    assert registro.correcao == {
        "ticker": "TSTC3",
        "cnpj": CNPJ_A,
        "codigo_na_fonte": "4030",
        "motivo": "código fora do formato",
        "arquivo": "fca_cia_aberta_valor_mobiliario_2026.csv",
        "coluna": "Codigo_Negociacao",
        "data": "2026-01-01",
    }
    assert registro.fonte == FONTES["fca"]["2026"]
    assert (registro.classe, registro.especie, registro.cd_cvm) == ("STOCK", "ON", 100)
    assert indice.excecoes == []


# ── demais regras ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("campo", ["ticker", "cnpj", "codigo_na_fonte", "motivo"])
def test_correcao_sem_campo_obrigatorio_e_rejeitada(campo):
    with pytest.raises(CorrecaoInvalida, match=campo):
        validar_correcoes([_correcao(**{campo: None})])


def test_correcao_repetida_e_rejeitada():
    with pytest.raises(CorrecaoInvalida, match="repetida"):
        validar_correcoes([_correcao(), _correcao(ticker="TSTD3")])


def test_tabela_sem_coluna_de_evidencia_e_rejeitada(tmp_path):
    caminho = _tabela(
        tmp_path,
        f"TSTC3;{CNPJ_A};4030;motivo",
        cabecalho="ticker;cnpj;codigo_na_fonte;motivo",
    )
    with pytest.raises(CorrecaoInvalida, match="colunas"):
        ler_correcoes(caminho)


def test_linha_curta_sem_as_colunas_de_evidencia_e_rejeitada(tmp_path):
    caminho = _tabela(tmp_path, f"TSTC3;{CNPJ_A};4030;motivo")
    with pytest.raises(CorrecaoInvalida, match="arquivo, coluna, data"):
        ler_correcoes(caminho)


def test_tabela_le_os_campos_sem_espacos(tmp_path):
    linha = ";".join(f" {v} " for v in LINHA_CSN.split(";"))
    assert ler_correcoes(_tabela(tmp_path, linha)) == [_correcao()]


def test_tabela_vazia_nao_corrige_nada(tmp_path):
    assert ler_correcoes(_tabela(tmp_path)) == []
    indice = _montar()
    assert "TSTC3" not in indice.registros
    assert [e.codigo for e in indice.excecoes] == ["4030"]


def test_correcao_so_vale_para_o_cnpj_e_o_codigo_da_evidencia():
    fca = _fca(
        {"Codigo_Negociacao": "4030", "CNPJ_Companhia": "99.999.999/0001-99"},
        {"Codigo_Negociacao": "5050"},
    )
    indice = _montar(fca=fca, correcoes=[_correcao()])
    assert "TSTC3" not in indice.registros
    assert sorted(e.codigo for e in indice.excecoes) == ["4030", "5050"]


def test_fonte_ja_corrigida_dispensa_a_correcao():
    indice = _montar(fca=_fca({"Codigo_Negociacao": "TSTC3"}), correcoes=[_correcao()])
    assert indice.registros["TSTC3"].regra == "fca:codigo_ativo"
    assert indice.registros["TSTC3"].correcao is None


def test_correcao_resolve_isin_repetido_de_fii():
    isin = "BRTSTFCTF001"
    informe = _informe(
        {"CNPJ_Fundo_Classe": "33.333.333/0001-33", "Nome_Fundo_Classe": "ANTIGO"},
        {"CNPJ_Fundo_Classe": "44.444.444/0001-44", "Nome_Fundo_Classe": "NOVO"},
    )
    correcao = _correcao(
        ticker="TSTF11", cnpj="33.333.333/0001-33", codigo_na_fonte=isin,
        arquivo="inf_mensal_fii_geral_2026.csv", coluna="Codigo_ISIN",
    )  # fmt: skip
    indice = _montar(
        fca=_fca().iloc[0:0],
        informe=informe,
        cotacoes=[_cot("TSTF11", codbdi="12", especi="CI", isin=isin)],
        correcoes=[correcao],
    )
    registro = indice.registros["TSTF11"]
    assert (registro.cnpj, registro.regra, registro.classe) == (
        "33.333.333/0001-33",
        "correcao",
        "FII",
    )
    assert [(e.codigo, e.motivo, e.cnpj) for e in indice.excecoes] == [
        ("TSTF11", MOTIVO_CORRECAO, "44.444.444/0001-44")
    ]


def test_sem_correcao_o_isin_repetido_tira_os_dois():
    informe = _informe(
        {"CNPJ_Fundo_Classe": "33.333.333/0001-33"},
        {"CNPJ_Fundo_Classe": "44.444.444/0001-44"},
    )
    indice = _montar(fca=_fca().iloc[0:0], informe=informe)
    assert indice.registros == {}
    assert len(indice.excecoes) == 2


def test_cobertura_conta_a_correcao_de_companhia_como_mapeada():
    fca = _fca({"Codigo_Negociacao": "4030"})
    indice = _montar(fca=fca, correcoes=[_correcao()])
    c = cobertura(indice, [(2026, fca)], _sem_fii())
    assert c["companhias"] == {"codigos_ativos_no_fca": 1, "mapeados": 1}
    assert c["correcoes"] == {"STOCK": ["TSTC3"]}


def test_tabela_versionada_e_valida_e_traz_evidencia():
    correcoes = ler_correcoes(CAMINHO_PADRAO)
    por_ticker = {c.ticker: c for c in correcoes}
    assert por_ticker["CSNA3"].cnpj == "33.042.730/0001-04"
    assert por_ticker["CSNA3"].codigo_na_fonte == "4030"
    assert por_ticker["CSNA3"].coluna == "Codigo_Negociacao"
    assert por_ticker["TRXF11"].cnpj == "28.548.288/0001-52"
    assert por_ticker["TRXF11"].codigo_na_fonte == "BRTRXFCTF003"


# ── correção de espécie (F2B-13; ficha 1.1, decisão 7.10) ─────────────────────

# Como a MGLU3: o FCA diz "Ações Preferenciais" (PNA); a Composição do Capital e a DRE do
# mesmo documento só trazem ON.
EVIDENCIA_ESPECIE = {
    "ticker": "TSTM3",
    "codigo_na_fonte": "TSTM3",
    "motivo": "o FCA classifica a ação como preferencial, e o documento só traz ON",
    "arquivo": (
        "fca_cia_aberta_valor_mobiliario_2026.csv (FCA, versão 1) + "
        "dfp_cia_aberta_composicao_capital_2025.csv e dfp_cia_aberta_DRE_con_2025.csv "
        "(DFP 2025, versão 1)"
    ),
    "coluna": (
        "Valor_Mobiliario (FCA) + QT_ACAO_PREF_CAP_INTEGR = 0 (Composição) + "
        "3.99.01.01 ON (DRE)"
    ),
    "data": "2026-01-01",
    "campo": "especie",
    "valor": "ON",
}


def _fca_preferencial():
    fca = _fca(
        {
            "Codigo_Negociacao": "TSTM3",
            "Valor_Mobiliario": "Ações Preferenciais",
            "Sigla_Classe_Acao_Preferencial": "PNA",
        }
    )
    fca["Sigla_Classe_Acao_Preferencial"] = ["PNA"]
    return fca


def test_correcao_de_especie_com_evidencia():
    indice = _montar(
        fca=_fca_preferencial(), correcoes=[_correcao(**EVIDENCIA_ESPECIE)]
    )
    registro = indice.registros["TSTM3"]
    assert (registro.especie, registro.classe_preferencial) == ("ON", None)
    assert registro.regra == "correcao"
    sem_correcao = _montar(fca=_fca_preferencial()).registros["TSTM3"]
    assert (sem_correcao.especie, sem_correcao.classe_preferencial) == ("PN", "PNA")


@pytest.mark.parametrize(
    "arquivo",
    [
        "dfp_cia_aberta_composicao_capital_2025.csv (DFP 2025, versão 1)",
        "dfp_cia_aberta_DRE_con_2025.csv (DFP 2025, versão 1)",
    ],
)
def test_correcao_de_especie_sem_evidencia_e_rejeitada(tmp_path, arquivo):
    with pytest.raises(CorrecaoInvalida, match="Composição do Capital e DRE"):
        validar_correcoes([_correcao(**{**EVIDENCIA_ESPECIE, "arquivo": arquivo})])
    with pytest.raises(CorrecaoInvalida, match="campo"):
        validar_correcoes([_correcao(**{**EVIDENCIA_ESPECIE, "campo": "setor"})])
    with pytest.raises(CorrecaoInvalida, match="valor"):
        validar_correcoes([_correcao(**{**EVIDENCIA_ESPECIE, "valor": "UNIT"})])


def test_correcao_de_especie_na_proveniencia(tmp_path):
    from sentinela.reports.rastreabilidade import _texto_referencia

    valores = {**EVIDENCIA_ESPECIE, "cnpj": CNPJ_A}
    linha = ";".join(valores[c] for c in (*CABECALHO.split(";"), "campo", "valor"))
    correcoes = ler_correcoes(
        _tabela(tmp_path, linha, cabecalho=CABECALHO + ";campo;valor")
    )
    registro = _montar(fca=_fca_preferencial(), correcoes=correcoes).registros["TSTM3"]
    assert registro.correcao["campo"] == "especie"
    assert registro.correcao["valor"] == "ON"
    texto = _texto_referencia({"regra": registro.regra, "gerado_em": "2026-10-08",
                               "correcao": registro.correcao})  # fmt: skip
    assert "espécie da tabela de correções, não do arquivo da fonte: ON" in texto
    assert "código da tabela" not in texto


@pytest.mark.parametrize(
    "ticker", ["INVALIDO", "tstc3", "TST3", "TSTC333", " TSTC3", "TSTC3\n", "3STC3"]
)
def test_correcao_rejeita_ticker_fora_do_formato_do_indice(ticker):
    from dataclasses import replace

    with pytest.raises(CorrecaoInvalida, match="Ticker inválido"):
        validar_correcoes([replace(_correcao(), ticker=ticker)])


# ── F2A-39: ligação por fonte externa ao arquivo do defeito ([BTG]) ───────────

LIGACAO_B3 = dict(
    ligacao_fonte="B3, GetDetail da companhia (listedCompaniesProxy/CompanyCall)",
    ligacao_campo='cnpj, codeCVM e otherCodes {"code": "BPAC11", "isin": "BRBPACUNT006"}',
    ligacao_data="2026-10-19",
)


def _correcao_unit(**campos):
    return _correcao(
        ticker="TSTU11",
        codigo_na_fonte="000000",
        motivo="unit com o código de negociação zerado no FCA",
        **{**LIGACAO_B3, **campos},
    )


def _fca_unit():
    return _fca(
        {
            "Valor_Mobiliario": "Units",
            "Codigo_Negociacao": "000000",
            "Composicao_BDR_Unit": "1 ON E 2 PNA",
        }
    )


def test_unit_entra_pela_tabela_com_a_evidencia_da_ligacao(tmp_path):
    linha = (
        f"TSTU11;{CNPJ_A};000000;unit com o código de negociação zerado no FCA;"
        "fca_cia_aberta_valor_mobiliario_2026.csv;Codigo_Negociacao;2026-01-01;;;"
        f"{LIGACAO_B3['ligacao_fonte']};{LIGACAO_B3['ligacao_campo']};"
        f"{LIGACAO_B3['ligacao_data']}"
    )
    cabecalho = f"{CABECALHO};campo;valor;ligacao_fonte;ligacao_campo;ligacao_data"
    correcoes = ler_correcoes(_tabela(tmp_path, linha, cabecalho=cabecalho))
    indice = _montar(fca=_fca_unit(), correcoes=correcoes)
    registro = indice.registros["TSTU11"]
    assert (registro.classe, registro.regra) == ("UNIT", "correcao")
    assert registro.acoes_por_unit == {"ON": 1, "PNA": 2}
    assert registro.correcao["ligacao_fonte"] == LIGACAO_B3["ligacao_fonte"]
    assert registro.correcao["ligacao_campo"] == LIGACAO_B3["ligacao_campo"]
    assert registro.correcao["ligacao_data"] == "2026-10-19"
    assert indice.excecoes == []


@pytest.mark.parametrize("campo", ["ligacao_fonte", "ligacao_campo", "ligacao_data"])
def test_ligacao_sem_evidencia_e_rejeitada(campo):
    # Código na fonte sem identidade (só zeros): a ligação não vem do arquivo do defeito, e
    # a evidência dela é obrigatória.
    with pytest.raises(CorrecaoInvalida, match="ligação"):
        validar_correcoes([_correcao_unit(**{campo: ""})])
