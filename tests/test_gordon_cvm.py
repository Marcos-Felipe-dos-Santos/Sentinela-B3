"""DVA consolidada: perímetro, totais e janela da ficha Gordon1.0."""

from datetime import date

import pytest

from sentinela.data import contas_cvm, gordon_cvm


def _l(v):
    return contas_cvm.Leitura(v, "conta", "descrição comprovada")


def _ausente():
    return contas_cvm.Abstencao(contas_cvm.MOTIVO_LINHA_AUSENTE)


def test_dva_separada_atribui_proventos_sem_somar_minoritarios():
    r = gordon_cvm.proventos_da_dva(
        _l(10903280), _l(0), _l(485033), _l(149947), _l(860742)
    )
    assert r == 10903280


def test_reserva_apenas_sem_minoritaros_e_ausencia_confirmada():
    assert (
        gordon_cvm.proventos_da_dva(_l(10), _ausente(), _ausente(), _l(0), _ausente())
        == 10
    )
    r = gordon_cvm.proventos_da_dva(_l(10), _ausente(), _ausente(), _l(1), _l(0))
    assert isinstance(r, gordon_cvm.Abstencao)
    assert "estrutura da DVA" in r.motivo


@pytest.mark.parametrize(
    "motivo",
    [
        contas_cvm.MOTIVO_SEM_CORRESPONDENCIA,
        contas_cvm.MOTIVO_VALOR_INVALIDO,
        contas_cvm.MOTIVO_LINHAS_DIVERGENTES,
    ],
)
def test_conta_invalida_nao_autoriza_reserva(motivo):
    r = gordon_cvm.proventos_da_dva(
        _l(10), _ausente(), contas_cvm.Abstencao(motivo), _l(0), _l(0)
    )
    assert isinstance(r, gordon_cvm.Abstencao)


def test_proventos_incompletos_ou_negativos_abstem():
    for dividendos, jcp in [
        (_ausente(), _ausente()),
        (_l(-1), _l(2)),
        (_l(2), _l(-1)),
        (_l(2), contas_cvm.Abstencao("desconhecido")),
    ]:
        assert isinstance(
            gordon_cvm.proventos_da_dva(dividendos, jcp, _l(1), _l(0), _l(0)),
            gordon_cvm.Abstencao,
        )


def _dados():
    return {
        "base_acionaria_gordon": {
            "proveniencia": {
                "periodo_referencia": "2025-12-31",
                "data_entrega": "2026-02-12",
                "data_coleta": "2026-02-20T18:00:00+00:00",
            }
        },
        "classe_ativo": "STOCK",
        "gordon_cvm": {
            "proveniencia": {
                "periodo_referencia": "2025-12-31",
                "data_entrega": "2026-02-12",
                "data_coleta": "2026-02-20T18:00:00+00:00",
            },
            "modelo": "empresa",
            "inicio": "2025-01-01",
            "fim": "2025-12-31",
            "data_entrega": "2026-02-12",
            "base_acionaria_compativel": True,
            "hipotese_dva_anual": True,
            "lucro_controladores": 15503400000.0,
            "pl_inicial_controladores": 98642139000.0,
            "proventos_controladores": 10903280000.0,
            "acoes_base": 15616526000.0,
            "lpa": 0.9926913764,
        },
        "taxa_real": {
            "custo_capital_real": 74.38 / 1100 + 0.05,
            "inflacao": {"valor": 0.0426, "inicio": "2025-01-01", "fim": "2025-12-31"},
            "pib": {"valor": 0.02},
        },
    }


def test_entradas_tipadas_preservam_totais_e_janela():
    from sentinela.domain.units import BRL, RateReal, Ratio

    r = gordon_cvm.entradas(_dados(), date(2026, 10, 20))
    assert r["lpa"] == BRL(0.9926913764)
    assert r["roe"] == Ratio(15503400 / 98642139)
    assert r["teto_pib_real"] == RateReal(0.02)
    assert r["proventos_controladores"].payout == Ratio(10903280 / 15503400)
    assert r["proventos_controladores"].dividendo_anual == BRL(10903280 / 15616526)


@pytest.mark.parametrize(
    "chave,valor",
    [
        ("modelo", "banco"),
        ("base_acionaria_compativel", False),
        ("hipotese_dva_anual", None),
        ("data_entrega", "2026-10-20"),
        ("lucro_controladores", 0),
        ("pl_inicial_controladores", -1),
        ("acoes_base", None),
    ],
)
def test_documento_invalido_abstem_sem_inferir_dy(chave, valor):
    d = _dados()
    d["gordon_cvm"][chave] = valor
    assert isinstance(gordon_cvm.entradas(d, date(2026, 10, 20)), gordon_cvm.Abstencao)


