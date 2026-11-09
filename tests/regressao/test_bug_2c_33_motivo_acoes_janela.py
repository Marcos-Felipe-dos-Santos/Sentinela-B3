"""BUG-2C-33: preservar motivo documental das ações, F2C-1."""

from tests.test_janelas_fundamentais import AS_OF, dados_exemplo
from sentinela.data.janelas_fundamentais import entradas


def test_motivo_acoes_identifica_documento_e_causa():
    d = dados_exemplo()
    e = d["serie_cvm"]["exercicios"][0]
    e["acoes"] = None
    e["motivos"] = {"acoes": "escala das ações indeterminada"}
    r = entradas(d, AS_OF)
    assert (
        r["graham"]["abstencao"]
        == "ações do exercício 2021: escala das ações indeterminada"
    )
    assert r["lynch"]["abstencao"] == r["graham"]["abstencao"]
