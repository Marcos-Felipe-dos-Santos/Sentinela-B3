"""F3-8d: fronteira, exclusão por horizonte e banda, com contas feitas à mão.

Ficha do backtest §9 e §10 caso 9; decisão 17. Grade: 36 datas mensais (dia 28,
jan/2019 a dez/2021) com 25 ativos cada; a distância do ativo i (1..25) é 2(i − 13),
de −24 a 24, e o retorno total é distância/100, com CDI de 10% no horizonte.
"""

import importlib.util
from datetime import date
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "banda_neutra_fase3.py"


@pytest.fixture(scope="module")
def banda():
    spec = importlib.util.spec_from_file_location("banda_neutra_fase3", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


SEM_QUINTIS = "lente sem data com quintis formados"
DATAS = [date(2019 + k // 12, k % 12 + 1, 28) for k in range(36)]


def _fim(dia, meses):
    total = dia.month - 1 + meses
    return date(dia.year + total // 12, total % 12 + 1, 28)


def _grade(lente="Graham", horizontes=(12, 24), abstencao=None):
    saida = []
    for dia in DATAS:
        for h in horizontes:
            for i in range(1, 26):
                distancia = 2 * (i - 13)
                saida.append(
                    {
                        "ticker": f"ATV{i:02d}3",
                        "lente": lente,
                        "D": dia.isoformat(),
                        "fim": _fim(dia, h).isoformat(),
                        "horizonte": h,
                        "modo": "estrito",
                        "distancia_ao_preco_pct": None if abstencao else distancia,
                        "abstencao": abstencao,
                        "retorno_total": distancia / 100,
                        "abstencao_retorno": None,
                        "retorno_cdi": 0.10,
                    }
                )
    return saida


def test_fronteira_e_exclusao_por_horizonte(banda):
    obs = _grade()
    doze = banda.calibrar_lente(obs, 12)
    # ceil(36/2) = 18ª data: 28/06/2020, inclusiva
    assert doze["fronteira"] == "2020-06-28"
    assert doze["datas_com_quintis"] == 36
    # D de jan a jun/2019 terminam até 28/06/2020; jul/2019 a jun/2020 (12 datas) saem
    assert doze["n_calibracao"] == 6 * 25
    assert doze["excluidas_pela_fronteira"] == 12 * 25
    assert doze["n_validacao"] == 18 * 25
    vinte_e_quatro = banda.calibrar_lente(obs, 24)
    # a mesma data, em 24 meses, termina depois da fronteira: toda a metade sai
    assert vinte_e_quatro["excluidas_pela_fronteira"] == 18 * 25
    assert vinte_e_quatro["n_calibracao"] == 0
    assert vinte_e_quatro["abstencao"] == (
        "nenhuma observação de calibração termina até a fronteira"
    )
    assert "banda_pct" not in vinte_e_quatro


def test_banda_pela_mediana_do_modulo_e_estados(banda):
    doze = banda.calibrar_lente(_grade(horizontes=(12,)), 12)
    # |d| por data: 0, 2, 2, 4, 4, ..., 24, 24; a 13ª de 25 é 12
    assert doze["banda_pct"] == 12
    cal = doze["calibracao"]
    # d > 12: 14..24 (6 ativos); |d| ≤ 12: 13 ativos; d < −12: 6 ativos; × 6 datas
    assert (
        cal["sinal positivo"]["n"],
        cal["neutro"]["n"],
        cal["sinal negativo"]["n"],
    ) == (
        36,
        78,
        36,
    )
    # média de 14..24 = 19 → 0,19; excesso sobre o CDI de 10% = 0,09
    assert cal["sinal positivo"]["retorno_medio"] == pytest.approx(0.19)
    assert cal["sinal positivo"]["excesso_cdi_medio"] == pytest.approx(0.09)
    assert cal["sinal negativo"]["retorno_medio"] == pytest.approx(-0.19)
    assert cal["neutro"]["retorno_medio"] == pytest.approx(0.0)
    val = doze["validacao"]
    assert val["neutro"]["n"] == 13 * 18 and val["sinal positivo"]["n"] == 6 * 18


def test_data_sem_quintis_fica_fora_da_calibracao(banda):
    # jan/2019 com 24 ativos não forma quintis: sai da série e das duas metades
    obs = [
        o
        for o in _grade(horizontes=(12,))
        if not (o["D"] == "2019-01-28" and o["ticker"] == "ATV013")
    ]
    doze = banda.calibrar_lente(obs, 12)
    # 35 datas; ceil(35/2) = 18ª, de fev/2019: 28/07/2020
    assert doze["datas_com_quintis"] == 35
    assert doze["fronteira"] == "2020-07-28"
    # fev a jul/2019 terminam até a fronteira; ago/2019 a jul/2020 saem
    assert doze["n_calibracao"] == 6 * 25
    assert doze["excluidas_pela_fronteira"] == 12 * 25
    assert doze["n_validacao"] == 17 * 25


def test_banda_nao_depende_do_retorno(banda):
    obs = _grade(horizontes=(12,))
    for o in obs:
        o["retorno_total"] = -o["retorno_total"] * 7
    assert banda.calibrar_lente(obs, 12)["banda_pct"] == 12


def test_fim_alem_da_fronteira_na_calibracao_e_erro(banda):
    obs = [
        {
            "lente": "Graham",
            "ticker": "X3",
            "D": "2019-01-28",
            "fim": "2020-07-28",
            "horizonte": 12,
        }
    ]
    with pytest.raises(ValueError, match="termina depois da fronteira 2020-06-28"):
        banda.conferir_calibracao(obs, date(2020, 6, 28))
    banda.conferir_calibracao([{**obs[0], "fim": "2020-06-28"}], date(2020, 6, 28))


def test_lente_sem_quintis_abstem_com_motivos(banda):
    obs = _grade(lente="Gordon", horizontes=(12,), abstencao="inflação incompatível")
    saida = banda.calibrar_lente(obs, 12)
    assert saida["abstencao"] == SEM_QUINTIS
    assert saida["datas_com_quintis"] == 0
    assert saida["motivos"] == {"inflação incompatível": 36 * 25}
    assert "banda_pct" not in saida and "fronteira" not in saida


def test_menos_de_25_por_data_nao_forma_quintis(banda):
    obs = [o for o in _grade(horizontes=(12,)) if o["ticker"] != "ATV013"]
    assert banda.calibrar_lente(obs, 12)["abstencao"] == SEM_QUINTIS


def test_cobertura_por_lente_e_por_ano(banda):
    obs = _grade(horizontes=(12,)) + _grade(
        lente="Bazin", horizontes=(12,), abstencao="depende do F3-3e"
    )
    obs[0]["retorno_total"] = None
    obs[0]["abstencao_retorno"] = "fechamento de entrada indisponível"
    cob = banda.cobertura(obs)
    assert cob["Graham"]["12"]["2019"] == {
        "observacoes": 12 * 25,
        "datas": 12,
        "com_valor": 12 * 25,
        "com_retorno": 12 * 25 - 1,
        "com_valor_e_retorno": 12 * 25 - 1,
        "motivos": {},
        "motivos_retorno": {"fechamento de entrada indisponível": 1},
    }
    assert cob["Bazin"]["12"]["2021"]["com_valor"] == 0
    assert cob["Bazin"]["12"]["2021"]["motivos"] == {"depende do F3-3e": 12 * 25}


def test_proposta_nao_inclui_a_linha_sem_analise(banda):
    obs = _grade(horizontes=(12,))
    obs.append({**obs[0], "lente": "analise", "abstencao": "sem histórico"})
    proposta = banda.propor(obs, [])
    assert list(proposta["lentes"]) == ["Graham"]
    assert proposta["sem_analise"] == {"sem histórico": 1}
    # BUG-3-56: a análise sem lente chega em `sem_lentes`, somada às gravadas antes
    sem_lentes = [{"ticker": "X", "D": "2020-06-30", "motivo": "sem histórico"}]
    assert banda.propor(obs, [], sem_lentes)["sem_analise"] == {"sem histórico": 2}
    assert [p["horizonte"] for p in proposta["lentes"]["Graham"]] == [12, 24, 36]


def test_ultimo_mes_aberto_fica_fora_das_datas(banda):
    pregoes = [
        date(2018, 1, 30),
        date(2018, 1, 31),
        date(2018, 2, 27),
        date(2018, 3, 1),
    ]
    assert banda.datas_fim_de_mes(pregoes, date(2018, 1, 1)) == [
        date(2018, 1, 31),
        date(2018, 2, 27),
    ]
    assert banda.datas_fim_de_mes(pregoes, date(2018, 2, 1)) == [date(2018, 2, 27)]


def test_saida_fora_de_outputs_e_recusada(banda, tmp_path):
    with pytest.raises(SystemExit, match="só em outputs/"):
        banda.main(["--saida", str(tmp_path), "--observacoes", "x.json"])


ELEGIVEIS = [
    {"ticker": "AAAA3", "classe": "STOCK"},
    {"ticker": "BBBB11", "classe": "FII"},
    {"ticker": "CCCC4", "classe": "STOCK"},
    {"ticker": "DDDD11", "classe": "UNIT"},
    {"ticker": "EEEE11", "classe": "FII"},
]


def _tickers(itens):
    return [item["ticker"] for item in itens]


def test_filtro_por_classe_sem_limite_mantem_todos_da_classe(banda):
    filtrados = banda.filtrar_elegiveis(ELEGIVEIS, None, ["STOCK", "UNIT"])
    assert _tickers(filtrados) == ["AAAA3", "CCCC4", "DDDD11"]


def test_limite_por_classe_sem_filtro_de_classe(banda):
    filtrados = banda.filtrar_elegiveis(ELEGIVEIS, 1, None)
    assert _tickers(filtrados) == ["AAAA3", "BBBB11", "DDDD11"]


def test_filtro_e_limite_juntos(banda):
    assert _tickers(banda.filtrar_elegiveis(ELEGIVEIS, 1, ["FII"])) == ["BBBB11"]


def test_sem_filtro_nem_limite_devolve_todos_agrupados_por_classe(banda):
    filtrados = banda.filtrar_elegiveis(ELEGIVEIS, None, None)
    assert _tickers(filtrados) == ["AAAA3", "CCCC4", "BBBB11", "EEEE11", "DDDD11"]


def test_classes_sem_valor_e_erro_de_uso(banda, tmp_path):
    with pytest.raises(SystemExit):
        banda.main(["--executar", "--saida", "outputs/x", "--classes"])
