"""F3-8b: fronteiras do retorno total, das fontes do retorno e do relatório.

Cada esperado é conta à mão pela ficha (docs/metodologia/backtest.md): proventos
com data ex em (D, T] reinvestidos no fechamento da ex (§5), eventos em ações na
mesma base, deslistagem com CDI em [L, T) (§5 e DD-55), suspensão com o último
preço, benchmarks do fechamento de D ao de T (§6). Unidades da B3: COTAHIST em
centavos ÷ FATCOT; relação de proventos em texto pt-BR por lote `cotado_por`.
"""

import math
from datetime import date

import numpy as np
import pytest

from backtesting.backtest_pit import (
    BacktestPIT,
    _fracao_supera,
    _iqr,
    _normalizar_hash,
    _preco_mantido,
    formar_quintis,
    fronteira_calibracao,
    quintis_por_modo,
    retorno_total,
    selecionar_horizonte,
)
from sentinela.data.pit.serie_ajustada import MOTIVO_SEM_DATA_EX
from sentinela.data.providers import b3_proventos

D = date(2022, 3, 31)
EX = date(2022, 4, 29)
MEIO = date(2022, 9, 30)
T = date(2023, 3, 31)
DEPOIS = date(2023, 4, 1)
PREGOES = [D, EX, MEIO, T]


class _Consulta:
    def __init__(self, linhas):
        self.linhas = linhas

    def fetchall(self):
        return self.linhas

    def fetchone(self):
        return self.linhas[0] if self.linhas else None


class _Banco:
    def __init__(self, precos, isin="BRABEVACNOR1"):
        self.precos = precos
        self.isin = isin

    def execute(self, sql, parametros):
        if "SELECT data, fechamento_centavos" in sql:
            return _Consulta(self.precos)
        if "SELECT isin FROM precos" in sql:
            return _Consulta([(self.isin,)] if self.isin else [])
        raise AssertionError(f"consulta não prevista no teste: {sql}")


def _precos(*pares, fator=1):
    return [(d.isoformat(), round(p * 100) * fator, fator) for d, p in pares]


class _Fontes:
    def __init__(
        self, monkeypatch, proventos=(), sem_prova=(), eventos=(), eventos_sp=()
    ):
        self.chamadas = []
        relacao = {"proventos": list(proventos), "coleta": "fixa"}
        if sem_prova is not None:
            relacao["sem_prova"] = list(sem_prova)
        self.relacao = relacao

        def proventos_ate(*a, **k):
            self.chamadas.append(("proventos", a, k))
            return relacao

        def eventos_ate(*a, **k):
            self.chamadas.append(("eventos", a, k))
            return {"eventos": list(eventos), "sem_prova": list(eventos_sp)}

        monkeypatch.setattr(b3_proventos, "proventos_ate", proventos_ate)
        monkeypatch.setattr(b3_proventos, "eventos_ate", eventos_ate)


def _executar(
    monkeypatch,
    precos,
    *,
    ticker="ABEV3",
    isin="BRABEVACNOR1",
    estado=None,
    benchmarks=None,
    pregoes=PREGOES,
    cnpj="cnpj",
):
    executor = BacktestPIT(
        _Banco(precos, isin), None, hoje=date(2026, 11, 13), cache_dir="cache"
    )
    chamadas = []

    def estado_terminal(cnpj_, ticker_, fim_, final_):
        chamadas.append((cnpj_, ticker_, fim_, final_))
        return estado or {
            "deslistagem": None,
            "suspensao_confirmada": False,
            "motivo_deslistagem": None,
        }

    monkeypatch.setattr(executor, "_estado_terminal", estado_terminal)
    saida = executor._retornos(
        ticker, cnpj, D, T, pregoes, benchmarks or {"IBOV": [], "CDI": []}, b3_proventos
    )
    return (*saida, chamadas)


def _provento(especie, ex, valor, cotado="1"):
    return {
        "especie": especie,
        "data_ex": ex.isoformat(),
        "valor_bruto": valor,
        "cotado_por": cotado,
    }


