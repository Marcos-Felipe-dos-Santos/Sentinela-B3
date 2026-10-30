"""BUG-2C-57: cobertura documental completa não comprova comparabilidade."""

import ast
from contextlib import nullcontext
from pathlib import Path

import pandas as pd

from sentinela.reports.rastreabilidade import _apresentar_qualidade
from tests.test_qualidade import documentos, quadro


def test_ui_mostra_causa_e_estado_parcial_com_cinco_documentos():
    docs = documentos()
    docs[2]["evidencia_comparabilidade"] = None
    qualidade = quadro(docs)
    assert qualidade["cobertura"]["observados"] == 5
    assert qualidade["comparavel"] is False
    textos = []

    class Tela:
        def expander(self, titulo):
            return nullcontext()

        def caption(self, texto):
            textos.append(texto)

        def info(self, texto):
            textos.append(texto)

        def dataframe(self, *args, **kwargs):
            pass

    caminho = Path(__file__).resolve().parents[2] / "app.py"
    arvore = ast.parse(caminho.read_text())
    no = next(
        n
        for n in ast.walk(arvore)
        if isinstance(n, ast.With)
        and any(
            isinstance(i.context_expr, ast.Call)
            and isinstance(i.context_expr.func, ast.Attribute)
            and i.context_expr.func.attr == "expander"
            and i.context_expr.args
            and isinstance(i.context_expr.args[0], ast.Constant)
            and i.context_expr.args[0].value == "Qualidade empresarial — descritiva"
            for i in n.items
        )
    )
    escopo = {
        "st": Tela(),
        "pd": pd,
        "quadro": _apresentar_qualidade(qualidade),
        "analise": {"qualidade": qualidade},
    }
    exec(compile(ast.Module(body=[no], type_ignores=[]), str(caminho), "exec"), escopo)  # noqa: S102 — executa apenas bloco local de apresentação
    assert any(qualidade["motivo"] in t for t in textos)
    assert any("Quadro parcial" in t for t in textos)
    assert any("Comparabilidade não demonstrada" in t for t in textos)
