"""BUG-3-62 (Codex C3-06, checkpoint da Fase 3): a cobertura da lente sem os ativos sem lentes.

A ficha do backtest (§7) pede a cobertura de cada lente como a fração do universo elegível
com valor. `BacktestPIT._resumir` contava no universo só as observações das lentes; o ativo
elegível que falhava antes delas ia para `sem_lentes` e saía do denominador (na sonda final,
2018 mostrava 40 FIIs quando eram 43). Decisão 51 do Marcos (20/11/2026): o denominador é o
universo elegível aplicável à lente, incluindo os `sem_lentes` da classe dela nas datas com o
horizonte completo, com os motivos separados.

Mesmo cenário do F3-8b (`test_backtest_pit_executar.py`): 27 ações com Graham e Bazin em D1 e
D2, mais duas ações sem registro de lente (uma com o erro do serviço, outra sem lentes);
horizonte de 12 meses completo e de 24 incompleto.
"""

import pytest
from test_backtest_pit_executar import cenario  # noqa: F401 (fixture)

from backtesting.backtest_pit import BacktestPIT

ANTES = {"histórico sem cadastro": 2, "análise sem lentes": 2}


def test_universo_da_lente_inclui_os_sem_lentes_da_classe(cenario):  # noqa: F811
    resumo = cenario.executar()["resumo"]
    graham = next(
        r for r in resumo["lentes"] if (r["lente"], r["horizonte"]) == ("Graham", 12)
    )
    assert graham["universo_elegivel"] == 2 * (27 + 2)
    assert graham["com_valor"] == 52
    assert graham["cobertura"] == pytest.approx(52 / 58)
    assert graham["sem_lentes"] == 4
    assert graham["abstencoes_antes_das_lentes"] == ANTES


def _observacao(lente="Gordon", horizonte=12, abstencao=None):
    return {
        "ticker": "T0013",
        "lente": lente,
        "horizonte": horizonte,
        "modo": "estrito",
        "D": "2018-06-29",
        "fim": "2019-06-28",
        "abstencao": abstencao,
        "abstencao_retorno": None,
        "retorno_total": 0.1,
    }


def _sem_lente(classe="STOCK", horizontes=(12,), motivo="DADOS INSUFICIENTES"):
    return {
        "ticker": "T0023",
        "D": "2018-06-29",
        "classe": classe,
        "motivo": motivo,
        "horizontes": list(horizontes),
    }


def _linha(sem_lentes, classes=None, observacoes=None):
    resumo = BacktestPIT._resumir(
        observacoes or [_observacao()],
        [],
        {},
        sem_lentes,
        {"Gordon": {"STOCK", "UNIT"}} if classes is None else classes,
    )
    (linha,) = resumo["lentes"]
    return linha


def test_so_a_classe_da_lente_e_o_horizonte_completo_entram():
    linha = _linha(
        [
            _sem_lente(),
            _sem_lente(classe="UNIT", motivo="outro"),
            _sem_lente(classe="FII"),
            _sem_lente(classe=None),
            _sem_lente(horizontes=(24,)),
            _sem_lente(horizontes=()),
        ]
    )
    assert linha["universo_elegivel"] == 3
    assert linha["com_valor"] == 1
    assert linha["cobertura"] == pytest.approx(1 / 3)
    assert linha["sem_lentes"] == 2
    assert linha["abstencoes_antes_das_lentes"] == {
        "DADOS INSUFICIENTES": 1,
        "outro": 1,
    }


def test_sem_mapa_de_classes_nada_entra_e_sem_valor_cobertura_zero():
    linha = _linha([_sem_lente()], classes={})
    assert (linha["universo_elegivel"], linha["sem_lentes"]) == (1, 0)
    assert linha["abstencoes_antes_das_lentes"] == {}
    sem_valor = _linha([_sem_lente()], observacoes=[_observacao(abstencao="sem dado")])
    assert sem_valor["cobertura"] == 0 and sem_valor["universo_elegivel"] == 2


def test_chamada_antiga_sem_os_sem_lentes_segue_igual():
    resumo = BacktestPIT._resumir([_observacao()], [], {})
    (linha,) = resumo["lentes"]
    assert (linha["universo_elegivel"], linha["cobertura"], linha["sem_lentes"]) == (
        1,
        1,
        0,
    )


def test_registro_sem_horizontes_nao_entra():
    """Registro de `sem_lentes` sem a lista de horizontes completos não prova o horizonte."""
    antigo = {k: v for k, v in _sem_lente().items() if k != "horizontes"}
    assert _linha([antigo])["universo_elegivel"] == 1
