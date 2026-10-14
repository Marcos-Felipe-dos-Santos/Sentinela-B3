"""Alavancagem pela dívida financeira líquida (F2A-8; F-12, armadilha 17).

Contas pela estrutura oficial da DFP (BPA, BPP, DRE e DVA consolidadas), com as descrições
conferidas no F2A-16. Os valores esperados saem da definição da medida, nunca do código.
"""

import pytest

from cvm_provider import CVMProvider
from sentinela.data import divida_liquida as dl
from sentinela.data.contas_cvm import Abstencao, Leitura
from tests.test_market_engine import FakeBrapi, _engine, _historico
from tests.test_market_engine_acoes_cvm import CD_CVM, _frame, _zip_dfp


def _l(valor, codigo="x"):
    return Leitura(valor, codigo, "")


def _contas(cp=100.0, lp=300.0, caixa=50.0, aplicacoes=30.0):
    return {
        "emprestimos_circulante": _l(cp),
        "emprestimos_nao_circulante": _l(lp),
        "caixa": _l(caixa),
        "aplicacoes": _l(aplicacoes),
    }


def _medir(contas=None, ebit=100.0, depreciacao=-60.0, pl=640.0, modelo="empresa"):
    return dl.medir(
        modelo=modelo,
        contas=contas or _contas(),
        ebit=_l(ebit) if isinstance(ebit, float) else ebit,
        depreciacao=_l(depreciacao) if isinstance(depreciacao, float) else depreciacao,
        pl=pl,
    )


BPA = [
    ("1", "Ativo Total", 10_000.0),
    ("1.01.01", "Caixa e Equivalentes de Caixa", 50.0),
    ("1.01.02", "Aplicações Financeiras", 30.0),
]
BPP = [
    ("2", "Passivo Total", 10_000.0),
    ("2.01.04", "Empréstimos e Financiamentos", 100.0),
    ("2.01.04.03", "Financiamento por Arrendamento", 40.0),
    ("2.02.01", "Empréstimos e Financiamentos", 300.0),
    ("2.02.01.03", "Financiamento por Arrendamento", 120.0),
    ("2.03", "Patrimônio Líquido Consolidado", 640.0),
]
DRE = [
    ("3.05", "Resultado Antes do Resultado Financeiro e dos Tributos", 100.0),
    ("3.11", "Lucro/Prejuízo Consolidado do Período", 50.0),
]
DVA = [("7.04.01", "Depreciação, Amortização e Exaustão", -60.0)]


def _calcular(
    tmp_path, monkeypatch, *, bpa=BPA, bpp=BPP, dre=DRE, dva=DVA, modelo="empresa"
):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    caminho = _zip_dfp(tmp_path / "dfp.zip")
    frames = {"BPA_con": _frame(bpa), "BPP_con": _frame(bpp), "DRE_con": _frame(dre)}
    if dva is not None:
        frames["DVA_con"] = _frame(dva)
    monkeypatch.setattr(provider, "baixar_dfp", lambda ano: caminho)
    monkeypatch.setattr(
        provider, "parsear_demonstrativo", lambda path, tipo, **kw: frames[tipo]
    )
    return next(
        iter(provider.calcular_indicadores(CD_CVM, anos=1, modelo=modelo).values())
    )


# ── aceite ───────────────────────────────────────────────────────────────────


def test_divida_liquida_por_ebitda():
    medida = _medir()
    # (100 + 300) − (50 + 30) = 320; EBITDA = 100 + 60 = 160.
    assert medida.divida_liquida == 320.0
    assert medida.ebitda == 160.0
    assert medida.divida_liq_ebitda == pytest.approx(2.0)
    assert medida.div_liq_patrimonio == pytest.approx(0.5)
    assert medida.motivos == {}
    assert medida.regime == "pós-IFRS 16, arrendamento incluído na dívida"


