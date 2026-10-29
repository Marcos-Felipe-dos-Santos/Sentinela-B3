"""Data-ex é o pregão após data-com; DVA não supre calendário/cobertura B3."""

from datetime import date, timedelta

from sentinela.data.qualidade_inputs import entradas
from tests.test_qualidade import AS_OF, documentos


def dados():
    inicio, fim = date(2019, 12, 1), date(2026, 1, 15)
    pregoes = [
        (inicio + timedelta(days=n)).isoformat()
        for n in range((fim - inicio).days + 1)
        if (inicio + timedelta(days=n)).weekday() < 5
    ]
    registros = [
        {
            "typeStock": "ON",
            "lastDatePriorEx": "10/06/2020",
            "dateApproval": "01/06/2020",
            "corporateAction": "DIVIDENDO",
            "valueCash": "1",
            "quotedPerShares": "1",
        },
        {
            "typeStock": "ON",
            "lastDatePriorEx": "31/12/2021",
            "dateApproval": "01/12/2021",
            "corporateAction": "DIVIDENDO",
            "valueCash": "1",
            "quotedPerShares": "1",
        },
    ]
    return {
        "classe_ativo": "STOCK",
        "especie": "ON",
        "serie_cvm": {"exercicios": documentos()},
        "proventos_b3": {
            "registros": registros,
            "total": 2,
            "coleta": "2026-03-02T12:00:00+00:00",
            "proveniencia": {"fonte": "B3 sintética"},
            "eventos_acoes": [],
        },
        "calendario_proventos_b3": {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "pregoes": pregoes,
            "fonte": "calendário sintético completo",
            "coleta": "2026-03-02T12:00:00+00:00",
        },
    }


def test_ano_data_ex_e_nao_ano_data_com():
    r = entradas(dados(), AS_OF)
    assert r[0]["proventos_b3"]["valor"] == 0
    assert r[1]["proventos_b3"]["valor"] == 1
    assert r[1]["proventos_b3"]["cobertura_integral"] is True


def test_sem_calendario_anual_nao_inventa_zero():
    d = dados()
    d.pop("calendario_proventos_b3")
    r = entradas(d, AS_OF)
    assert r[0]["proventos_b3"]["valor"] is None
    assert "calendário" in r[0]["proventos_b3"]["motivo"]
    assert r[0]["lucro_controladores"] == 10


def test_sem_relacao_nao_usa_dva_nem_bloco_precalculado():
    d = dados()
    d.pop("proventos_b3")
    d["serie_cvm"]["exercicios"][0].update(dividendos=100, jcp=200)
    assert entradas(d, AS_OF)[0]["proventos_b3"]["valor"] is None


def test_coleta_futura_nao_prova_historico():
    d = dados()
    d["proventos_b3"]["coleta"] = "2027-01-01T12:00:00+00:00"
    assert entradas(d, AS_OF)[0]["proventos_b3"]["valor"] is None


import pytest


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("total", 3),
        ("total", True),
        ("abstencao", "fonte recusada"),
        ("coleta", "inválido"),
        ("coleta", "2026-03-02T12:00:00"),
        ("proveniencia", {}),
        ("proveniencia", None),
    ],
)
def test_relacao_sem_evidencia_nao_e_ano_zero(campo, valor):
    d = dados()
    d["proventos_b3"][campo] = valor
    r = entradas(d, AS_OF)
    assert all(e["proventos_b3"]["valor"] is None for e in r)
    assert all(e["proventos_b3"]["motivo"] for e in r)


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("fonte", None),
        ("coleta", "2027-01-01T12:00:00+00:00"),
        ("inicio", "2021-01-01"),
        ("fim", "2021-12-31"),
        ("pregoes", ["não é data"]),
    ],
)
def test_calendario_incompleto_nao_e_cobertura(campo, valor):
    d = dados()
    d["calendario_proventos_b3"][campo] = valor
    assert entradas(d, AS_OF)[0]["proventos_b3"]["valor"] is None


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("valueCash", "-1"),
        ("valueCash", "NaN"),
        ("quotedPerShares", "100"),
        ("corporateAction", "RENDIMENTO"),
        ("lastDatePriorEx", "sem data"),
        ("typeStock", None),
    ],
)
def test_evento_invalido_recusa_indicador_com_motivo(campo, valor):
    d = dados()
    d["proventos_b3"]["registros"][1][campo] = valor
    r = entradas(d, AS_OF)
    assert r[1]["proventos_b3"]["valor"] is None and r[1]["proventos_b3"]["motivo"]


def test_unidade_sem_componente_nao_supre_com_unt():
    d = dados()
    d.update(classe_ativo="UNIT", acoes_por_unit={"ON": 1, "PN": 2})
    assert entradas(d, AS_OF)[0]["proventos_b3"]["valor"] is None


def test_sem_historico_sem_source_de_ano_zero():
    d = dados()
    d["proventos_b3"]["registros"] = d["proventos_b3"]["registros"][1:]
    d["proventos_b3"]["total"] = 1
    assert entradas(d, AS_OF)[0]["proventos_b3"]["valor"] is None


def test_asof_sem_fuso_e_serie_malformada():
    assert entradas({}, AS_OF) == []
    assert entradas({"serie_cvm": {"exercicios": "2021"}}, AS_OF) == []
    assert (
        entradas(dados(), AS_OF.replace(tzinfo=None))[0]["proventos_b3"]["valor"]
        is None
    )


def test_exercicio_fiscal_nao_anual_nao_e_regularidade():
    d = dados()
    d["serie_cvm"]["exercicios"][0]["inicio"] = "2021-03-01"
    assert entradas(d, AS_OF)[0]["proventos_b3"]["valor"] is None


def test_cobertura_certificada_preserva_fonte_calendario_e_janela_sem_mutar():
    from copy import deepcopy

    d = dados()
    original = deepcopy(d)
    anual = entradas(d, AS_OF)[1]["proventos_b3"]
    assert anual == {
        "valor": 1.0,
        "cobertura_integral": True,
        "inicio": "2022-01-01",
        "fim": "2022-12-31",
        "fonte": "B3 sintética",
        "coleta": "2026-03-02T12:00:00+00:00",
        "calendario": {k: d["calendario_proventos_b3"][k] for k in ("fonte", "inicio", "fim", "coleta")},
    }
    assert d == original


@pytest.mark.parametrize("bloco", ["proventos_b3", "calendario_proventos_b3"])
@pytest.mark.parametrize("campo,valor", [("fonte", "   "), ("fonte", 123), ("coleta", None), ("coleta", "inválido"), ("coleta", "2026-03-02T12:00:00")])
def test_prova_anual_exige_fonte_textual_e_instante_com_fuso(bloco, campo, valor):
    d = dados()
    alvo = d[bloco]["proveniencia"] if bloco == "proventos_b3" and campo == "fonte" else d[bloco]
    alvo[campo] = valor
    for e in entradas(d, AS_OF):
        assert e["proventos_b3"]["cobertura_integral"] is False
        assert e["proventos_b3"]["valor"] is None
        assert e["proventos_b3"]["motivo"]


def test_coleta_exatamente_no_asof_e_admitida():
    d = dados()
    for bloco in ("proventos_b3", "calendario_proventos_b3"):
        d[bloco]["coleta"] = AS_OF.isoformat()
    assert entradas(d, AS_OF)[1]["proventos_b3"]["valor"] == 1
