"""Exemplos independentes da ficha qualidade 1.0, não saída do motor."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from sentinela.methods.qualidade import Qualidade

AS_OF = datetime(2026, 10, 20, 18, tzinfo=UTC)


def documentos():
    return [
        {
            "exercicio": ano,
            "inicio": f"{ano}-01-01",
            "fim": f"{ano}-12-31",
            "dt_refer": f"{ano}-12-31",
            "versao": "1",
            "lucro_controladores": lucro,
            "pl_inicial_controladores": 100,
            "lucro_liquido": consolidado,
            "receita_liquida": 100,
            "divida_liquida": 30,
            "ebitda": -5 if ano == 2025 else 10,
            "perimetro": "controladores",
            "evidencia_comparabilidade": "notas conciliadas",
            "proveniencia": {
                "fonte": "DFP sintética independente",
                "data_entrega": "2026-03-01",
                "data_coleta": "2026-03-02T12:00:00+00:00",
            },
            "proventos_b3": {
                "valor": distribuicao,
                "cobertura_integral": True,
                "inicio": f"{ano}-01-01",
                "fim": f"{ano}-12-31",
                "fonte": "B3 sintética por data-ex",
                "coleta": "2026-03-02T12:00:00+00:00",
            },
        }
        for ano, lucro, consolidado, distribuicao in zip(
            range(2021, 2026),
            [10, 12, -2, 15, 15],
            [12, 14, -1, 16, 17],
            [1, 0, 1, 2, 2],
            strict=True,
        )
    ]


def quadro(registros=None, **kw):
    return Qualidade().calcular(
        documentos() if registros is None else registros,
        as_of=AS_OF,
        classe="STOCK",
        modelo=kw.pop("modelo", "empresa"),
        **kw,
    )


def test_exemplo_independente_da_ficha():
    r = quadro()
    assert r["roe"]["media"] == pytest.approx(0.1)
    assert r["roe"]["desvio_populacional_pp"] == pytest.approx(6.292853089)
    assert r["roe"]["minimo"] == -0.02 and r["roe"]["maximo"] == 0.15
    assert r["lucros"]["positivos"] == 4 and r["lucros"]["observados"] == 5
    assert r["margem_consolidada"]["minimo"] == -0.01
    assert r["margem_consolidada"]["ultimo"] == 0.17
    assert r["alavancagem"]["minimo"] == 3
    assert r["alavancagem"]["ultimo"] is None
    assert "EBITDA não positivo" in r["exercicios"][-1]["motivos"]["alavancagem"]
    assert r["proventos"]["positivos"] == 4 and r["proventos"]["observados"] == 5
    assert not ({"score", "valor", "classificacao", "pesos"} & r.keys())


def test_quatro_anos_nao_sao_cinco():
    r = quadro(documentos()[:-1])
    assert r["cobertura"] == {"observados": 4, "esperados": 5, "completa": False}
    assert r["lucros"]["positivos"] == 3 and r["lucros"]["observados"] == 4


@pytest.mark.parametrize(
    "valor", [None, float("nan"), float("inf"), float("-inf"), True, "10"]
)
def test_lucro_invalido_nao_vira_zero(valor):
    docs = documentos()
    docs[-1]["lucro_controladores"] = valor
    r = quadro(docs)
    assert r["lucros"]["observados"] == 4
    assert r["roe"]["observados"] == 4
    assert r["exercicios"][-1]["lucro_controladores"] is None


@pytest.mark.parametrize("valor", [0, -100, None])
def test_pl_inicial_nao_positivo_ou_ausente(valor):
    docs = documentos()
    docs[0]["pl_inicial_controladores"] = valor
    r = quadro(docs)
    assert r["roe"]["observados"] == 4
    assert r["lucros"]["observados"] == 5
    assert r["exercicios"][0]["roe"] is None


def test_provento_ausente_difere_zero_com_fonte():
    docs = documentos()
    docs[1].pop("proventos_b3")
    r = quadro(docs)
    assert r["proventos"]["positivos"] == 4 and r["proventos"]["observados"] == 4
    assert quadro()["proventos"]["observados"] == 5


def test_banco_sem_razao_empresarial():
    r = quadro(modelo="banco")
    assert r["roe"]["observados"] == 5
    assert r["margem_consolidada"]["motivo"] == "não aplicável ao modelo banco"
    assert r["alavancagem"]["observados"] == 0


@pytest.mark.parametrize("modelo", [None, "seguradora", "desconhecido"])
def test_modelo_sem_ficha_nao_certifica(modelo):
    r = quadro(modelo=modelo)
    assert r["cobertura"]["observados"] == 0 and r["motivo"]


def test_ruptura_nao_herda_dispensa_graham_lynch():
    docs = documentos()
    docs[2]["evidencia_comparabilidade"] = None
    r = quadro(docs)
    assert r["roe"]["media"] is None
    assert r["lucros"]["positivos"] is None
    assert r["exercicios"][0]["roe"] == 0.1
    assert r["comparavel"] is False


def test_fontes_futuras_nao_entram():
    docs = documentos()
    docs[-1]["proveniencia"]["data_coleta"] = "2027-01-01T12:00:00+00:00"
    assert quadro(docs)["lucros"]["observados"] == 4


def test_sensibilidades_independentes():
    docs = documentos()
    docs[-1]["lucro_controladores"] = 25
    assert quadro(docs)["roe"]["media"] == pytest.approx(0.12)
    original = deepcopy(documentos())
    juros = deepcopy(original)
    for e in juros:
        e.update(selic=0.90, ntnb=0.80)
    assert quadro(original) == quadro(juros)


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("inicio", "2021-01-02"),
        ("inicio", "sem data"),
        ("fim", "2030-12-31"),
        ("dt_refer", "2020-12-31"),
        ("versao", None),
    ],
)
def test_janela_documental_invalida_por_ano(campo, valor):
    docs = documentos()
    docs[0][campo] = valor
    r = quadro(docs)
    assert r["exercicios"][0]["lucro_controladores"] is None
    assert r["cobertura"]["completa"] is False
    assert r["lucros"]["observados"] == 4


@pytest.mark.parametrize(
    "prov",
    [
        None,
        [],
        {},
        {"fonte": "CVM"},
        {"fonte": "CVM", "data_coleta": "ontem", "data_entrega": "2026-03-01"},
        {
            "fonte": "CVM",
            "data_coleta": "2026-03-02T12:00:00",
            "data_entrega": "2026-03-01",
        },
        {
            "fonte": "CVM",
            "data_coleta": "2026-03-02T12:00:00+00:00",
            "data_entrega": "2026-10-20",
        },
        {"fonte": "CVM", "data_coleta": "2026-03-02T12:00:00+00:00"},
    ],
)
def test_proveniencia_documental_sem_evidencia(prov):
    docs = documentos()
    docs[0]["proveniencia"] = prov
    r = quadro(docs)
    assert r["lucros"]["observados"] == 4 and r["cobertura"]["observados"] == 4


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("perimetro", "outro"),
        ("perimetro", {}),
        ("perimetro", None),
        ("evidencia_comparabilidade", ""),
        ("evidencia_comparabilidade", True),
        ("mudanca_estrutural_sem_reconciliacao", True),
    ],
)
def test_metadados_nao_atestam_comparabilidade(campo, valor):
    docs = documentos()
    docs[0][campo] = valor
    r = quadro(docs)
    assert r["comparavel"] is False and r["roe"]["media"] is None
    assert r["exercicios"][0]["lucro_controladores"] == 10


@pytest.mark.parametrize("receita", [0, -100, None, float("nan")])
def test_margem_com_denominador_nao_positivo(receita):
    docs = documentos()
    docs[0]["receita_liquida"] = receita
    r = quadro(docs)
    assert r["margem_consolidada"]["observados"] == 4
    assert r["roe"]["observados"] == 5


@pytest.mark.parametrize(
    "divida,ebitda,trecho",
    [
        (30, 0, "positiva"),
        (0, -1, "não positiva"),
        (-30, -1, "não positiva"),
        (None, 10, "não demonstrada"),
        (30, None, "EBITDA não demonstrado"),
    ],
)
def test_alavancagem_sinais_sem_numero_inventado(divida, ebitda, trecho):
    docs = documentos()
    docs[0].update(divida_liquida=divida, ebitda=ebitda)
    r = quadro(docs)
    assert r["exercicios"][0]["alavancagem"] is None
    assert trecho in r["exercicios"][0]["motivos"]["alavancagem"]
    assert r["exercicios"][0]["divida_liquida"] == divida


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("valor", -1),
        ("valor", None),
        ("valor", float("inf")),
        ("valor", True),
        ("cobertura_integral", False),
        ("inicio", "2020-01-01"),
        ("fim", "2020-12-31"),
        ("fonte", None),
        ("coleta", "2027-01-01T00:00:00+00:00"),
    ],
)
def test_proventos_incompletos_nao_contam_como_ano_zero(campo, valor):
    docs = documentos()
    docs[0]["proventos_b3"][campo] = valor
    r = quadro(docs)
    assert r["proventos"]["observados"] == 4
    assert r["exercicios"][0]["proventos"] is None


def test_zero_lucro_e_divida_negativa_observados():
    docs = documentos()
    docs[0].update(lucro_controladores=0, divida_liquida=-30)
    r = quadro(docs)
    assert r["lucros"]["observados"] == 5 and r["lucros"]["positivos"] == 3
    assert r["exercicios"][0]["roe"] == 0 and r["exercicios"][0]["alavancagem"] == -3


@pytest.mark.parametrize(
    "registros",
    [[None], [{"exercicio": True}], [{"exercicio": 2025}, {"exercicio": 2025}]],
)
def test_identidade_ambigua_nao_escolhe_documento(registros):
    r = quadro(registros)
    assert r["exercicios"] == [] and r["motivo"]


def test_asof_sem_fuso_e_classe_fii_ficam_fora():
    assert (
        Qualidade().calcular(
            documentos(),
            as_of=AS_OF.replace(tzinfo=None),
            classe="STOCK",
            modelo="empresa",
        )["motivo"]
        == "as_of exige fuso horário"
    )
    assert (
        Qualidade().calcular(documentos(), as_of=AS_OF, classe="FII", modelo="empresa")[
            "cobertura"
        ]["observados"]
        == 0
    )


def test_estatistica_nao_representavel_tem_motivo():
    docs = documentos()
    for e in docs:
        e.update(
            lucro_controladores=1e308 if e["exercicio"] % 2 else -1e308,
            pl_inicial_controladores=1,
        )
    r = quadro(docs)
    assert r["roe"]["media"] is None and r["roe"]["desvio_populacional_pp"] is None
    assert r["roe"]["motivo"] == "estatística não representável"
