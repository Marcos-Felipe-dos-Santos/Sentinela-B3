"""Leituras da CVM pela tabela de contas (F2A-38; ADR-0003, D20).

`calcular_indicadores` lia cada conta só pelo código: num banco, a 2.03 ("Provisões") virava
o patrimônio líquido e alimentava a alavancagem (`divida_pl` → `div_liq_patrimonio`).
"""

from datetime import date

import pytest

import cvm_provider
from cvm_provider import CVMProvider
from sentinela.data import contas_cvm
from tests.test_contratos_provedores import _montar
from tests.test_market_engine import _engine, _historico
from tests.test_market_engine_acoes_cvm import _calcular

# Banco no modelo do BBAS3: PL na 2.07, provisões na 2.03, lucro na 3.11 com "aos sócios".
BANCO_BPP = [
    ("2", "Passivo Total", 2_000.0),
    ("2.03", "Provisões", 50.0),
    ("2.07", "Patrimônio Líquido Consolidado", 190.0),
]
BANCO_DRE = [
    ("3.11", "Lucro ou Prejuízo Líquido Consolidado do Período", 17.0),
    ("3.11.01", "Atribuído aos Sócios da Empresa Controladora", 16.0),
    ("3.11.02", "Atribuído aos Sócios Não Controladores", 1.0),
]


class _Hoje(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 8)


def test_banco_sem_pl_na_2_03_nao_gera_patrimonio_nem_alavancagem(
    tmp_path, monkeypatch
):
    ind = _calcular(tmp_path, monkeypatch, dre=BANCO_DRE, bpp=BANCO_BPP)
    assert ind["patrimonio_liquido"] is None
    assert ind["divida_pl"] is None
    assert ind["pl_controladores"] is None
    assert ind["roe"] is None


def test_empresa_nao_financeira_segue_igual(tmp_path, monkeypatch):
    caminho, _ = _montar("dfp_2025_petrobras.json", tmp_path)
    provider = CVMProvider(str(tmp_path / "cache"))
    monkeypatch.setattr(cvm_provider, "date", _Hoje)
    monkeypatch.setattr(provider, "baixar_dfp", lambda ano: caminho)
    ind = provider.calcular_indicadores(9512, anos=1)[2025]
    # Valores do recorte (milhares de reais × 1.000), lidos à mão nas linhas ÚLTIMO.
    mil = 1_000
    esperado = {
        "ativo_total": 1_223_389_000 * mil,
        "ativo_circulante": 140_026_000 * mil,
        "passivo_total": 1_223_389_000 * mil,
        "passivo_circulante": 198_368_000 * mil,
        "patrimonio_liquido": 417_587_000 * mil,
        "receita_liquida": 497_549_000 * mil,
        "ebit": 145_628_000 * mil,
        "lucro_liquido": 110_605_000 * mil,
        "lucro_controladores": 110_129_000 * mil,
        "pl_controladores": (417_587_000 - 1_801_000) * mil,
    }
    for campo, valor in esperado.items():
        assert ind[campo] == pytest.approx(valor), campo
    assert ind["divida_pl"] == pytest.approx(
        (1_223_389_000 - 417_587_000) / 417_587_000
    )
    assert ind["margem_liquida"] == pytest.approx(110_605_000 / 497_549_000)
    assert ind["roe"] == pytest.approx(110_129_000 / (417_587_000 - 1_801_000))
    assert ind.get("contas_abstidas", {}) == {}


class _CVMBanco:
    """Provedor real sobre o balanço sintético do banco."""

    def __init__(self, tmp_path, monkeypatch):
        self.tmp_path, self.monkeypatch = tmp_path, monkeypatch

    def calcular_indicadores(self, cd_cvm, anos=1, **kwargs):
        ind = _calcular(self.tmp_path, self.monkeypatch, dre=BANCO_DRE, bpp=BANCO_BPP)
        return {2025: ind}


