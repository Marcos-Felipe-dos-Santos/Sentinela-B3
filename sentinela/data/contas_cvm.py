"""Contas da CVM lidas pelo par (código, descrição) (F2A-33; ADR-0003, D20).

Nenhuma conta é lida só pelo código. A tabela versionada `referencia/contas_cvm.csv` diz,
por modelo de demonstração (empresa não financeira, banco, seguradora), quais pares
representam cada campo, com a evidência (arquivo, ano e uma empresa em que o par aparece).
Par sem correspondência vira abstenção com motivo, nunca o valor de outra conta.

Linha ausente e valor inválido são motivos diferentes: só a primeira pode autorizar uma
reserva (D20); a segunda faz o campo se abster.

Funções puras: sem rede, sem relógio, sem `config`.
"""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

TABELA = Path(__file__).parent / "referencia" / "contas_cvm.csv"
MODELOS = ("empresa", "banco", "seguradora")
SETORES_BANCO = frozenset({"bancos"})
MOTIVO_LINHA_AUSENTE = "linha ausente no documento"
MOTIVO_SEM_CORRESPONDENCIA = "par (código, descrição) sem correspondência na tabela"
MOTIVO_VALOR_INVALIDO = "valor inválido na linha (não numérico, NaN ou infinito)"
MOTIVO_CAMPO_FORA_DO_MODELO = "campo sem conta na tabela para o modelo"


def normalizar_descricao(texto: object) -> str:
    """Sem acento, em minúsculas e com um só espaço entre palavras."""
    decomposto = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def modelo_do_setor(setor: str | None) -> str:
    """Modelo de demonstração pelo setor do FCA (F2A-2).

    "Bancos" → banco; "Seguradoras e Corretoras", com ou sem "Emp. Adm. Part. -" →
    seguradora; o resto, inclusive setor desconhecido, → empresa. Uma companhia cujo
    documento segue outro modelo cai em abstenção pela descrição, nunca em outra conta.
    """
    normalizado = normalizar_descricao(setor)
    if normalizado in SETORES_BANCO:
        return "banco"
    if "seguradoras" in normalizado:
        return "seguradora"
    return "empresa"


@dataclass(frozen=True)
class Conta:
    modelo: str
    campo: str
    codigo: str
    descricao: str
    arquivo: str
    ano: int
    empresa: str


@dataclass(frozen=True)
class Leitura:
    valor: float
    codigo: str
    descricao: str


@dataclass(frozen=True)
class Abstencao:
    motivo: str
    detalhe: str = ""


def ler_tabela(caminho: Path = TABELA) -> tuple[Conta, ...]:
    """Lê a tabela; descrição fora da forma normalizada ou modelo desconhecido é erro."""
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    contas = []
    for linha in linhas:
        conta = Conta(
            modelo=linha["modelo"],
            campo=linha["campo"],
            codigo=linha["codigo"],
            descricao=linha["descricao"],
            arquivo=linha["arquivo"],
            ano=int(linha["ano"]),
            empresa=linha["empresa"],
        )
        if conta.modelo not in MODELOS:
            raise ValueError(f"modelo desconhecido na tabela: {conta.modelo!r}")
        if conta.descricao != normalizar_descricao(conta.descricao):
            raise ValueError(
                f"descrição não normalizada na tabela: {conta.descricao!r}"
            )
        contas.append(conta)
    pares = [(c.modelo, c.codigo, c.descricao) for c in contas]
    if len(set(pares)) != len(pares):
        raise ValueError("par repetido na tabela")
    return tuple(contas)


def _numero(valor: object) -> float | None:
    try:
        numero = float(str(valor).strip()) if isinstance(valor, str) else float(valor)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def ler_conta(
    linhas: list[dict],
    campo: str,
    modelo: str,
    tabela: tuple[Conta, ...],
) -> Leitura | Abstencao:
    """Valor do campo nas linhas do documento (`CD_CONTA`, `DS_CONTA`, `VL_CONTA`).

    Os códigos do campo no modelo são tentados na ordem da tabela. Código presente com a
    descrição da tabela: o valor, se for número finito, senão abstenção por valor inválido.
    Código presente só com outra descrição: abstenção sem correspondência. Nenhum código
    presente: abstenção por linha ausente.
    """
    if modelo not in MODELOS:
        raise ValueError(f"modelo desconhecido: {modelo!r}")
    candidatas = [c for c in tabela if c.modelo == modelo and c.campo == campo]
    if not candidatas:
        return Abstencao(MOTIVO_CAMPO_FORA_DO_MODELO, f"{campo} em {modelo}")
    por_codigo: dict[str, list[dict]] = {}
    for linha in linhas:
        por_codigo.setdefault(str(linha.get("CD_CONTA")), []).append(linha)
    divergentes = []
    for conta in candidatas:
        for linha in por_codigo.get(conta.codigo, []):
            descricao = normalizar_descricao(linha.get("DS_CONTA"))
            if descricao != conta.descricao:
                divergentes.append(f"{conta.codigo} {descricao!r}")
                continue
            valor = _numero(linha.get("VL_CONTA"))
            if valor is None:
                return Abstencao(MOTIVO_VALOR_INVALIDO, f"{conta.codigo} {descricao!r}")
            return Leitura(valor, conta.codigo, descricao)
    if divergentes:
        return Abstencao(MOTIVO_SEM_CORRESPONDENCIA, "; ".join(divergentes))
    codigos = ", ".join(c.codigo for c in candidatas)
    return Abstencao(MOTIVO_LINHA_AUSENTE, f"{campo}: {codigos}")
