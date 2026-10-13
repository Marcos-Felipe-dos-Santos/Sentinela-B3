"""Funções puras de `sentinela.data.acoes_cvm` (F2A-3): escala, abstenções, unit e divergência."""

import pytest

from sentinela.data.acoes_cvm import (
    FAIXA_DA_ESCALA,
    MOTIVO_CLASSES_PREFERENCIAIS,
    MOTIVO_ESCALA,
    MOTIVO_LINHAS_CONFLITANTES,
    MOTIVO_LUCRO_ZERO,
    MOTIVO_ROE_PL,
    MOTIVO_ROE_SEM_LUCRO,
    MOTIVO_ROE_SEM_PL,
    MOTIVO_SEM_COMPOSICAO,
    MOTIVO_SEM_RECALCULADO,
    MOTIVO_SINAL_CONSOLIDADO,
    MOTIVO_SINAL_CONTROLADORES,
    MOTIVO_SINAL_NAO_CONFERIVEL,
    MOTIVO_TOTAL,
    MOTIVO_UNIT,
    NOTA_FIM_DO_PERIODO,
    NOTA_RECALCULADO,
    NOTA_SINAL_CONSOLIDADO,
    Abstencao,
    Composicao,
    LpaDivulgado,
    PorAcao,
    derivar_por_acao,
    divergencia_acoes,
    divulgado_da_escala,
    divulgados_coerentes,
    inferir_escala,
    lpa_dos_metodos,
    roe_dos_controladores,
)
from sentinela.domain.units import Escala


def _cc(on=700.0, pn=400.0, tes_on=60.0, tes_pn=40.0, tes_total=None):
    return Composicao(
        on=on, pn=pn, tesouraria_on=tes_on, tesouraria_pn=tes_pn,
        tesouraria_total=tes_on + tes_pn if tes_total is None else tes_total,
        dt_refer="2025-12-31", versao="1",
    )  # fmt: skip


def _derivar(**campos):
    base = dict(
        lucro_controladores=2_000.0, pl_controladores=10_000.0, composicao=_cc(),
        motivo_composicao=None, lpa_divulgado=2.0, preco=20.0, eh_unit=False,
        acoes_por_unit=None,
    )  # fmt: skip
    return derivar_por_acao(**{**base, **campos})


# ── composição ───────────────────────────────────────────────────────────────


def test_total_e_on_mais_pn_menos_a_tesouraria_total():
    assert _cc().total == pytest.approx(1_000.0)
    assert _cc(tes_total=0.0).total == pytest.approx(1_100.0)


# ── escala ───────────────────────────────────────────────────────────────────


def test_escala_unidade():
    assert inferir_escala(2_000.0, 1_000.0, 2.0) == (Escala.UNIDADE, pytest.approx(1.0))


def test_escala_mil():
    escala, razao = inferir_escala(2_000_000.0, 1_000.0, 1.6)
    assert escala is Escala.MIL
    assert razao == pytest.approx(1.25)


def test_prejuizo_com_lpa_negativo_tambem_determina_a_escala():
    assert inferir_escala(-500.0, 1_000.0, -0.5) == (Escala.UNIDADE, pytest.approx(1.0))


@pytest.mark.parametrize(
    ("lucro", "acoes", "lpa"),
    [
        (None, 1_000.0, 2.0),
        (0.0, 1_000.0, 2.0),
        (2_000.0, 1_000.0, None),
        (2_000.0, 1_000.0, 0.0),
        (2_000.0, 0.0, 2.0),
        (2_000.0, -5.0, 2.0),
        (2_000.0, 1_000.0, -2.0),
        (-2_000.0, 1_000.0, 2.0),
    ],
)
def test_escala_sem_insumo_ou_com_sinais_trocados_fica_indeterminada(lucro, acoes, lpa):
    assert inferir_escala(lucro, acoes, lpa) is None


def test_limites_da_faixa_da_escala():
    baixo, alto = FAIXA_DA_ESCALA
    assert (baixo, alto) == (0.1, 10.0)
    assert inferir_escala(100.0, 1_000.0, 1.0) == (Escala.UNIDADE, pytest.approx(0.1))
    assert inferir_escala(99.9, 1_000.0, 1.0) is None
    assert inferir_escala(10_000.0, 1_000.0, 1.0) == (
        Escala.UNIDADE,
        pytest.approx(10.0),
    )
    assert inferir_escala(10_001.0, 1_000.0, 1.0) is None


