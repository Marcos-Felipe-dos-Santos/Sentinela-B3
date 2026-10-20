"""Proventos de 12 meses pela relação da B3 (F2B-31; ficha Bazin 1.0, §2 a §4)."""

from datetime import UTC, date, datetime

import pytest

from sentinela.data import proventos_b3 as pb

REF = date(2026, 9, 30)  # janela (30/09/2025, 30/09/2026]
HOJE = date(2026, 10, 19)


def _r(data_com, valor="1,0", natureza="DIVIDENDO", especie="ON", **kw):
    registro = {
        "typeStock": especie,
        "corporateAction": natureza,
        "valueCash": valor,
        "lastDatePriorEx": data_com,
        "dateApproval": "01/01/2025",
        "quotedPerShares": "1",
    }
    registro.update(kw)
    return registro


ANTIGO = _r("10/06/2020", "9,0")  # cobertura: provento antes da janela


def _serie(registros, total=None, **kw):
    registros = [*registros, ANTIGO]
    kw.setdefault("referencia", REF)
    kw.setdefault("dia_as_of", HOJE)
    kw.setdefault("especie", "ON")
    return pb.serie_12_meses(
        registros, total=len(registros) if total is None else total, **kw
    )


# ── janela por data ex ───────────────────────────────────────────────────────


def test_soma_dividendos_e_jcp_da_especie_na_janela():
    s = _serie(
        [
            _r("10/12/2025", "0,40"),
            _r("10/06/2026", "0,20", "JRS CAP PROPRIO"),
            _r("10/06/2026", "5,0", especie="PN"),
        ]
    )
    assert s["d_bruto_12m"] == pytest.approx(0.60, abs=1e-12)
    assert s["por_componente"] == {"ON": pytest.approx(0.60)}
    assert s["componentes"] == {"ON": 1}
    assert (s["inicio_exclusivo"], s["referencia"]) == ("2025-09-30", "2026-09-30")
    assert [(e["natureza"], e["valor"]) for e in s["eventos"]] == [
        ("dividendo", 0.40),
        ("jcp", 0.20),
    ]
    assert s["eventos"][0] == {
        "especie": "ON",
        "natureza": "dividendo",
        "valor": 0.40,
        "data_com": "2025-12-10",
        "aprovacao": "2025-01-01",
    }


@pytest.mark.parametrize(
    ("data_com", "entra"),
    [
        ("29/09/2026", True),  # data ex no pregão de referência
        ("30/09/2026", False),  # data ex depois da referência
        ("30/09/2025", True),  # data com no início: data ex depois dele
        ("23/09/2025", False),  # sete dias antes: data ex antes do início
        ("01/01/2025", False),
    ],
)
def test_fronteiras_da_janela_sem_calendario(data_com, entra):
    s = _serie([_r(data_com, "0,5")])
    assert s["d_bruto_12m"] == (0.5 if entra else 0.0)


@pytest.mark.parametrize(
    ("data_com", "pregoes", "entra"),
    [
        # data com na semana antes do início: a data ex é o pregão seguinte
        ("29/09/2025", [date(2025, 9, 29), date(2025, 9, 30)], False),
        ("29/09/2025", [date(2025, 9, 29), date(2025, 10, 1)], True),
        ("24/09/2025", [date(2025, 9, 24), date(2025, 10, 1)], True),
    ],
)
def test_data_ex_pelo_calendario(data_com, pregoes, entra):
    s = _serie([_r(data_com, "0,5")], pregoes=pregoes)
    assert s["d_bruto_12m"] == (0.5 if entra else 0.0)


@pytest.mark.parametrize(
    "pregoes",
    [None, [], [date(2025, 9, 26)], [date(2025, 9, 29)]],
)
def test_sem_calendario_suficiente_abstem(pregoes):
    s = _serie([_r("29/09/2025", "0,5")], pregoes=pregoes)
    assert s == pb.Abstencao(f"{pb.MOTIVO_CALENDARIO}: data com 2025-09-29")


