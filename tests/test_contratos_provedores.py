"""Contratos dos provedores existentes (F2A-32; ADR-0003, D18): colunas, tipos, unidades e escala.

As fixtures em `tests/fixtures/contratos/` são recortes dos arquivos reais, com a fonte, a data
da coleta e o hash do arquivo original anotados no próprio JSON, e o hash de cada membro do
recorte. O teste remonta o ZIP em `tmp_path` e passa pelo parser do provedor. Sem rede.
Os valores esperados são lidos à mão nas linhas do recorte, nunca calculados pelo código.
"""

import hashlib
import json
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import cvm_fii_provider
import cvm_provider
from cvm_fii_provider import CVMFIIProvider
from cvm_provider import CVMProvider
from sentinela.data.providers import b3_cotahist
from sentinela.data.referencia import fontes

PASTA = Path(__file__).parent / "fixtures" / "contratos"
PETROBRAS = "33.000.167/0001-01"
HGLG = "11.728.688/0001-47"
COLUNAS_INDICE_CVM = {
    "CNPJ_CIA",
    "DT_REFER",
    "VERSAO",
    "CD_CVM",
    "CATEG_DOC",
    "DT_RECEB",
}
COLUNAS_DEMONSTRATIVO = {
    "CNPJ_CIA", "DT_REFER", "VERSAO", "CD_CVM", "GRUPO_DFP", "ESCALA_MOEDA",
    "ORDEM_EXERC", "CD_CONTA", "DS_CONTA", "VL_CONTA",
}  # fmt: skip
COLUNAS_COMPOSICAO = {
    "CNPJ_CIA", "DT_REFER", "VERSAO", "QT_ACAO_ORDIN_CAP_INTEGR", "QT_ACAO_PREF_CAP_INTEGR",
    "QT_ACAO_ORDIN_TESOURO", "QT_ACAO_PREF_TESOURO", "QT_ACAO_TOTAL_TESOURO",
}  # fmt: skip


class _Hoje(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 8)


def _fixture(nome):
    return json.loads((PASTA / nome).read_text(encoding="utf-8"))


def _montar(nome, tmp_path):
    """(ZIP remontado com os membros do recorte, fixture)."""
    fixture = _fixture(nome)
    caminho = tmp_path / fixture["arquivo_original"]
    with zipfile.ZipFile(caminho, "w") as zf:
        for membro, texto in fixture["membros"].items():
            zf.writestr(membro, texto.encode("latin-1"))
    return caminho, fixture


def _csv(fixture, membro):
    from io import StringIO

    return pd.read_csv(StringIO(fixture["membros"][membro]), sep=";", dtype=str)


@pytest.mark.parametrize("nome", sorted(p.name for p in PASTA.glob("*.json")))
def test_fixture_traz_fonte_data_e_hash_e_nao_foi_editada(nome):
    fixture = _fixture(nome)
    assert fixture["fonte"].startswith("https://")
    assert fixture["fonte"].endswith(fixture["arquivo_original"])
    assert fixture["data_coleta"].startswith("2026-")
    assert len(fixture["sha256_original"]) == 64
    assert fixture["recorte"]
    assert set(fixture["sha256_membros"]) == set(fixture["membros"])
    for membro, texto in fixture["membros"].items():
        assert (
            hashlib.sha256(texto.encode("latin-1")).hexdigest()
            == (fixture["sha256_membros"][membro])
        ), membro


# ── CVM: DFP ─────────────────────────────────────────────────────────────────