def _split(ex, isin="BRABEVACNOR1", data_com=None, fator=2, **extra):
    return {
        "isin": isin,
        "ativo_emitido": isin,
        "data_com": (data_com or date.fromordinal(ex.toordinal() - 1)).isoformat(),
        "data_ex": ex.isoformat(),
        "fator": fator,
        **extra,
    }


BASE = _precos((D, 10), (EX, 10), (T, 11))


# --- unidades da fonte ------------------------------------------------------


def test_cotacao_e_dividida_pelo_fator_de_cotacao(monkeypatch):
    _Fontes(monkeypatch)
    retorno, entrada, *_ = _executar(monkeypatch, _precos((D, 10), (T, 11), fator=1000))
    assert entrada == pytest.approx(10.0)
    assert retorno["retorno"] == pytest.approx(0.1)


def test_ticker_pn_le_so_a_especie_pn_com_milhar_e_lote(monkeypatch):
    _Fontes(
        monkeypatch,
        proventos=[
            _provento("ON", EX, "9,00"),
            _provento("PN", EX, "1.000,00", "1.000"),
        ],
    )
    retorno, *_ = _executar(monkeypatch, BASE, ticker="ABEV4", isin="BRABEVACNPR1")
    # 1.000,00 por lote de 1.000 = R$ 1 por ação, comprada a 10: 1,1 × 1,1 − 1
    assert retorno["retorno"] == pytest.approx(0.21)


def test_provento_cotado_por_lote_divide_pelo_lote(monkeypatch):
    _Fontes(monkeypatch, proventos=[_provento("ON", EX, "5,00", "10")])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["retorno"] == pytest.approx(1.1 * 1.05 - 1)


def test_provento_zero_e_valido_e_nao_altera_o_retorno(monkeypatch):
    _Fontes(monkeypatch, proventos=[_provento("ON", EX, "0,00")])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.1)


def test_especie_sem_mapeamento_abstem_com_motivo(monkeypatch):
    _Fontes(monkeypatch)
    retorno, *_ = _executar(monkeypatch, BASE, ticker="ABEV11", isin="BRABEVCDAM11")
    assert retorno["abstencao"] == "espécie do ticker não mapeada para proventos brutos"


def test_provento_ilegivel_abstem_com_motivo(monkeypatch):
    _Fontes(monkeypatch, proventos=[_provento("ON", EX, None)])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] == "provento sem valor, unidade ou data ex demonstrados"


@pytest.mark.parametrize(
    "ex,esperado",
    [
        (D, 0.1),  # ex em D: a entrada no fechamento já é ex (decisão 42)
        (T, 1.1 * (1 + 1 / 11) - 1),  # ex em T entra, comprada a 11
    ],
)
def test_fronteira_dos_proventos_e_aberta_em_d_e_fechada_em_t(
    monkeypatch, ex, esperado
):
    _Fontes(monkeypatch, proventos=[_provento("ON", ex, "1,00")])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["retorno"] == pytest.approx(esperado)


def test_fontes_de_proventos_e_eventos_sao_lidas_ate_t_inclusive(monkeypatch):
    fontes = _Fontes(monkeypatch)
    _executar(monkeypatch, BASE)
    (_, args_p, kwargs_p), (_, args_e, _) = fontes.chamadas
    # decisão 43 (F3-8d-fix): o ticker vai junto, para o ISIN do pregão na identidade
    assert args_p[1:] == ("ABEV", DEPOIS)
    assert kwargs_p == {"por_publicacao": True, "ticker": "ABEV3"}
    assert args_e[1:] == ("ABEV", DEPOIS)


@pytest.mark.parametrize(
    "data_com,abstem",
    [
        (D.isoformat(), True),
        (T.isoformat(), True),
        (DEPOIS.isoformat(), False),
        (None, True),
        ("31/03/2022", True),
    ],
)
def test_provento_sem_prova_no_horizonte_abstem(monkeypatch, data_com, abstem):
    _Fontes(monkeypatch, sem_prova=[{"data_com": data_com}])
    retorno, *_ = _executar(monkeypatch, BASE)
    if abstem:
        assert retorno["abstencao"] == (
            "relação de proventos contém registros sem prova no horizonte"
        )
    else:
        assert retorno["retorno"] == pytest.approx(0.1)