def test_inflacao_de_outra_janela_nao_e_usada():
    d = _dados()
    d["taxa_real"]["inflacao"]["fim"] = "2026-09-30"
    assert "inflação incompatível" in gordon_cvm.entradas(d, date(2026, 10, 20)).motivo


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("classe_ativo", "FII"),
        ("classes_preferenciais", ["PNA", "PNB"]),
        ("gordon_cvm", None),
        ("gordon_cvm", {"abstencao": "documento indisponível"}),
    ],
)
def test_exclusoes_sem_reserva(campo, valor):
    d = _dados()
    d[campo] = valor
    assert isinstance(gordon_cvm.entradas(d, date(2026, 10, 20)), gordon_cvm.Abstencao)


@pytest.mark.parametrize(
    "chave",
    [
        "lucro_controladores",
        "pl_inicial_controladores",
        "acoes_base",
        "proventos_controladores",
    ],
)
@pytest.mark.parametrize("valor", [True, "texto", float("nan"), float("inf")])
def test_valor_invalido_nao_chega_ao_metodo(chave, valor):
    d = _dados()
    d["gordon_cvm"][chave] = valor
    assert isinstance(gordon_cvm.entradas(d, date(2026, 10, 20)), gordon_cvm.Abstencao)


def test_unit_pondera_d0_sem_alterar_payout_de_totais():
    d = _dados()
    d["classe_ativo"] = "UNIT"
    d["gordon_cvm"].update(fator_unit=3, direitos_compativeis=True)
    r = gordon_cvm.entradas(d, date(2026, 10, 20))
    assert r["proventos_controladores"].dividendo_anual.valor == pytest.approx(
        3 * 10903280 / 15616526
    )
    assert r["proventos_controladores"].payout.valor == pytest.approx(
        10903280 / 15503400
    )
    assert r["custo_capital_real"].valor == pytest.approx(74.38 / 1100 + 0.05)
    assert r["inflacao"].valor == 0.0426
    assert r["proventos_controladores"].inicio == date(2025, 1, 1)
    assert r["proventos_controladores"].fim == date(2025, 12, 31)


@pytest.mark.parametrize("fator", [0, -1, 1.5, True, "3", float("nan"), float("inf")])
def test_unit_exige_quantidades_inteiras_positivas(fator):
    d = _dados()
    d["classe_ativo"] = "UNIT"
    d["gordon_cvm"].update(fator_unit=fator, direitos_compativeis=True)
    assert "unit sem composição" in gordon_cvm.entradas(d, date(2026, 10, 20)).motivo


@pytest.mark.parametrize("minoritarios", [_l(1), contas_cvm.Abstencao("inválido")])
def test_linha_dva_zerada_nao_esconde_minoritaros(minoritarios):
    assert isinstance(
        gordon_cvm.proventos_da_dva(_l(10), _l(0), _l(0), minoritarios, _l(0)),
        gordon_cvm.Abstencao,
    )


@pytest.mark.parametrize("valor", [True, -1, float("inf"), float("nan")])
def test_participacao_e_proventos_invalidos(valor):
    assert isinstance(
        gordon_cvm.proventos_da_dva(_l(10), _l(0), _l(valor), _l(0), _l(0)),
        gordon_cvm.Abstencao,
    )
    assert isinstance(
        gordon_cvm.proventos_da_dva(_l(valor), _l(0), _l(1), _l(0), _l(0)),
        gordon_cvm.Abstencao,
    )


def test_soma_dva_nao_finita_abstem():
    assert isinstance(
        gordon_cvm.proventos_da_dva(_l(1e308), _l(1e308), _l(1), _l(0), _l(0)),
        gordon_cvm.Abstencao,
    )


@pytest.mark.parametrize(
    "chave,valor,motivo",
    [
        ("modelo", "banco", "classe ou modelo fora do escopo do Gordon"),
        (
            "base_acionaria_compativel",
            False,
            "base de ações incompatível ou sem evidência vigente",
        ),
        (
            "hipotese_dva_anual",
            False,
            "hipótese de DVA anual não demonstrada",
        ),
        ("data_entrega", "2026-10-20", "DFP entregue após o corte de disponibilidade"),
        ("fim", "2026-10-20", "DFP entregue após o corte de disponibilidade"),
        (
            "lucro_controladores",
            0,
            "lucro ou PL inicial dos controladores não positivo ou inválido",
        ),
        (
            "pl_inicial_controladores",
            0,
            "lucro ou PL inicial dos controladores não positivo ou inválido",
        ),
        ("acoes_base", 1.5, "ações da DFP não positivas ou inválidas"),
        ("acoes_base", -1, "ações da DFP não positivas ou inválidas"),
        ("proventos_controladores", True, "provento DVA inválido"),
    ],
)
def test_motivos_preservam_causa_da_abstencao(chave, valor, motivo):
    d = _dados()
    d["gordon_cvm"][chave] = valor
    assert gordon_cvm.entradas(d, date(2026, 10, 20)) == gordon_cvm.Abstencao(motivo)


