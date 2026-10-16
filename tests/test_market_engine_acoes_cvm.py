"""LPA, VPA, P/L e P/VP pela Composição do Capital da CVM (F2A-3, E-1): dados sintéticos, sem rede.

Colunas e contas pelo layout da DFP (CVM): `QT_ACAO_*` da Composição do Capital; 3.11.01
(lucro atribuído à controladora), 2.03 e 2.03.09 (PL e não controladores) e 3.99.01.xx (LPA
básico por espécie, em R$ por ação).
"""

import io
import zipfile

import pandas as pd
import pytest

from cvm_provider import CVMProvider
from sentinela.data.acoes_cvm import (
    MOTIVO_CLASSES_PREFERENCIAIS,
    MOTIVO_DOCUMENTO_DIFERENTE,
    MOTIVO_ESCALA,
    MOTIVO_LINHAS_CONFLITANTES,
    MOTIVO_ROE_PL,
    MOTIVO_SEM_COMPOSICAO,
    MOTIVO_SINAL_CONSOLIDADO,
    MOTIVO_SINAL_CONTROLADORES,
    MOTIVO_SINAL_NAO_CONFERIVEL,
    MOTIVO_UNIT,
    NOTA_RECALCULADO,
    NOTA_SINAL_CONSOLIDADO,
    Composicao,
)
from sentinela.data.controladores import MOTIVO_LUCRO_NAO_SEPARADO
from tests.test_market_engine import FakeCVM, _engine, _historico
from tests.test_market_engine_referencia import FakeReferencia, _indice, _registro

PRECO = 20.0
CNPJ = "11.111.111/0001-11"


def _composicao(
    on=700.0, pn=400.0, tes_on=60.0, tes_pn=40.0, dt="2025-12-31", versao="1"
):
    return Composicao(
        on=on, pn=pn, tesouraria_on=tes_on, tesouraria_pn=tes_pn,
        tesouraria_total=tes_on + tes_pn, dt_refer=dt, versao=versao,
    )  # fmt: skip


def _ind(**campos):
    base = {
        "patrimonio_liquido": 12_000.0, "lucro_liquido": 2_500.0, "receita_liquida": 10_000.0,
        "roe": 0.2, "margem_liquida": 0.2, "divida_pl": 0.5, "ativo_total": 20_000.0,
        "ativo_circulante": 5_000.0, "cvm_dt_refer": "2025-12-31", "cvm_versao": "1",
        "cnpj": CNPJ, "lucro_controladores": 2_000.0, "pl_controladores": 10_000.0,
        "roe_motivo": None, "lpa_divulgado": {"especie": "ON", "conta": "3.99.01.01", "valor": 2.1},
        "composicao_capital": _composicao(), "composicao_motivo": None,
    }  # fmt: skip
    return {2025: {**base, **campos}}


def _motor(monkeypatch, ind, *, shares=400.0, referencia=None, info_extra=None):
    info = {"currentPrice": PRECO, "quoteType": "EQUITY", "sharesOutstanding": shares}
    engine = _engine(
        monkeypatch,
        historico=_historico(PRECO),
        info={**info, **(info_extra or {})},
        cvm=FakeCVM(ind),
    )
    if referencia is not None:
        engine.referencia = referencia
    return engine


# ── aceite ───────────────────────────────────────────────────────────────────


def test_lpa_usa_on_mais_pn_menos_tesouraria(monkeypatch):
    # ON 700 + PN 400 − tesouraria 100 = 1.000 ações; o yfinance informa só a PN (400).
    # F2A-36: o recalculado é conferência (`lpa_recalculado`) e reserva: sem divulgado da
    # espécie do ticker (aqui, sem espécie no índice), ele entra nos métodos, com a marca.
    dados = _motor(monkeypatch, _ind(), shares=400.0).buscar_dados_ticker("PETR4")
    assert dados["acoes_cvm"]["lpa_recalculado"] == pytest.approx(2.0)
    assert dados["lpa"] == pytest.approx(2.0)
    assert dados["lpa_cvm"]["origem"] == "recalculado"
    assert NOTA_RECALCULADO in dados["lpa_cvm"]["notas"]
    assert dados["vpa"] == pytest.approx(10.0)
    assert dados["pl"] == pytest.approx(PRECO / 2.0)
    assert dados["pvp"] == pytest.approx(PRECO / 10.0)


def test_escala_em_milhares_vira_unidades(monkeypatch):
    ind = _ind(
        lucro_controladores=2_000_000.0,
        pl_controladores=10_000_000.0,
        lpa_divulgado={"especie": "ON", "conta": "3.99.01.01", "valor": 1.9},
    )
    dados = _motor(monkeypatch, ind).buscar_dados_ticker("PETR4")
    assert dados["acoes_cvm"]["escala"] == "MIL"
    assert dados["acoes_cvm"]["acoes"] == pytest.approx(1_000_000.0)
    assert dados["lpa"] == pytest.approx(2.0)
    assert dados["vpa"] == pytest.approx(10.0)


def test_escala_indeterminada_abstem(monkeypatch):
    ind = _ind(lpa_divulgado={"especie": "ON", "conta": "3.99.01.01", "valor": 0.05})
    dados = _motor(monkeypatch, ind).buscar_dados_ticker("PETR4")
    assert "lpa" not in dados and "vpa" not in dados
    assert (
        f"CVM não derivou LPA, VPA, P/L e P/VP: {MOTIVO_ESCALA}"
        in dados["riscos_dados"]
    )
    assert "acoes_cvm" not in dados


