"""Leitura ponto-no-tempo das demonstrações da CVM e do Informe de FII (F3-3c, D17, F3-P12).

Lê o banco único carregado pelo F3-3b (`carga_cvm`) numa data D, em dois modos que nunca se
misturam (`Leitura.modo`; `modo_unico` recusa leituras de modos diferentes):

- **estrito**: um documento vale em D pela versão vigente em D, a maior entregue antes do
  dia local de D (a data de entrega não tem hora: o dia de D só vale depois de acabar, como
  no `_entregue` do FII e no contrato F3-P12). Vale só se os números dessa versão estão no
  banco; senão o documento fica fora, com o motivo: versão posterior entregue depois de D
  (a fonte aberta só guarda a última, DD-34) ou números não carregados. Nada é inventado.
- **exploratório**: o documento entregue antes de D vale pela maior versão com números no
  banco, mesmo entregue depois de D; a leitura leva o rótulo e o aviso "possível
  reapresentação posterior não observável".

Os formatos são os da cascata atual, para que, com D = hoje, os insumos sejam os mesmos:
`demonstrativo` como `CVMProvider.parsear_demonstrativo` (ÚLTIMO, valor com a escala aplicada,
CD_CVM, versão e período), `composicao` como o CSV da composição do capital, `entregas` como o
índice do ZIP e `informe_fii` como `CVMFIIProvider._linhas_do_fundo` (complemento com a entrega
e o ISIN do geral de mesma referência e versão, e o ativo/passivo). Este módulo não altera a
cascata nem o serviço: o consumidor de produção é o F3-3d.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from sentinela.data.pit.carga_cvm import linha_do_informe
from sentinela.domain.units import Escala

ESTRITO = "estrito"
EXPLORATORIO = "exploratorio"
MODOS = (ESTRITO, EXPLORATORIO)
AVISO_EXPLORATORIO = "possível reapresentação posterior não observável"
MOTIVO_ENTREGA_POSTERIOR = (
    "versão vigente em D não disponível na fonte aberta (última entrega posterior)"
)
MOTIVO_SEM_NUMEROS = "números da versão vigente em D não carregados"
MOTIVO_ENTREGA_ILEGIVEL = "versão posterior com data de entrega ilegível"
MOTIVO_VERSAO_NAO_VISTA = (
    "versão intermediária não observada: a vigente em D não é demonstrável"
)
MOTIVO_CONFLITO_NA_FONTE = (
    "a fonte traz a mesma linha do documento com valores diferentes (conflito na carga)"
)
MOTIVO_SEM_GERAL = "complemento sem documento geral de mesma referência e versão"
MOTIVO_GERAL_EM_CONFLITO = "documento geral com entregas diferentes na mesma versão"
MOTIVO_INFORME_INDISPONIVEL = "Informe aberto indisponível para a data"
INICIO_INFORME = date(2016, 1, 1)
_FUSO = ZoneInfo("America/Sao_Paulo")
_COMPOSICAO = {
    "QT_ACAO_ORDIN_CAP_INTEGR": "acoes_ordinarias",
    "QT_ACAO_PREF_CAP_INTEGR": "acoes_preferenciais",
    "QT_ACAO_TOTAL_CAP_INTEGR": "acoes_total",
    "QT_ACAO_ORDIN_TESOURO": "tesouraria_ordinarias",
    "QT_ACAO_PREF_TESOURO": "tesouraria_preferenciais",
    "QT_ACAO_TOTAL_TESOURO": "tesouraria_total",
}


class ModosMisturados(ValueError):
    """Leituras do modo estrito e do exploratório na mesma série ou resultado."""


@dataclass(frozen=True)
class Leitura:
    """O que vale em D num modo, com os motivos dos documentos que ficaram fora."""

    modo: str
    dia: date
    dados: object
    motivos: dict = field(default_factory=dict)
    avisos: tuple[str, ...] = ()
    proveniencia: tuple[tuple[str, str, str], ...] = ()


def modo_unico(leituras: Iterable[Leitura]) -> str:
    """O modo comum das leituras que vão compor uma série ou um resultado; misturar recusa."""
    modos = {leitura.modo for leitura in leituras}
    if len(modos) != 1:
        raise ModosMisturados(f"leituras de modos diferentes: {sorted(modos)}")
    return modos.pop()


def _dia(as_of: datetime, modo: str) -> date:
    if modo not in MODOS:
        raise ValueError(f"modo desconhecido: {modo!r}")
    if as_of.utcoffset() is None:
        raise ValueError("as_of exige fuso horário")
    return as_of.astimezone(_FUSO).date()


def _data(texto: object) -> date | None:
    try:
        return date.fromisoformat(str(texto)[:10])
    except ValueError:
        return None


def _antes(texto: object, dia: date) -> bool:
    """Entrega demonstrada e anterior ao dia de D."""
    entrega = _data(texto)
    return entrega is not None and entrega < dia


def _mes_encerrado(dt_refer: str, dia: date) -> bool:
    """Mês de referência do Informe (`AAAA-MM-01`) terminado antes do dia de D."""
    inicio = _data(dt_refer)
    if inicio is None:
        return False
    seguinte = date(inicio.year + inicio.month // 12, inicio.month % 12 + 1, 1)
    return seguinte <= dia


def _avisos(modo: str) -> tuple[str, ...]:
    return (AVISO_EXPLORATORIO,) if modo == EXPLORATORIO else ()


def _escolher(versoes: dict[tuple, list[tuple[int, str]]], com_numeros: set, dia, modo):
    """Versão de cada documento (cnpj, dt_refer) em D, e os motivos dos que ficam fora."""
    escolhidos, motivos = {}, {}
    for documento, entregas in sorted(versoes.items()):
        entregues = [v for v, receb in entregas if _antes(receb, dia)]
        if not entregues:
            continue  # o documento ainda não existia em D
        if modo == ESTRITO:
            vigente = max(entregues)
            posteriores = sorted(v for v, _ in entregas if v > vigente)
            if any(_data(receb) is None for v, receb in entregas if v > vigente):
                motivos[documento] = MOTIVO_ENTREGA_ILEGIVEL
            elif posteriores and posteriores[0] != vigente + 1:
                # a CVM numera em sequência: a versão que falta pode ter sido entregue
                # antes de D, e então a vigente não seria esta
                motivos[documento] = MOTIVO_VERSAO_NAO_VISTA
            elif (*documento, vigente) in com_numeros:
                escolhidos[documento] = vigente
            elif any(v > vigente for v, _ in entregas):
                motivos[documento] = MOTIVO_ENTREGA_POSTERIOR
            else:
                motivos[documento] = MOTIVO_SEM_NUMEROS
        else:
            disponiveis = [v for v, _ in entregas if (*documento, v) in com_numeros]
            if disponiveis:
                escolhidos[documento] = max(disponiveis)
            else:
                motivos[documento] = MOTIVO_SEM_NUMEROS
    return escolhidos, motivos


def _filtro_cnpj(cnpj: str | None) -> tuple[str, tuple]:
    return ("", ()) if cnpj is None else (" AND cnpj = ?", (cnpj,))


def _entregas_cia(conn, documento: str, cnpj: str | None) -> list[tuple]:
    filtro, parametros = _filtro_cnpj(cnpj)
    return conn.execute(
        "SELECT cnpj, dt_refer, versao, dt_receb, cd_cvm, denominacao, categoria, "
        "id_documento, fonte, coleta, hash_sha256 FROM entregas WHERE documento = ?"
        + filtro
        + " ORDER BY cnpj, dt_refer, versao",
        (documento, *parametros),
    ).fetchall()


def _versoes(linhas: list[tuple]) -> dict[tuple, list[tuple[int, str]]]:
    versoes: dict[tuple, list[tuple[int, str]]] = defaultdict(list)
    for cnpj, dt_refer, versao, dt_receb, *_ in linhas:
        versoes[(cnpj, dt_refer)].append((versao, dt_receb))
    return versoes


def _escolha_cia(conn, tabela: str, documento: str, cnpj, dia, modo, extra=("", ())):
    """Entregas, versão escolhida por documento e motivos, pelos números de `tabela`."""
    filtro, parametros = _filtro_cnpj(cnpj)
    entregas = _entregas_cia(conn, documento, cnpj)
    com_numeros = set(
        conn.execute(
            f"SELECT DISTINCT cnpj, dt_refer, versao FROM {tabela} WHERE documento = ?"
            + extra[0]
            + filtro,
            (documento, *extra[1], *parametros),
        ).fetchall()
    )
    escolhidos, motivos = _escolher(_versoes(entregas), com_numeros, dia, modo)
    _sem_conflito(conn, documento, cnpj, escolhidos, motivos)
    return entregas, escolhidos, motivos


def _sem_conflito(conn, documento: str, cnpj, escolhidos: dict, motivos: dict) -> None:
    """Tira o documento com conflito da carga (DD-57), nos dois modos, com o motivo.

    Conta o conflito no índice de entregas em qualquer versão (a data de entrega em dúvida
    pode mudar a versão vigente) e o das contas e da composição na versão escolhida.
    """
    filtro, parametros = _filtro_cnpj(cnpj)
    for c, dt_refer, tabela, versao in conn.execute(
        "SELECT DISTINCT cnpj, dt_refer, tabela, versao FROM conflitos_carga "
        "WHERE documento = ?" + filtro,
        (documento, *parametros),
    ):
        chave = (c, dt_refer)
        if chave not in escolhidos and chave not in motivos:
            continue  # o documento ainda não existia em D
        if tabela == "entregas" or escolhidos.get(chave) == versao:
            escolhidos.pop(chave, None)
            motivos[chave] = MOTIVO_CONFLITO_NA_FONTE


def _ordem_da_conta(conta: str) -> tuple:
    """Conta pelos segmentos numéricos, como a CVM ordena (`3.2` antes de `3.10`)."""
    return tuple(
        (0, int(p), "") if p.isdigit() else (1, 0, p) for p in conta.split(".")
    )


def _codigo_cvm(texto: str | None):
    return int(texto) if texto and texto.strip().isdigit() else pd.NA


def demonstrativo(
    conn: sqlite3.Connection,
    documento: str,
    demonstracao: str,
    as_of: datetime,
    *,
    modo: str = ESTRITO,
    cnpj: str | None = None,
    aplicar_escala: bool = True,
) -> Leitura:
    """Contas da demonstração (`DRE_con`, `BPA_con`...) em D, no formato da cascata.

    Colunas de `parsear_demonstrativo` com CD_CVM, versão e período: só `ÚLTIMO`, o valor
    vezes o fator da escala do documento (`aplicar_escala=False` devolve o valor declarado,
    como a cascata lê o LPA das contas 3.99); `DT_INI_EXERC` só nas demonstrações que o
    têm. A ordem é a dos arquivos da CVM: documento, conta pelos segmentos numéricos, período
    (início e fim) e coluna da DMPL; a ordem das colunas da DMPL no arquivo não é guardada.
    """
    dia = _dia(as_of, modo)
    entregas, escolhidos, motivos = _escolha_cia(
        conn,
        "demonstracoes",
        documento,
        cnpj,
        dia,
        modo,
        (" AND demonstracao = ? AND ordem_exerc = 'ÚLTIMO'", (demonstracao,)),
    )
    codigos = {(c, d, v): cd for c, d, v, _, cd, *_ in entregas}
    filtro, parametros = _filtro_cnpj(cnpj)
    linhas, proveniencia = [], set()
    for (
        c, dt_refer, versao, conta, descricao, valor, escala, inicio, fim, coluna, fonte, coleta,
        hash_,
    ) in conn.execute(
        "SELECT cnpj, dt_refer, versao, conta, descricao, valor, escala, dt_ini_exerc, "
        "dt_fim_exerc, coluna_df, fonte, coleta, hash_sha256 FROM demonstracoes "
        "WHERE documento = ? "
        "AND demonstracao = ? AND ordem_exerc = 'ÚLTIMO'"
        + filtro
        + " ORDER BY cnpj, dt_refer, versao, dt_ini_exerc, dt_fim_exerc, coluna_df, conta",
        (documento, demonstracao, *parametros),
    ):  # fmt: skip
        if escolhidos.get((c, dt_refer)) != versao:
            continue
        linhas.append(
            {
                "CNPJ_CIA": c,
                "DT_REFER": dt_refer,
                "CD_CONTA": conta,
                "DS_CONTA": descricao,
                "VL_CONTA": float("nan")
                if valor is None
                else valor * (Escala[escala].fator if aplicar_escala else 1),
                "CD_CVM": _codigo_cvm(codigos.get((c, dt_refer, versao))),
                "VERSAO": str(versao),
                "DT_INI_EXERC": inicio,
                "DT_FIM_EXERC": fim,
                "_ordem": (c, dt_refer, _ordem_da_conta(conta), inicio, fim, coluna),
            }
        )
        proveniencia.add((fonte, coleta, hash_))
    colunas = [
        "CNPJ_CIA",
        "DT_REFER",
        "CD_CONTA",
        "DS_CONTA",
        "VL_CONTA",
        "CD_CVM",
        "VERSAO",
    ]
    colunas += ["DT_INI_EXERC", "DT_FIM_EXERC"]
    linhas.sort(key=lambda linha: linha.pop("_ordem"))
    frame = pd.DataFrame(linhas, columns=colunas)
    frame["CD_CVM"] = frame["CD_CVM"].astype("Int64")
    if demonstracao.startswith(("BPA", "BPP")):  # balanços: o CSV não tem a coluna
        frame = frame.drop(columns=["DT_INI_EXERC"])
    return Leitura(
        modo, dia, frame, motivos, _avisos(modo), tuple(sorted(proveniencia))
    )


def composicao(
    conn: sqlite3.Connection,
    documento: str,
    as_of: datetime,
    *,
    modo: str = ESTRITO,
    cnpj: str | None = None,
) -> Leitura:
    """Composição do capital em D, com as colunas do CSV da CVM e as quantidades declaradas."""
    dia = _dia(as_of, modo)
    entregas, escolhidos, motivos = _escolha_cia(
        conn, "composicao_capital", documento, cnpj, dia, modo
    )
    nomes = {(c, d, v): nome for c, d, v, _, _, nome, *_ in entregas}
    filtro, parametros = _filtro_cnpj(cnpj)
    linhas, proveniencia = [], set()
    for registro in conn.execute(
        "SELECT cnpj, dt_refer, versao, "
        + ", ".join(_COMPOSICAO.values())
        + ", fonte, coleta, hash_sha256 FROM composicao_capital WHERE documento = ?"
        + filtro
        + " ORDER BY cnpj, dt_refer, versao",
        (documento, *parametros),
    ):
        c, dt_refer, versao, *quantidades, fonte, coleta, hash_ = registro
        if escolhidos.get((c, dt_refer)) != versao:
            continue
        linha = {
            "CNPJ_CIA": c,
            "DT_REFER": dt_refer,
            "VERSAO": str(versao),
            "DENOM_CIA": nomes.get((c, dt_refer, versao)),
        }
        linha.update(zip(_COMPOSICAO, quantidades))
        linhas.append(linha)
        proveniencia.add((fonte, coleta, hash_))
    frame = pd.DataFrame(
        linhas, columns=["CNPJ_CIA", "DT_REFER", "VERSAO", "DENOM_CIA", *_COMPOSICAO]
    )
    return Leitura(
        modo, dia, frame, motivos, _avisos(modo), tuple(sorted(proveniencia))
    )


def entregas(
    conn: sqlite3.Connection,
    documento: str,
    as_of: datetime,
    *,
    modo: str = ESTRITO,
    cnpj: str | None = None,
) -> Leitura:
    """Linhas do índice de entregas visíveis em D, no formato do índice do ZIP.

    Estrito: só as entregas anteriores ao dia de D. Exploratório: todas as versões dos
    documentos entregues antes de D, inclusive as posteriores.
    """
    dia = _dia(as_of, modo)
    linhas_banco = _entregas_cia(conn, documento, cnpj)
    existentes = {(c, d) for c, d, _, receb, *_ in linhas_banco if _antes(receb, dia)}
    linhas, proveniencia = [], set()
    for (
        c,
        d,
        versao,
        receb,
        cd_cvm,
        nome,
        categoria,
        id_doc,
        fonte,
        coleta,
        hash_,
    ) in linhas_banco:
        visivel = _antes(receb, dia) if modo == ESTRITO else (c, d) in existentes
        if not visivel:
            continue
        linhas.append(
            {
                "CNPJ_CIA": c,
                "DT_REFER": d,
                "VERSAO": str(versao),
                "DENOM_CIA": nome,
                "CD_CVM": cd_cvm,
                "CATEG_DOC": categoria,
                "ID_DOC": id_doc,
                "DT_RECEB": receb,
            }
        )
        proveniencia.add((fonte, coleta, hash_))
    return Leitura(modo, dia, linhas, {}, _avisos(modo), tuple(sorted(proveniencia)))


def _inteiro(versao: str) -> int | None:
    return int(versao) if versao.isascii() and versao.isdigit() else None


def _versoes_do_informe(versoes: dict[str, set], dia: date, modo: str):
    """(motivo ou None, {versão: (entrega, ISIN)}) de uma referência do Informe em D.

    Estrito: as versões cujo geral foi entregue antes de D (conflito entre essas entregas
    abstém a referência); sem nenhuma, reapresentação guardada (versão > 1) dá o motivo da
    entrega posterior; versão intermediária faltando entre a maior entregue e a próxima
    guardada abstém. Exploratório: todas as versões, se a referência tem versão entregue
    antes de D ou é reapresentação; conflito em qualquer versão abstém a referência.
    """
    vistas = {}
    for versao, valores in versoes.items():
        if modo == ESTRITO:
            valores = {v for v in valores if _antes(v[0], dia)}
        if len(valores) > 1:
            return MOTIVO_GERAL_EM_CONFLITO, {}
        if valores:
            vistas[versao] = next(iter(valores))
    legiveis = {v: _inteiro(v) for v in versoes if _inteiro(v) is not None}
    if modo == EXPLORATORIO:
        existia = any(_antes(e, dia) for e, _ in vistas.values()) or any(
            n > 1 for n in legiveis.values()
        )
        return None, vistas if existia else {}
    if any(
        _data(e) is None
        for v, valores in versoes.items()
        if v not in vistas
        for e, _ in valores
    ):
        return MOTIVO_ENTREGA_ILEGIVEL, {}
    if not vistas:
        if any(n > 1 for n in legiveis.values()):
            return MOTIVO_ENTREGA_POSTERIOR, {}
        return None, {}
    vigente = max((legiveis[v] for v in vistas if v in legiveis), default=0)
    posteriores = sorted(
        n for v, n in legiveis.items() if v not in vistas and n > vigente
    )
    if vigente and posteriores and posteriores[0] != vigente + 1:
        return MOTIVO_VERSAO_NAO_VISTA, {}
    return None, vistas


def informe_fii(
    conn: sqlite3.Connection, cnpj: str, as_of: datetime, *, modo: str = ESTRITO
) -> Leitura:
    """Linhas do Informe do fundo em D: `{"registros": complemento, "composicoes": ativo}`.

    Cada linha do complemento recebe a `Data_Entrega` e o `Codigo_ISIN` do geral de mesma
    referência e versão (regra 3 da F2C-47). Só referências com o mês encerrado antes de D;
    a regra das versões de cada uma está em `_versoes_do_informe`. A escolha entre as versões
    passadas e as guardas de versão ilegível e de conflito do complemento continuam com
    `rendimento_fii` (as mesmas da cascata). Linha sem geral de mesma referência e versão
    fica fora, com motivo.
    """
    dia = _dia(as_of, modo)
    geral: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    partes: dict[str, list] = defaultdict(list)
    for dt_refer, versao, parte, entrega, texto, fonte, coleta, hash_ in conn.execute(
        "SELECT dt_refer, versao, parte, data_entrega, linha_json, fonte, coleta, hash_sha256 "
        "FROM fii_informe_linhas WHERE cnpj = ? ORDER BY dt_refer, versao, parte, linha_sha256",
        (cnpj,),
    ):
        linha = linha_do_informe(texto)
        partes[parte].append((dt_refer, versao, linha, (fonte, coleta, hash_)))
        if parte == "geral":
            geral[dt_refer][versao].add((entrega, linha.get("Codigo_ISIN")))
    motivos: dict = {}
    if dia < INICIO_INFORME:
        motivos[(cnpj, "")] = MOTIVO_INFORME_INDISPONIVEL
    usadas: dict[tuple, tuple] = {}  # (referência, versão) → (entrega, ISIN) do geral
    for dt_refer, versoes in sorted(geral.items()):
        if not _mes_encerrado(dt_refer, dia):
            continue  # referência que ainda não existia em D: nem dados, nem motivo
        motivo, escolhidas = _versoes_do_informe(versoes, dia, modo)
        if motivo:
            motivos[(cnpj, dt_refer)] = motivo
        for versao, valor in escolhidas.items():
            usadas[(dt_refer, versao)] = valor
    for parte in ("complemento", "ativo_passivo"):
        for dt_refer, versao, _, _ in partes[parte]:
            if _mes_encerrado(dt_refer, dia) and versao not in geral.get(dt_refer, {}):
                # versão sem geral: entrega desconhecida; a referência inteira fica fora
                motivos[(cnpj, dt_refer)] = MOTIVO_SEM_GERAL
    registros, composicoes, proveniencia = [], [], set()
    for parte, destino in (("complemento", registros), ("ativo_passivo", composicoes)):
        for dt_refer, versao, linha, prov in partes[parte]:
            if (cnpj, dt_refer) in motivos:
                continue
            if (dt_refer, versao) in usadas:
                if parte == "complemento":
                    entrega, isin = usadas[(dt_refer, versao)]
                    linha = {**linha, "Data_Entrega": entrega, "Codigo_ISIN": isin}
                destino.append(linha)
                proveniencia.add(prov)
    return Leitura(
        modo,
        dia,
        {"registros": registros, "composicoes": composicoes},
        motivos,
        _avisos(modo),
        tuple(sorted(proveniencia)),
    )