def test_arrendamento_entra_na_divida_liquida(tmp_path, monkeypatch):
    # O arrendamento (2.0x.0x.03) está dentro do total do grupo: entra uma vez, não duas.
    ind = _calcular(tmp_path, monkeypatch)
    assert ind["divida_liquida"] == 100.0 + 300.0 - 50.0 - 30.0
    assert ind["divida_liq_ebitda"] == pytest.approx(320.0 / 160.0)
    assert ind["div_liq_patrimonio"] == pytest.approx(320.0 / 640.0)
    assert ind["alavancagem_regime"] == dl.REGIME
    # Sem o arrendamento, a dívida cai pelo valor dele.
    sem_arrendamento = [
        ("2.01.04", "Empréstimos e Financiamentos", 60.0) if c == "2.01.04" else
        ("2.02.01", "Empréstimos e Financiamentos", 180.0) if c == "2.02.01" else (c, d, v)
        for c, d, v in BPP
    ]  # fmt: skip
    ind = _calcular(tmp_path, monkeypatch, bpp=sem_arrendamento)
    assert ind["divida_liquida"] == 320.0 - 40.0 - 120.0


def test_caixa_maior_que_divida_da_negativo():
    medida = _medir(_contas(cp=10.0, lp=20.0, caixa=100.0, aplicacoes=30.0))
    assert medida.divida_liquida == -100.0
    assert medida.divida_liq_ebitda == pytest.approx(-100.0 / 160.0)
    assert medida.div_liq_patrimonio == pytest.approx(-100.0 / 640.0)


def test_banco_nao_recebe_medida(tmp_path, monkeypatch):
    for modelo in ("banco", "seguradora"):
        medida = _medir(modelo=modelo)
        assert (medida.divida_liquida, medida.divida_liq_ebitda, medida.div_liq_patrimonio) == (
            None, None, None,
        )  # fmt: skip
        assert medida.motivos == {
            "divida_liq_ebitda": dl.MOTIVO_MODELO,
            "div_liq_patrimonio": dl.MOTIVO_MODELO,
        }
    ind = _calcular(tmp_path, monkeypatch, modelo="banco")
    assert ind["divida_liq_ebitda"] is None
    assert ind["alavancagem_motivos"]["divida_liq_ebitda"] == dl.MOTIVO_MODELO


def test_ebitda_nao_positivo_abstem():
    medida = _medir(ebit=-100.0, depreciacao=-60.0)
    assert medida.ebitda == -40.0
    assert medida.divida_liq_ebitda is None
    assert medida.motivos == {"divida_liq_ebitda": dl.MOTIVO_EBITDA}
    # A razão sobre o PL não depende do EBITDA.
    assert medida.div_liq_patrimonio == pytest.approx(0.5)
    assert _medir(ebit=-60.0, depreciacao=-60.0).motivos == {
        "divida_liq_ebitda": dl.MOTIVO_EBITDA
    }


def test_pl_nao_positivo_abstem_div_liq_patrimonio():
    for pl in (0.0, -10.0):
        medida = _medir(pl=pl)
        assert medida.div_liq_patrimonio is None
        assert medida.motivos == {"div_liq_patrimonio": dl.MOTIVO_PL}
        assert medida.divida_liq_ebitda == pytest.approx(2.0)
    assert _medir(pl=None).motivos == {"div_liq_patrimonio": dl.MOTIVO_SEM_PL}


def test_brapi_nao_preenche_a_alavancagem(monkeypatch):
    brapi = FakeBrapi(
        resposta={"preco_atual": 20.0, "pl": 8.0, "divida_liq_ebitda": 2.5}
    )
    engine = _engine(
        monkeypatch,
        info={"currentPrice": 20.0},
        historico=_historico(20.0),
        brapi=brapi,
    )
    dados = engine.buscar_dados_ticker("TSTE3")
    assert dados["pl"] == 8.0  # a brapi segue preenchendo o resto
    assert "divida_liq_ebitda" not in dados
    assert "divida_liq_ebitda" not in dados["valores_por_fonte"].get("brapi", {})


# ── bordas ───────────────────────────────────────────────────────────────────