def test_escala_escolhe_a_mais_perto_de_1_em_log():
    # Razão 4 na unidade e 0,004 no milhar: vale a unidade, mesmo longe de 1.
    assert inferir_escala(4_000.0, 1_000.0, 1.0)[0] is Escala.UNIDADE
    # Razão 40 na unidade e 0,04 no milhar: as duas estão fora da faixa.
    assert inferir_escala(40_000.0, 1_000.0, 1.0) is None


# ── derivação ────────────────────────────────────────────────────────────────


def test_derivacao_completa():
    r = _derivar()
    assert isinstance(r, PorAcao)
    assert r.acoes.valor == pytest.approx(1_000.0)
    assert r.acoes.escala is Escala.UNIDADE
    assert r.escala is Escala.UNIDADE
    assert r.razao_lpa == pytest.approx(1.0)
    assert (r.lpa, r.vpa, r.pl, r.pvp) == pytest.approx((2.0, 10.0, 10.0, 2.0))


def test_derivacao_em_milhares():
    r = _derivar(lucro_controladores=2_000_000.0, pl_controladores=10_000_000.0)
    assert r.escala is Escala.MIL
    assert r.acoes.valor == pytest.approx(1_000_000.0)
    assert (r.lpa, r.vpa) == pytest.approx((2.0, 10.0))


def test_detalhe_traz_documento_escala_e_nota():
    documento = {"cnpj": "1", "dt_refer": "2025-12-31", "versao": "1"}
    assert _derivar().detalhe(documento) == {
        "documento": documento,
        "escala": "UNIDADE",
        "acoes": 1_000.0,
        "razao_lpa_calculado_sobre_divulgado": pytest.approx(1.0),
        "nota": NOTA_FIM_DO_PERIODO,
    }


@pytest.mark.parametrize(
    ("campos", "motivo"),
    [
        ({"composicao": None}, MOTIVO_SEM_COMPOSICAO),
        ({"composicao": None, "motivo_composicao": "outro"}, "outro"),
        ({"eh_unit": True, "acoes_por_unit": None}, MOTIVO_UNIT),
        ({"eh_unit": True, "acoes_por_unit": {}}, MOTIVO_UNIT),
        ({"composicao": _cc(on=0.0, pn=0.0, tes_on=0.0, tes_pn=0.0)}, MOTIVO_TOTAL),
        ({"composicao": _cc(on=50.0, pn=50.0, tes_on=60.0, tes_pn=40.0)}, MOTIVO_TOTAL),
        ({"lpa_divulgado": None}, MOTIVO_ESCALA),
        ({"lucro_controladores": None}, MOTIVO_ESCALA),
    ],
)
def test_abstencoes(campos, motivo):
    assert _derivar(**campos) == Abstencao(motivo)


def test_sem_pl_deriva_so_o_lpa():
    r = _derivar(pl_controladores=None)
    assert (r.lpa, r.pl) == pytest.approx((2.0, 10.0))
    assert r.vpa is None and r.pvp is None


def test_sem_preco_valido_nao_ha_multiplos():
    for preco in (None, 0.0, -1.0):
        r = _derivar(preco=preco)
        assert r.lpa == pytest.approx(2.0)
        assert r.pl is None and r.pvp is None


def test_prejuizo_da_pl_negativo_como_na_v1():
    r = _derivar(lucro_controladores=-2_000.0, lpa_divulgado=-2.0)
    assert r.lpa == pytest.approx(-2.0)
    assert r.pl == pytest.approx(-10.0)


def test_pl_zero_nao_divide():
    r = _derivar(pl_controladores=0.0)
    assert r.vpa == pytest.approx(0.0)
    assert r.pvp is None


def test_unit_multiplica_lpa_e_vpa_pelas_acoes_da_unit():
    r = _derivar(eh_unit=True, acoes_por_unit={"ON": 1, "PN": 4})
    assert (r.lpa, r.vpa) == pytest.approx((10.0, 50.0))
    assert (r.pl, r.pvp) == pytest.approx((2.0, 0.4))
    assert r.acoes.valor == pytest.approx(1_000.0)