def test_relacao_sem_lista_de_registros_sem_prova_segue(monkeypatch):
    _Fontes(monkeypatch, sem_prova=None)
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["retorno"] == pytest.approx(0.1)


# --- eventos em ações -------------------------------------------------------


def test_desdobramento_com_ex_em_t_ajusta_a_entrada_depois_de_eventos_alheios(
    monkeypatch,
):
    # irrelevantes primeiro: ex depois de T, outra espécie e sem ex fora do horizonte
    _Fontes(
        monkeypatch,
        eventos=[
            _split(DEPOIS),
            _split(EX, isin="BRABEVACPNR1"),
            {"isin": "BRABEVACNOR1", "data_com": DEPOIS.isoformat(), "data_ex": None},
            {"isin": "BRABEVACNOR1", "data_ex": None},
            _split(T, data_com=MEIO),
        ],
    )
    retorno, *_ = _executar(monkeypatch, _precos((D, 10), (MEIO, 10), (T, 5.5)))
    # 2:1 com ex em T: entrada ajustada 10 / 2 = 5; 5,5 / 5 − 1
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.1)


@pytest.mark.parametrize("data_com", [D, T])
def test_evento_sem_data_ex_no_horizonte_abstem_com_motivo_padrao(
    monkeypatch, data_com
):
    _Fontes(
        monkeypatch,
        eventos=[
            {"isin": "BRABEVACNOR1", "data_com": data_com.isoformat(), "data_ex": None}
        ],
    )
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] == (
        "evento em ações sem data ex demonstrada no horizonte"
    )


@pytest.mark.parametrize(
    "data_com,abstem",
    [(D, True), (T, True), (DEPOIS, False), ("31/03/2022", True)],
    ids=["em_d", "em_t", "depois_de_t", "data_ilegivel"],
)
def test_evento_sem_prova_no_horizonte_abstem(monkeypatch, data_com, abstem):
    texto = data_com.isoformat() if isinstance(data_com, date) else data_com
    _Fontes(monkeypatch, eventos_sp=[{"data_com": texto}])
    retorno, *_ = _executar(monkeypatch, BASE)
    if abstem:
        assert retorno["abstencao"] == "evento em ações sem prova no horizonte"
    else:
        assert retorno["retorno"] == pytest.approx(0.1)


def test_evento_com_fator_e_motivo_sem_fator_abstem_pelo_motivo(monkeypatch):
    _Fontes(monkeypatch, eventos=[_split(EX, motivo_sem_fator="fator ilegível")])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] == "fator ilegível"


def test_evento_sem_fator_nem_motivo_abstem_com_motivo_padrao(monkeypatch):
    _Fontes(monkeypatch, eventos=[_split(EX, fator=None)])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] == "fator do evento ausente"


def test_evento_sem_isin_abstem_com_motivo(monkeypatch):
    _Fontes(monkeypatch, eventos=[_split(EX, isin=None)])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] == "evento em ações sem ISIN para associar ao ticker"


def test_ativo_sem_isin_anterior_e_sem_eventos_segue(monkeypatch):
    _Fontes(monkeypatch)
    retorno, *_, evidencia, _ = _executar(monkeypatch, BASE, isin=None)
    assert retorno["retorno"] == pytest.approx(0.1)
    assert evidencia["isin"] is None


# --- estado terminal, CDI e benchmarks --------------------------------------

CDI = [
    {"data": "2022-03-30", "valor": 9.0},
    {"data": D.isoformat(), "valor": 0.04},
    {"data": EX.isoformat(), "valor": 0.05},
    {"data": MEIO.isoformat(), "valor": 0.03},
    {"data": T.isoformat(), "valor": 0.5},
]
IBOV = [
    {"data": D.isoformat(), "valor": 100.0},
    {"data": EX.isoformat(), "valor": 90.0},
    {"data": T.isoformat(), "valor": 120.0},
]


