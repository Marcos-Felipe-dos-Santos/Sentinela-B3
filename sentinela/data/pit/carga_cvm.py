"""Carga dos ZIPs abertos da CVM no banco único (F3-3b, PLANO §5).

`carregar(conn, arquivo, tipo=..., fonte=..., coleta=...)` lê um ZIP oficial e grava:

- DFP e ITR: o índice de entregas (`entregas`, com todas as versões que ele lista e a
  `DT_RECEB` de cada uma), as contas das demonstrações (`demonstracoes`, com a escala do
  documento validada por `units.Escala` e o valor como declarado, sem aplicar a escala) e a
  composição do capital (`composicao_capital`, quantidades como declaradas);
- FCA: o índice de entregas (`fca_entregas`) e as linhas de cada parte (`fca_linhas`);
- Informe mensal de FII: as linhas do geral, do complemento e do ativo/passivo
  (`fii_informe_linhas`), com a `Data_Entrega` do geral.

Regras:

- **Idempotência pelo hash:** um arquivo já carregado (mesmo SHA-256) não é lido de novo.
- **Só inserção:** linha cuja chave já existe não é regravada. Com os mesmos dados, conta
  como repetida; com dados diferentes, fica a gravada e o caso entra em `conflitos` (no
  resumo, até 100) e em `conflitos_carga` (todos, para o leitor; BUG-3-26, DD-57).
- **Informe de 2016 a 2020:** a coluna do fundo é `CNPJ_Fundo` (leiaute anterior à
  Resolução 175); a chave usa o CNPJ das duas, e `linha_do_informe` lê com os nomes atuais.
- **Vazio não é zero:** valor ou quantidade vazios são gravados como nulos.
- **Linha ilegível** (versão, escala, ordem do exercício ou número inválidos, chave vazia,
  colunas a mais ou a menos) é recusada com o motivo, sem derrubar a carga.
- **Marca do L1 (DD-34):** `entregas.valores_na_fonte` diz se o arquivo que registrou a
  entrega trazia os números daquela versão. É a observação da primeira carga e não muda
  depois (uma reapresentação posterior tira os números da versão antiga do arquivo novo, e
  isso não é conflito); quais versões têm números no banco se lê em `demonstracoes`.
  `cargas_arquivo.so_ultima_versao` é medido no arquivo: 1 quando cada documento do
  conteúdo tem uma versão só (e, com índice, a maior do índice).
- **Atomicidade:** a carga de um arquivo roda num `SAVEPOINT`; falha desfaz tudo o que ela
  gravou, também com `autocommit`. Sem transação aberta por quem chama, o fim da carga
  grava; dentro de uma transação de quem chama, a gravação fica com ela.

Documento do conteúdo sem linha no índice entra em `sem_entrega` no resumo; sem data de
entrega, a leitura por data (F3-3c) não o usa. O parecer dos auditores e arquivos fora do
leiaute ficam em `ignorados`. A cascata atual não lê estas tabelas.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import sqlite3
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from sentinela.data import proveniencia
from sentinela.domain.units import Escala

TIPOS = ("DFP", "ITR", "FCA", "FII_INFORME")
ORDENS = ("ÚLTIMO", "PENÚLTIMO")
PARTES_FII = ("geral", "complemento", "ativo_passivo")
LIMITE_REGISTROS = 100
# Informe de FII de 2016 a 2020: a CVM manteve o leiaute anterior à Resolução 175 (BUG-3-25).
LEIAUTE_ANTERIOR_175 = {
    "CNPJ_Fundo": "CNPJ_Fundo_Classe",
    "Nome_Fundo": "Nome_Fundo_Classe",
}
_A_MAIS = "__colunas_a_mais__"

_DEMONSTRACAO = r"(?P<dem>(?:BPA|BPP|DRE|DRA|DMPL|DFC_MD|DFC_MI|DVA)_(?:con|ind))"
_COMPOSICAO = {
    "acoes_ordinarias": "QT_ACAO_ORDIN_CAP_INTEGR",
    "acoes_preferenciais": "QT_ACAO_PREF_CAP_INTEGR",
    "acoes_total": "QT_ACAO_TOTAL_CAP_INTEGR",
    "tesouraria_ordinarias": "QT_ACAO_ORDIN_TESOURO",
    "tesouraria_preferenciais": "QT_ACAO_PREF_TESOURO",
    "tesouraria_total": "QT_ACAO_TOTAL_TESOURO",
}


class ArquivoInvalido(ValueError):
    """ZIP fora do leiaute oficial do tipo pedido (sem o índice ou sem o arquivo geral)."""


class LinhaRecusada(ValueError):
    """Linha ilegível: recusada com o motivo, sem derrubar a carga."""


@dataclass
class Resumo:
    """O que a carga de um arquivo fez."""

    hash_sha256: str
    tipo: str
    ja_carregado: bool = False
    relido: bool = False
    so_ultima_versao: bool | None = None
    inseridas: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    repetidas: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    total_conflitos: int = 0
    conflitos: list[dict] = field(default_factory=list)
    total_recusadas: int = 0
    recusadas: list[dict] = field(default_factory=list)
    sem_entrega: list[list[str]] = field(default_factory=list)
    ignorados: list[str] = field(default_factory=list)

    def para_dict(self) -> dict:
        return {
            "inseridas": dict(self.inseridas),
            "repetidas": dict(self.repetidas),
            "total_conflitos": self.total_conflitos,
            "conflitos": self.conflitos,
            "total_recusadas": self.total_recusadas,
            "recusadas": self.recusadas,
            "sem_entrega": self.sem_entrega,
            "ignorados": self.ignorados,
        }

    def _conflito(self, tabela: str, chave: dict, gravado: tuple, novo: tuple) -> None:
        self.total_conflitos += 1
        if len(self.conflitos) < LIMITE_REGISTROS:
            self.conflitos.append(
                {
                    "tabela": tabela,
                    "chave": chave,
                    "gravado": list(gravado),
                    "arquivo": list(novo),
                }
            )

    def _recusa(self, nome: str, linha: int, motivo: str) -> None:
        self.total_recusadas += 1
        if len(self.recusadas) < LIMITE_REGISTROS:
            self.recusadas.append({"arquivo": nome, "linha": linha, "motivo": motivo})


@dataclass(frozen=True)
class _Tabela:
    nome: str
    chave: tuple[str, ...]
    dados: tuple[str, ...]
    # Colunas gravadas mas fora da conferência de repetida ou conflito: observações do
    # arquivo, não dados do documento (a marca `valores_na_fonte`).
    sem_comparar: tuple[str, ...] = ()

    def gravar(
        self, conn, resumo: Resumo, chave: tuple, dados: tuple, prov: tuple
    ) -> None:
        """Insere a linha nova; chave existente: repetida (mesmos dados) ou conflito."""
        onde = " AND ".join(f"{c} = ?" for c in self.chave)
        gravado = conn.execute(
            f"SELECT {', '.join(self.dados)} FROM {self.nome} WHERE {onde}",
            chave,
        ).fetchone()
        if gravado is None:
            colunas = (*self.chave, *self.dados, "fonte", "coleta", "hash_sha256")
            conn.execute(
                f"INSERT INTO {self.nome} ({', '.join(colunas)}) "
                f"VALUES ({', '.join('?' * len(colunas))})",
                (*chave, *dados, *prov),
            )
            resumo.inseridas[self.nome] += 1
            return
        comparar = [
            i for i, coluna in enumerate(self.dados) if coluna not in self.sem_comparar
        ]
        antes = tuple(gravado[i] for i in comparar)
        agora = tuple(dados[i] for i in comparar)
        if antes == agora:
            resumo.repetidas[self.nome] += 1
            return
        campos = dict(zip(self.chave, chave))
        resumo._conflito(self.nome, campos, antes, agora)
        conn.execute(
            "INSERT OR IGNORE INTO conflitos_carga (tabela, cnpj, documento, dt_refer, versao, "
            "chave_json, gravado_json, arquivo_json, fonte, coleta, hash_sha256) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self.nome,
                campos["cnpj"],
                campos.get("documento", "FCA"),
                campos["dt_refer"],
                campos["versao"],
                json.dumps(campos, ensure_ascii=False, sort_keys=True),
                json.dumps(antes, ensure_ascii=False),
                json.dumps(agora, ensure_ascii=False),
                *prov,
            ),
        )


_ENTREGAS = _Tabela(
    "entregas",
    ("cnpj", "documento", "dt_refer", "versao"),
    (
        "cd_cvm",
        "denominacao",
        "categoria",
        "id_documento",
        "dt_receb",
        "valores_na_fonte",
    ),
    ("valores_na_fonte",),
)
_DEMONSTRACOES = _Tabela(
    "demonstracoes",
    (
        "cnpj", "documento", "dt_refer", "versao", "demonstracao", "ordem_exerc",
        "dt_ini_exerc", "dt_fim_exerc", "coluna_df", "conta",
    ),
    ("descricao", "valor", "escala", "moeda", "conta_fixa"),
)  # fmt: skip
_COMPOSICAO_CAPITAL = _Tabela(
    "composicao_capital",
    ("cnpj", "documento", "dt_refer", "versao"),
    tuple(_COMPOSICAO),
)
_FCA_ENTREGAS = _Tabela(
    "fca_entregas",
    ("cnpj", "dt_refer", "versao"),
    (
        "cd_cvm",
        "denominacao",
        "categoria",
        "id_documento",
        "dt_receb",
        "valores_na_fonte",
    ),
    ("valores_na_fonte",),
)
_FCA_LINHAS = _Tabela(
    "fca_linhas",
    ("cnpj", "dt_refer", "versao", "parte", "linha_sha256"),
    ("linha_json",),
)
_FII_LINHAS = _Tabela(
    "fii_informe_linhas",
    ("cnpj", "dt_refer", "versao", "parte", "linha_sha256"),
    ("data_entrega", "linha_json"),
)


def _linhas(zf: zipfile.ZipFile, nome: str):
    """(número da linha no arquivo, linha) do CSV oficial (latin-1, separador ';').

    O latin-1 só tem letras acentuadas compostas: `ÚLTIMO` não chega decomposto.
    """
    with zf.open(nome) as bruto:
        texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
        yield from enumerate(
            csv.DictReader(texto, delimiter=";", restkey=_A_MAIS), start=2
        )


def _texto(linha: dict, coluna: str, *, obrigatorio: bool = False) -> str:
    valor = (linha.get(coluna) or "").strip()
    if obrigatorio and not valor:
        raise LinhaRecusada(f"{coluna} vazio")
    return valor


def _versao(linha: dict, coluna: str) -> int:
    bruto = _texto(linha, coluna, obrigatorio=True)
    if not (bruto.isascii() and bruto.isdigit()):  # '²'.isdigit() é verdadeiro
        raise LinhaRecusada(f"versão ilegível: {bruto!r}")
    return int(bruto)


def _numero(linha: dict, coluna: str) -> float | None:
    """Número como declarado; vazio é nulo (nunca zero)."""
    bruto = _texto(linha, coluna)
    if not bruto:
        return None
    try:
        valor = float(bruto)
    except ValueError:
        raise LinhaRecusada(f"{coluna} não numérico: {bruto!r}") from None
    if not math.isfinite(valor):
        raise LinhaRecusada(f"{coluna} não finito: {bruto!r}")
    return valor


def _sem_colunas_a_mais(linha: dict) -> None:
    if _A_MAIS in linha or None in linha.values():
        raise LinhaRecusada("linha com número de colunas diferente do cabeçalho")


def _linha_json(linha: dict) -> tuple[str, str]:
    texto = json.dumps(linha, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest(), texto


def _unico(zf: zipfile.ZipFile, padrao: str) -> str:
    nomes = [n for n in zf.namelist() if re.fullmatch(padrao, n)]
    if len(nomes) != 1:
        raise ArquivoInvalido(
            f"esperado um arquivo {padrao!r}, encontrados {len(nomes)}"
        )
    return nomes[0]


def _so_ultima(conteudo: dict[tuple, set], indice: dict[tuple, set] | None) -> bool:
    for documento, versoes in conteudo.items():
        if len(versoes) != 1:
            return False
        if (
            indice is not None
            and documento in indice
            and versoes != {max(indice[documento])}
        ):
            return False
    return True


def _carregar_cia(conn, zf, tipo: str, prov: tuple, resumo: Resumo) -> bool:
    doc = tipo.lower()
    nome_indice = _unico(zf, rf"{doc}_cia_aberta_\d{{4}}\.csv")
    demonstracao = re.compile(rf"{doc}_cia_aberta_{_DEMONSTRACAO}_\d{{4}}\.csv")
    composicao = re.compile(rf"{doc}_cia_aberta_composicao_capital_\d{{4}}\.csv")
    conteudo: dict[tuple, set] = defaultdict(set)
    for nome in sorted(zf.namelist()):
        if casado := demonstracao.fullmatch(nome):
            for numero, linha in _linhas(zf, nome):
                try:
                    _sem_colunas_a_mais(linha)
                    chave, dados = _conta(linha, tipo, casado["dem"])
                except LinhaRecusada as motivo:
                    resumo._recusa(nome, numero, str(motivo))
                    continue
                _DEMONSTRACOES.gravar(conn, resumo, chave, dados, prov)
                conteudo[(chave[0], chave[2])].add(chave[3])
        elif composicao.fullmatch(nome):
            for numero, linha in _linhas(zf, nome):
                try:
                    _sem_colunas_a_mais(linha)
                    chave = (
                        _texto(linha, "CNPJ_CIA", obrigatorio=True),
                        tipo,
                        _texto(linha, "DT_REFER", obrigatorio=True),
                        _versao(linha, "VERSAO"),
                    )
                    dados = tuple(
                        _numero(linha, coluna) for coluna in _COMPOSICAO.values()
                    )
                except LinhaRecusada as motivo:
                    resumo._recusa(nome, numero, str(motivo))
                    continue
                _COMPOSICAO_CAPITAL.gravar(conn, resumo, chave, dados, prov)
                conteudo[(chave[0], chave[2])].add(chave[3])
        elif nome != nome_indice:
            resumo.ignorados.append(nome)
    indice = _carregar_indice(
        conn, zf, nome_indice, _ENTREGAS, (tipo,), conteudo, prov, resumo
    )
    return _so_ultima(conteudo, indice)


def _conta(linha: dict, tipo: str, demonstracao: str) -> tuple[tuple, tuple]:
    ordem = _texto(linha, "ORDEM_EXERC", obrigatorio=True)
    if ordem not in ORDENS:
        raise LinhaRecusada(f"ordem do exercício desconhecida: {ordem!r}")
    escala = _texto(linha, "ESCALA_MOEDA", obrigatorio=True).upper()
    if escala not in Escala.__members__:
        raise LinhaRecusada(f"escala desconhecida: {escala!r}")
    chave = (
        _texto(linha, "CNPJ_CIA", obrigatorio=True),
        tipo,
        _texto(linha, "DT_REFER", obrigatorio=True),
        _versao(linha, "VERSAO"),
        demonstracao,
        ordem,
        _texto(linha, "DT_INI_EXERC"),
        _texto(linha, "DT_FIM_EXERC", obrigatorio=True),
        _texto(linha, "COLUNA_DF"),
        _texto(linha, "CD_CONTA", obrigatorio=True),
    )
    dados = (
        _texto(linha, "DS_CONTA") or None,
        _numero(linha, "VL_CONTA"),
        Escala[escala].name,
        _texto(linha, "MOEDA") or None,
        _texto(linha, "ST_CONTA_FIXA") or None,
    )
    return chave, dados


def _carregar_indice(conn, zf, nome, tabela, prefixo, conteudo, prov, resumo):
    """Índice de entregas: todas as versões, com `valores_na_fonte` pelo conteúdo."""
    indice: dict[tuple, set] = defaultdict(set)
    for numero, linha in _linhas(zf, nome):
        try:
            _sem_colunas_a_mais(linha)
            cnpj = _texto(linha, "CNPJ_CIA", obrigatorio=True)
            dt_refer = _texto(linha, "DT_REFER", obrigatorio=True)
            versao = _versao(linha, "VERSAO")
            dados = (
                _texto(linha, "CD_CVM") or None,
                _texto(linha, "DENOM_CIA") or None,
                _texto(linha, "CATEG_DOC") or None,
                _texto(linha, "ID_DOC") or None,
                _texto(linha, "DT_RECEB", obrigatorio=True),
                int(versao in conteudo.get((cnpj, dt_refer), ())),
            )
        except LinhaRecusada as motivo:
            resumo._recusa(nome, numero, str(motivo))
            continue
        chave = (cnpj, *prefixo, dt_refer, versao)
        tabela.gravar(conn, resumo, chave, dados, prov)
        indice[(cnpj, dt_refer)].add(versao)
    for documento in sorted(set(conteudo) - set(indice)):
        if len(resumo.sem_entrega) < LIMITE_REGISTROS:
            resumo.sem_entrega.append(list(documento))
    return indice


def _carregar_fca(conn, zf, prov: tuple, resumo: Resumo) -> bool:
    nome_indice = _unico(zf, r"fca_cia_aberta_\d{4}\.csv")
    parte = re.compile(r"fca_cia_aberta_(?P<parte>[a-z_]+)_\d{4}\.csv")
    conteudo: dict[tuple, set] = defaultdict(set)
    for nome in sorted(zf.namelist()):
        casado = parte.fullmatch(nome)
        if not casado:
            if nome != nome_indice:
                resumo.ignorados.append(nome)
            continue
        for numero, linha in _linhas(zf, nome):
            try:
                _sem_colunas_a_mais(linha)
                cnpj = _texto(linha, "CNPJ_Companhia", obrigatorio=True)
                dt_refer = _texto(linha, "Data_Referencia", obrigatorio=True)
                versao = _texto(linha, "Versao", obrigatorio=True)
            except LinhaRecusada as motivo:
                resumo._recusa(nome, numero, str(motivo))
                continue
            hash_linha, texto = _linha_json(linha)
            chave = (cnpj, dt_refer, versao, casado["parte"], hash_linha)
            _FCA_LINHAS.gravar(conn, resumo, chave, (texto,), prov)
            if versao.isascii() and versao.isdigit():
                conteudo[(cnpj, dt_refer)].add(int(versao))
    indice = _carregar_indice(
        conn, zf, nome_indice, _FCA_ENTREGAS, (), conteudo, prov, resumo
    )
    return _so_ultima(conteudo, indice)


def linha_do_informe(texto: str) -> dict:
    """Linha guardada do Informe com os nomes de coluna do leiaute atual (Resolução 175).

    A linha fica guardada como o arquivo a traz (DD-43); a leitura troca `CNPJ_Fundo` e
    `Nome_Fundo`, do leiaute de 2016 a 2020, pelos nomes atuais.
    """
    linha = json.loads(texto)
    return {LEIAUTE_ANTERIOR_175.get(coluna, coluna): v for coluna, v in linha.items()}


def _cnpj_do_fundo(linha: dict) -> str:
    """CNPJ do fundo no leiaute atual ou no anterior; os dois juntos na mesma linha recusam."""
    if "CNPJ_Fundo_Classe" in linha and "CNPJ_Fundo" in linha:
        raise LinhaRecusada("CNPJ_Fundo e CNPJ_Fundo_Classe na mesma linha")
    coluna = "CNPJ_Fundo" if "CNPJ_Fundo" in linha else "CNPJ_Fundo_Classe"
    return _texto(linha, coluna, obrigatorio=True)


def _carregar_fii(conn, zf, prov: tuple, resumo: Resumo) -> bool:
    _unico(zf, r"inf_mensal_fii_geral_\d{4}\.csv")
    parte = re.compile(
        rf"inf_mensal_fii_(?P<parte>{'|'.join(PARTES_FII)})_\d{{4}}\.csv"
    )
    geral: dict[tuple, set] = defaultdict(set)
    for nome in sorted(zf.namelist()):
        casado = parte.fullmatch(nome)
        if not casado:
            resumo.ignorados.append(nome)
            continue
        for numero, linha in _linhas(zf, nome):
            try:
                _sem_colunas_a_mais(linha)
                chave_doc = (
                    _cnpj_do_fundo(linha),
                    _texto(linha, "Data_Referencia", obrigatorio=True),
                )
            except LinhaRecusada as motivo:
                resumo._recusa(nome, numero, str(motivo))
                continue
            versao = _texto(linha, "Versao")
            entrega = (
                _texto(linha, "Data_Entrega") if casado["parte"] == "geral" else ""
            )
            hash_linha, texto = _linha_json(linha)
            chave = (*chave_doc, versao, casado["parte"], hash_linha)
            _FII_LINHAS.gravar(conn, resumo, chave, (entrega, texto), prov)
            if casado["parte"] == "geral":
                geral[chave_doc].add(versao)
    return _so_ultima(geral, None)


def carregar(
    conn: sqlite3.Connection,
    arquivo: Path | str,
    *,
    tipo: str,
    fonte: str,
    coleta: str,
    reler: bool = False,
) -> Resumo:
    """Carrega o ZIP oficial no banco (migrações 004, 005 e 010 aplicadas), num `SAVEPOINT`.

    `fonte` é a URL de origem e `coleta` o instante do download (ISO 8601), gravados em cada
    linha com o hash do arquivo. Arquivo já carregado devolve `ja_carregado`, sem ler o ZIP;
    com `reler`, é lido de novo pelas mesmas regras (o que faltava é inserido, o gravado conta
    como repetido ou conflito) e o registro em `cargas_arquivo` fica como estava (`relido`).
    """
    if tipo not in TIPOS:
        raise ValueError(f"tipo desconhecido: {tipo!r}")
    if not fonte or not coleta:
        raise ValueError("fonte e coleta são obrigatórias")
    arquivo = Path(arquivo)
    resumo = Resumo(proveniencia.hash_sha256(arquivo), tipo)
    if conn.execute(
        "SELECT 1 FROM cargas_arquivo WHERE hash_sha256 = ?", (resumo.hash_sha256,)
    ).fetchone():
        if not reler:
            resumo.ja_carregado = True
            return resumo
        resumo.relido = True
    conn.execute("SAVEPOINT carga_cvm")
    try:
        _carregar_arquivo(conn, arquivo, tipo, fonte, coleta, resumo)
    except BaseException:
        if conn.in_transaction:  # o SQLite pode já ter desfeito tudo (disco cheio, E/S)
            conn.execute("ROLLBACK TO carga_cvm")
            conn.execute("RELEASE carga_cvm")
        raise
    conn.execute("RELEASE carga_cvm")
    return resumo


def _carregar_arquivo(
    conn, arquivo: Path, tipo: str, fonte: str, coleta: str, resumo: Resumo
):
    prov = (fonte, coleta, resumo.hash_sha256)
    with zipfile.ZipFile(arquivo) as zf:
        if tipo in ("DFP", "ITR"):
            so_ultima = _carregar_cia(conn, zf, tipo, prov, resumo)
        elif tipo == "FCA":
            so_ultima = _carregar_fca(conn, zf, prov, resumo)
        else:
            so_ultima = _carregar_fii(conn, zf, prov, resumo)
        resumo.so_ultima_versao = so_ultima
        if resumo.relido:
            return
        conn.execute(
            "INSERT INTO cargas_arquivo (hash_sha256, tipo, arquivo, fonte, coleta, "
            "so_ultima_versao, resumo_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                resumo.hash_sha256,
                tipo,
                arquivo.name,
                fonte,
                coleta,
                int(so_ultima),
                json.dumps(resumo.para_dict(), ensure_ascii=False),
            ),
        )