def test_contrato_dfp(tmp_path, monkeypatch):
    caminho, fixture = _montar("dfp_2025_petrobras.json", tmp_path)
    indice = _csv(fixture, "dfp_cia_aberta_2025.csv")
    assert COLUNAS_INDICE_CVM <= set(indice.columns)
    for tipo in ("DRE_con", "BPA_con", "BPP_con"):
        bruto = _csv(fixture, f"dfp_cia_aberta_{tipo}_2025.csv")
        assert COLUNAS_DEMONSTRATIVO <= set(bruto.columns), tipo
        assert set(bruto["ESCALA_MOEDA"]) == {"MIL"}
        assert set(bruto["ORDEM_EXERC"]) == {"ÚLTIMO", "PENÚLTIMO"}
    assert COLUNAS_COMPOSICAO <= set(
        _csv(fixture, "dfp_cia_aberta_composicao_capital_2025.csv").columns
    )

    provider = CVMProvider(str(tmp_path / "cache"))
    bpa = provider.parsear_demonstrativo(
        caminho, "BPA_con", include_cd_cvm=True, include_versao=True
    )
    assert list(bpa.columns) == [
        "CNPJ_CIA", "DT_REFER", "CD_CONTA", "DS_CONTA", "VL_CONTA", "CD_CVM", "VERSAO",
    ]  # fmt: skip
    # Só o exercício ÚLTIMO, em reais: 1.223.389.000 mil no arquivo.
    assert bpa.set_index("CD_CONTA").loc["1", "VL_CONTA"] == pytest.approx(
        1_223_389_000_000
    )
    assert bpa["VL_CONTA"].dtype == float
    assert int(bpa["CD_CVM"].iloc[0]) == 9512

    # O LPA divulgado (R$ por ação) não leva a escala monetária.
    linhas_399, cc = provider._dados_por_acao(caminho)
    assert set(linhas_399["CD_CONTA"]) >= {"3.99.01.01", "3.99.01.02"}
    assert cvm_provider.lpa_divulgado_por_especie(linhas_399) == {
        "ON": 8.54,
        "PN": 8.54,
    }
    assert int(cc["QT_ACAO_ORDIN_CAP_INTEGR"].iloc[0]) == 7_442_231_382

    monkeypatch.setattr(cvm_provider, "date", _Hoje)
    monkeypatch.setattr(provider, "baixar_dfp", lambda ano: caminho)
    ind = provider.calcular_indicadores(9512, anos=1)[2025]
    assert ind["cnpj"] == PETROBRAS
    assert (ind["cvm_dt_refer"], ind["cvm_versao"]) == ("2025-12-31", "1")
    assert ind["lucro_liquido"] == pytest.approx(110_605_000_000)
    assert ind["lucro_controladores"] == pytest.approx(110_129_000_000)
    assert ind["pl_controladores"] == pytest.approx(417_587_000_000 - 1_801_000_000)
    assert ind["proveniencia"]["data_entrega"] == "2026-03-05"
    assert ind["proveniencia"]["periodo_referencia"] == "2025-12-31"
    assert ind["proveniencia"]["versao"] == "1"


# ── CVM: ITR ─────────────────────────────────────────────────────────────────


def test_contrato_itr(tmp_path):
    caminho, fixture = _montar("itr_2026_petrobras.json", tmp_path)
    indice = _csv(fixture, "itr_cia_aberta_2026.csv")
    assert COLUNAS_INDICE_CVM <= set(indice.columns)
    for tipo in ("DRE_con", "BPA_con", "BPP_con"):
        bruto = _csv(fixture, f"itr_cia_aberta_{tipo}_2026.csv")
        assert COLUNAS_DEMONSTRATIVO <= set(bruto.columns), tipo
        assert set(bruto["ESCALA_MOEDA"]) <= {"MIL", "UNIDADE"}
    assert COLUNAS_COMPOSICAO <= set(
        _csv(fixture, "itr_cia_aberta_composicao_capital_2026.csv").columns
    )

    provider = CVMProvider(str(tmp_path / "cache"))
    entregas = provider._entregas(caminho)
    # 1º trimestre reapresentado: versões 1 e 2, entregues no mesmo dia.
    assert [(e["DT_REFER"], e["VERSAO"], e["DT_RECEB"]) for e in entregas] == [
        ("2026-03-31", "1", "2026-05-11"),
        ("2026-03-31", "2", "2026-05-11"),
        ("2026-06-30", "1", "2026-08-06"),
    ]
    dre = provider.parsear_demonstrativo(caminho, "DRE_con", include_versao=True)
    assert set(dre["VERSAO"]) <= {"1", "2"}
    assert dre["VL_CONTA"].dtype == float


# ── CVM: FCA ─────────────────────────────────────────────────────────────────


