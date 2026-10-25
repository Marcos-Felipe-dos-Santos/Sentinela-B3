"""Elegibilidade do FII para a lente de rendimento (F2B-2; ficha FII 1.1, §2 a §4 e §3a)."""

from datetime import date

import pytest

from sentinela.data import fii_elegibilidade as fe

# ── tipo pela composição do ativo_passivo ─────────────────────────────────────


def _composicao(**kw):
    linha = {c: "0" for c in (*fe.TIJOLO, *fe.PAPEL, *fe.FUNDO_DE_FUNDOS)}
    linha.update({k: str(v) for k, v in kw.items()})
    return linha


@pytest.mark.parametrize(
    ("valores", "tipo"),
    [
        ({"Imoveis_Renda_Acabados": 90, "CRI": 5, "FII": 5}, "tijolo"),
        ({"Terrenos": 30, "Direitos_Bens_Imoveis": 30, "LCI": 40}, "tijolo"),
        ({"CRI_CRA": 80, "Imoveis_Renda_Acabados": 20}, "papel"),
        ({"FII": 70, "LIG": 30}, "fundo de fundos"),
    ],
)
def test_tipo_pela_maioria_estrita(valores, tipo):
    assert fe.tipo_pela_composicao(_composicao(**valores)) == tipo


@pytest.mark.parametrize(
    "valores",
    [
        {"Imoveis_Renda_Acabados": 50, "CRI": 50},  # sem maioria estrita
        {},  # base zero
        {"Imoveis_Renda_Acabados": 100, "CRI": -1},  # posição negativa
        {"Imoveis_Renda_Acabados": "x"},  # não numérico
    ],
)
def test_tipo_desconhecido_abstem(valores):
    r = fe.tipo_pela_composicao(_composicao(**valores))
    assert isinstance(r, fe.Abstencao)
    assert r.motivo.startswith(fe.MOTIVO_TIPO_DESCONHECIDO)


def test_caixa_e_renda_fixa_nao_entram_na_base():
    linha = _composicao(Imoveis_Renda_Acabados=60, CRI=40)
    linha["Disponibilidades"] = "1000"
    linha["Titulos_Publicos"] = "1000"
    assert fe.tipo_pela_composicao(linha) == "tijolo"


def test_celula_vazia_conta_como_zero():
    linha = _composicao(Imoveis_Renda_Acabados=60)
    linha["CRI"] = None
    linha["FII"] = ""
    assert fe.tipo_pela_composicao(linha) == "tijolo"


# ── resposta da B3 e eventos de cota (§3a) ────────────────────────────────────


def _resposta(code="HGLG", fund="FII HGLG PAX", cash=(), stock=()):
    return {
        "code": code,
        "fund": fund,
        "cashDividends": list(cash),
        "stockDividends": list(stock),
    }


@pytest.mark.parametrize(
    "resposta",
    [
        None,
        "",
        [],
        _resposta(fund="ISIN GENERIC"),  # código desconhecido: registro genérico
        _resposta(code="XPML"),
        {**_resposta(), "stockDividends": None},
        {k: v for k, v in _resposta().items() if k != "cashDividends"},
    ],
)
def test_resposta_invalida_e_fonte_indisponivel(resposta):
    assert not fe.resposta_b3_valida(resposta, "HGLG")


def test_resposta_valida_com_listas_vazias():
    assert fe.resposta_b3_valida(_resposta(), "HGLG")


def _evento(label, data):
    return {"label": label, "lastDatePrior": data, "factor": "900,0"}


@pytest.mark.parametrize(
    ("eventos", "motivo"),
    [
        ([], None),
        ([_evento("DESDOBRAMENTO", "17/04/2018")], None),  # fora da janela
        ([_evento("DESDOBRAMENTO", "17/04/2026")], "desdobramento"),
        ([_evento("GRUPAMENTO", "01/09/2025")], "grupamento"),
        ([_evento("GRUPAMENTO", "18/10/2026")], "grupamento"),  # até o as_of
        ([_evento("DESDOBRAMENTO", "20/10/2026")], None),  # depois do as_of
        ([_evento("DESDOBRAMENTO", "xx")], "data ilegível"),
    ],
)
def test_evento_de_cota_na_janela_abstem(eventos, motivo):
    r = fe.evento_de_cota(eventos, date(2025, 9, 1), date(2026, 10, 19))
    if motivo is None:
        assert r is None
    else:
        assert motivo in r


# ── conferência com o rendimento oficial da B3 (§3a, complemento (a)) ─────────


def _pagamento(rate, mes, isin="BRHGLGCTF004"):
    return {"rate": rate, "relatedTo": mes, "isinCode": isin, "label": "RENDIMENTO"}


def test_conferencia_igual_em_duas_casas_sem_aviso():
    cash = [_pagamento("1,17000000000", "SETEMBRO/2026")]
    assert fe.conferencia_b3({"2026-09": 1.170289}, cash, "BRHGLGCTF004") == []


def test_conferencia_diferente_gera_aviso_com_mes_e_valores():
    cash = [_pagamento("1,10000000000", "SETEMBRO/2026")]
    avisos = fe.conferencia_b3({"2026-09": 1.170289}, cash, "BRHGLGCTF004")
    assert avisos == [
        "rendimento do Informe diverge da B3: 2026-09 Informe R$ 1,17, B3 R$ 1,10"
    ]


def test_conferencia_ignora_outro_isin_e_avisa_mes_sem_b3():
    cash = [
        _pagamento("1,09200000000", "SETEMBRO/2026", isin="BRHGLGR26M17"),
        _pagamento("1,10000000000", "AGOSTO/2026"),
    ]
    avisos = fe.conferencia_b3(
        {"2026-08": 1.1, "2026-09": 1.170289}, cash, "BRHGLGCTF004"
    )
    assert avisos == ["rendimento sem valor da B3 para conferir: 2026-09"]


def test_conferencia_soma_pagamentos_do_mesmo_mes():
    cash = [
        _pagamento("0,50000000000", "SETEMBRO/2026"),
        _pagamento("0,67000000000", "SETEMBRO/2026"),
    ]
    assert fe.conferencia_b3({"2026-09": 1.17}, cash, "BRHGLGCTF004") == []


def test_conferencia_sem_resposta_da_b3():
    assert fe.conferencia_b3({"2026-09": 1.17}, None, "BRHGLGCTF004") == [
        fe.AVISO_SEM_CONFERENCIA
    ]