def test_estado_terminal_recebe_cnpj_ticker_fim_e_fechamento_final(monkeypatch):
    _Fontes(monkeypatch)
    *_, chamadas = _executar(monkeypatch, BASE)
    *_, chamadas_sem_final = _executar(monkeypatch, _precos((D, 10), (EX, 12)))
    assert chamadas == [("cnpj", "ABEV3", T, True)]
    assert chamadas_sem_final == [("cnpj", "ABEV3", T, False)]


def test_deslistagem_rende_cdi_de_l_a_t_e_benchmarks_de_d_a_t(monkeypatch):
    _Fontes(monkeypatch)
    estado = {
        "deslistagem": EX,
        "suspensao_confirmada": False,
        "motivo_deslistagem": "OPA",
    }
    retorno, _, ibov, cdi, evidencia, _ = _executar(
        monkeypatch,
        _precos((D, 10), (EX, 12)),
        estado=estado,
        benchmarks={"IBOV": IBOV, "CDI": CDI},
    )
    # 12/10, depois CDI de [29/04, 31/03): pregões 29/04 e 30/09
    assert retorno["retorno"] == pytest.approx(1.2 * 1.0005 * 1.0003 - 1)
    assert retorno["deslistada"] is True
    assert ibov == pytest.approx(0.2)
    assert cdi == pytest.approx(1.0004 * 1.0005 * 1.0003 - 1)
    assert evidencia == {
        "ticker": "ABEV3",
        "precos": _precos((D, 10), (EX, 12)),
        "proventos": {"proventos": [], "coleta": "fixa", "sem_prova": []},
        "eventos": {"eventos": [], "sem_prova": []},
        "ibov": [IBOV[0], IBOV[2]],
        "cdi": CDI[1:4],
        "isin": "BRABEVACNOR1",
        "motivo": None,
        "estado_terminal": estado,
    }


def test_suspensao_confirmada_mantem_o_ultimo_preco(monkeypatch):
    _Fontes(monkeypatch)
    retorno, *_ = _executar(
        monkeypatch,
        _precos((D, 10), (EX, 12)),
        estado={
            "deslistagem": None,
            "suspensao_confirmada": True,
            "motivo_deslistagem": None,
        },
    )
    assert retorno["retorno"] == pytest.approx(0.2)
    assert retorno["suspensao"] is True


@pytest.mark.parametrize("faltante", [D.isoformat(), EX.isoformat()])
def test_cdi_sem_taxa_de_um_pregao_fica_sem_fator(monkeypatch, faltante):
    _Fontes(monkeypatch)
    cdi_lido = [r for r in CDI if r["data"] != faltante]
    *_, cdi, _, _ = _executar(
        monkeypatch, BASE, benchmarks={"IBOV": [], "CDI": cdi_lido}
    )
    assert cdi is None


def test_ibovespa_sem_fechamento_de_t_fica_sem_retorno(monkeypatch):
    _Fontes(monkeypatch)
    _, _, ibov, *_ = _executar(
        monkeypatch, BASE, benchmarks={"IBOV": IBOV[:2], "CDI": []}
    )
    assert ibov is None


def test_evidencia_do_retorno_sem_entrada_tem_so_precos_e_estado(monkeypatch):
    _Fontes(monkeypatch)
    retorno, entrada, ibov, cdi, evidencia, chamadas = _executar(
        monkeypatch, _precos((EX, 10), (T, 11))
    )
    assert retorno["abstencao"] == "fechamento de entrada indisponível"
    assert entrada is ibov is cdi is None and chamadas == []
    assert evidencia == {
        "ticker": "ABEV3",
        "precos": _precos((EX, 10), (T, 11)),
        "estado_terminal": {
            "deslistagem": None,
            "suspensao_confirmada": False,
            "motivo_deslistagem": None,
        },
    }


# --- retorno_total: fronteiras e motivos ------------------------------------


def test_intervalo_de_um_dia_tem_retorno_zero():
    assert retorno_total({D: 10}, inicio=D, fim=D)["retorno"] == 0


def test_deslistagem_no_proprio_d_rende_so_cdi():
    saida = retorno_total(
        {D: 10}, inicio=D, fim=T, deslistagem=D, cdi={D: 1.0}, pregoes=[D, T]
    )
    assert saida["retorno"] == pytest.approx(0.01)


