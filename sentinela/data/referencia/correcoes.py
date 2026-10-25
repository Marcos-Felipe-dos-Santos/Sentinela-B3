"""Tabela de correções de fonte (F2A-19, decisão [CORREÇÕES] de 5/10/2026).

Cada linha liga um ticker ao CNPJ que a evidência oficial aponta, no lugar de um código
defeituoso da fonte (`codigo_na_fonte`: o `Codigo_Negociacao` do FCA ou o `Codigo_ISIN` do
Informe Mensal). Nenhum código é inventado: a linha só vale se a evidência (arquivo oficial,
coluna e data em que o defeito aparece) estiver preenchida.

Correção de espécie (F2B-13; ficha por ação 1.1, decisão 7.10): `campo` = "especie" e
`valor` = a espécie correta (ON ou PN), para o ticker do `codigo_na_fonte`. Exige as duas
evidências do mesmo documento citadas em `arquivo`: a Composição do Capital e a DRE; com uma
só, a linha é rejeitada. Caso a caso, nunca automática.

Evidência da ligação (F2A-39, [BTG]): quando a ligação do ticker ao CNPJ não vem do próprio
arquivo do defeito, a linha cita a fonte dela (`ligacao_fonte`, `ligacao_campo`,
`ligacao_data`). É obrigatória com código na fonte sem identidade (só zeros, como o
`000000` da unit do BTG no FCA); preenchida em parte, a linha é rejeitada.
"""

from __future__ import annotations

import csv
import re
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
    campo: str = ""
    valor: str = ""
    ligacao_fonte: str = ""
    ligacao_campo: str = ""
    ligacao_data: str = ""

    def para_dict(self) -> dict:
        """Os campos da linha; `campo` e `valor` só na correção de espécie, e a ligação só
        quando citada."""
        dados = asdict(self)
        if not self.campo:
            dados.pop("campo")
            dados.pop("valor")
        if not self.ligacao_fonte:
            for chave in _LIGACAO:
                dados.pop(chave)
        return dados


_LIGACAO = ("ligacao_fonte", "ligacao_campo", "ligacao_data")
_OPCIONAIS = ("campo", "valor", *_LIGACAO)
_CAMPOS = tuple(f.name for f in fields(Correcao) if f.name not in _OPCIONAIS)
CAMPOS_CORRIGIVEIS = {"especie": ("ON", "PN")}
_EVIDENCIAS_DA_ESPECIE = ("composicao_capital", "dre")


def validar_correcoes(correcoes) -> dict[tuple[str, str], Correcao]:
    """(CNPJ, código na fonte) → correção; levanta `CorrecaoInvalida` em linha incompleta."""
    por_chave: dict[tuple[str, str], Correcao] = {}
    for correcao in correcoes:
        vazios = [c for c in _CAMPOS if not str(getattr(correcao, c) or "").strip()]
        if vazios:
            raise CorrecaoInvalida(
                f"Correção de {correcao.ticker or '?'} rejeitada: sem {', '.join(vazios)}"
            )
        if not re.fullmatch(r"[A-Z][A-Z0-9]{3}\d{1,2}", correcao.ticker):
            raise CorrecaoInvalida(f"Ticker inválido na correção: {correcao.ticker!r}")
        _validar_campo(correcao)
        _validar_ligacao(correcao)
        chave = (correcao.cnpj, correcao.codigo_na_fonte)
        if chave in por_chave:
            raise CorrecaoInvalida(f"Correção repetida para {chave}")
        por_chave[chave] = correcao
    return por_chave


def _validar_ligacao(correcao: Correcao) -> None:
    """Evidência da ligação: obrigatória com código sem identidade; nunca pela metade."""
    preenchidos = [c for c in _LIGACAO if str(getattr(correcao, c) or "").strip()]
    sem_identidade = set(correcao.codigo_na_fonte.strip()) == {"0"}
    if (
        preenchidos
        and len(preenchidos) < len(_LIGACAO)
        or (sem_identidade and not preenchidos)
    ):
        faltando = [c for c in _LIGACAO if c not in preenchidos]
        raise CorrecaoInvalida(
            f"Correção de {correcao.ticker} rejeitada: evidência da ligação sem "
            f"{', '.join(faltando)}"
        )


def _validar_campo(correcao: Correcao) -> None:
    """Correção de campo (hoje, só a espécie): campo conhecido, valor permitido, evidências."""
    if not correcao.campo:
        return
    if correcao.campo not in CAMPOS_CORRIGIVEIS:
        raise CorrecaoInvalida(
            f"Correção de {correcao.ticker} rejeitada: campo {correcao.campo!r} não corrigível"
        )
    if correcao.valor not in CAMPOS_CORRIGIVEIS[correcao.campo]:
        raise CorrecaoInvalida(
            f"Correção de {correcao.ticker} rejeitada: valor {correcao.valor!r} fora de "
            f"{CAMPOS_CORRIGIVEIS[correcao.campo]}"
        )
    arquivo = correcao.arquivo.lower()
    if not all(evidencia in arquivo for evidencia in _EVIDENCIAS_DA_ESPECIE):
        raise CorrecaoInvalida(
            f"Correção de espécie de {correcao.ticker} rejeitada: exige as duas evidências do "
            "mesmo documento, Composição do Capital e DRE"
        )


def ler_correcoes(caminho: Path = CAMINHO_PADRAO) -> list[Correcao]:
    """Lê a tabela (CSV com `;`, UTF-8) e a valida."""
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        faltando = [c for c in _CAMPOS if c not in (leitor.fieldnames or [])]
        if faltando:
            raise CorrecaoInvalida(f"Tabela de correções sem as colunas {faltando}")
        correcoes = [
            Correcao(
                **{
                    c: (linha.get(c) or "").strip()
                    for c in (*_CAMPOS, *_OPCIONAIS)
                    if c in _CAMPOS or c in (leitor.fieldnames or [])
                }
            )
            for linha in leitor
        ]
    validar_correcoes(correcoes)
    return correcoes