def test_acoes_por_unit_ignoradas_quando_nao_e_unit():
    r = _derivar(eh_unit=False, acoes_por_unit={"ON": 1, "PN": 4})
    assert r.lpa == pytest.approx(2.0)


# ── divergência ──────────────────────────────────────────────────────────────


def _div(**campos):
    base = dict(
        especie="ON", eh_unit=False, acoes_por_unit=None, shares_outstanding=640.0
    )
    return divergencia_acoes(_cc(), Escala.UNIDADE, **{**base, **campos})


def test_divergencia_on_desconta_a_tesouraria_on():
    assert _div() == {
        "especie": "ON",
        "acoes_cvm": 640.0,
        "acoes_yfinance": 640.0,
        "diferenca": pytest.approx(0.0),
    }


def test_divergencia_pn_desconta_a_tesouraria_pn():
    d = _div(especie="PN", shares_outstanding=720.0)
    assert (d["especie"], d["acoes_cvm"], d["diferenca"]) == (
        "PN",
        360.0,
        pytest.approx(1.0),
    )


def test_divergencia_de_unit_usa_o_total_sobre_as_acoes_da_unit():
    d = _div(eh_unit=True, acoes_por_unit={"ON": 1, "PN": 4}, shares_outstanding=150.0)
    assert d == {
        "especie": "UNIT",
        "acoes_cvm": pytest.approx(200.0),
        "acoes_yfinance": 150.0,
        "diferenca": pytest.approx(-0.25),
    }


def test_divergencia_converte_a_escala():
    d = divergencia_acoes(
        _cc(), Escala.MIL, especie="ON", eh_unit=False, acoes_por_unit=None,
        shares_outstanding=640_000.0,
    )  # fmt: skip
    assert d["acoes_cvm"] == pytest.approx(640_000.0)
    assert d["diferenca"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    "campos",
    [
        {"shares_outstanding": None},
        {"shares_outstanding": 0.0},
        {"shares_outstanding": -1.0},
        {"especie": None},
        {"especie": "PNA"},
        {"eh_unit": True, "acoes_por_unit": None},
    ],
)
def test_divergencia_sem_insumo_e_none(campos):
    assert _div(**campos) is None


def test_divergencia_com_especie_zerada_e_none():
    cc = _cc(on=60.0)
    assert (
        divergencia_acoes(
            cc,
            Escala.UNIDADE,
            especie="ON",
            eh_unit=False,
            acoes_por_unit=None,
            shares_outstanding=10.0,
        )  # fmt: skip
        is None
    )


# ── ROE ──────────────────────────────────────────────────────────────────────


def test_roe_dos_controladores():
    assert roe_dos_controladores(200.0, 1_000.0) == (pytest.approx(0.2), None)


@pytest.mark.parametrize(
    ("lucro", "pl", "motivo"),
    [
        (-200.0, -1_000.0, MOTIVO_ROE_PL),
        (200.0, 0.0, MOTIVO_ROE_PL),
        (200.0, None, MOTIVO_ROE_SEM_PL),
        (None, 1_000.0, MOTIVO_ROE_SEM_LUCRO),
    ],
)
def test_roe_abstem(lucro, pl, motivo):
    assert roe_dos_controladores(lucro, pl) == (None, motivo)


# ── LPA dos métodos (F2A-36, D19) ────────────────────────────────────────────


def test_divulgados_conferem_cada_classe_pelo_sinal_do_lucro():
    linhas = {"ON": [1.0, 2.0], "PN": [-0.5, -0.5], "PNA": [0.5]}
    assert divulgados_coerentes(linhas, -100.0, None) == {
        "ON": Abstencao(MOTIVO_LINHAS_CONFLITANTES),
        "PN": LpaDivulgado(-0.5),
        "PNA": Abstencao(MOTIVO_SINAL_CONTROLADORES),
    }
    assert divulgados_coerentes({"PN": [0.5]}, 0.0, 10.0) == {
        "PN": Abstencao(MOTIVO_LUCRO_ZERO)
    }
    assert divulgados_coerentes({"PN": [0.5]}, 0.5, None) == {"PN": LpaDivulgado(0.5)}


