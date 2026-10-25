"""Rendimento do FII com as guardas da ficha FII 1.1 (F2B-2): entrega, idade, tipo e eventos."""

from datetime import date

import pytest

from sentinela.data import fii_elegibilidade as fe
from sentinela.data import rendimento_fii as rf

HOJE = date(2026, 10, 19)
ISIN = "BRTSTICTF000"


def _meses(final=(2026, 9), n=13):
    ano, mes = final
    saida = []
    for _ in range(n):
        saida.append((ano, mes))
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    return saida[::-1]


def _entrega(ano, mes):
    ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return f"{ano:04d}-{mes:02d}-14"


def _registros(final=(2026, 9), dy="0.01", vp="100", **por_mes):
    linhas = []
    for i, (ano, mes) in enumerate(_meses(final)):
        chave = f"{ano:04d}-{mes:02d}"
        linha = {
            "Data_Referencia": f"{chave}-01",
            "Versao": "1",
            "Data_Entrega": _entrega(ano, mes),
            "Valor_Patrimonial_Cotas": vp,
            "Percentual_Dividend_Yield_Mes": None if i == 0 else dy,
            "Percentual_Amortizacao_Cotas_Mes": "0",
            "Cotas_Emitidas": "1000",
        }
        linha.update(por_mes.get(chave, {}))
        linhas.append(linha)
    return linhas


def _composicao(final=(2026, 9), **kw):
    linha = {c: "0" for c in (*fe.TIJOLO, *fe.PAPEL, *fe.FUNDO_DE_FUNDOS)}
    linha.update({"Imoveis_Renda_Acabados": "90", "CRI": "10"})
    linha.update({k: str(v) for k, v in kw.items()})
    linha.update(
        {"Data_Referencia": f"{final[0]:04d}-{final[1]:02d}-01", "Versao": "1"}
    )
    return [linha]


def _b3(stock=(), cash=None):
    return {
        "code": "TSTI",
        "fund": "FII TESTE",
        "stockDividends": list(stock),
        "cashDividends": [
            {"rate": "1,00", "relatedTo": f"{m}/2026", "isinCode": ISIN}
            for m in ("JULHO", "AGOSTO", "SETEMBRO")
        ]
        if cash is None
        else cash,
    }


def _avaliar(registros=None, composicoes=None, b3=None, preco=100.0, dia=HOJE):
    return rf.avaliar(
        _registros() if registros is None else registros,
        _composicao() if composicoes is None else composicoes,
        b3=_b3() if b3 is None else b3,
        codigo="TSTI",
        isin=ISIN,
        preco=preco,
        dia_as_of=dia,
    )


def test_tijolo_elegivel_soma_doze_meses():
    r = _avaliar()
    assert r["rendimento_12m"] == pytest.approx(12.0)
    assert r["dy"] == pytest.approx(0.12)
    assert r["mes_final"] == "2026-09"
    assert r["tipo"] == "tijolo"
    assert r["avisos"] == [
        (
            "rendimento sem valor da B3 para conferir: "
            "2025-10, 2025-11, 2025-12, 2026-01, 2026-02, 2026-03, 2026-04, 2026-05, "
            "2026-06"
        )
    ]


def test_entrega_no_dia_do_as_of_ainda_nao_vale():
    # A entrega de setembro é 14/10: num as_of de 14/10, a janela termina em agosto e o
    # Informe de agosto (entregue em 14/09) precisa do VP de agosto/2025.
    r = _avaliar(dia=date(2026, 10, 14))
    assert isinstance(r, rf.Abstencao)
    assert r.motivo == rf.MOTIVO_MESES_INCOMPLETOS


def test_versao_entregue_depois_do_as_of_tira_o_mes():
    registros = _registros(**{"2026-05": {"Data_Entrega": "2026-10-20"}})
    r = _avaliar(registros)
    assert isinstance(r, rf.Abstencao)
    assert r.motivo == rf.MOTIVO_MESES_INCOMPLETOS


@pytest.mark.parametrize("entrega", [None, "", "x"])
def test_entrega_ilegivel_nao_e_demonstrada(entrega):
    registros = _registros(**{"2026-09": {"Data_Entrega": entrega}})
    r = _avaliar(registros, composicoes=_composicao(final=(2026, 8)))
    # sem a entrega de setembro, a janela termina em agosto, e falta o VP de ago/2025
    assert isinstance(r, rf.Abstencao)


def test_informe_com_mais_de_tres_meses_abstem():
    r = _avaliar(_registros(final=(2026, 6)), _composicao(final=(2026, 6)))
    assert r == rf.Abstencao(rf.MOTIVO_IDADE)


