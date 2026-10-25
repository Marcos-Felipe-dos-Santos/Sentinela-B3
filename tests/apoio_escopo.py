"""Escopo que a cascata grava para uma ação de empresa (F2B-4), para os testes do motor.

A cascata sempre grava a classe oficial e o modelo do BPP consolidado; o motor não presume
nenhum dos dois. O helper completa o mesmo dicionário (o motor grava nele), sem trocar um
valor que o teste já declarou, inclusive `None`.
"""

ESCOPO_EMPRESA = {"classe_ativo": "STOCK", "modelo_bpp": "empresa"}


def de_empresa(dados):
    for chave, valor in ESCOPO_EMPRESA.items():
        dados.setdefault(chave, valor)
    return dados