def test_calendario_que_nao_alcanca_o_inicio_abstem():
    # o pregão seguinte conhecido é anterior ao início: o calendário não cobre a janela
    s = _serie(
        [_r("24/09/2025", "0,5")],
        pregoes=[date(2025, 9, 24), date(2025, 9, 25)],
    )
    assert isinstance(s, pb.Abstencao)


def test_ano_bissexto():
    assert pb.inicio_da_janela(date(2028, 2, 29)) == date(2027, 2, 28)
    assert pb.inicio_da_janela(date(2026, 3, 1)) == date(2025, 3, 1)


# ── abstenções ───────────────────────────────────────────────────────────────


def test_preco_do_proprio_dia_abstem():
    assert _serie([], referencia=HOJE) == pb.Abstencao(pb.MOTIVO_PRECO_NAO_ENCERRADO)
    assert isinstance(_serie([], referencia=HOJE.replace(day=18)), dict)


@pytest.mark.parametrize("total", [None, "2", 1, 3, True])
def test_relacao_incompleta_abstem(total):
    registros = [_r("10/12/2025"), ANTIGO]
    assert pb.serie_12_meses(
        registros, total=total, referencia=REF, dia_as_of=HOJE, especie="ON"
    ) == pb.Abstencao(pb.MOTIVO_INCOMPLETA)


def test_historico_menor_que_12_meses_abstem():
    registros = [_r("10/12/2025"), _r("30/09/2025")]
    assert pb.serie_12_meses(
        registros, total=2, referencia=REF, dia_as_of=HOJE, especie="ON"
    ) == pb.Abstencao(pb.MOTIVO_HISTORICO)
    assert pb.serie_12_meses(
        [], total=0, referencia=REF, dia_as_of=HOJE, especie="ON"
    ) == pb.Abstencao(pb.MOTIVO_HISTORICO)
    # um provento um dia antes do início demonstra a cobertura
    assert isinstance(
        pb.serie_12_meses(
            [_r("29/09/2025")],
            total=1,
            referencia=REF,
            dia_as_of=HOJE,
            especie="ON",
            pregoes=[date(2025, 9, 29), date(2025, 9, 30)],
        ),
        dict,
    )


def test_cobertura_vale_para_qualquer_especie():
    # a cobertura é da relação da companhia; o provento antigo pode ser de outra espécie
    registros = [_r("10/12/2025", "0,3"), _r("10/06/2020", especie="PN")]
    s = pb.serie_12_meses(
        registros, total=2, referencia=REF, dia_as_of=HOJE, especie="ON"
    )
    assert s["d_bruto_12m"] == pytest.approx(0.3)


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("valueCash", None, "insumo ausente: valor do provento"),
        ("valueCash", "  ", "insumo ausente: valor do provento"),
        ("valueCash", 1.0, "insumo ausente: valor do provento"),
        ("valueCash", "abc", "insumo inválido: valor do provento, tipo ou unidade"),
        ("valueCash", "nan", "insumo inválido: valor do provento, NaN"),
        ("valueCash", "inf", "insumo inválido: valor do provento, infinito"),
        ("valueCash", "-0,1", pb.MOTIVO_NEGATIVO),
        ("quotedPerShares", "1000", pb.MOTIVO_LOTE),
        ("quotedPerShares", None, "insumo ausente: cotação por lote do provento"),
        ("dateApproval", None, pb.MOTIVO_DISPONIBILIDADE),
        ("dateApproval", "2026-01-01", pb.MOTIVO_DISPONIBILIDADE),
        ("corporateAction", "REST CAP DIN", f"{pb.MOTIVO_NATUREZA}: REST CAP DIN"),
        ("corporateAction", None, f"{pb.MOTIVO_NATUREZA}: None"),
    ],
)
def test_campo_invalido_na_janela_abstem(campo, valor, motivo):
    assert _serie([_r("10/12/2025", **{campo: valor})]) == pb.Abstencao(motivo)


def test_campo_invalido_fora_da_janela_ou_de_outra_especie_nao_abstem():
    s = _serie(
        [
            _r("10/12/2024", valueCash="abc"),
            _r("10/12/2025", natureza="REST CAP DIN", especie="PN"),
            _r("10/12/2025", "0,1"),
        ]
    )
    assert s["d_bruto_12m"] == pytest.approx(0.1)


