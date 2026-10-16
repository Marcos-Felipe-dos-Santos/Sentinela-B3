"""Índice oficial de tickers, emissores e classes de ativo (F2A-1)."""

from sentinela.data.referencia.indice import carregar_indice, salvar_indice
from sentinela.data.referencia.registro import Excecao, Indice, Registro

__all__ = ["Excecao", "Indice", "Registro", "carregar_indice", "salvar_indice"]