def test_conta_sem_correspondencia_aparece_em_riscos_dados(tmp_path, monkeypatch):
    engine = _engine(
        monkeypatch,
        info={"currentPrice": 20.0, "quoteType": "EQUITY"},
        historico=_historico(20.0),
        cvm=_CVMBanco(tmp_path, monkeypatch),
    )
    dados = engine.buscar_dados_ticker("PETR4")
    riscos = [r for r in dados["riscos_dados"] if "patrimonio_liquido" in r]
    assert len(riscos) == 1
    assert "sem correspondência" in riscos[0]
    assert "2.03 'provisoes'" in riscos[0]
    assert dados.get("div_liq_patrimonio") is None


# ── modelo da companhia ──────────────────────────────────────────────────────


def _calcular_com_modelo(tmp_path, monkeypatch, modelo, *, dre, bpp):
    import tests.test_market_engine_acoes_cvm as base

    original = CVMProvider.calcular_indicadores
    monkeypatch.setattr(
        CVMProvider,
        "calcular_indicadores",
        lambda self, cd_cvm, anos=1: original(self, cd_cvm, anos, modelo=modelo),
    )
    return base._calcular(tmp_path, monkeypatch, dre=dre, bpp=bpp)


def test_banco_le_pl_e_lucro_pelo_modelo_financeiro(tmp_path, monkeypatch):
    ind = _calcular_com_modelo(
        tmp_path, monkeypatch, "banco", dre=BANCO_DRE, bpp=BANCO_BPP
    )
    # Como no F2A-3: o lucro dos controladores do banco sai da 3.11.01 ("aos sócios").
    assert ind["lucro_controladores"] == pytest.approx(16.0)
    # F2A-9: o PL (2.07) e o lucro (3.11) do banco vêm do modelo financeiro.
    assert ind["patrimonio_liquido"] == pytest.approx(190.0)
    assert ind["lucro_liquido"] == pytest.approx(17.0)
    # Lucro de não controladores sem a separação no balanço: o PL dos controladores se
    # abstém (D20, F2A-37).
    assert ind["pl_controladores"] is None
    assert ind["passivo_total"] == pytest.approx(2_000.0)
    assert set(ind["contas_abstidas"]) == {
        "ativo_circulante", "passivo_circulante", "ebit", "receita_liquida", "margem_liquida",
    }  # fmt: skip
    assert ind["contas_abstidas"]["receita_liquida"] == cvm_provider.MOTIVO_SEM_SIGNIFICADO_BANCO
    assert ind["contas_abstidas"]["ebit"].startswith(contas_cvm.MOTIVO_CAMPO_FORA_DO_MODELO)


def test_seguradora_le_o_lucro_na_3_13(tmp_path, monkeypatch):
    dre = [
        ("3.05", "Outras Receitas e Despesas Operacionais", 48.0),
        ("3.07", "Resultado Antes do Resultado Financeiro e dos Tributos", 98.0),
        ("3.11", "Resultado Líquido das Operações Continuadas", 90.0),
        ("3.13", "Lucro/Prejuízo Consolidado do Período", 90.0),
        ("3.13.01", "Atribuído a Sócios da Empresa Controladora", 89.0),
        ("3.13.02", "Atribuído a Sócios Não Controladores", 1.0),
    ]
    # F2A-37: com lucro de não controladores, o PL precisa da 2.03.09 separada (D20).
    bpp = [("2.03", "Patrimônio Líquido Consolidado", 900.0),
           ("2.03.09", "Participação dos Acionistas Não Controladores", 10.0)]  # fmt: skip
    ind = _calcular_com_modelo(tmp_path, monkeypatch, "seguradora", dre=dre, bpp=bpp)
    assert ind["ebit"] == pytest.approx(98.0)
    assert ind["lucro_liquido"] == pytest.approx(90.0)
    assert ind["lucro_controladores"] == pytest.approx(89.0)
    assert ind["roe"] == pytest.approx(89.0 / 890.0)


def test_controladora_sem_correspondencia_vale_o_lucro_total_como_no_f2a_3(
    tmp_path, monkeypatch
):
    # A revisão das reservas (D20) é do F2A-37; aqui o resultado do F2A-3 não muda.
    ind = _calcular(
        tmp_path, monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 1_000.0),
             ("3.11.01", "Outra Conta", 800.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 5_000.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] == pytest.approx(1_000.0)