def test_data_com_invalida_abstem():
    assert _serie([_r("2025-12-10")]) == pb.Abstencao(
        "insumo inválido: data com do provento, tipo ou unidade"
    )
    assert _serie([_r(None)]) == pb.Abstencao(
        "insumo inválido: data com do provento, tipo ou unidade"
    )


def test_provento_aprovado_depois_do_as_of_nao_entra():
    s = _serie(
        [_r("10/12/2025", "0,3"), _r("10/09/2026", "0,7", dateApproval="20/10/2026")]
    )
    assert s["d_bruto_12m"] == pytest.approx(0.3)
    no_dia = _serie([_r("10/09/2026", "0,7", dateApproval="19/10/2026")])
    assert no_dia["d_bruto_12m"] == pytest.approx(0.7)


def test_zero_informado_e_valido_e_milhar_com_ponto():
    s = _serie([_r("10/12/2025", "0,0"), _r("10/01/2026", "1.234,5")])
    assert s["d_bruto_12m"] == pytest.approx(1234.5)
    assert len(s["eventos"]) == 2


def test_valor_com_ponto_decimal():
    assert _serie([_r("10/12/2025", "0.25")])["d_bruto_12m"] == pytest.approx(0.25)


def test_duplicata_identica_conta_uma_vez():
    s = _serie(
        [_r("10/12/2025", "0,5"), _r("10/12/2025", "0,5"), _r("10/12/2025", "0,2")]
    )
    assert s["d_bruto_12m"] == pytest.approx(0.7)


@pytest.mark.parametrize(
    ("evento", "abstem"),
    [
        (
            {
                "label": "BONIFICACAO",
                "lastDatePrior": "23/12/2025",
                "isinCode": "BRXXXXACNOR1",
            },
            True,
        ),
        (
            {
                "label": "DESDOBRAMENTO",
                "lastDatePrior": "24/09/2025",
                "isinCode": "BRXXXXACNOR1",
            },
            True,
        ),
        (
            {
                "label": "GRUPAMENTO",
                "lastDatePrior": "23/09/2025",
                "isinCode": "BRXXXXACNOR1",
            },
            False,
        ),
        (
            {
                "label": "GRUPAMENTO",
                "lastDatePrior": "30/09/2026",
                "isinCode": "BRXXXXACNOR1",
            },
            False,
        ),
        (
            {
                "label": "BONIFICACAO",
                "lastDatePrior": "23/12/2025",
                "isinCode": "BRXXXXACNPR1",
            },
            False,
        ),
        (
            {
                "label": "BONIFICACAO",
                "lastDatePrior": "23/12/2025",
                "isinCode": "BRXXXXCDAM00",
            },
            True,
        ),
        (
            {"label": "BONIFICACAO", "lastDatePrior": None, "isinCode": "BRXXXXACNOR1"},
            True,
        ),
        ({"label": "BONIFICACAO", "lastDatePrior": "23/12/2025"}, True),
    ],
)
def test_evento_em_acoes_na_janela_abstem(evento, abstem):
    s = _serie([_r("10/12/2025", "0,5")], eventos_acoes=[evento])
    if abstem:
        assert s == pb.Abstencao(
            f"{pb.MOTIVO_EVENTO_ACOES}: {evento['label']} {evento.get('lastDatePrior')}"
        )
    else:
        assert s["d_bruto_12m"] == pytest.approx(0.5)


def test_especie_ausente_abstem():
    assert _serie([], especie=None) == pb.Abstencao(pb.MOTIVO_ESPECIE)
    assert _serie([], especie="") == pb.Abstencao(pb.MOTIVO_ESPECIE)


# ── units ────────────────────────────────────────────────────────────────────


def test_unit_soma_os_componentes():
    s = _serie(
        [
            _r("10/12/2025", "0,1", especie="ON"),
            _r("10/12/2025", "0,1", especie="PN"),
            _r("10/03/2026", "0,05", "JRS CAP PROPRIO", especie="PN"),
            _r("10/03/2026", "9,0", especie="PNA"),
        ],
        especie=None,
        eh_unit=True,
        acoes_por_unit={"ON": 1, "pn": 2.0},
    )
    assert s["componentes"] == {"ON": 1, "PN": 2}
    assert s["d_bruto_12m"] == pytest.approx(0.1 + 2 * 0.15)