def test_contrato_fca(tmp_path):
    caminho, fixture = _montar("fca_2026_petrobras.json", tmp_path)
    assert COLUNAS_INDICE_CVM <= set(_csv(fixture, "fca_cia_aberta_2026.csv").columns)

    valores = fontes._ler_do_zip(caminho, "fca_cia_aberta_valor_mobiliario_2026.csv")
    assert {
        "CNPJ_Companhia", "Data_Referencia", "Versao", "Nome_Empresarial", "Valor_Mobiliario",
        "Sigla_Classe_Acao_Preferencial", "Codigo_Negociacao", "Composicao_BDR_Unit",
        "Mercado", "Data_Fim_Negociacao",
    } <= set(valores.columns)  # fmt: skip
    por_ticker = valores.set_index("Codigo_Negociacao")["Valor_Mobiliario"]
    assert por_ticker["PETR3"] == "Ações Ordinárias"
    assert por_ticker["PETR4"] == "Ações Preferenciais"

    geral = fontes._ler_do_zip(caminho, "fca_cia_aberta_geral_2026.csv")
    assert {"CNPJ_Companhia", "Setor_Atividade", "Especie_Controle_Acionario"} <= set(
        geral.columns
    )
    assert geral["Setor_Atividade"].iloc[0] == "Petróleo e Gás"


# ── Informe Mensal de FII ────────────────────────────────────────────────────


def test_contrato_informe_mensal_fii(tmp_path, monkeypatch):
    caminho, fixture = _montar("inf_mensal_fii_2026_hglg.json", tmp_path)
    geral = _csv(fixture, "inf_mensal_fii_geral_2026.csv")
    assert {
        "CNPJ_Fundo_Classe", "Data_Referencia", "Versao", "Data_Entrega", "Nome_Fundo_Classe",
        "Codigo_ISIN", "Mercado_Negociacao_Bolsa", "Segmento_Atuacao",
    } <= set(geral.columns)  # fmt: skip
    complemento = _csv(fixture, "inf_mensal_fii_complemento_2026.csv")
    assert {
        "CNPJ_Fundo_Classe", "Data_Referencia", "Versao", "Patrimonio_Liquido",
        "Cotas_Emitidas", "Valor_Patrimonial_Cotas", "Percentual_Dividend_Yield_Mes",
    } <= set(complemento.columns)  # fmt: skip
    # DY do mês em fração decimal (0,7%), não em pontos percentuais.
    assert pd.to_numeric(complemento["Percentual_Dividend_Yield_Mes"]).max() < 0.05

    provider = CVMFIIProvider(str(tmp_path / "cache"))
    monkeypatch.setattr(cvm_fii_provider, "date", _Hoje)
    monkeypatch.setattr(provider, "baixar_informe", lambda ano: caminho)
    dados = provider.obter_dados_fii(HGLG)
    assert dados["dt_referencia"] == "2026-08-01"
    assert dados["valor_cota"] == pytest.approx(165.951408188109)
    assert dados["cotas_emitidas"] == pytest.approx(45_601_713)
    assert dados["proveniencia"]["versao"] == "2"
    assert dados["proveniencia"]["data_entrega"] == "2026-09-23"


# ── COTAHIST ─────────────────────────────────────────────────────────────────


def test_contrato_cotahist(tmp_path):
    caminho, fixture = _montar("cotahist_m092026_petrobras.json", tmp_path)
    linhas = fixture["membros"]["COTAHIST_M092026.TXT"].splitlines()
    assert {len(linha) for linha in linhas} == {245}
    assert [linha[:2] for linha in (linhas[0], linhas[-1])] == ["00", "99"]
    assert b3_cotahist.data_de_geracao(caminho) == "2026-09-30"

    cotacoes = b3_cotahist.ler_zip(caminho)
    assert [(c.data.isoformat(), c.codigo_negociacao) for c in cotacoes] == [
        ("2026-09-01", "PETR3"),
        ("2026-09-01", "PETR4"),
        ("2026-09-02", "PETR3"),
        ("2026-09-02", "PETR4"),
    ]
    petr3 = cotacoes[0]
    # PREULT 0000000005237 (centavos), FATCOT 1, VOLTOT 000000056836696800 (centavos).
    assert petr3.fechamento == pytest.approx(52.37)
    assert petr3.fator_cotacao == 1
    assert petr3.volume_financeiro == pytest.approx(568_366_968.00)
    assert petr3.isin == "BRPETRACNOR9"
    assert petr3.tipo_mercado == "010"


