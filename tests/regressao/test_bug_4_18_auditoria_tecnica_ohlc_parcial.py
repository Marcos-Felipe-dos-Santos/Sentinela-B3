"""BUG-4-18: com High ou Low inválido, a auditoria técnica levanta exceção no ATR.

O refactor `e29ade6` (F4-A14) delegou momento e tendência a `TechnicalEngine`, que calcula
também o ATR com `High` e `Low`. Com fechamento utilizável e `High` textual, o relatório que
antes saía (RSI, médias e tendência só do `Close`) passou a levantar `TypeError` (bloqueador 4 da
auditoria R2 do bloco 0, `docs/loop/auditorias/bloco0-codex.md`).

Séries sintéticas; o esperado é o relatório da mesma série só com o `Close`.
"""

import contextlib
import io
import math

import pandas as pd
import pytest

import auditoria

FECHAMENTOS = [round(20 + 3 * math.sin(i / 5) + i * 0.05, 4) for i in range(60)]


def _relatorio(monkeypatch, historico: pd.DataFrame) -> tuple[dict, str]:
    monkeypatch.setattr(auditoria, "_rel", {"tickers": {"TSTA3": {}}})
    impresso = io.StringIO()
    with contextlib.redirect_stdout(impresso):
        auditoria.auditar_tecnica("TSTA3", {"historico": historico})
    return (
        auditoria._rel["tickers"]["TSTA3"]["tecnica"],
        auditoria.strip_ansi(impresso.getvalue()),
    )


@pytest.mark.parametrize(
    ("high", "low"),
    [
        pytest.param(["x"] * 60, FECHAMENTOS, id="high_textual"),
        pytest.param(["1,0"] * 60, ["a"] * 60, id="high_e_low_textuais"),
    ],
)
def test_high_ou_low_invalido_da_o_mesmo_relatorio_do_fechamento(
    monkeypatch, high, low
):
    esperado = _relatorio(monkeypatch, pd.DataFrame({"Close": FECHAMENTOS}))

    obtido = _relatorio(
        monkeypatch, pd.DataFrame({"Close": FECHAMENTOS, "High": high, "Low": low})
    )

    assert obtido == esperado


@pytest.mark.parametrize(
    ("high", "low"),
    [
        pytest.param(
            [c + 1 for c in FECHAMENTOS], [c - 1 for c in FECHAMENTOS], id="validos"
        ),
        pytest.param(FECHAMENTOS, [None] * 60, id="low_ausente"),
    ],
)
def test_high_e_low_numericos_ou_ausentes_nao_mudam_o_relatorio(monkeypatch, high, low):
    """Controle: o relatório da auditoria nunca usou High e Low."""
    esperado = _relatorio(monkeypatch, pd.DataFrame({"Close": FECHAMENTOS}))

    obtido = _relatorio(
        monkeypatch, pd.DataFrame({"Close": FECHAMENTOS, "High": high, "Low": low})
    )

    assert obtido == esperado