def test_lucro_dos_controladores_invalido_abstem(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path, monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 1_000.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", float("nan"))],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 5_000.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] is None


@pytest.mark.parametrize(
    "minoritarios",
    # O valor NaN na linha dos não controladores saiu daqui no F2A-37: valor inválido nunca
    # autoriza reserva (`tests/test_cvm_controladores.py::test_valor_invalido_nao_autoriza_reserva`).
    [("3.11.02", "Outra Conta", 1_000.0)],
)  # fmt: skip
def test_controladora_zerada_e_minoritarios_nao_lidos_valem_o_total_como_no_f2a_3(
    tmp_path, monkeypatch, minoritarios
):
    ind = _calcular(
        tmp_path, monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 1_000.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", 0.0),
             minoritarios],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 5_000.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] == pytest.approx(1_000.0)


def test_banco_sem_setor_segue_com_o_lucro_dos_controladores(tmp_path, monkeypatch):
    # Sem setor, o modelo é o de empresa; a linha "aos sócios" do banco segue reconhecida.
    ind = _calcular(tmp_path, monkeypatch, dre=BANCO_DRE, bpp=BANCO_BPP)
    assert ind["lucro_controladores"] == pytest.approx(16.0)


def test_banco_sem_linha_da_controladora_usa_o_lucro_do_banco(tmp_path, monkeypatch):
    ind = _calcular_com_modelo(
        tmp_path, monkeypatch, "banco", dre=BANCO_DRE[:1], bpp=BANCO_BPP
    )
    assert ind["lucro_liquido"] == pytest.approx(17.0)  # F2A-9: modelo de banco
    assert ind["lucro_controladores"] == pytest.approx(17.0)


def test_controladora_zerada_sem_linha_de_minoritarios_vale_o_total(
    tmp_path, monkeypatch
):
    ind = _calcular(
        tmp_path, monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 1_000.0),
             ("3.11.01", "Atribuído a Sócios da Empresa Controladora", 0.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 5_000.0)],
    )  # fmt: skip
    assert ind["lucro_controladores"] == pytest.approx(1_000.0)


def test_pl_dos_controladores_desconta_os_minoritarios(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path, monkeypatch,
        dre=[("3.11", "Lucro/Prejuízo Consolidado do Período", 100.0)],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 1_000.0),
             ("2.03.09", "Participação dos Acionistas Não Controladores", 200.0)],
    )  # fmt: skip
    assert ind["pl_controladores"] == pytest.approx(800.0)
    assert ind["patrimonio_liquido"] == pytest.approx(1_000.0)


def test_valor_invalido_vai_para_contas_abstidas(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path, monkeypatch,
        dre=[("3.01", "Receita de Venda de Bens e/ou Serviços", float("nan"))],
        bpp=[("2.03", "Patrimônio Líquido Consolidado", 1_000.0)],
    )  # fmt: skip
    assert ind["receita_liquida"] is None
    assert ind["contas_abstidas"]["receita_liquida"] == (
        f"{contas_cvm.MOTIVO_VALOR_INVALIDO} (3.01 'receita de venda de bens e/ou servicos')"
    )
    assert "ebit" not in ind["contas_abstidas"]  # linha ausente não é registrada


class _CVMQueGuardaOModelo:
    def __init__(self):
        self.chamadas = []

    def calcular_indicadores(self, cd_cvm, anos=1, **kwargs):
        self.chamadas.append(kwargs)
        return {}


@pytest.mark.parametrize(
    ("setor", "esperado"),
    [(None, {}), ("Bancos", {"modelo": "banco"}),
     ("Seguradoras e Corretoras", {"modelo": "seguradora"}), ("Petróleo e Gás", {})],
)  # fmt: skip
def test_cascata_passa_o_modelo_do_setor(monkeypatch, setor, esperado):
    cvm = _CVMQueGuardaOModelo()
    engine = _engine(monkeypatch, info={"currentPrice": 20.0}, cvm=cvm)
    dados = {"setor": setor, "cd_cvm": 9512, "riscos_dados": []}  # F2A-31: CD_CVM do índice
    engine._buscar_cvm("PETR4", dados)
    assert cvm.chamadas == [esperado]
