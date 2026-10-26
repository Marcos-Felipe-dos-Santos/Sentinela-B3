"""BUG-2B-50 (reaberto): o card "Valor Justo" do `app.py` mostra R$ 0.00 na abstenção.

Auditoria rápida do fechamento da 2B (Codex, 25/10/2026): desde o F2B-62 os motores não
trazem `fair_value` quando se abstêm, e `app.py` lia `analise.get('fair_value', 0)`,
convertendo a ausência em "Valor Justo R$ 0.00". Decisão do Marcos de 25/10/2026 (F2B-69):
sem valor numérico, o card mostra "—" e o motivo (`metodos_usados` ou `riscos`).

O `app.py` não é importável nos testes (desenha a tela no import); a função de formatação
é lida do código-fonte e executada isolada.
"""

import ast
import math
import numbers
from pathlib import Path

import numpy as np
import pytest

from valuation_engine import _abstencao_de_escopo

APP = Path(__file__).resolve().parents[2] / "app.py"


def _texto_valor_justo():
    arvore = ast.parse(APP.read_text(encoding="utf-8"))
    no = next(
        n
        for n in arvore.body
        if isinstance(n, ast.FunctionDef) and n.name == "_texto_valor_justo"
    )
    escopo = {"math": math, "numbers": numbers}
    exec(compile(ast.Module(body=[no], type_ignores=[]), str(APP), "exec"), escopo)  # noqa: S102 -- código do próprio repositório
    return escopo["_texto_valor_justo"]


@pytest.mark.parametrize(
    "analise, motivo",
    [
        (
            {
                "score_final": 50,
                "recomendacao": "NEUTRO",
                "perfil": "FII",
                "metodos_usados": "Dados insuficientes (DY ausente ou inválido)",
            },
            "Dados insuficientes (DY ausente ou inválido)",
        ),
        (
            _abstencao_de_escopo("classe ETF fora do escopo", "ETF"),
            "classe ETF fora do escopo",
        ),
        (
            {"fair_value": float("nan"), "metodos_usados": "", "riscos": ["sem preço"]},
            "sem preço",
        ),
    ],
)
def test_abstencao_mostra_traco_e_o_motivo(analise, motivo):
    assert _texto_valor_justo()(analise) == ("—", motivo)


def test_abstencao_sem_motivo_gravado_nao_mostra_numero():
    texto, motivo = _texto_valor_justo()({"metodos_usados": "", "riscos": []})
    assert texto == "—"
    assert motivo


@pytest.mark.parametrize("valor", [12.345, np.float64(12.345)])
def test_valor_numerico_continua_no_card(valor):
    assert _texto_valor_justo()({"fair_value": valor}) == ("R$ 12.35", None)


def test_card_nao_le_a_ausencia_como_zero():
    codigo = APP.read_text(encoding="utf-8")
    assert "get('fair_value', 0)" not in codigo
    assert 'k2.metric("Valor Justo", valor_justo)' in codigo
