"""Tabela de correções de fonte (F2A-19, decisão [CORREÇÕES] de 5/10/2026).

Cada linha liga um ticker ao CNPJ que a evidência oficial aponta, no lugar de um código
defeituoso da fonte (`codigo_na_fonte`: o `Codigo_Negociacao` do FCA ou o `Codigo_ISIN` do
Informe Mensal). Nenhum código é inventado: a linha só vale se a evidência (arquivo oficial,
coluna e data em que o defeito aparece) estiver preenchida.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path

CAMINHO_PADRAO = Path(__file__).with_name("correcoes.csv")


class CorrecaoInvalida(Exception):
    """Linha da tabela de correções sem evidência ou sem campo obrigatório."""


@dataclass(frozen=True)
class Correcao:
    ticker: str
    cnpj: str
    codigo_na_fonte: str
    motivo: str
    arquivo: str
    coluna: str
    data: str

    def para_dict(self) -> dict:
        return asdict(self)


_CAMPOS = tuple(f.name for f in fields(Correcao))


def validar_correcoes(correcoes) -> dict[tuple[str, str], Correcao]:
    """(CNPJ, código na fonte) → correção; levanta `CorrecaoInvalida` em linha incompleta."""
    por_chave: dict[tuple[str, str], Correcao] = {}
    for correcao in correcoes:
        vazios = [c for c in _CAMPOS if not str(getattr(correcao, c) or "").strip()]
        if vazios:
            raise CorrecaoInvalida(
                f"Correção de {correcao.ticker or '?'} rejeitada: sem {', '.join(vazios)}"
            )
        chave = (correcao.cnpj, correcao.codigo_na_fonte)
        if chave in por_chave:
            raise CorrecaoInvalida(f"Correção repetida para {chave}")
        por_chave[chave] = correcao
    return por_chave


def ler_correcoes(caminho: Path = CAMINHO_PADRAO) -> list[Correcao]:
    """Lê a tabela (CSV com `;`, UTF-8) e a valida."""
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        faltando = [c for c in _CAMPOS if c not in (leitor.fieldnames or [])]
        if faltando:
            raise CorrecaoInvalida(f"Tabela de correções sem as colunas {faltando}")
        correcoes = [
            Correcao(**{c: (linha[c] or "").strip() for c in _CAMPOS})
            for linha in leitor
        ]
    validar_correcoes(correcoes)
    return correcoes