def test_deslistagem_anterior_a_entrada_abstem():
    saida = retorno_total(
        {D: 10}, inicio=D, fim=T, deslistagem=date(2022, 3, 30), pregoes=[D, T]
    )
    assert saida["abstencao"] == "último pregão negociado anterior à entrada"


def test_deslistagem_em_t_nao_pede_cdi():
    saida = retorno_total({D: 10, T: 11}, inicio=D, fim=T, deslistagem=T)
    assert saida["retorno"] == pytest.approx(0.1) and saida["deslistada"] is True


def test_preco_abaixo_de_um_real_vale_e_zero_abstem():
    assert retorno_total({D: 0.5, T: 0.55}, inicio=D, fim=T)["retorno"] == (
        pytest.approx(0.1)
    )
    zero = retorno_total({D: 10, EX: 0, T: 11}, inicio=D, fim=T)
    assert zero["abstencao"] == "preço não positivo ou não finito no intervalo"


def test_deslistagem_sem_fechamento_do_ultimo_pregao_abstem():
    saida = retorno_total({D: 10, T: 11}, inicio=D, fim=T, deslistagem=EX)
    assert saida["abstencao"] == "último fechamento da deslistagem indisponível"


def test_suspensao_sem_o_pregao_final_no_calendario_abstem():
    saida = retorno_total(
        {D: 10}, inicio=D, fim=T, suspensao_confirmada=True, pregoes=[D]
    )
    assert saida["abstencao"] == "cobertura do pregão final indisponível"


def test_suspensao_com_preco_abaixo_de_um_real_mantem_o_preco():
    saida = retorno_total(
        {D: 0.5}, inicio=D, fim=T, suspensao_confirmada=True, pregoes=[D, T]
    )
    assert saida["retorno"] == 0 and saida["suspensao"] is True


def test_suspensao_com_evento_bloqueado_abstem_pelo_motivo_do_evento():
    eventos = [{"data_com": EX.isoformat(), "data_ex": None}]
    saida = retorno_total(
        {D: 10},
        (),
        eventos,
        inicio=D,
        fim=T,
        suspensao_confirmada=True,
        pregoes=PREGOES,
    )
    assert saida["abstencao"] == MOTIVO_SEM_DATA_EX
    assert _preco_mantido([(D, 10)], T, eventos) == (None, MOTIVO_SEM_DATA_EX)


def test_serie_bloqueada_abstem_pelo_motivo_do_ajuste():
    eventos = [{"data_com": EX.isoformat(), "data_ex": None}]
    saida = retorno_total({D: 10, T: 11}, (), eventos, inicio=D, fim=T)
    assert saida["abstencao"] == MOTIVO_SEM_DATA_EX


@pytest.mark.parametrize("valor", [-1.0, math.nan])
def test_provento_negativo_ou_nao_finito_abstem(valor):
    saida = retorno_total(
        {D: 10, T: 11}, [{"data_ex": T, "valor": valor}], inicio=D, fim=T
    )
    assert saida["abstencao"] == "provento bruto inválido no intervalo"


def test_soma_de_proventos_nao_representavel_abstem():
    proventos = [{"data_ex": T, "valor": 1e308}, {"data_ex": T, "valor": 1e308}]
    saida = retorno_total({D: 10, T: 11}, proventos, inicio=D, fim=T)
    assert saida["abstencao"] == "soma dos proventos não representável"


def test_ex_fora_do_calendario_abstem_com_a_data():
    saida = retorno_total(
        {D: 10, T: 11}, [{"data_ex": EX, "valor": 1}], inicio=D, fim=T, pregoes=[D, T]
    )
    assert saida["abstencao"] == "fechamento da data ex indisponível: 2022-04-29"


def test_ex_em_pregao_sem_negocio_reinveste_ao_ultimo_preco():
    # sem negócio em 29/04: compra ao último fechamento (12, de 30/03), não ao de D
    meio = date(2022, 4, 20)
    saida = retorno_total(
        {D: 10, meio: 12, T: 11},
        [{"data_ex": EX, "valor": 1}],
        inicio=D,
        fim=T,
        pregoes=[D, meio, EX, T],
    )
    assert saida["retorno"] == pytest.approx(1.1 * (1 + 1 / 12) - 1)


