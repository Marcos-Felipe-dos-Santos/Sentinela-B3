"""Calibração do spread dos FIIs de tijolo (F2B-2; ficha FII 1.1, §6; plano final, seção 3)."""

import math

import pytest

from sentinela.data import spread_fii as sf


def _meses(final="2026-09", n=60):
    ano, mes = int(final[:4]), int(final[5:])
    saida = []
    for _ in range(n):
        saida.append(f"{ano:04d}-{mes:02d}")
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    return saida[::-1]


def test_mediana_das_sessenta_medianas_mensais():
    por_mes = {m: [0.01 * (i % 5), 0.02, 0.03] for i, m in enumerate(_meses())}
    c = sf.calibrar(por_mes, "2026-09")
    medianas = [sorted([0.01 * (i % 5), 0.02, 0.03])[1] for i in range(60)]
    assert c.spread == pytest.approx(
        sorted(medianas)[29] / 2 + sorted(medianas)[30] / 2
    )
    assert (c.mes_inicial, c.mes_final) == ("2021-10", "2026-09")
    assert c.fundos_por_mes == (3, 3, 3)
    assert len(c.medianas) == 60
    assert c.medianas[0] == ("2021-10", medianas[0], 3)


def test_cada_mes_pesa_igual_independente_do_numero_de_fundos():
    por_mes = {m: [0.02] for m in _meses()}
    por_mes["2026-09"] = [0.10] * 500
    assert sf.calibrar(por_mes, "2026-09").spread == pytest.approx(0.02)


def test_meses_fora_da_janela_nao_entram():
    por_mes = {m: [0.02] for m in _meses()}
    por_mes["2021-09"] = [9.0]
    por_mes["2026-10"] = [9.0]
    assert sf.calibrar(por_mes, "2026-09").spread == pytest.approx(0.02)


@pytest.mark.parametrize("lacuna", [[], [float("nan")], [float("inf")], None])
def test_mes_sem_fundo_valido_e_lacuna(lacuna):
    por_mes = {m: [0.02] for m in _meses()}
    if lacuna is None:
        del por_mes["2024-03"]
    else:
        por_mes["2024-03"] = lacuna
    r = sf.calibrar(por_mes, "2026-09")
    assert r == sf.Abstencao(f"{sf.MOTIVO_LACUNA}: 2024-03")


def test_quartis_e_contagens():
    por_mes = {m: [float(i)] * (1 + i % 3) for i, m in enumerate(_meses())}
    c = sf.calibrar(por_mes, "2026-09")
    assert c.spread == pytest.approx(29.5)
    assert c.fundos_por_mes == (1, 3, 2)
    assert c.p25 == pytest.approx(14.75)
    assert c.p75 == pytest.approx(44.25)


def test_mediana_do_mes_ignora_nao_finitos():
    assert sf.mediana_do_mes([0.01, math.nan, 0.03, math.inf]) == pytest.approx(0.02)
    assert sf.mediana_do_mes([]) is None