def test_sem_controladores_o_consolidado_confere_e_marca():
    assert divulgados_coerentes({"ON": [0.2], "PN": [-0.2]}, None, 0.5) == {
        "ON": LpaDivulgado(0.2, NOTA_SINAL_CONSOLIDADO),
        "PN": Abstencao(MOTIVO_SINAL_CONSOLIDADO),
    }
    assert divulgados_coerentes({"ON": [0.2]}, None, None) == {
        "ON": Abstencao(MOTIVO_SINAL_NAO_CONFERIVEL)
    }
    assert divulgados_coerentes({"ON": [0.2]}, None, float("nan")) == {
        "ON": Abstencao(MOTIVO_SINAL_NAO_CONFERIVEL)
    }


def test_escala_usa_on_depois_pn_depois_as_classes():
    conflito = Abstencao("x")
    assert (
        divulgado_da_escala({"PNB": LpaDivulgado(3.0), "PNA": LpaDivulgado(2.0)}) == 2.0
    )
    assert (
        divulgado_da_escala({"PN": LpaDivulgado(2.0), "ON": LpaDivulgado(1.0)}) == 1.0
    )
    assert divulgado_da_escala({"ON": conflito, "PN": LpaDivulgado(2.0)}) == 2.0
    assert divulgado_da_escala({"ON": conflito}) is None


def _metodos(**campos):
    base = {
        "especie": "PN", "classe": "PN", "classes_preferenciais": None, "eh_unit": False,
        "acoes_por_unit": None, "divulgados": {}, "recalculado": 2.0,
    }  # fmt: skip
    return lpa_dos_metodos(**{**base, **campos})


def test_classe_sem_linha_propria_usa_a_da_especie_com_uma_so_classe():
    valor, detalhe = _metodos(
        classe="PNA",
        classes_preferenciais=["PNA"],
        divulgados={"PN": LpaDivulgado(2.5)},
    )
    assert (valor, detalhe["classe"], detalhe["origem"]) == (2.5, "PN", "divulgado")


def test_sem_divulgado_nem_recalculado_abstem():
    assert _metodos(recalculado=None) == Abstencao(MOTIVO_SEM_RECALCULADO)
    assert _metodos(classe=None, especie=None) == (
        2.0,
        {"origem": "recalculado", "classe": None, "notas": [NOTA_RECALCULADO]},
    )
    assert _metodos(classe=None)[1]["classe"] == "PN"


def test_uma_classe_preferencial_nao_bloqueia_o_recalculado():
    assert _metodos(classes_preferenciais=["PNA", "ONA"])[0] == 2.0
    assert _metodos(classes_preferenciais=["PNA", "PNB"]) == Abstencao(
        MOTIVO_CLASSES_PREFERENCIAIS
    )
    assert (
        _metodos(especie="ON", classe="ON", classes_preferenciais=["PNA", "PNB"])[0]
        == 2.0
    )


def test_unit_soma_componentes_e_junta_as_notas():
    divulgados = {"ON": LpaDivulgado(1.0, NOTA_SINAL_CONSOLIDADO)}
    valor, detalhe = _metodos(
        eh_unit=True, acoes_por_unit={"ON": 1, "PN": 2}, divulgados=divulgados
    )
    assert valor == pytest.approx(1.0 + 2 * 2.0)
    assert detalhe["notas"] == [NOTA_SINAL_CONSOLIDADO, NOTA_RECALCULADO]
    assert detalhe["componentes"]["PN"]["origem"] == "recalculado"
    dois_recalculados = _metodos(eh_unit=True, acoes_por_unit={"ON": 1, "PN": 2})
    assert dois_recalculados[1]["notas"] == [NOTA_RECALCULADO]
    assert _metodos(eh_unit=True, acoes_por_unit=None) == Abstencao(MOTIVO_UNIT)
    sem_recalculado = _metodos(eh_unit=True, acoes_por_unit={"ON": 1}, recalculado=None)
    assert sem_recalculado.motivo.endswith("(ON da unit)")