@pytest.mark.parametrize(
    "composicao",
    [
        None,
        {},
        [("ON", 1)],
        {"ON": 0},
        {"ON": -1},
        {"ON": 1.5},
        {"ON": True},
        {"ON": "1"},
        {"ON": float("inf")},
    ],
)
def test_unit_sem_composicao_valida_abstem(composicao):
    assert _serie([], eh_unit=True, acoes_por_unit=composicao) == pb.Abstencao(
        pb.MOTIVO_UNIT
    )


def test_unit_soma_quantidades_da_mesma_especie():
    s = _serie(
        [_r("10/12/2025", "0,1")],
        eh_unit=True,
        acoes_por_unit={"ON": 1, "on": 2},
    )
    assert s["componentes"] == {"ON": 3}
    assert s["d_bruto_12m"] == pytest.approx(0.3)


def test_soma_nao_finita_abstem():
    s = _serie([_r("10/12/2025", "1e308"), _r("10/01/2026", "1e308")])
    assert s == pb.Abstencao("resultado não finito: soma dos proventos")


# ── conferência no yfinance ──────────────────────────────────────────────────


SERIE = {
    "d_bruto_12m": 0.6,
    "inicio_exclusivo": "2025-09-30",
    "referencia": "2026-09-30",
}


def test_conferencia_igual_sem_aviso_e_fora_da_janela_ignorada():
    dividendos = {
        "2025-12-11": 0.4,
        "2026-06-11T00:00:00": 0.2,
        "2025-09-30": 7.0,
        "2026-10-01": 7.0,
    }
    assert pb.conferencia_yfinance(SERIE, dividendos) == []


def test_conferencia_tolera_o_arredondamento_por_evento():
    assert (
        pb.conferencia_yfinance(SERIE, {"2025-12-11": 0.4000015, "2026-06-11": 0.2})
        == []
    )
    assert pb.conferencia_yfinance(SERIE, {"2025-12-11": 0.6000009}) == []
    divergente = pb.conferencia_yfinance(SERIE, {"2025-12-11": 0.6000011})
    assert divergente == [
        (
            "proventos de 12 meses divergem do yfinance na mesma janela: "
            "B3 R$ 0.600000, yfinance R$ 0.600001"
        )
    ]


@pytest.mark.parametrize(
    "dividendos",
    [None, {}, {"x": 0.6}, {"2025-12-11": "abc"}, {"2025-12-11": float("nan")}],
)
def test_conferencia_indisponivel(dividendos):
    assert pb.conferencia_yfinance(SERIE, dividendos) == [pb.AVISO_SEM_CONFERENCIA]


def test_conferencia_sem_eventos_do_yfinance_na_janela_diverge():
    assert pb.conferencia_yfinance(SERIE, {"2024-01-02": 0.6})[0].startswith(
        "proventos de 12 meses divergem"
    )


# ── entradas do motor ────────────────────────────────────────────────────────


INSTANTE = datetime(2026, 10, 20, 15, tzinfo=UTC)


def _dados(**kw):
    relacao = {
        "registros": [_r("10/12/2025", "0,6"), ANTIGO],
        "total": 2,
        "eventos_acoes": [],
        "fechamentos": {"2026-10-16": 9.0, "2026-10-19": 10.0, "2026-10-20": 50.0},
        "pregoes": None,
        "conferencia_yfinance": {"2025-12-11": 0.6},
        "coleta": "2026-10-20T14:00:00+00:00",
    }
    relacao.update(kw.pop("relacao", {}))
    dados = {"especie": "ON", "classe_ativo": "STOCK", "proventos_b3": relacao}
    dados.update(kw)
    return dados