def test_dois_proventos_em_datas_ex_distintas_se_compoem():
    saida = retorno_total(
        {D: 10, EX: 10, MEIO: 10, T: 11},
        [{"data_ex": EX, "valor": 1}, {"data_ex": MEIO, "valor": 1}],
        inicio=D,
        fim=T,
    )
    assert saida["retorno"] == pytest.approx(1.1 * 1.1 * 1.1 - 1)


@pytest.mark.parametrize(
    "pregoes",
    [None, [D, T], [D, EX]],
    ids=["sem_calendario", "sem_ultimo_pregao", "sem_t"],
)
def test_deslistagem_sem_calendario_do_cdi_abstem(pregoes):
    saida = retorno_total(
        {D: 10, EX: 12}, inicio=D, fim=T, deslistagem=EX, cdi={EX: 0.1}, pregoes=pregoes
    )
    assert saida["abstencao"] == "calendário do CDI indisponível no horizonte"


def test_cdi_exige_a_taxa_do_ultimo_pregao_e_ignora_a_de_t():
    sem_l = retorno_total(
        {D: 10, EX: 12},
        inicio=D,
        fim=T,
        deslistagem=EX,
        cdi={MEIO: 0.1},
        pregoes=PREGOES,
    )
    assert sem_l["abstencao"] == "CDI indisponível no pregão 2022-04-29"
    com_t = retorno_total(
        {D: 10, EX: 12},
        inicio=D,
        fim=T,
        deslistagem=EX,
        cdi={D: 9.0, EX: 0.1, MEIO: 0.2},
        pregoes=PREGOES,
    )
    # taxa anterior a L ignorada; [L, T) = 29/04 e 30/09; sem taxa em T
    assert com_t["retorno"] == pytest.approx(1.2 * 1.001 * 1.002 - 1)


@pytest.mark.parametrize("taxa", [-100.0, -100.5, math.nan])
def test_taxa_do_cdi_invalida_abstem(taxa):
    saida = retorno_total(
        {D: 10, EX: 12},
        inicio=D,
        fim=T,
        deslistagem=EX,
        cdi={EX: taxa, MEIO: 0.1},
        pregoes=PREGOES,
    )
    assert saida["abstencao"] == "CDI indisponível no dia 2022-04-29"


def test_retorno_que_estoura_abstem():
    saida = retorno_total({D: 1e-300, T: 1e300}, inicio=D, fim=T)
    assert saida["abstencao"] == "retorno não finito"


# --- quintis, horizonte e relatório -----------------------------------------


def test_quintis_recusam_ativo_repetido_com_o_codigo():
    obs = [{"ticker": "A3", "distancia_ao_preco_pct": 1}] * 2
    with pytest.raises(ValueError) as erro:
        formar_quintis(obs)
    assert str(erro.value) == "ativo repetido no mesmo grupo: A3"


def test_quintis_contam_abstencoes_e_empates_nos_cortes():
    obs = [
        {"ticker": f"T{i:02d}3", "distancia_ao_preco_pct": 30 - i, "retorno_total": 0}
        for i in range(25)
    ]
    # posições 5/6 e 10/11 empatadas: dois empates atravessam cortes
    obs[5]["distancia_ao_preco_pct"] = obs[4]["distancia_ao_preco_pct"]
    obs[10]["distancia_ao_preco_pct"] = obs[9]["distancia_ao_preco_pct"]
    obs += [
        {"ticker": "AB3", "distancia_ao_preco_pct": 5, "abstencao": "sem DFP"},
        {"ticker": "AC3", "distancia_ao_preco_pct": None},
        {"ticker": "AD3", "distancia_ao_preco_pct": math.nan},
    ]
    saida = formar_quintis(obs)
    assert set(saida["quintis"]) == {1, 2, 3, 4, 5}
    assert saida["empates_nos_cortes"] == 2
    assert saida["abstencoes"] == {"sem DFP": 1, "distância ao preço indisponível": 2}