def test_contrato_tesouro():
    from sentinela.data.providers import tesouro
    from sentinela.domain.units import RateNominal, RateReal

    fixture = _fixture("tesouro_2026.json")
    titulos = tesouro.ler_csv(
        fixture["membros"]["precotaxatesourodireto.csv"], as_of=date(2026, 10, 19)
    )
    por_nome = {titulo.nome: titulo for titulo in titulos}
    assert len(titulos) == 4
    real = por_nome["Tesouro IPCA+ com Juros Semestrais"]
    assert real.tipo == "NTN-B"
    assert real.data_base == date(2026, 10, 15)
    assert real.vencimento == date(2035, 5, 15)
    assert real.taxa_aplicacao == RateReal(0.0682)
    assert real.taxa_resgate == RateReal(0.0694)
    assert por_nome["Tesouro IPCA+"].taxa_aplicacao == RateReal(0.0673)
    assert por_nome["Tesouro Prefixado"].taxa_aplicacao == RateNominal(0.1264)
    assert por_nome[
        "Tesouro Prefixado com Juros Semestrais"
    ].taxa_resgate == RateNominal(0.1303)


# ── B3: relação de proventos em dinheiro (F2B-31) ───────────────────────────


def _b3_obter(fixture):
    from sentinela.data.providers import b3_proventos

    por_url = {
        b3_proventos.url(
            "GetDetail", {"codeCVM": "8133", "language": "pt-br"}
        ): "GetDetail.json",
        fixture["fonte"]: "GetListedCashDividends.json",
        b3_proventos.url(
            "GetListedSupplementCompany",
            {"issuingCompany": "LREN", "language": "pt-br"},
        ): "GetListedSupplementCompany.json",
    }

    def obter(endereco):
        nome = por_url[endereco]
        return json.loads(fixture["membros"][nome]), {"url": endereco}

    return obter


def test_contrato_proventos_b3():
    from datetime import UTC, datetime

    from sentinela.data import proventos_b3
    from sentinela.data.providers import b3_proventos

    fixture = _fixture("b3_proventos_lren_2026.json")
    relacao = b3_proventos.coletar(
        8133, datetime(2026, 10, 20, 20, 40, tzinfo=UTC), _b3_obter(fixture)
    )
    assert (relacao.nome_pregao, relacao.emissor) == ("LOJAS RENNER", "LREN")
    assert relacao.total == len(relacao.registros) == 99
    campos = {
        "typeStock",
        "corporateAction",
        "valueCash",
        "lastDatePriorEx",
        "dateApproval",
        "quotedPerShares",
    }
    assert all(campos <= set(r) for r in relacao.registros)
    assert {r["corporateAction"] for r in relacao.registros} == {
        "DIVIDENDO",
        "JRS CAP PROPRIO",
    }
    assert {e["label"] for e in relacao.eventos_acoes} >= {
        "BONIFICACAO",
        "DESDOBRAMENTO",
    }
    # os proventos recentes do complemento (por ISIN) estão todos na relação pelo nome
    assert {e["isinCode"] for e in relacao.dinheiro_complemento} == {"BRLRENACNOR1"}
    assert len(relacao.dinheiro_complemento) >= 4
    # Ficha Bazin 1.0, §5: LREN3, preço COTAHIST de 30/09/2026 (R$ 11,60), as_of 19/10/2026.
    serie = proventos_b3.serie_12_meses(
        relacao.registros,
        total=relacao.total,
        referencia=date(2026, 9, 30),
        dia_as_of=date(2026, 10, 19),
        especie="ON",
        eventos_acoes=relacao.eventos_acoes,
        dinheiro_complemento=relacao.dinheiro_complemento,
    )
    assert [(e["data_com"], e["natureza"], e["valor"]) for e in serie["eventos"]] == [
        ("2025-12-11", "jcp", 0.227784),
        ("2026-03-24", "jcp", 0.222698),
        ("2026-06-23", "jcp", 0.229299),
        ("2026-09-22", "jcp", 0.240666),
    ]
    assert serie["d_bruto_12m"] == pytest.approx(0.920447, abs=1e-12)
    assert serie["d_bruto_12m"] / 11.60 == pytest.approx(0.07934887931034, abs=1e-10)
    assert serie["d_bruto_12m"] / 0.06 == pytest.approx(15.340783333333, abs=1e-6)
    # a mesma soma da conferência do yfinance da ficha: nenhum aviso
    assert (
        proventos_b3.conferencia_yfinance(
            serie,
            {
                "2025-12-12": 0.227784,
                "2026-03-25": 0.222698,
                "2026-06-24": 0.229299,
                "2026-09-23": 0.240666,
            },
        )
        == []
    )