def test_motivos_dva_e_documento_ausente():
    assert gordon_cvm.entradas({}, date(2026, 10, 20)) == gordon_cvm.Abstencao(
        "DFP anual dos controladores ausente"
    )
    assert gordon_cvm.proventos_da_dva(
        _ausente(), _ausente(), _l(1), _l(0), _l(0)
    ) == gordon_cvm.Abstencao("proventos incompletos: duas rubricas ausentes")
    assert gordon_cvm.proventos_da_dva(
        _l(-1), _l(1), _l(1), _l(0), _l(0)
    ) == gordon_cvm.Abstencao("provento inválido ou negativo na DVA")
    assert gordon_cvm.proventos_da_dva(
        _l(1), _l(0), _ausente(), _l(1), _l(0)
    ) == gordon_cvm.Abstencao(
        "estrutura da DVA não permite atribuir proventos aos controladores"
    )
    assert gordon_cvm.proventos_da_dva(
        _l(1), contas_cvm.Abstencao("inválido"), _l(1), _l(0), _l(0)
    ) == gordon_cvm.Abstencao("proventos incompletos: inválido")
    assert gordon_cvm.proventos_da_dva(
        _l(1e308), _l(1e308), _l(1), _l(0), _l(0)
    ) == gordon_cvm.Abstencao("resultado não finito: proventos DVA")


@pytest.mark.parametrize(
    "total,compativel",
    [
        (899, False),
        (900, False),
        (901, True),
        (1000, True),
        (1099, True),
        (1100, False),
        (2000, False),
        (500, False),
    ],
)
def test_gordon11_razao_aberta_da_composicao(total, compativel):
    from sentinela.data.acoes_cvm import Composicao
    from sentinela.domain.units import Escala

    base = Composicao(
        on=1000,
        pn=0,
        tesouraria_on=0,
        tesouraria_pn=0,
        tesouraria_total=0,
        dt_refer="2025-12-31",
        versao="1",
    )
    recente = Composicao(
        on=total,
        pn=0,
        tesouraria_on=0,
        tesouraria_pn=0,
        tesouraria_total=0,
        dt_refer="2026-06-30",
        versao="1",
    )
    r = gordon_cvm.compatibilidade_base(
        base,
        recente,
        escala=Escala.UNIDADE,
        escala_recente=Escala.UNIDADE,
        especie="ON",
        eh_unit=False,
        acoes_por_unit=None,
        shares_outstanding=None,
    )
    assert r["compativel"] is compativel
    assert r["razao"] == total / 1000
    assert (
        "evento posterior ao último documento entregue não é detectado" in r["avisos"]
    )


@pytest.mark.parametrize(
    "shares,avisa",
    [(950, False), (1050, False), (1051, True), (949, True), (None, False)],
)
def test_gordon11_yfinance_so_avisa(shares, avisa):
    from sentinela.data.acoes_cvm import Composicao
    from sentinela.domain.units import Escala

    base = Composicao(
        on=1000,
        pn=0,
        tesouraria_on=0,
        tesouraria_pn=0,
        tesouraria_total=0,
        dt_refer="2025-12-31",
        versao="1",
    )
    r = gordon_cvm.compatibilidade_base(
        base,
        base,
        escala=Escala.UNIDADE,
        escala_recente=Escala.UNIDADE,
        especie="ON",
        eh_unit=False,
        acoes_por_unit=None,
        shares_outstanding=shares,
    )
    assert r["compativel"] is True
    assert any("yfinance" in a for a in r["avisos"]) is avisa


