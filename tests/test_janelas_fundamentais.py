"""FichasGraham/Lynch aprovadas: exemplos externos, continuidade e disponibilidade."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from sentinela.data.janelas_fundamentais import entradas

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)


def sem_valor(resultado: dict, motivo: str) -> bool:
    """Abstenção mantém a causa e não fornece número; metadados são permitidos."""
    return (
        resultado.get("abstencao") == motivo
        and "lpa" not in resultado
        and "vpa" not in resultado
    )


def dados_exemplo():
    anos = list(range(2021, 2026))
    return {
        "serie_cvm": {
            "exercicios": [
                {
                    "exercicio": a,
                    "acoes": 100,
                    "inicio": f"{a}-01-01",
                    "fim": f"{a}-12-31",
                    "lpa": l,
                    "vpa": 20,
                    "perimetro": "controladores",
                    "evidencia_comparabilidade": "documentos sintéticos reconciliados",
                    "proveniencia": {
                        "fonte": "DFP sintética",
                        "data_entrega": "2026-02-12",
                        "data_coleta": "2026-03-01T12:00:00+00:00",
                    },
                }
                for a, l in zip(anos, [1, 2, 3, 4, 5])
            ]
        },
        "reconciliacao_serie": {
            "fonte": "eventos oficiais sintéticos",
            "inicio": "2021-01-01",
            "fim": "2025-12-31",
            "coleta": "2026-03-01T12:00:00+00:00",
            "fatores": {str(a): 1 for a in anos},
        },
        "ipca_serie": {
            "fonte": "IBGE sintético",
            "coleta": "2026-03-01T12:00:00+00:00",
            "indices": {
                f"{a}-12": 100 / f for a, f in zip(anos, [1.2, 1.15, 1.1, 1.05, 1])
            },
            "publicacoes": {f"{a}-12": "2026-02-01" for a in anos},
        },
    }


def test_media_corrigida_e_cagr_quatro_intervalos_independentes():
    r = entradas(dados_exemplo(), AS_OF)
    assert r["graham"]["lpa"] == pytest.approx(3.2)
    assert r["graham"]["vpa"] == 20
    assert r["lynch"]["crescimento_lpa"] == pytest.approx(5**0.25 - 1)
    assert r["lynch"]["lpa"] == 5
    assert r["cobertura"] == {"esperados": 5, "disponiveis": 5}


@pytest.mark.parametrize("chave", ["serie_cvm", "ipca_serie"])
def test_falta_de_fonte_tem_motivo_sem_valor_fabricado(chave):
    d = dados_exemplo()
    d.pop(chave)
    r = entradas(d, AS_OF)
    assert "abstencao" in r["graham"]
    if chave != "ipca_serie":
        assert "abstencao" in r["lynch"]
    else:
        assert "crescimento_lpa" in r["lynch"]


@pytest.mark.parametrize(
    "tipo",
    [
        "lacuna",
        "duplicado",
        "parcial",
        "futuro",
        "sem_fuso",
        "evento",
        "ipca",
        "lpa_nan",
        "fator_zero",
        "coleta_futura",
    ],
)
def test_rejeita_janela_ou_fonte_nao_demonstrada(tipo):
    d = dados_exemplo()
    e = d["serie_cvm"]["exercicios"]
    if tipo in ("evento", "fator_zero", "coleta_futura"):
        e[0]["acoes"] = 50
    if tipo == "lacuna":
        e.pop(1)
    if tipo == "duplicado":
        e[1] = deepcopy(e[0])
    if tipo == "parcial":
        e[0]["inicio"] = "2021-01-02"
    if tipo == "futuro":
        e[0]["proveniencia"]["data_entrega"] = "2027-01-01"
    if tipo == "sem_fuso":
        e[0]["proveniencia"]["data_coleta"] = "2026-03-01T12:00:00"
    if tipo == "perimetro":
        e[0]["perimetro"] = "outro"
    if tipo == "sem_evidencia":
        e[0].pop("evidencia_comparabilidade")
    if tipo == "evento":
        d["reconciliacao_serie"]["fatores"].pop("2021")
    if tipo == "ipca":
        d["ipca_serie"]["indices"].pop("2021-12")
    if tipo == "lpa_nan":
        e[0]["lpa"] = float("nan")
    if tipo == "fator_zero":
        d["reconciliacao_serie"]["fatores"]["2021"] = 0
    if tipo == "coleta_futura":
        d["reconciliacao_serie"]["coleta"] = "2027-01-01T00:00:00+00:00"
    assert "abstencao" in entradas(d, AS_OF)["graham"]


def test_prejuizo_intermediario_nao_e_descartado():
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"][2]["lpa"] = -3
    r = entradas(d, AS_OF)
    assert r["graham"]["lpa"] == pytest.approx(1.88)
    assert "crescimento_lpa" in r["lynch"]


def test_split_oficial_ajusta_o_lucro_antigo():
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"][0]["acoes"] = 50
    d["reconciliacao_serie"]["fatores"]["2021"] = 2
    assert entradas(d, AS_OF)["lynch"]["crescimento_lpa"] == pytest.approx(10**0.25 - 1)


def test_metadados_distinguem_as_janelas_e_fontes_de_cada_lente():
    d = dados_exemplo()
    r = entradas(d, AS_OF)
    for chave in ("graham", "lynch"):
        janela = r[chave]
        assert janela["inicio"] == "2021-01-01"
        assert janela["fim"] == "2025-12-31"
        assert janela["exercicios"] == [2021, 2022, 2023, 2024, 2025]
        assert janela["perimetro"] == "controladores"
        assert janela["fontes_documentais"] == [
            e["proveniencia"] for e in d["serie_cvm"]["exercicios"]
        ]
        assert janela["fonte_eventos"] == d["reconciliacao_serie"]["fonte"]
    assert r["graham"]["fonte_ipca"] == d["ipca_serie"]["fonte"]
    assert r["graham"]["regime"] == "nominal na moeda final"
    assert r["lynch"]["regime"] == "nominal"


@pytest.mark.parametrize("extremo", [0, 4])
@pytest.mark.parametrize("valor", [-1, 0])
def test_cagr_recusa_extremos_nao_positivos(extremo, valor):
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"][extremo]["lpa"] = valor
    assert sem_valor(entradas(d, AS_OF)["lynch"], "CAGR exige extremos positivos")


def test_prejuizo_penultimo_nao_vira_extremo_do_cagr():
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"][-2]["lpa"] = -4
    assert entradas(d, AS_OF)["lynch"]["crescimento_lpa"] == pytest.approx(5**0.25 - 1)


@pytest.mark.parametrize(
    "tipo",
    ["zero", "negativo", "media_pequena", "vpa_zero", "vpa_negativo", "vpa_pequeno"],
)
def test_limites_da_media_e_vpa_usam_ultimo_documento(tipo):
    d = dados_exemplo()
    e = d["serie_cvm"]["exercicios"]
    for ano in d["ipca_serie"]["indices"]:
        d["ipca_serie"]["indices"][ano] = 100
    if tipo in ("zero", "negativo"):
        for item, v in zip(
            e, [1, -1, 0, -1, 1] if tipo == "zero" else [1, -2, -2, -2, 1]
        ):
            item["lpa"] = v
    if tipo == "media_pequena":
        for item in e:
            item["lpa"] = 0.5
    if tipo.startswith("vpa_"):
        e[-1]["vpa"] = {"vpa_zero": 0, "vpa_negativo": -1, "vpa_pequeno": 0.5}[tipo]
    r = entradas(d, AS_OF)["graham"]
    if tipo in ("zero", "negativo", "vpa_zero", "vpa_negativo"):
        assert sem_valor(r, "LPA médio ou VPA não positivo ou inválido")
    elif tipo == "media_pequena":
        assert r["lpa"] == 0.5
    else:
        assert r["vpa"] == 0.5


@pytest.mark.parametrize("chave", ["inicio", "fim"])
def test_eventos_tem_cobertura_das_duas_bordas(chave):
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"][0]["acoes"] = 50
    d["reconciliacao_serie"][chave] = (
        "2022-01-01" if chave == "inicio" else "2024-12-31"
    )
    r = entradas(d, AS_OF)
    assert sem_valor(r["graham"], "eventos sem cobertura da janela") and sem_valor(
        r["lynch"], "eventos sem cobertura da janela"
    )


@pytest.mark.parametrize("alvo", ["lpa", "vpa", "fator", "indice"])
def test_booleano_nao_e_valor_financeiro(alvo):
    d = dados_exemplo()
    if alvo in ("lpa", "vpa"):
        d["serie_cvm"]["exercicios"][-1][alvo] = True
    if alvo == "fator":
        d["serie_cvm"]["exercicios"][0]["acoes"] = 50
        d["reconciliacao_serie"]["fatores"]["2021"] = True
    if alvo == "indice":
        d["ipca_serie"]["indices"]["2021-12"] = True
    assert (
        entradas(d, AS_OF)["graham"]["abstencao"]
        == "insumo numérico ausente ou não finito"
    )


@pytest.mark.parametrize("valor", [0, -100])
def test_indice_nao_positivo_e_recusado(valor):
    d = dados_exemplo()
    d["ipca_serie"]["indices"]["2021-12"] = valor
    assert sem_valor(
        entradas(d, AS_OF)["graham"], "IPCA de fim de exercício inválido ou futuro"
    )


def test_indice_unitario_positivo_e_valido_e_independente_da_base():
    d = dados_exemplo()
    for mes in d["ipca_serie"]["indices"]:
        d["ipca_serie"]["indices"][mes] = 1
    assert entradas(d, AS_OF)["graham"]["lpa"] == 3


def test_coleta_no_instante_e_permitida_mas_publicacao_no_dia_nao():
    d = dados_exemplo()
    for e in d["serie_cvm"]["exercicios"]:
        e["proveniencia"]["data_coleta"] = AS_OF.isoformat()
    d["reconciliacao_serie"]["coleta"] = d["ipca_serie"]["coleta"] = AS_OF.isoformat()
    assert "lpa" in entradas(d, AS_OF)["graham"]
    d["ipca_serie"]["publicacoes"]["2025-12"] = AS_OF.date().isoformat()
    assert sem_valor(
        entradas(d, AS_OF)["graham"], "IPCA de fim de exercício inválido ou futuro"
    )


def test_documento_entregue_no_dia_ainda_nao_e_elegivel():
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"][0]["proveniencia"]["data_entrega"] = (
        AS_OF.date().isoformat()
    )
    assert sem_valor(entradas(d, AS_OF)["graham"], "documento não entregue até o corte")


def test_as_of_ingenuo_nao_certifica_janela():
    r = entradas(dados_exemplo(), AS_OF.replace(tzinfo=None))
    assert sem_valor(r["graham"], "as_of exige fuso horário")
    assert r["cobertura"] == {"esperados": 5, "disponiveis": 0}


def test_ausencia_da_lista_nao_vira_cobertura_parcial_inventada():
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"] = None
    r = entradas(d, AS_OF)
    assert r["cobertura"] == {"esperados": 5, "disponiveis": 0}
    assert sem_valor(r["graham"], "série anual ausente")


def test_fonte_sem_identificacao_nao_e_evidencia():
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"][0]["acoes"] = 50
    d["reconciliacao_serie"].pop("fonte")
    assert sem_valor(entradas(d, AS_OF)["graham"], "fonte não demonstrada")
