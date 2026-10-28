"""Conversões B3 demonstradas pelo manual e avisos oficiais, sem fator presumido."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from sentinela.data.fatores_acoes_b3 import fatores_da_relacao

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)
ON = "BRTESTACNOR0"
PN = "BRTESTACNPR0"


def documentos(quantidades=(100, 100, 200, 200, 200)):
    return [
        {
            "exercicio": a,
            "inicio": f"{a}-01-01",
            "fim": f"{a}-12-31",
            "acoes": q,
            "proveniencia": {
                "fonte": "DFP sintética",
                "data_coleta": "2026-03-01T12:00:00+00:00",
            },
        }
        for a, q in zip(range(2021, 2026), quantidades, strict=True)
    ]


def evento(rotulo="DESDOBRAMENTO", fator="100,00000000000", isin=ON, **extra):
    return {
        "label": rotulo,
        "factor": fator,
        "isinCode": isin,
        "assetIssued": isin,
        "approvedOn": "01/04/2023",
        "lastDatePrior": "15/04/2023",
        **extra,
    }


def dados(eventos=None):
    return {
        "classe_ativo": "STOCK",
        "especie": "ON",
        "proventos_b3": {
            "eventos_acoes": [evento()] if eventos is None else eventos,
            "coleta": "2026-10-20T12:00:00+00:00",
            "proveniencia": {
                "fonte": "B3 CompanyCall",
                "arquivos": [{"fonte": "URL B3", "hash": "sintético"}],
            },
        },
    }


def test_split_acumula_fator_somente_nos_anos_anteriores():
    r = fatores_da_relacao(dados(), documentos(), AS_OF)
    assert r["fatores"] == {"2021": 2, "2022": 2, "2023": 1, "2024": 1, "2025": 1}
    assert r["fonte"] == "B3 CompanyCall"
    assert r["coleta"] == "2026-10-20T12:00:00+00:00"
    assert r["inicio"] == "2021-01-01" and r["fim"] == "2025-12-31"
    assert r["evidencias"][1]["razao_residual"] == 1
    assert r["evidencias"][1]["eventos"][0]["factor"] == "100,00000000000"


@pytest.mark.parametrize(
    ("rotulo", "bruto", "q", "esperado"),
    [
        ("DESDOBRAMENTO", "300,00000000000", 400, 4),
        ("BONIFICACAO", "30,00000002726", 130, 1.3000000002726),
        ("GRUPAMENTO", "0,00200000000", 0.2, 0.002),
    ],
)
def test_conversoes_demonstradas_por_eventos_oficiais(rotulo, bruto, q, esperado):
    # Cosan AGOE30/04/2021:1→4; Cemig aviso29/04/2024:30,00000002726%; DFP2007:500→1.
    r = fatores_da_relacao(
        dados([evento(rotulo, bruto)]), documentos((100, 100, q, q, q)), AS_OF
    )
    assert r["fatores"]["2021"] == pytest.approx(esperado)


def test_fatores_de_dois_pares_sao_multiplicados():
    eventos = [evento(), evento("GRUPAMENTO", "0,5", lastDatePrior="15/04/2024")]
    r = fatores_da_relacao(dados(eventos), documentos((100, 100, 200, 100, 100)), AS_OF)
    assert r["fatores"] == {"2021": 1, "2022": 1, "2023": 0.5, "2024": 1, "2025": 1}


def test_pares_compativeis_nao_exigem_fonte_de_eventos():
    r = fatores_da_relacao({}, documentos((100, 100, 100, 100, 100)), AS_OF)
    assert r["fatores"] == {str(a): 1 for a in range(2021, 2026)}
    assert r["coleta"] == "2026-03-01T12:00:00+00:00"


@pytest.mark.parametrize("q", [90, 110])
def test_limites_exatos_sem_evento_nao_provam_compatibilidade(q):
    r = fatores_da_relacao(dados([]), documentos((100, q, q, q, q)), AS_OF)
    assert "sem evento oficial" in r["abstencao"]


def test_fator_incompleto_recusado_pela_razao_residual():
    r = fatores_da_relacao(dados(), documentos((100, 100, 300, 300, 300)), AS_OF)
    assert "residual" in r["abstencao"]


@pytest.mark.parametrize("q", [180, 220])
def test_limites_residuais_exatos_sao_recusados(q):
    r = fatores_da_relacao(dados(), documentos((100, 100, q, q, q)), AS_OF)
    assert "residual" in r["abstencao"]


@pytest.mark.parametrize("rotulo", ["CIS RED CAP", "SUBSCRICAO", "OUTRO"])
def test_rotulo_sem_contrato_nao_vira_split(rotulo):
    r = fatores_da_relacao(dados([evento(rotulo)]), documentos(), AS_OF)
    assert "não demonstrado" in r["abstencao"]


@pytest.mark.parametrize("campo", ["isinCode", "assetIssued"])
def test_evento_em_outra_especie_nao_ajusta_a_especie_estudada(campo):
    r = fatores_da_relacao(dados([evento(**{campo: PN})]), documentos(), AS_OF)
    assert "espécie" in r["abstencao"]


def test_unit_exige_mesmo_fator_em_todos_componentes():
    d = dados([evento(isin=ON), evento(isin=PN)])
    d.update(classe_ativo="UNIT", acoes_por_unit={"ON": 1, "PN": 2})
    assert fatores_da_relacao(d, documentos(), AS_OF)["fatores"]["2021"] == 2
    d["proventos_b3"]["eventos_acoes"].pop()
    assert "componente" in fatores_da_relacao(d, documentos(), AS_OF)["abstencao"]


def test_unit_com_fatores_diferentes_nao_tem_base_unica():
    d = dados([evento(isin=ON), evento(fator="200", isin=PN)])
    d.update(classe_ativo="UNIT", acoes_por_unit={"ON": 1, "PN": 2})
    assert "distintos" in fatores_da_relacao(d, documentos(), AS_OF)["abstencao"]


@pytest.mark.parametrize("data", ["31/12/2022", "31/12/2023"])
def test_data_com_no_encerramento_nao_inventa_data_ex(data):
    assert (
        "encerramento"
        in fatores_da_relacao(dados([evento(lastDatePrior=data)]), documentos(), AS_OF)[
            "abstencao"
        ]
    )


@pytest.mark.parametrize(
    "alteracao",
    [
        {"approvedOn": "21/10/2026"},
        {"approvedOn": "20/10/2026"},
        {"approvedOn": None},
        {"lastDatePrior": None},
        {"lastDatePrior": "31/02/2023"},
    ],
)
def test_datas_sem_elegibilidade_produzem_motivo(alteracao):
    assert "abstencao" in fatores_da_relacao(
        dados([evento(**alteracao)]), documentos(), AS_OF
    )


@pytest.mark.parametrize("valor", ["0", "-1", "NaN", "inf", None, True, "lixo"])
def test_fator_invalido_nunca_vira_unidade(valor):
    assert "abstencao" in fatores_da_relacao(
        dados([evento("GRUPAMENTO", valor)]), documentos(), AS_OF
    )


@pytest.mark.parametrize("valor", ["-100", "-101", "NaN", "inf"])
def test_percentual_sem_fator_positivo_e_recusado(valor):
    assert "abstencao" in fatores_da_relacao(
        dados([evento(fator=valor)]), documentos(), AS_OF
    )


@pytest.mark.parametrize(
    "tipo",
    [
        "sem_relacao",
        "sem_fonte",
        "coleta_futura",
        "coleta_ingenua",
        "sem_eventos",
        "lista_invalida",
        "sem_especie",
        "unit_invalida",
    ],
)
def test_fonte_e_identidade_nao_demonstradas(tipo):
    d = dados()
    if tipo == "sem_relacao":
        d.pop("proventos_b3")
    if tipo == "sem_fonte":
        d["proventos_b3"]["proveniencia"] = {}
    if tipo == "coleta_futura":
        d["proventos_b3"]["coleta"] = "2027-01-01T00:00:00+00:00"
    if tipo == "coleta_ingenua":
        d["proventos_b3"]["coleta"] = "2026-01-01T00:00:00"
    if tipo == "sem_eventos":
        d["proventos_b3"].pop("eventos_acoes")
    if tipo == "lista_invalida":
        d["proventos_b3"]["eventos_acoes"] = "inválida"
    if tipo == "sem_especie":
        d.pop("especie")
    if tipo == "unit_invalida":
        d.update(classe_ativo="UNIT", acoes_por_unit={"ON": 0})
    assert "abstencao" in fatores_da_relacao(d, documentos(), AS_OF)


@pytest.mark.parametrize("q", [0, -1, None, True, float("nan"), float("inf")])
def test_quantidade_documental_invalida(q):
    r = documentos()
    r[1]["acoes"] = q
    assert "abstencao" in fatores_da_relacao(dados(), r, AS_OF)


def test_asof_ingenuo_nao_certifica_fonte():
    assert "abstencao" in fatores_da_relacao(
        dados(), documentos(), AS_OF.replace(tzinfo=None)
    )


def test_evento_duplicado_identico_nao_dobra_fator():
    e = evento()
    assert (
        fatores_da_relacao(dados([e, deepcopy(e)]), documentos(), AS_OF)["fatores"][
            "2021"
        ]
        == 2
    )


def test_proveniencia_e_trilha_dos_quatro_pares_preservam_documentos_e_eventos():
    # A evidência deve permitir refazer cada fator e explicar quais anos foram ajustados.
    d = dados()
    r = fatores_da_relacao(d, list(reversed(documentos())), AS_OF)
    assert r["proveniencia"] == d["proventos_b3"]["proveniencia"]
    assert r["evidencias"] == [
        {
            "anterior": 2021,
            "posterior": 2022,
            "razao": 1,
            "fator": 1,
            "razao_residual": 1,
            "eventos": [],
        },
        {
            "anterior": 2022,
            "posterior": 2023,
            "razao": 2,
            "fator": 2,
            "razao_residual": 1,
            "eventos": [evento()],
        },
        {
            "anterior": 2023,
            "posterior": 2024,
            "razao": 1,
            "fator": 1,
            "razao_residual": 1,
            "eventos": [],
        },
        {
            "anterior": 2024,
            "posterior": 2025,
            "razao": 1,
            "fator": 1,
            "razao_residual": 1,
            "eventos": [],
        },
    ]


def test_fonte_documental_sem_eventos_guarda_proveniencia_e_coleta_mais_recente():
    docs = documentos((100, 100, 100, 100, 100))
    docs[1]["proveniencia"]["data_coleta"] = "2026-03-02T12:00:00+00:00"
    r = fatores_da_relacao({}, docs, AS_OF)
    assert r["fonte"] == "Composição do Capital de cada documento"
    assert r["coleta"] == "2026-03-02T12:00:00+00:00"
    assert r["proveniencia"] == [e["proveniencia"] for e in docs]
    assert r["inicio"] == "2021-01-01" and r["fim"] == "2025-12-31"
    assert len(r["evidencias"]) == 4
    assert all(e["fator"] == e["razao_residual"] == 1 for e in r["evidencias"])


@pytest.mark.parametrize(
    ("q", "motivo"),
    [
        (None, "quantidade de ações do documento inválida"),
        (True, "quantidade de ações do documento inválida"),
        (False, "quantidade de ações do documento inválida"),
        ("100", "quantidade de ações do documento inválida"),
        (0, "quantidade de ações do documento não positiva ou não finita"),
        (-1, "quantidade de ações do documento não positiva ou não finita"),
        (float("inf"), "quantidade de ações do documento não positiva ou não finita"),
        (float("nan"), "quantidade de ações do documento não positiva ou não finita"),
    ],
)
def test_causa_de_quantidade_invalida_nao_e_trocada_por_ausencia_de_evento(q, motivo):
    docs = documentos()
    docs[0]["acoes"] = q
    assert fatores_da_relacao(dados(), docs, AS_OF) == {"abstencao": motivo}


@pytest.mark.parametrize(
    ("alteracao", "motivo"),
    [
        ({"isinCode": None}, "espécie do evento em ações não demonstrada"),
        ({"assetIssued": None}, "espécie do evento em ações não demonstrada"),
        ({"isinCode": "BRTESTXXXX0"}, "espécie do evento em ações não demonstrada"),
        ({"lastDatePrior": None}, "data com do evento em ações inválida"),
        (
            {"lastDatePrior": "31/12/2022"},
            "data com coincide com encerramento; data ex não demonstrada",
        ),
        (
            {"assetIssued": PN},
            "evento em espécie distinta sem reconciliação demonstrada",
        ),
        (
            {"approvedOn": None},
            "aprovação ou data com do evento não elegível até o as_of",
        ),
        (
            {"approvedOn": "20/10/2026"},
            "aprovação ou data com do evento não elegível até o as_of",
        ),
        ({"factor": None}, "insumo ausente: fator oficial B3"),
        ({"factor": "lixo"}, "insumo inválido: fator oficial B3, tipo ou unidade"),
        ({"factor": "NaN"}, "insumo inválido: fator oficial B3, NaN"),
        ({"factor": "inf"}, "insumo inválido: fator oficial B3, infinito"),
        ({"factor": "-100"}, "fator oficial B3 não positivo ou não finito"),
        ({"label": "CIS RED CAP"}, "evento em ações não demonstrado: CIS RED CAP"),
    ],
)
def test_motivo_identifica_qual_prova_oficial_faltou(alteracao, motivo):
    assert fatores_da_relacao(dados([evento(**alteracao)]), documentos(), AS_OF) == {
        "abstencao": motivo
    }


@pytest.mark.parametrize(
    ("tipo", "motivo"),
    [
        ("relacao", "relação de eventos B3 ausente ou inválido"),
        ("proveniencia", "proveniência B3 ausente ou inválido"),
        ("fonte", "fonte B3 não demonstrada"),
        ("eventos", "lista de eventos em ações ausente ou inválida"),
        ("evento", "evento em ações ausente ou inválido"),
        ("futura", "coleta sem fuso ou posterior ao as_of"),
        ("ingenua", "coleta sem fuso ou posterior ao as_of"),
    ],
)
def test_ausencia_de_fonte_tem_motivo_do_campo_correto(tipo, motivo):
    d = dados()
    if tipo == "relacao":
        d.pop("proventos_b3")
    if tipo == "proveniencia":
        d["proventos_b3"]["proveniencia"] = None
    if tipo == "fonte":
        d["proventos_b3"]["proveniencia"] = {}
    if tipo == "eventos":
        d["proventos_b3"]["eventos_acoes"] = None
    if tipo == "evento":
        d["proventos_b3"]["eventos_acoes"] = [None]
    if tipo == "futura":
        d["proventos_b3"]["coleta"] = "2027-01-01T12:00:00+00:00"
    if tipo == "ingenua":
        d["proventos_b3"]["coleta"] = "2026-01-01T12:00:00"
    assert fatores_da_relacao(d, documentos(), AS_OF) == {"abstencao": motivo}


def test_abstencao_original_da_fonte_chega_ao_consumidor_sem_ser_substituida():
    d = dados()
    d["proventos_b3"] = {"abstencao": "B3 temporariamente indisponível"}
    assert fatores_da_relacao(d, documentos(), AS_OF) == {
        "abstencao": "B3 temporariamente indisponível"
    }


@pytest.mark.parametrize(
    "coleta", ["2026-10-20T15:00:00+00:00", "2026-10-20T12:00:00-03:00"]
)
def test_coleta_no_instante_exato_e_elegivel(coleta):
    d = dados()
    d["proventos_b3"]["coleta"] = coleta
    assert fatores_da_relacao(d, documentos(), AS_OF)["coleta"] == coleta


def test_evento_de_outra_classe_antes_do_correto_nao_interrompe_busca():
    d = dados([evento(isin=PN), evento()])
    r = fatores_da_relacao(d, documentos(), AS_OF)
    assert r["fatores"]["2021"] == 2
    assert r["evidencias"][1]["eventos"] == [evento()]


def test_eventos_fora_do_par_nao_fornecem_fator_nem_impedem_o_correto():
    d = dados(
        [
            evento(lastDatePrior="15/04/2022"),
            evento(),
            evento(lastDatePrior="15/04/2024"),
        ]
    )
    r = fatores_da_relacao(d, documentos(), AS_OF)
    assert r["fatores"]["2021"] == 2
    assert r["evidencias"][1]["eventos"] == [evento()]


def test_dois_eventos_no_mesmo_par_compõem_os_ajustes():
    eventos = [
        evento(fator="100", lastDatePrior="15/04/2023"),
        evento(fator="100", lastDatePrior="15/08/2023"),
    ]
    r = fatores_da_relacao(dados(eventos), documentos((100, 100, 400, 400, 400)), AS_OF)
    assert r["fatores"]["2021"] == 4
    assert r["evidencias"][1]["eventos"] == eventos


def test_eventos_distintos_no_mesmo_dia_nao_sao_duplicatas():
    eventos = [evento(fator="100"), evento("BONIFICACAO", "50")]
    r = fatores_da_relacao(dados(eventos), documentos((100, 100, 300, 300, 300)), AS_OF)
    assert r["fatores"]["2021"] == 3
    assert r["evidencias"][1]["eventos"] == eventos


@pytest.mark.parametrize("documento", [None, {}, {"exercicio": 2021}])
def test_documentos_incompletos_nao_viram_identidade_documental(documento):
    docs = documentos()
    docs[1] = documento
    assert "abstencao" in fatores_da_relacao(dados(), docs, AS_OF)


@pytest.mark.parametrize("registros", [None, [], documentos()[:1], "inválidos"])
def test_sem_pares_documentais_a_cobertura_nao_e_inventada(registros):
    assert fatores_da_relacao(dados(), registros, AS_OF) == {
        "abstencao": "pares documentais anuais ausentes"
    }


@pytest.mark.parametrize("tipo", ["sem_proveniencia", "sem_fonte", "coleta_futura"])
def test_base_compativel_tambem_exige_evidencia_documental_elegivel(tipo):
    docs = documentos((100, 100, 100, 100, 100))
    if tipo == "sem_proveniencia":
        docs[0]["proveniencia"] = None
        motivo = "proveniência documental ausente ou inválido"
    elif tipo == "sem_fonte":
        docs[0]["proveniencia"] = {}
        motivo = "fonte documental não demonstrada"
    else:
        docs[0]["proveniencia"]["data_coleta"] = "2027-01-01T12:00:00+00:00"
        motivo = "coleta sem fuso ou posterior ao as_of"
    assert fatores_da_relacao({}, docs, AS_OF) == {"abstencao": motivo}