@pytest.mark.parametrize("nome", ["DFP", "composição"])
@pytest.mark.parametrize(
    "campo,valor,motivo",
    [
        ("periodo_referencia", "2026-10-20", "posterior"),
        ("data_entrega", "2026-10-20", "posterior"),
        ("data_coleta", "2026-10-21T18:00:00+00:00", "posterior"),
        ("data_coleta", "2026-02-20T18:00:00", "sem fuso horário"),
        ("data_entrega", None, "ausente"),
    ],
)
def test_corte_revalidado_para_cada_evidencia(nome, campo, valor, motivo):
    d = _dados()
    prov = (
        d["gordon_cvm"]["proveniencia"]
        if nome == "DFP"
        else d["base_acionaria_gordon"]["proveniencia"]
    )
    prov[campo] = valor
    r = gordon_cvm.entradas(d, date(2026, 10, 20))
    esperado = (
        f"evidência da {nome} posterior ao as_of"
        if motivo == "posterior"
        else f"coleta da {nome} sem fuso horário"
        if motivo == "sem fuso horário"
        else f"proveniência temporal da {nome} ausente"
    )
    assert r == gordon_cvm.Abstencao(esperado)


def test_instante_de_coleta_exato_e_fuso_do_asof():
    from datetime import UTC, datetime

    d = _dados()
    for prov in (
        d["gordon_cvm"]["proveniencia"],
        d["base_acionaria_gordon"]["proveniencia"],
    ):
        prov["data_coleta"] = "2026-10-20T18:00:00+00:00"
    assert isinstance(
        gordon_cvm.entradas(d, datetime(2026, 10, 20, 18, tzinfo=UTC)), dict
    )
    assert gordon_cvm.entradas(
        d, datetime(2026, 10, 20, 17, 59, tzinfo=UTC)
    ) == gordon_cvm.Abstencao("evidência da DFP posterior ao as_of")
    assert gordon_cvm.entradas(
        d, datetime(2026, 10, 20, 18, tzinfo=UTC).replace(tzinfo=None)
    ) == gordon_cvm.Abstencao("as_of exige fuso horário")


@pytest.mark.parametrize(
    "evento",
    [
        "distribuicao_extraordinaria_identificada",
        "mudanca_estrutural_sem_reconciliacao",
    ],
)
def test_evento_identificado_impede_projecao_mesmo_com_dva_anual(evento):
    d = _dados()
    d["gordon_cvm"]["hipotese_dva_anual"] = True
    d["gordon_cvm"][evento] = True
    assert gordon_cvm.entradas(d, date(2026, 10, 20)) == gordon_cvm.Abstencao(
        "fluxo não representativo: evento identificado sem reconciliação"
    )


@pytest.mark.parametrize(
    "corte_macro,aceita",
    [("2026-10-20T18:00:00+00:00", True), ("2026-10-21T18:00:00+00:00", False)],
)
def test_contexto_macro_revalidado_quando_o_corte_e_so_data(corte_macro, aceita):
    d = _dados()
    d["taxa_real"]["as_of"] = corte_macro
    r = gordon_cvm.entradas(d, date(2026, 10, 20))
    if aceita:
        assert isinstance(r, dict)
    else:
        assert r == gordon_cvm.Abstencao("contexto da taxa real posterior ao as_of")


def _composicao(total, dt_refer):
    from sentinela.data.acoes_cvm import Composicao

    return Composicao(
        on=total,
        pn=0,
        tesouraria_on=0,
        tesouraria_pn=0,
        tesouraria_total=0,
        dt_refer=dt_refer,
        versao="1",
    )


@pytest.mark.parametrize(
    "escala_dfp,total_dfp,escala_recente,total_recente",
    [("MIL", 1000, "UNIDADE", 1_010_000), ("UNIDADE", 1_000_000, "MIL", 1010)],
)
def test_escala_da_composicao_recente_converte_antes_da_razao(
    escala_dfp, total_dfp, escala_recente, total_recente
):
    # F2B-54 (auditoria D30 do F2B-1): DFP e ITR em escalas diferentes não são evento.
    from sentinela.domain.units import Escala

    r = gordon_cvm.compatibilidade_base(
        _composicao(total_dfp, "2025-12-31"),
        _composicao(total_recente, "2026-06-30"),
        escala=Escala[escala_dfp],
        escala_recente=Escala[escala_recente],
        especie="ON",
        eh_unit=False,
        acoes_por_unit=None,
        shares_outstanding=None,
    )
    assert r["compativel"] is True
    assert r["razao"] == pytest.approx(1.01)


def test_escala_da_composicao_recente_indeterminada_abstem():
    from sentinela.domain.units import Escala

    r = gordon_cvm.compatibilidade_base(
        _composicao(1000, "2025-12-31"),
        _composicao(1000, "2026-06-30"),
        escala=Escala.UNIDADE,
        escala_recente=None,
        especie="ON",
        eh_unit=False,
        acoes_por_unit=None,
        shares_outstanding=None,
    )
    assert r["compativel"] is False
    assert r["motivo"] == "escala das ações do documento mais recente indeterminada"
