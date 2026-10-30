"""Helpers da UI por lente, sem importar/desenhar o app nem acessar rede."""

import ast
import math
import numbers
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app.py"


def _helpers():
    arvore = ast.parse(APP.read_text())
    nomes = {"_texto_lente", "_linhas_lentes"}
    nos = [n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name in nomes]
    assert len(nos) == 2
    escopo = {"math": math, "numbers": numbers}
    exec(compile(ast.Module(body=nos, type_ignores=[]), str(APP), "exec"), escopo)  # noqa: S102 — somente helpers locais selecionados por AST
    return escopo


@pytest.mark.parametrize("valor", [None, math.nan, math.inf, 0, -1, True])
def test_abstencao_por_lente_mostra_traco_e_causa(valor):
    assert _helpers()["_texto_lente"]({"valor": valor, "abstencao": "sem fonte"}) == (
        "—",
        "sem fonte",
    )


def test_ui_preserva_valores_distintos_distancias_e_criterio():
    linhas = _helpers()["_linhas_lentes"](
        {
            "lentes": {
                "Graham": {
                    "valor": 150,
                    "versao": "2.1",
                    "as_of": "2026-10-28T20:34:41-03:00",
                    "distancia_ao_preco_pct": 50,
                    "regime": "SEM_TAXA",
                    "janela": {"inicio": "2021-01-01", "fim": "2025-12-31"},
                    "premissas": ["hipótese"],
                },
                "Bazin": {
                    "valor": 100,
                    "distancia_ao_preco_pct": 0,
                    "regime": "NOMINAL",
                    "janela": {},
                    "tipo_valor": "preço-limite informativo",
                    "criterio_6pct": "atinge 6%",
                },
                "Lynch": {
                    "valor": None,
                    "abstencao": "perfil renda",
                    "distancia_ao_preco_pct": None,
                    "regime": "NOMINAL",
                    "janela": {},
                },
            }
        }
    )
    assert [r["Valor"] for r in linhas] == ["R$ 150.00", "R$ 100.00", "—"]
    assert [r["Distância ao preço (%)"] for r in linhas] == ["50.00%", "0.00%", "—"]
    assert linhas[1]["Referencial"] == "preço-limite informativo"
    assert linhas[1]["Critério Bazin"] == "atinge 6%"
    assert linhas[2]["Motivo"] == "perfil renda"
    assert linhas[0]["Janela"] == "2021-01-01 a 2025-12-31"
    assert linhas[0]["Versão"] == "2.1"
    assert linhas[0]["Corte"] == "2026-10-28T20:34:41-03:00"


def test_terminal_nao_tem_card_unico_score_ou_cores_de_sinal():
    codigo = APP.read_text()
    assert 'k2.metric("Valor Justo"' not in codigo
    assert 'k4.metric("Score"' not in codigo
    assert "_cor_recomendacao(" not in codigo
    assert "cores_bar = ['#00c853'" not in codigo
    assert "_linhas_lentes(analise)" in codigo


def test_grafico_usa_lentes_reais_sem_colorir_sinal():
    import plotly.graph_objects as go

    arvore = ast.parse(APP.read_text())
    no = next(
        n
        for n in arvore.body
        if isinstance(n, ast.FunctionDef) and n.name == "_plotar_metodos"
    )
    contexto = {"go": go}
    exec(compile(ast.Module(body=[no], type_ignores=[]), str(APP), "exec"), contexto)  # noqa: S102 — somente helper local selecionado por AST
    f = contexto["_plotar_metodos"]
    fig = f(
        {"Graham": {"valor": 150}, "Bazin": {"valor": 80}, "Lynch": {"valor": None}},
        100,
    )
    assert list(fig.data[0].x) == [150, 80]
    assert list(fig.data[0].y) == ["Graham", "Bazin"]
    assert len(set(fig.data[0].marker.color)) == 1
    assert f({"Lynch": {"valor": None}}, 100) is None