def test_entradas_usam_o_ultimo_fechamento_antes_do_as_of():
    e = pb.entradas(_dados(), INSTANTE)
    assert e["preco_referencia"] == 10.0
    assert e["dy"] == pytest.approx(0.06)
    assert e["serie"]["referencia"] == "2026-10-19"
    assert e["avisos"] == []
    # 02h UTC de 20/10 ainda é 19/10 em Brasília: o fechamento de 19/10 não serve
    noite = pb.entradas(
        _dados(relacao={"coleta": "2026-10-19T12:00:00+00:00"}),
        datetime(2026, 10, 20, 2, tzinfo=UTC),
    )
    assert noite["preco_referencia"] == 9.0


def test_entradas_com_unit():
    dados = _dados(
        especie=None,
        classe_ativo="UNIT",
        acoes_por_unit={"ON": 2},
        relacao={"conferencia_yfinance": None},
    )
    e = pb.entradas(dados, INSTANTE)
    assert e["dy"] == pytest.approx(0.12)
    assert e["avisos"] == [pb.AVISO_SEM_CONFERENCIA]


@pytest.mark.parametrize(
    ("dados", "motivo"),
    [
        ({}, pb.MOTIVO_SEM_RELACAO),
        ({"proventos_b3": "x"}, pb.MOTIVO_SEM_RELACAO),
        ({"proventos_b3": {"abstencao": "fora do escopo"}}, "fora do escopo"),
        (_dados(relacao={"fechamentos": None}), pb.MOTIVO_PRECO),
        (_dados(relacao={"fechamentos": {}}), pb.MOTIVO_PRECO),
        (_dados(relacao={"fechamentos": {"19/10/2026": 10.0}}), pb.MOTIVO_PRECO),
        (
            _dados(relacao={"fechamentos": {"2026-10-20": 10.0}}),
            pb.MOTIVO_PRECO_NAO_ENCERRADO,
        ),
        (
            _dados(relacao={"fechamentos": {"2026-10-19": 0.0}}),
            "insumo fora do domínio: preço, não positivo",
        ),
        (
            _dados(relacao={"fechamentos": {"2026-10-19": float("nan")}}),
            "insumo fora do domínio: preço, não positivo",
        ),
        (
            _dados(relacao={"fechamentos": {"2026-10-19": "10"}}),
            "insumo fora do domínio: preço, não positivo",
        ),
        (
            _dados(relacao={"fechamentos": {"2026-10-19": True}}),
            "insumo fora do domínio: preço, não positivo",
        ),
        (
            _dados(relacao={"registros": [_r("10/12/2025", "0,0"), ANTIGO]}),
            "insumo fora do domínio: rendimento, não positivo",
        ),
        (_dados(relacao={"total": 3}), pb.MOTIVO_INCOMPLETA),
        (_dados(relacao={"registros": None, "total": 0}), pb.MOTIVO_HISTORICO),
    ],
)
def test_entradas_abstem(dados, motivo):
    assert pb.entradas(dados, INSTANTE) == pb.Abstencao(motivo)


def test_entradas_exigem_fuso():
    assert pb.entradas(_dados(), datetime(2026, 10, 20, 15)) == pb.Abstencao(
        pb.MOTIVO_AS_OF
    )


def test_entradas_passam_calendario_e_eventos_em_acoes():
    dados = _dados(
        relacao={
            "fechamentos": {"2026-09-30": 10.0},
            "registros": [_r("29/09/2025", "0,6"), _r("10/12/2025", "0,6"), ANTIGO],
            "total": 3,
            "pregoes": ["2025-09-29", "2025-10-01"],
        }
    )
    e = pb.entradas(dados, INSTANTE)
    assert e["serie"]["d_bruto_12m"] == pytest.approx(1.2)
    com_evento = _dados(
        relacao={
            "eventos_acoes": [
                {
                    "label": "DESDOBRAMENTO",
                    "lastDatePrior": "10/01/2026",
                    "isinCode": "BRXXXXACNOR1",
                }
            ]
        }
    )
    assert pb.entradas(com_evento, INSTANTE) == pb.Abstencao(
        f"{pb.MOTIVO_EVENTO_ACOES}: DESDOBRAMENTO 10/01/2026"
    )


# ── conferência do emissor pelo complemento ──────────────────────────────────


