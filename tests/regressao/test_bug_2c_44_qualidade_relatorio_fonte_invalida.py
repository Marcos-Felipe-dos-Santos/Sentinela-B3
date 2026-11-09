"""BUG-2C-44: relatório deve mostrar fonte inválida como ausência, sem AttributeError."""

from sentinela.reports.rastreabilidade import renderizar
from tests.test_qualidade_integracao import dados
from tests.test_rastreabilidade import _contexto


def test_proveniencia_lista_no_relatorio_tem_motivo():
    d = dados()
    d["serie_cvm"]["exercicios"][0]["proveniencia"] = ["fonte ilegível"]
    html = renderizar(_contexto(d))
    assert "fonte/disponibilidade da DFP não demonstrada" in html