def test_conta_ausente_abstem_com_o_motivo(tmp_path, monkeypatch):
    sem_aplicacoes = [linha for linha in BPA if linha[0] != "1.01.02"]
    ind = _calcular(tmp_path, monkeypatch, bpa=sem_aplicacoes)
    assert ind["divida_liquida"] is None
    assert ind["divida_liq_ebitda"] is None and ind["div_liq_patrimonio"] is None
    assert (
        "conta aplicacoes sem valor (linha ausente"
        in ind["alavancagem_motivos"]["divida_liq_ebitda"]
    )
    assert (
        ind["alavancagem_motivos"]["div_liq_patrimonio"]
        == ind["alavancagem_motivos"]["divida_liq_ebitda"]
    )


def test_sem_dva_o_ebitda_se_abstem_e_a_razao_sobre_o_pl_segue(tmp_path, monkeypatch):
    ind = _calcular(tmp_path, monkeypatch, dva=None)
    assert ind["ebitda"] is None
    assert ind["divida_liq_ebitda"] is None
    assert "depreciacao_amortizacao" in ind["alavancagem_motivos"]["divida_liq_ebitda"]
    assert ind["div_liq_patrimonio"] == pytest.approx(0.5)


def test_conta_com_outra_descricao_nao_entra(tmp_path, monkeypatch):
    # Seguradora no modelo de empresa: 2.02.01 com outra descrição → abstenção.
    outra = [
        ("2.02.01", "Passivo Exigível a Longo Prazo", 300.0)
        if c == "2.02.01"
        else (c, d, v)
        for c, d, v in BPP
    ]
    ind = _calcular(tmp_path, monkeypatch, bpp=outra)
    assert ind["divida_liquida"] is None
    assert "sem correspondência" in ind["alavancagem_motivos"]["divida_liq_ebitda"]


def test_d_e_a_positiva_entra_em_modulo():
    assert _medir(depreciacao=60.0).ebitda == 160.0


def test_motivos_das_duas_contas_do_ebitda():
    medida = _medir(
        ebit=Abstencao("linha ausente no documento"),
        depreciacao=Abstencao("valor inválido", "7.04.01"),
    )
    assert medida.ebitda is None
    assert medida.motivos["divida_liq_ebitda"] == (
        "conta ebit sem valor (linha ausente no documento); "
        "conta depreciacao_amortizacao sem valor (valor inválido: 7.04.01)"
    )
    assert medida.para_dict() == {
        "divida_liquida": 320.0,
        "ebitda": None,
        "divida_liq_ebitda": None,
        "div_liq_patrimonio": 0.5,
        "motivos": {"divida_liq_ebitda": medida.motivos["divida_liq_ebitda"]},
        "regime": dl.REGIME,
    }


def test_cascata_grava_a_medida_e_os_motivos(monkeypatch):
    class _CVM:
        def calcular_indicadores(self, cd_cvm, anos=1, **kwargs):
            return {
                2025: {
                    "roe": 0.1,
                    "divida_liq_ebitda": None,
                    "div_liq_patrimonio": 0.5,
                    "divida_liquida": 320.0,
                    "ebitda": -40.0,
                    "alavancagem_motivos": {"divida_liq_ebitda": dl.MOTIVO_EBITDA},
                    "alavancagem_regime": dl.REGIME,
                }
            }

    engine = _engine(
        monkeypatch, info={"currentPrice": 20.0}, historico=_historico(20.0), cvm=_CVM()
    )
    dados = engine.buscar_dados_ticker("PETR4")  # ticker do mapa público
    assert dados["div_liq_patrimonio"] == 0.5
    assert "divida_liq_ebitda" not in dados
    assert dados["alavancagem_cvm"] == {
        "regime": dl.REGIME,
        "divida_liquida": 320.0,
        "ebitda": -40.0,
        "motivos": {"divida_liq_ebitda": dl.MOTIVO_EBITDA},
    }
    assert (
        f"alavancagem não avaliada (divida_liq_ebitda): {dl.MOTIVO_EBITDA}"
        in dados["riscos_dados"]
    )