def test_documento_diferente_do_lucro_abstem(monkeypatch):
    ind = _ind(composicao_capital=None, composicao_motivo=MOTIVO_DOCUMENTO_DIFERENTE)
    dados = _motor(monkeypatch, ind).buscar_dados_ticker("PETR4")
    assert "lpa" not in dados
    assert (
        f"CVM não derivou LPA, VPA, P/L e P/VP: {MOTIVO_DOCUMENTO_DIFERENTE}"
        in dados["riscos_dados"]
    )


def test_unit_multiplica_pelas_acoes_por_unit(monkeypatch):
    # F2A-36: o recalculado da unit (1 ON + 2 PN) fica como conferência; nos métodos entra
    # 1 × LPA divulgado ON (2,1) + 2 × recalculado PN (2,0, sem divulgado da PN).
    unit = _registro(
        "TSTA11", classe="UNIT", especie=None, acoes_por_unit={"ON": 1, "PN": 2}
    )
    engine = _motor(monkeypatch, _ind(), referencia=FakeReferencia(_indice(unit)))
    dados = engine.buscar_dados_ticker("TSTA11")
    assert dados["acoes_cvm"]["lpa_recalculado"] == pytest.approx(6.0)
    assert dados["lpa"] == pytest.approx(2.1 + 2 * 2.0)
    assert dados["vpa"] == pytest.approx(30.0)
    assert dados["pl"] == pytest.approx(PRECO / 6.1)
    assert dados["divergencia_acoes"]["especie"] == "UNIT"
    assert dados["divergencia_acoes"]["acoes_cvm"] == pytest.approx(1_000.0 / 3)


def test_unit_sem_composicao_oficial_abstem(monkeypatch):
    unit = _registro("TSTA11", classe="UNIT", especie=None, acoes_por_unit=None)
    engine = _motor(monkeypatch, _ind(), referencia=FakeReferencia(_indice(unit)))
    dados = engine.buscar_dados_ticker("TSTA11")
    assert "lpa" not in dados
    assert (
        f"CVM não derivou LPA, VPA, P/L e P/VP: {MOTIVO_UNIT}" in dados["riscos_dados"]
    )


def test_divergencia_por_especie_e_registrada(monkeypatch):
    pn = _registro("TSTA4", especie="PN")
    engine = _motor(
        monkeypatch, _ind(), shares=378.0, referencia=FakeReferencia(_indice(pn))
    )
    dados = engine.buscar_dados_ticker("TSTA4")
    # PN 400 − tesouraria PN 40 = 360; o yfinance informa 378: 5% acima.
    assert dados["divergencia_acoes"] == {
        "especie": "PN",
        "acoes_cvm": pytest.approx(360.0),
        "acoes_yfinance": 378.0,
        "diferenca": pytest.approx(0.05),
    }
    assert dados["lpa"] == pytest.approx(2.0)  # alerta, não abstenção


def test_sem_composicao_mantem_multiplos_das_outras_fontes(monkeypatch):
    ind = _ind(composicao_capital=None, composicao_motivo=MOTIVO_SEM_COMPOSICAO)
    engine = _motor(
        monkeypatch, ind, info_extra={"trailingPE": 9.0, "priceToBook": 1.4}
    )
    dados = engine.buscar_dados_ticker("PETR4")
    assert dados["pl"] == pytest.approx(9.0)
    assert dados["pvp"] == pytest.approx(1.4)
    assert dados["field_provenance"]["pl"]["provenance"]["source"] == "yfinance"
    assert (
        f"CVM não derivou LPA, VPA, P/L e P/VP: {MOTIVO_SEM_COMPOSICAO}"
        in dados["riscos_dados"]
    )