def test_contrato_fundos_b3():
    # F2B-2 (ficha FII 1.1, §3a): a resposta real do HGLG11 tem o fundo, os rendimentos
    # por ISIN e mês, e o desdobramento de 2018 (fator 900) nos eventos de cota.
    from datetime import UTC, datetime

    from sentinela.data import fii_elegibilidade
    from sentinela.data.providers import b3_fundos

    fixture = _fixture("b3_fundos_hglg_2026.json")
    corpo = fixture["membros"]["GetListedSupplementFunds"]
    endereco = b3_fundos.url("11.728.688/0001-47", "HGLG11")
    assert endereco == fixture["fonte"]
    coleta = b3_fundos.coletar(
        "11.728.688/0001-47",
        "HGLG11",
        datetime(2026, 10, 21, 12, 41, tzinfo=UTC),
        lambda u: (json.loads(corpo), {"url": u}),
    )
    resposta = coleta["resposta"]
    assert coleta["codigo"] == "HGLG"
    assert fii_elegibilidade.resposta_b3_valida(resposta, "HGLG")
    assert {"rate", "relatedTo", "isinCode", "label", "lastDatePrior"} <= set(
        resposta["cashDividends"][0]
    )
    assert [
        (e["label"], e["lastDatePrior"], e["factor"])
        for e in resposta["stockDividends"]
    ] == [("DESDOBRAMENTO", "17/04/2018", "900,00000000000")]
    # Ficha FII 1.1, §3a: setembro/2026, R$ 1,17 por cota contra R$ 1,170289 do Informe.
    assert (
        fii_elegibilidade.conferencia_b3(
            {"2026-09": 1.170289}, resposta["cashDividends"], "BRHGLGCTF004"
        )
        == []
    )


def test_contrato_ifdata_com_proveniencia(tmp_path, monkeypatch):
    # Recorte público do controle BB, F2A-16, fontes-fase2a §5. Unidade: razão.
    from datetime import UTC, datetime

    from sentinela.data import proveniencia
    from sentinela.data.providers import ifdata
    from tests.regressao.test_bug_2a_19_ifdata_sem_proveniencia import _get_falso

    monkeypatch.setattr(ifdata.requests, "get", _get_falso)
    capital = ifdata.IFDataProvider(str(tmp_path)).capital(
        "00.000.000/0001-91",
        date(2026, 10, 13),
        as_of=datetime(2026, 10, 13, 12, tzinfo=UTC),
    )
    assert capital.codinst == "C0080329"
    assert capital.basileia == pytest.approx(0.151297835513664)
    assert len(capital.proveniencia) == 2
    for registro in capital.proveniencia:
        assert registro["documento"] == "IF.data"
        assert registro["periodo_referencia"] == "202609"
        assert registro["data_entrega"] is None
        assert (
            registro["motivo_sem_entrega"] == proveniencia.MOTIVO_SEM_ENTREGA_NA_FONTE
        )
        assert registro["versao"] is None
        assert registro["fonte"].startswith(ifdata.URL_BASE)
        caminho = registro["fonte"].removeprefix(ifdata.URL_BASE + "/")
        arquivo = tmp_path / (hashlib.sha256(caminho.encode()).hexdigest() + ".json")
        assert (
            registro["hash_sha256"] == hashlib.sha256(arquivo.read_bytes()).hexdigest()
        )
        assert registro["data_coleta"] == proveniencia.data_da_coleta(arquivo)