def test_modo_desconhecido_e_horizonte_fora_recusam_com_mensagem_exata():
    with pytest.raises(ValueError) as erro:
        quintis_por_modo([{"ticker": "A3", "modo": "misto"}])
    assert str(erro.value) == "modo histórico desconhecido: misto"
    with pytest.raises(ValueError) as erro:
        selecionar_horizonte([], 6, limite=T)
    assert str(erro.value) == "horizonte deve ser 12, 24 ou 36 meses"
    estrito = quintis_por_modo([{"ticker": "A3", "modo": "estrito"}])
    assert estrito["estrito"]["aviso"] is None


def test_fronteira_de_calibracao_e_a_data_da_metade_superior():
    datas = [date(2020, 1, 31), date(2020, 2, 28), date(2020, 3, 31)]
    assert fronteira_calibracao(datas) == date(2020, 2, 28)
    assert fronteira_calibracao([]) is None


def test_iqr_e_fracao_que_supera_sao_estritos():
    assert _iqr([1, 2, 3, 4, 5]) == 2
    assert _fracao_supera([(0.1, 0.1), (0.2, 0.1)]) == 0.5


def test_normalizacao_do_hash_trata_nao_finitos_e_escalares():
    assert _normalizar_hash(math.inf) == {"numero_nao_finito": "inf"}
    assert _normalizar_hash(math.nan) == {"numero_nao_finito": "nan"}
    assert _normalizar_hash(np.int64(3)) == 3
    assert _normalizar_hash(_SemItem()) == "sem item"


class _SemItem:
    def __str__(self):
        return "sem item"


# --- estado terminal pelo FCA -----------------------------------------------


def _fca(monkeypatch, referencias):
    from sentinela.data.referencia import universo

    monkeypatch.setattr(universo, "_fca_por_referencia", lambda *_: referencias)
    return BacktestPIT(_Banco([]), None, hoje=date(2026, 11, 13), cache_dir="c")


NEUTRO = {
    "deslistagem": None,
    "suspensao_confirmada": False,
    "motivo_deslistagem": None,
}


def test_fca_com_linha_sem_codigo_antes_da_do_ticker(monkeypatch):
    executor = _fca(
        monkeypatch,
        {
            ("cnpj", "2021-12-31"): [
                {"Codigo_Negociacao": "", "Data_Fim_Negociacao": ""},
                {"Codigo_Negociacao": "abev3", "Data_Fim_Negociacao": T.isoformat()},
            ],
            ("cnpj", "2020-12-31"): [
                {"Codigo_Negociacao": "ABEV3", "Data_Fim_Negociacao": ""}
            ],
        },
    )
    # fim de negociação em T é deslistagem no próprio T; a referência mais nova vale
    assert executor._estado_terminal("cnpj", "ABEV3", T, False) == {
        "deslistagem": T,
        "suspensao_confirmada": False,
        "motivo_deslistagem": None,
    }


def test_fca_sem_o_ticker_ou_com_referencia_ilegivel_e_neutro(monkeypatch):
    executor = _fca(
        monkeypatch,
        {("cnpj", "xx"): [{"Codigo_Negociacao": "ABEV3", "Data_Fim_Negociacao": ""}]},
    )
    assert executor._estado_terminal("cnpj", "ABEV4", T, False) == NEUTRO
    assert executor._estado_terminal("cnpj", "ABEV3", T, False) == NEUTRO


def test_motivo_de_cancelamento_sem_cadastro_ou_com_linha_vazia(monkeypatch):
    sem = BacktestPIT(_Banco([]), None, hoje=date(2026, 11, 13), cache_dir="c")
    assert sem._motivo_cancelamento("12345678000190") is None

    class _Cadastro:
        columns = ("CNPJ_CIA", "MOTIVO_CANCEL")

        def to_dict(self, orient):
            return [
                {"CNPJ_CIA": "", "MOTIVO_CANCEL": "OPA"},
                {"CNPJ_CIA": "11.111.111/0001-11", "MOTIVO_CANCEL": None},
            ]

    executor = BacktestPIT(
        _Banco([]), _Cadastro(), hoje=date(2026, 11, 13), cache_dir="c"
    )
    assert executor._motivo_cancelamento("") is None
    assert executor._motivo_cancelamento("11111111000111") is None