def _c(data_com, rate="0,5", label="DIVIDENDO", isin="BRTSTEACNOR1"):
    return {"lastDatePrior": data_com, "rate": rate, "label": label, "isinCode": isin}


@pytest.mark.parametrize(
    ("complemento", "faltante"),
    [
        ([_c("10/12/2025", "0,50000000000")], None),
        ([_c("10/12/2025"), _c("10/12/2025")], None),  # duas datas de pagamento
        (
            [_c("10/12/2025", isin="BRTSTECDAM10")],
            None,
        ),  # unit: a relação é por espécie
        ([_c("10/12/2025", isin=None)], None),
        ([_c("11/12/2025")], "DIVIDENDO 11/12/2025 ON"),
        ([_c("10/12/2025", "0,51")], "DIVIDENDO 10/12/2025 ON"),
        ([_c("10/12/2025", label="JRS CAP PROPRIO")], "JRS CAP PROPRIO 10/12/2025 ON"),
        ([_c("10/12/2025", isin="BRTSTEACNPR1")], "DIVIDENDO 10/12/2025 PN"),
        ([_c("10/12/2025", rate="x")], "DIVIDENDO 10/12/2025 ON"),
        # anúncio com data com na referência ou depois: fora da janela, não conferido
        ([_c("30/09/2026"), _c("07/10/2026")], None),
        ([_c("29/09/2026")], "DIVIDENDO 29/09/2026 ON"),
        ([_c(None)], "DIVIDENDO None ON"),
    ],
)
def test_relacao_conferida_pelo_complemento(complemento, faltante):
    s = _serie([_r("10/12/2025", "0,5")], dinheiro_complemento=complemento)
    if faltante is None:
        assert s["d_bruto_12m"] == pytest.approx(0.5)
    else:
        assert s == pb.Abstencao(f"{pb.MOTIVO_CRUZAMENTO}: {faltante}")


def test_relacao_vazia_com_proventos_no_complemento_abstem_pelo_cruzamento():
    # "AMBEV S/A": a busca pelo nome devolve zero registros, e o complemento tem proventos
    s = pb.serie_12_meses(
        [],
        total=0,
        referencia=REF,
        dia_as_of=HOJE,
        especie="ON",
        dinheiro_complemento=[_c("18/12/2025")],
    )
    assert s == pb.Abstencao(f"{pb.MOTIVO_CRUZAMENTO}: DIVIDENDO 18/12/2025 ON")


def test_registro_com_valor_ilegivel_nao_confere_o_complemento():
    registros = [_r("10/12/2025", "abc"), ANTIGO]
    s = pb.serie_12_meses(
        registros,
        total=2,
        referencia=REF,
        dia_as_of=HOJE,
        especie="ON",
        dinheiro_complemento=[_c("10/12/2025")],
    )
    assert s == pb.Abstencao(f"{pb.MOTIVO_CRUZAMENTO}: DIVIDENDO 10/12/2025 ON")


def test_entradas_passam_o_complemento():
    dados = _dados(relacao={"dinheiro_complemento": [_c("11/12/2025")]})
    assert pb.entradas(dados, INSTANTE) == pb.Abstencao(
        f"{pb.MOTIVO_CRUZAMENTO}: DIVIDENDO 11/12/2025 ON"
    )


@pytest.mark.parametrize(
    ("coleta", "valida"),
    [
        ("2026-10-20T15:00:00+00:00", True),  # igual ao as_of
        ("2026-10-20T12:00:00-03:00", True),
        ("2026-10-20T15:00:01+00:00", False),  # depois do as_of
        ("2026-10-20T12:00:01-03:00", False),
        ("2026-10-20T14:00:00", False),  # sem fuso
        ("20/10/2026", False),
        (None, False),
    ],
)
def test_coleta_depois_do_as_of_nao_prova_disponibilidade(coleta, valida):
    e = pb.entradas(_dados(relacao={"coleta": coleta}), INSTANTE)
    if valida:
        assert e["dy"] == pytest.approx(0.06)
    else:
        assert e == pb.Abstencao(pb.MOTIVO_COLETA)