def test_lucro_e_pl_sao_dos_controladores(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 1_000.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", 800.0),
             ("3.11.02", "Atribuído a Sócios Não Controladores", 200.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 5_000.0),
             ("2.03.09", "Participação dos Acionistas Não Controladores", 1_000.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] == pytest.approx(800.0)
    assert ind["pl_controladores"] == pytest.approx(4_000.0)
    assert ind["roe"] == pytest.approx(0.2)
    assert ind["lucro_liquido"] == pytest.approx(1_000.0)  # o consolidado continua lá


def test_roe_com_pl_nao_positivo_abstem(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", -500.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", -500.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", -2_000.0)],
    )  # fmt: skip
    assert ind["roe"] is None
    assert ind["roe_motivo"] == MOTIVO_ROE_PL
    dados = _motor(
        monkeypatch, {2025: ind}, info_extra={"returnOnEquity": 0.12}
    ).buscar_dados_ticker("PETR4")
    assert f"CVM sem ROE: {MOTIVO_ROE_PL}" in dados["riscos_dados"]
    assert dados["roe"] == pytest.approx(0.12)
    assert dados["field_provenance"]["roe"]["provenance"]["source"] == "yfinance"


# ── provedor: arquivos sintéticos pelo layout da DFP ─────────────────────────

CD_CVM = 9512
COLUNAS_DEM = [
    "CNPJ_CIA",
    "DT_REFER",
    "VERSAO",
    "CD_CVM",
    "CD_CONTA",
    "DS_CONTA",
    "VL_CONTA",
]


def _frame(linhas, dt="2025-12-31", versao="1"):
    return pd.DataFrame(
        [[CNPJ, dt, versao, CD_CVM, c, d, v] for c, d, v in linhas], columns=COLUNAS_DEM
    )


def _csv(linhas, colunas):
    texto = ";".join(colunas) + "\n"
    texto += "\n".join(";".join(str(x) for x in linha) for linha in linhas)
    return texto.encode("latin-1")


def _zip_dfp(caminho, *, linhas_399=(), composicao=()):
    colunas_dre = ["CNPJ_CIA", "DT_REFER", "VERSAO", "CD_CVM", "GRUPO_DFP", "ESCALA_MOEDA",
                   "ORDEM_EXERC", "CD_CONTA", "DS_CONTA", "VL_CONTA"]  # fmt: skip
    dre = [
        [CNPJ, dt, v, CD_CVM, "DF Consolidado - DRE", "MIL", ordem, c, d, x]
        for c, d, x, dt, v, ordem in linhas_399
    ]
    colunas_cc = ["CNPJ_CIA", "DT_REFER", "VERSAO", "DENOM_CIA", "QT_ACAO_ORDIN_CAP_INTEGR",
                  "QT_ACAO_PREF_CAP_INTEGR", "QT_ACAO_TOTAL_CAP_INTEGR", "QT_ACAO_ORDIN_TESOURO",
                  "QT_ACAO_PREF_TESOURO", "QT_ACAO_TOTAL_TESOURO"]  # fmt: skip
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("dfp_cia_aberta_DRE_con_2025.csv", _csv(dre, colunas_dre))
        zf.writestr(
            "dfp_cia_aberta_composicao_capital_2025.csv", _csv(composicao, colunas_cc)
        )
    return caminho


def _calcular(tmp_path, monkeypatch, *, dre, bpp, linhas_399=(), composicao=()):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    caminho = _zip_dfp(
        tmp_path / "dfp.zip", linhas_399=linhas_399, composicao=composicao
    )
    frames = {"BPA_con": _frame([("1", "Ativo Total", 10_000.0)]), "BPP_con": _frame(bpp),
              "DRE_con": _frame(dre)}  # fmt: skip
    monkeypatch.setattr(provider, "baixar_dfp", lambda ano: caminho)
    monkeypatch.setattr(
        provider, "parsear_demonstrativo", lambda path, tipo, **kw: frames[tipo]
    )
    resultado = provider.calcular_indicadores(CD_CVM, anos=1)
    return next(iter(resultado.values()))


def test_provedor_le_composicao_e_lpa_do_mesmo_documento(tmp_path, monkeypatch):
    linhas_399 = [
        ("3.99.01.01", "PN", "2.5", "2025-12-31", "1", "ÚLTIMO"),
        ("3.99.01.02", "ON", "2.25", "2025-12-31", "1", "ÚLTIMO"),
        ("3.99.01.02", "ON", "9.99", "2025-12-31", "1", "PENÚLTIMO"),
        ("3.99.01.02", "ON", "7.77", "2024-12-31", "1", "ÚLTIMO"),
    ]
    composicao = [
        [CNPJ, "2025-12-31", "1", "TESTE", 700, 400, 1100, 60, 40, 100],
        [CNPJ, "2025-12-31", "2", "TESTE", 1, 1, 2, 0, 0, 0],
    ]
    ind = _calcular(
        tmp_path, monkeypatch,
        dre=[("3.11", "Lucro", 2_000.0)], bpp=[("2.03", "Patrimônio Líquido Consolidado", 1.0)],
        linhas_399=linhas_399, composicao=composicao,
    )  # fmt: skip
    # A espécie vem da descrição (ON), não do código; o valor não passa pela escala MIL.
    assert ind["lpa_divulgado"] == {
        "especie": "ON",
        "conta": "3.99.01.02",
        "valor": 2.25,
    }
    assert ind["composicao_capital"] == _composicao()
    assert ind["composicao_motivo"] is None
    assert ind["cnpj"] == CNPJ


def test_provedor_sem_a_versao_do_documento_aponta_documento_diferente(
    tmp_path, monkeypatch
):
    composicao = [[CNPJ, "2025-12-31", "2", "TESTE", 700, 400, 1100, 60, 40, 100]]
    ind = _calcular(
        tmp_path, monkeypatch, dre=[("3.11", "Lucro", 2_000.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 1.0)], composicao=composicao,
    )  # fmt: skip
    assert ind["composicao_capital"] is None
    assert ind["composicao_motivo"] == MOTIVO_DOCUMENTO_DIFERENTE


def test_provedor_sem_zip_legivel_aponta_falta_de_composicao(tmp_path, monkeypatch):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    frames = {"BPA_con": _frame([("1", "Ativo", 1.0)]),
              "BPP_con": _frame([("2.03", "Patrimônio Líquido Consolidado", 1.0)]),
              "DRE_con": _frame([("3.11", "Lucro", 1.0)])}  # fmt: skip
    monkeypatch.setattr(provider, "baixar_dfp", lambda ano: tmp_path / "nao_existe.zip")
    monkeypatch.setattr(
        provider, "parsear_demonstrativo", lambda path, tipo, **kw: frames[tipo]
    )
    ind = next(iter(provider.calcular_indicadores(CD_CVM, anos=1).values()))
    assert ind["composicao_capital"] is None
    assert ind["composicao_motivo"] == MOTIVO_SEM_COMPOSICAO
    assert ind["lpa_divulgado"] is None


def test_provedor_banco_sem_pl_em_2_03_nao_inventa_pl(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path, monkeypatch,
        dre=[("3.09", "Lucro", 100.0),
             ("3.09.01", "Atribuído a Sócios da Empresa Controladora", 90.0)],
        bpp=[("2.03", "Provisões", 7_000.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] == pytest.approx(90.0)
    assert ind["pl_controladores"] is None
    assert ind["roe"] is None


def test_provedor_le_zip_real_uma_vez(tmp_path, monkeypatch):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    caminho = _zip_dfp(
        tmp_path / "dfp.zip",
        linhas_399=[("3.99.01.01", "ON", "1.5", "2025-12-31", "1", "ÚLTIMO")],
    )
    leituras = []
    original = provider._read_raw

    def contar(zip_path, tipo):
        leituras.append(tipo)
        return original(zip_path, tipo)

    monkeypatch.setattr(provider, "_read_raw", contar)
    primeiro = provider._dados_por_acao(caminho)
    segundo = provider._dados_por_acao(caminho)
    assert leituras == ["DRE_con", "composicao_capital"]
    assert segundo[0] is primeiro[0]
    assert list(primeiro[0]["VL_CONTA"]) == ["1.5"]


def test_provedor_zip_sem_composicao_devolve_vazio(tmp_path):
    caminho = tmp_path / "dfp.zip"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("dfp_cia_aberta_DRE_con_2025.csv", io.BytesIO(b"A;B\n1;2\n").read())
    linhas, cc = CVMProvider(cache_dir=str(tmp_path / "c"))._dados_por_acao(caminho)
    assert linhas.empty and cc.empty


# ── relatório do F1-12 ───────────────────────────────────────────────────────

ACOES_CVM = {
    "documento": {"cnpj": CNPJ, "dt_refer": "2025-12-31", "versao": "2"},
    "escala": "MIL",
    "acoes": 1_234_567.0,
    "razao_lpa_calculado_sobre_divulgado": 1.0,
    "nota": "ações do fim do período",
}


def _proveniencias(**dados):
    from tests.test_rastreabilidade import _acao, _contexto

    contexto = _contexto(_acao(**dados))
    return {i["campo"]: i["proveniencia"] for i in contexto["insumos"]}, contexto


def test_relatorio_mostra_documento_e_escala_do_lpa_e_do_vpa():
    # F2A-44: o LPA da CVM é o recalculado só quando `lpa_cvm` o marca (F2A-36).
    recalculado = {"origem": "recalculado", "classe": "ON", "notas": [NOTA_RECALCULADO]}
    proveniencias, _ = _proveniencias(acoes_cvm=ACOES_CVM, lpa_cvm=recalculado)
    assert proveniencias["lpa"] == (
        "derivado no motor: preço ÷ P/L; P/L da CVM: LPA recalculado da classe ON: lucro dos "
        "controladores ÷ 1.234.567 ações da Composição do Capital (DFP de 2025-12-31, versão "
        "2, escala MIL; ações do fim do período) [ações do fim do período, não média "
        "ponderada]"
    )
    assert "P/VP da CVM: PL dos controladores ÷ 1.234.567 ações" in proveniencias["vpa"]


def test_relatorio_descreve_o_lpa_da_unit_e_o_divulgado_sem_acoes():
    # F2A-44: unit com classes de origens diferentes; o divulgado traz a nota do sinal.
    unit = {
        "origem": "unit",
        "componentes": {
            "ON": {"quantidade": 1, "lpa": 2.1, "origem": "divulgado", "classe": "ON",
                   "notas": [NOTA_SINAL_CONSOLIDADO]},
            "PN": {"quantidade": 2.0, "lpa": 2.0, "origem": "recalculado", "classe": "PN",
                   "notas": [NOTA_RECALCULADO]},
        },
        "notas": [NOTA_SINAL_CONSOLIDADO, NOTA_RECALCULADO],
    }  # fmt: skip
    proveniencias, _ = _proveniencias(acoes_cvm=ACOES_CVM, lpa_cvm=unit)
    assert proveniencias["lpa"] == (
        "derivado no motor: preço ÷ P/L; P/L da CVM: soma das classes da unit: 1 × LPA "
        "básico divulgado na DRE da classe ON (média ponderada de ações do exercício) "
        f"[{NOTA_SINAL_CONSOLIDADO}] + 2 × LPA recalculado da classe PN: lucro dos "
        "controladores ÷ 1.234.567 ações da Composição do Capital (DFP de 2025-12-31, versão "
        f"2, escala MIL; ações do fim do período) [{NOTA_RECALCULADO}]"
    )
    # Escala indeterminada: sem a Composição do Capital, o LPA divulgado ainda é da CVM.
    divulgado = {"origem": "divulgado", "classe": "ON", "notas": []}
    sem_acoes, _ = _proveniencias(lpa_cvm=divulgado)
    assert sem_acoes["lpa"] == (
        "derivado no motor: preço ÷ P/L; P/L da CVM: LPA básico divulgado na DRE da classe "
        "ON (média ponderada de ações do exercício)"
    )


def test_relatorio_sem_multiplo_da_cvm_nao_cita_o_documento():
    from tests.test_rastreabilidade import _prov

    pl_de_outra_fonte = {
        "name": "pl",
        "value": 10.0,
        "unit": "ratio",
        "provenance": _prov("brapi"),
    }
    proveniencias, _ = _proveniencias(acoes_cvm=ACOES_CVM)
    sem_acoes, _ = _proveniencias()
    assert sem_acoes["lpa"] == "derivado no motor: preço ÷ P/L"
    from tests.test_rastreabilidade import _acao, _contexto

    dados = _acao(
        acoes_cvm=ACOES_CVM,
        lpa_cvm={"origem": "divulgado", "classe": "ON", "notas": []},
    )
    dados["field_provenance"]["pl"] = pl_de_outra_fonte
    outras = {i["campo"]: i["proveniencia"] for i in _contexto(dados)["insumos"]}
    assert outras["lpa"] == "derivado no motor: preço ÷ P/L"
    assert "Composição do Capital" in proveniencias["vpa"]


def test_relatorio_troca_o_limite_do_e1():
    _, contexto = _proveniencias()
    (e1,) = [t for t in contexto["limites"] if t.startswith("E-1")]
    assert "Composição do Capital do mesmo documento" in e1
    assert "sem reconciliar" not in e1


def test_controladora_e_minoritarios_zerados_valem_o_lucro_total(tmp_path, monkeypatch):
    # KLBN11 e SBSP3 na DFP 2025: 3.11.01 e 3.11.02 zeradas, lucro só em 3.11.
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 1_000.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", 0.0),
             ("3.11.02", "Atribuído a Sócios Não Controladores", 0.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 5_000.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] == pytest.approx(1_000.0)


def test_controladora_zerada_com_minoritarios_fica_zero(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 1_000.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", 0.0),
             ("3.11.02", "Atribuído aos Sócios não Controladores", 1_000.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 5_000.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] == 0.0


def test_sem_linha_da_controladora_e_minoritarios_de_outra_descricao_se_abstem(
    tmp_path, monkeypatch
):
    # F2A-41 (D20): a 2.03.09 com outra descrição não é ausência de minoritários.
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 700.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 7_000.0),
             ("2.03.09", "Outra conta", 300.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] is None
    assert ind["pl_controladores"] is None
    assert ind["roe"] is None
    assert ind["roe_motivo"] == MOTIVO_LUCRO_NAO_SEPARADO


def test_pl_e_pvp_da_cvm_declaram_as_acoes_do_fim_do_periodo(monkeypatch):
    dados = _motor(monkeypatch, _ind()).buscar_dados_ticker("PETR4")
    for campo in ("pl", "pvp"):
        prov = dados["field_provenance"][campo]["provenance"]
        assert prov["source"] == "CVM"
        assert "shares_end_of_period" in prov["warnings"]
    assert (
        "shares_end_of_period"
        not in (dados["field_provenance"]["roe"]["provenance"]["warnings"])
    )


def test_sem_acoes_cvm_nao_ha_aviso_do_fim_do_periodo(monkeypatch):
    ind = _ind(composicao_capital=None, composicao_motivo=MOTIVO_SEM_COMPOSICAO)
    dados = _motor(
        monkeypatch, ind, info_extra={"trailingPE": 9.0}
    ).buscar_dados_ticker("PETR4")
    assert (
        "shares_end_of_period"
        not in dados["field_provenance"]["pl"]["provenance"]["warnings"]
    )


@pytest.mark.parametrize(
    ("linhas", "esperado"),
    [
        ([("3.99.01.01", "PNA", "1.5"), ("3.99.01.02", "PNB", "1.6")],
         {"especie": "PN", "conta": "3.99.01.01", "valor": 1.5}),
        ([("3.99.01.01", "ON", "0"), ("3.99.01.02", "PN", "0.7")],
         {"especie": "PN", "conta": "3.99.01.02", "valor": 0.7}),
        ([("3.99", "Lucro por Ação", "0"), ("3.99.01", "Lucro Básico por Ação", "0.9")],
         {"especie": "BASICO", "conta": "3.99.01", "valor": 0.9}),
        ([("3.99", "Lucro por Ação", "2.4"), ("3.99.01", "Lucro Básico por Ação", "0")],
         {"especie": "BASICO", "conta": "3.99", "valor": 2.4}),
        ([("3.99", "Lucro por Ação", "0"), ("3.99.01.01", "ON", "0")], None),
        ([], None),
    ],
)  # fmt: skip
def test_lpa_divulgado_reservas(linhas, esperado):
    from cvm_provider import lpa_divulgado

    frame = pd.DataFrame(linhas, columns=["CD_CONTA", "DS_CONTA", "VL_CONTA"])
    assert lpa_divulgado(frame) == esperado


def test_3_11_01_vale_antes_da_3_09_01(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=[("3.09.01", "Atribuído a Sócios da Empresa Controladora", 600.0),
             ("3.11", "Lucro/Prejuízo Consolidado do Período", 1_000.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", 900.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 9_000.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] == pytest.approx(900.0)


def test_tesouraria_total_vazia_usa_a_soma_das_especies(tmp_path, monkeypatch):
    composicao = [[CNPJ, "2025-12-31", "1", "TESTE", 700, 400, 1100, 60, 40, ""]]
    ind = _calcular(
        tmp_path, monkeypatch, dre=[("3.11", "Lucro", 2_000.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 1.0)], composicao=composicao,
    )  # fmt: skip
    assert ind["composicao_capital"].tesouraria_total == pytest.approx(100.0)
    assert ind["composicao_capital"].total == pytest.approx(1_000.0)


def test_dre_sem_as_colunas_esperadas_devolve_vazio(tmp_path):
    caminho = tmp_path / "dfp.zip"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("dfp_cia_aberta_DRE_con_2025.csv", "CD_CONTA;X\n3.99;1\n")
        zf.writestr("dfp_cia_aberta_composicao_capital_2025.csv", "A;B\n1;2\n")
    linhas, cc = CVMProvider(cache_dir=str(tmp_path / "c"))._dados_por_acao(caminho)
    assert linhas.empty and cc.empty


def test_cache_por_acao_tem_teto(tmp_path, monkeypatch):
    import cvm_provider

    monkeypatch.setattr(cvm_provider, "_cache_por_acao", {})
    provider = CVMProvider(cache_dir=str(tmp_path / "c"))
    for i in range(cvm_provider._CACHE_POR_ACAO_MAX + 3):
        provider._dados_por_acao(_zip_dfp(tmp_path / f"dfp{i}.zip"))
    assert len(cvm_provider._cache_por_acao) == cvm_provider._CACHE_POR_ACAO_MAX


# ── F2A-36: LPA divulgado por espécie nos métodos (ADR-0003, D19) ─────────────


def test_lpa_dos_metodos_e_o_divulgado_da_especie(monkeypatch):
    pn = _registro("TSTA4", especie="PN")
    ind = _ind(lpa_divulgado_por_especie={"ON": 2.1, "PN": 2.3})
    dados = _motor(
        monkeypatch, ind, referencia=FakeReferencia(_indice(pn))
    ).buscar_dados_ticker("TSTA4")
    assert dados["lpa"] == pytest.approx(2.3)
    assert dados["pl"] == pytest.approx(PRECO / 2.3)
    assert dados["vpa"] == pytest.approx(10.0)


def _por_classe(monkeypatch, ticker, linhas, *, registro=None, **ind):
    registro = registro or _registro(ticker, especie="PN")
    return _motor(
        monkeypatch,
        _ind(lpa_basico_por_classe=linhas, **ind),
        referencia=FakeReferencia(_indice(registro)),
    ).buscar_dados_ticker(ticker)


def test_sem_divulgado_usa_recalculado_com_marca(monkeypatch):
    # Só a ON tem LPA divulgado: ela fixa a escala, e a PN usa o recalculado (D19, regra 2).
    dados = _por_classe(monkeypatch, "TSTA4", {"ON": [2.1]})
    assert dados["lpa"] == pytest.approx(2.0)
    assert dados["lpa_cvm"] == {
        "origem": "recalculado",
        "classe": "PN",
        "notas": [NOTA_RECALCULADO],
    }


def test_divulgado_incoerente_abstem_sem_recalculado(monkeypatch):
    # Lucro dos controladores positivo, LPA da PN negativo: a PN se abstém, sem reserva.
    dados = _por_classe(monkeypatch, "TSTA4", {"ON": [2.1], "PN": [-2.0]})
    assert "lpa" not in dados and "pl" not in dados
    assert f"CVM sem LPA: {MOTIVO_SINAL_CONTROLADORES}" in dados["riscos_dados"]
    assert dados["vpa"] == pytest.approx(10.0)  # o VPA não depende do divulgado da PN


def test_linhas_conflitantes_da_especie_abstem(monkeypatch):
    # QUAL3 na DFP 2025: duas linhas básicas "ON" com valores diferentes.
    on = _registro("TSTA3", especie="ON")
    dados = _por_classe(monkeypatch, "TSTA3", {"ON": [-0.00895, 0.04662]}, registro=on)
    assert "lpa" not in dados
    assert f"CVM sem LPA: {MOTIVO_LINHAS_CONFLITANTES}" in dados["riscos_dados"]
    assert (
        f"CVM não derivou LPA, VPA, P/L e P/VP: {MOTIVO_ESCALA}"
        in dados["riscos_dados"]
    )


def test_escala_indeterminada_mantem_o_divulgado(monkeypatch):
    # Razão 2,0 ÷ 0,05 = 40, fora de [0,1; 10]: sem VPA, mas o divulgado segue (ficha, 7.1).
    dados = _por_classe(monkeypatch, "TSTA4", {"ON": [0.05], "PN": [0.05]})
    assert dados["lpa"] == pytest.approx(0.05)
    assert dados["pl"] == pytest.approx(PRECO / 0.05)
    assert "vpa" not in dados and "pvp" not in dados and "acoes_cvm" not in dados
    assert f"CVM não derivou VPA e P/VP: {MOTIVO_ESCALA}" in dados["riscos_dados"]
    assert not any(r.startswith("CVM não derivou LPA") for r in dados["riscos_dados"])


def test_escala_vem_de_outra_especie_do_mesmo_documento(monkeypatch):
    # Ações em milhares: a ON (1,9) fixa a escala MIL; a PN sem divulgado usa o recalculado.
    dados = _por_classe(
        monkeypatch,
        "TSTA4",
        {"ON": [1.9]},
        lucro_controladores=2_000_000.0,
        pl_controladores=10_000_000.0,
    )
    assert dados["acoes_cvm"]["escala"] == "MIL"
    assert dados["lpa"] == pytest.approx(2.0)
    assert dados["vpa"] == pytest.approx(10.0)


def test_sinal_conferido_pelo_consolidado_quando_controladores_se_abstem(monkeypatch):
    # KLBN11 pela decisão 7.2: lucro dos controladores abstido; o consolidado confere o sinal.
    dados = _por_classe(
        monkeypatch, "TSTA4", {"ON": [0.2286], "PN": [0.2286]},
        lucro_controladores=None, proveniencia={"dt_refer": "2025-12-31"},
    )  # fmt: skip
    assert dados["lpa"] == pytest.approx(0.2286)
    assert dados["lpa_cvm"]["notas"] == [NOTA_SINAL_CONSOLIDADO]
    assert dados["proveniencia"]["lpa"] == {
        "dt_refer": "2025-12-31",
        "lpa": dados["lpa_cvm"],
    }
    contra = _por_classe(monkeypatch, "TSTA4", {"PN": [-0.2]}, lucro_controladores=None)
    assert f"CVM sem LPA: {MOTIVO_SINAL_CONSOLIDADO}" in contra["riscos_dados"]


def test_sem_lucro_valido_o_divulgado_se_abstem(monkeypatch):
    dados = _por_classe(
        monkeypatch,
        "TSTA4",
        {"PN": [0.5]},
        lucro_controladores=None,
        lucro_liquido=None,
    )
    assert "lpa" not in dados
    assert f"CVM sem LPA: {MOTIVO_SINAL_NAO_CONFERIVEL}" in dados["riscos_dados"]


def test_classe_preferencial_vem_do_fca():
    # Banrisul no FCA 2026 (documento 156166): BRSR3 ON, BRSR5 PNA, BRSR6 PNB.
    from tests.test_referencia import _fca
    from tests.test_referencia import _indice as _indice_oficial

    fca = _fca(
        {"Codigo_Negociacao": "TSTB3"},
        {"Codigo_Negociacao": "TSTB5", "Valor_Mobiliario": "Ações Preferenciais",
         "Sigla_Classe_Acao_Preferencial": "PNA"},
        {"Codigo_Negociacao": "TSTB6", "Valor_Mobiliario": "Ações Preferenciais",
         "Sigla_Classe_Acao_Preferencial": "PNB"},
    )  # fmt: skip
    fca["Sigla_Classe_Acao_Preferencial"] = [None, "PNA", "PNB"]
    registros = _indice_oficial(fca=fca).registros
    assert (registros["TSTB5"].especie, registros["TSTB5"].classe_preferencial) == (
        "PN",
        "PNA",
    )
    assert registros["TSTB6"].classe_preferencial == "PNB"
    assert registros["TSTB3"].classe_preferencial is None
    assert registros["TSTB3"].classes_preferenciais == ["PNA", "PNB"]


def _banrisul(ticker, especie, classe):
    return _registro(
        ticker, especie=especie, classe_preferencial=classe,
        classes_preferenciais=["PNA", "PNB"],
    )  # fmt: skip


def test_pna_e_pnb_nao_usam_lpa_comum(monkeypatch):
    linhas = {"ON": [2.1], "PNA": [2.3]}
    pna = _por_classe(
        monkeypatch, "TSTB5", linhas, registro=_banrisul("TSTB5", "PN", "PNA")
    )
    assert pna["lpa"] == pytest.approx(2.3)
    assert pna["lpa_cvm"]["classe"] == "PNA"
    pnb = _por_classe(
        monkeypatch, "TSTB6", linhas, registro=_banrisul("TSTB6", "PN", "PNB")
    )
    assert "lpa" not in pnb
    assert f"CVM sem LPA: {MOTIVO_CLASSES_PREFERENCIAIS}" in pnb["riscos_dados"]
    on = _por_classe(
        monkeypatch, "TSTB3", {"PNA": [2.3]}, registro=_banrisul("TSTB3", "ON", None)
    )
    assert on["lpa"] == pytest.approx(2.0)  # a ON sem divulgado ainda tem a reserva
    assert on["lpa_cvm"]["origem"] == "recalculado"


def _unit(**campos):
    return _registro(
        "TSTA11",
        classe="UNIT",
        especie=None,
        acoes_por_unit={"ON": 1, "PN": 4},
        **campos,
    )


def test_unit_soma_lpas_ponderados_pela_composicao(monkeypatch):
    dados = _por_classe(
        monkeypatch, "TSTA11", {"ON": [2.1], "PN": [2.3]}, registro=_unit()
    )
    assert dados["lpa"] == pytest.approx(1 * 2.1 + 4 * 2.3)
    assert dados["lpa_cvm"]["origem"] == "unit"
    assert dados["lpa_cvm"]["componentes"]["PN"] == {
        "quantidade": 4, "lpa": 2.3, "origem": "divulgado", "classe": "PN", "notas": [],
    }  # fmt: skip


def test_unit_com_componente_sem_reserva_abstem(monkeypatch):
    # A PN da unit, numa companhia com PNA e PNB, não tem divulgado nem reserva (regra 3).
    dados = _por_classe(
        monkeypatch,
        "TSTA11",
        {"ON": [2.1]},
        registro=_unit(classes_preferenciais=["PNA", "PNB"]),
    )
    assert "lpa" not in dados
    assert (
        f"CVM sem LPA: {MOTIVO_CLASSES_PREFERENCIAIS} (PN da unit)"
        in dados["riscos_dados"]
    )
    assert dados["vpa"] == pytest.approx(50.0)  # 5 ações por unit × 10


def _documento_da_ficha(tmp_path, monkeypatch, *, dre, bpp, lpa, acoes):
    on, pn = acoes
    linhas_399 = [
        ("3.99.01.01", "ON", lpa, "2025-12-31", "1", "ÚLTIMO"),
        ("3.99.01.02", "PN", lpa, "2025-12-31", "1", "ÚLTIMO"),
    ]
    composicao = [[CNPJ, "2025-12-31", "1", "TESTE", on, pn, on + pn, 0, 0, 0]]
    return _calcular(
        tmp_path, monkeypatch, dre=dre, bpp=bpp, linhas_399=linhas_399,
        composicao=composicao,
    )  # fmt: skip


def test_exemplo_da_ficha_por_acao(tmp_path, monkeypatch):
    # docs/metodologia/por-acao.md, seção 5 (valores da DFP 2025 lidos à mão, em reais).
    petrobras = _documento_da_ficha(
        tmp_path / "petr", monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 110_605_000_000.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", 110_129_000_000.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 417_587_000_000.0),
             ("2.03.09", "Participação dos Acionistas Não Controladores", 1_801_000_000.0)],
        lpa="8.54", acoes=(7_442_231_382, 5_446_501_379),
    )  # fmt: skip
    for ticker, especie in (("TSTP3", "ON"), ("TSTP4", "PN")):
        dados = _motor(
            monkeypatch, {2025: petrobras},
            referencia=FakeReferencia(_indice(_registro(ticker, especie=especie))),
        ).buscar_dados_ticker(ticker)  # fmt: skip
        assert dados["lpa"] == pytest.approx(8.54)
        assert dados["acoes_cvm"]["escala"] == "UNIDADE"
        assert dados["acoes_cvm"]["lpa_recalculado"] == pytest.approx(8.5446, abs=5e-5)
        assert dados["vpa"] == pytest.approx(32.26, abs=5e-3)

    taesa = _documento_da_ficha(
        tmp_path / "taee", monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 1_579_863_000.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", 1_579_863_000.0),
             ("3.11.02", "Atribuído a Sócios Não Controladores", 0.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 7_608_982_000.0),
             ("2.03.09", "Participação dos Acionistas Não Controladores", 0.0)],
        lpa="1.52866", acoes=(590_714, 442_783),
    )  # fmt: skip
    unit = _registro(
        "TSTT11", classe="UNIT", especie=None, acoes_por_unit={"ON": 1, "PN": 2}
    )
    dados = _motor(
        monkeypatch, {2025: taesa}, referencia=FakeReferencia(_indice(unit))
    ).buscar_dados_ticker("TSTT11")
    assert dados["acoes_cvm"]["escala"] == "MIL"
    assert dados["lpa"] == pytest.approx(4.58598)
    assert dados["vpa"] == pytest.approx(22.087, abs=5e-4)


def test_conferencia_usa_a_linha_da_especie_quando_a_dre_nao_traz_a_classe(monkeypatch):
    # FCA com a sigla PNA e uma só classe preferencial; a DRE rotula a linha só como "PN".
    pna = _registro("TSTA5", especie="PN", classe_preferencial="PNA",
                    classes_preferenciais=["PNA"])  # fmt: skip
    dados = _por_classe(
        monkeypatch, "TSTA5", {"ON": [2.1], "PN": [2.5]}, registro=pna,
        lpa_divulgado_por_especie={"ON": 2.1, "PN": 2.5},
    )  # fmt: skip
    assert dados["lpa"] == pytest.approx(2.5)
    assert dados["acoes_cvm"]["lpa_divulgado_comparado"] == {
        "especie": "PN",
        "valor": 2.5,
    }


def test_pl_do_divulgado_nao_declara_as_acoes_do_fim_do_periodo(monkeypatch):
    # O divulgado usa a média ponderada: o aviso fica só no P/VP (e no P/L do recalculado).
    dados = _por_classe(monkeypatch, "TSTA4", {"ON": [2.1], "PN": [2.3]})
    avisos = {
        c: dados["field_provenance"][c]["provenance"]["warnings"] for c in ("pl", "pvp")
    }
    assert "shares_end_of_period" not in avisos["pl"]
    assert "shares_end_of_period" in avisos["pvp"]
    unit = _por_classe(monkeypatch, "TSTA11", {"ON": [2.1]}, registro=_unit())
    assert (
        "shares_end_of_period"
        in unit["field_provenance"]["pl"]["provenance"]["warnings"]
    )