def test_informe_com_tres_meses_vale():
    r = _avaliar(_registros(final=(2026, 7)), _composicao(final=(2026, 7)))
    assert r["mes_final"] == "2026-07"


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("Percentual_Dividend_Yield_Mes", "-0.001", rf.MOTIVO_DY_NEGATIVO),
        ("Percentual_Amortizacao_Cotas_Mes", "0.01", rf.MOTIVO_AMORTIZACAO),
        ("Percentual_Amortizacao_Cotas_Mes", "-0.01", rf.MOTIVO_AMORTIZACAO_INVALIDA),
        ("Cotas_Emitidas", "0", rf.MOTIVO_COTAS),
        ("Cotas_Emitidas", "-10", rf.MOTIVO_COTAS),
        ("Cotas_Emitidas", "inf", rf.MOTIVO_COTAS),
        ("Cotas_Emitidas", "nan", rf.MOTIVO_COTAS),
        ("Cotas_Emitidas", None, rf.MOTIVO_COTAS),
    ],
)
def test_guardas_da_matriz(campo, valor, motivo):
    r = _avaliar(_registros(**{"2026-03": {campo: valor}}))
    assert r == rf.Abstencao(motivo)


def test_cotas_fracionarias_valem():
    r = _avaliar(_registros(**{"2026-03": {"Cotas_Emitidas": "10.5"}}))
    assert r["rendimento_12m"] == pytest.approx(12.0)


def test_variacao_so_na_fracao_fica_em_contexto():
    depois = {
        f"2026-{m:02d}": {"Cotas_Emitidas": "1000.00003248"} for m in range(5, 10)
    }
    r = _avaliar(_registros(**depois))
    assert r["rendimento_12m"] == pytest.approx(12.0)
    assert r["emissoes"] == [
        {"mes": "2026-05", "cotas_antes": 1000, "cotas_depois": 1000.00003248}
    ]


def test_mes_sem_rendimento_vale_como_zero():
    r = _avaliar(_registros(**{"2026-03": {"Percentual_Dividend_Yield_Mes": "0"}}))
    assert r["rendimento_12m"] == pytest.approx(11.0)


def test_emissao_com_vp_continuo_fica_em_contexto():
    depois = {f"2026-{m:02d}": {"Cotas_Emitidas": "1500"} for m in range(5, 10)}
    r = _avaliar(_registros(**depois))
    assert r["rendimento_12m"] == pytest.approx(12.0)
    assert r["emissoes"] == [
        {"mes": "2026-05", "cotas_antes": 1000, "cotas_depois": 1500}
    ]


@pytest.mark.parametrize(
    ("composicao", "motivo"),
    [
        (_composicao(CRI="900"), "tipo de FII fora do escopo na 2B: papel"),
        (_composicao(FII="900"), "tipo de FII fora do escopo na 2B: fundo de fundos"),
        (
            _composicao(CRI="90"),
            "classificação de FII desconhecida: sem maioria estrita",
        ),
        ([], rf.MOTIVO_SEM_COMPOSICAO),
        (_composicao(final=(2026, 8)), rf.MOTIVO_SEM_COMPOSICAO),
    ],
)
def test_so_tijolo_pela_composicao_do_mes(composicao, motivo):
    assert _avaliar(composicoes=composicao) == rf.Abstencao(motivo)


def test_evento_de_base_na_janela_abstem():
    b3 = _b3(stock=[{"label": "DESDOBRAMENTO", "lastDatePrior": "10/03/2026"}])
    r = _avaliar(b3=b3)
    assert isinstance(r, rf.Abstencao)
    assert r.motivo.startswith("desdobramento oficial na janela")


def test_evento_antes_da_janela_nao_abstem():
    b3 = _b3(stock=[{"label": "DESDOBRAMENTO", "lastDatePrior": "17/04/2018"}])
    assert _avaliar(b3=b3)["rendimento_12m"] == pytest.approx(12.0)


@pytest.mark.parametrize("b3", [{}, {"code": "TSTI", "fund": "ISIN GENERIC"}])
def test_fonte_de_eventos_indisponivel_abstem(b3):
    r = rf.avaliar(
        _registros(),
        _composicao(),
        b3=b3,
        codigo="TSTI",
        isin=ISIN,
        preco=100.0,
        dia_as_of=HOJE,
    )
    assert r == rf.Abstencao(rf.MOTIVO_EVENTOS_INDISPONIVEIS)


@pytest.mark.parametrize(
    ("preco", "motivo"),
    [(0.0, rf.MOTIVO_PRECO), (40.0, rf.MOTIVO_DY_NAO_CONFIAVEL)],
)
def test_preco_e_dy_anual(preco, motivo):
    assert _avaliar(preco=preco) == rf.Abstencao(motivo)


def test_rendimento_anual_zero_abstem():
    r = _avaliar(_registros(dy="0"))
    assert r == rf.Abstencao(rf.MOTIVO_RENDIMENTO_NAO_POSITIVO)


def test_conferencia_divergente_vira_aviso_sem_abster():
    cash = [{"rate": "0,50", "relatedTo": "SETEMBRO/2026", "isinCode": ISIN}]
    r = _avaliar(b3=_b3(cash=cash))
    assert r["rendimento_12m"] == pytest.approx(12.0)
    assert r["avisos"][0] == (
        "rendimento do Informe diverge da B3: 2026-09 Informe R$ 1,00, B3 R$ 0,50"
    )
