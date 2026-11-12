"""Universo ponto-no-tempo com as deslistadas (F3-5, pacote §2.2).

Tudo é lido só com o que existia antes de D (o dia local, `date`):

- **Universo em D** (`universo_em`): o índice de referência (D32) pela mesma montagem do
  índice atual (`indice_em`), com o FCA, o Informe mensal e as cotações anteriores a D, e o
  primeiro e o último pregão de cada ticker antes de D. Ação ou unit negociada sem código no
  FCA (o FCA antigo muitas vezes não traz o código, como a ALL em 2015) vai, com o motivo, para
  `sem_identificacao`.
- **Tickers** (`tickers_em`): códigos com negócio à vista nos 63 pregões antes de D, com a classe
  pelo ISIN (posições 7 a 9: `ACN` ação, `UNT` unit, `CTF` cota de fundo, FII só com o ISIN no
  Informe entregue antes de D); as deslistadas depois de D entram, as que pararam antes da
  janela não.
- **Companhias** (`companhias_em`): FCA entregue antes de D, com CNPJ e datas de negociação.
- **Universo do backtest** (`universo_backtest`): o universo em D filtrado pela liquidez da
  própria data, pelas regras da 2B (`liquidez.avaliar`), com os limiares por parâmetro.

A tabela `universo` (`gerar`) é o registro da listagem por código e ISIN em toda a história
guardada, por geração (início e fim de listagem); não é lida pelo ponto-no-tempo, porque o fim
de listagem posterior a D revelaria a deslistagem de antemão.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime

import pandas as pd

from sentinela.data import liquidez
from sentinela.data.pit.carga_cvm import linha_do_informe
from sentinela.data.providers import b3_cotahist
from sentinela.data.referencia import montagem
from sentinela.data.referencia.registro import Excecao, Indice

CLASSES_DO_ISIN = {"ACN": "STOCK", "UNT": "UNIT", "CTF": "FUNDO", "BDR": "BDR"}
JANELA = 63


def classe_do_isin(isin: str) -> str:
    """Classe pelo tipo do ativo no ISIN (posições 7 a 9); fora do formato, `OUTRO`."""
    if len(isin) != 12:
        return "OUTRO"
    return CLASSES_DO_ISIN.get(isin[6:9], "OUTRO")


def _dia(dia: date) -> str:
    if isinstance(dia, datetime) or not isinstance(dia, date):
        raise TypeError("o universo recebe o dia local de D (date), não um instante")
    return dia.isoformat()


def gerar(conn, gerado_em: str) -> int:
    """Grava a fotografia das listagens por código e ISIN, num `SAVEPOINT`; devolve quantas."""
    linhas = [
        (gerado_em, codigo, isin, classe_do_isin(isin), primeiro, ultimo, pregoes)
        for codigo, isin, primeiro, ultimo, pregoes in conn.execute(
            "SELECT codigo_negociacao, isin, MIN(data), MAX(data), COUNT(DISTINCT data) "
            "FROM precos WHERE tipo_mercado = ? AND isin IS NOT NULL AND isin != '' "
            "GROUP BY codigo_negociacao, isin ORDER BY codigo_negociacao, isin",
            (b3_cotahist.MERCADO_A_VISTA,),
        )
    ]
    conn.execute("SAVEPOINT universo")
    try:
        conn.executemany(
            "INSERT INTO universo (gerado_em, codigo_negociacao, isin, classe, primeiro_pregao, "
            "ultimo_pregao, pregoes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            linhas,
        )
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK TO universo")
            conn.execute("RELEASE universo")
        raise
    conn.execute("RELEASE universo")
    return len(linhas)


def _fiis_com_informe(conn, dia: str) -> set[str]:
    """ISINs dos fundos com Informe mensal (geral) entregue antes de D."""
    return {
        isin
        for (texto,) in conn.execute(
            "SELECT linha_json FROM fii_informe_linhas WHERE parte = 'geral' "
            "AND data_entrega != '' AND data_entrega < ?",
            (dia,),
        )
        if (isin := json.loads(texto).get("Codigo_ISIN"))
    }


def _janela(conn, texto: str) -> tuple[str, str] | None:
    """(último pregão antes de D, primeiro dos 63 pregões antes de D), ou `None` sem pregão."""
    pregoes = [
        d
        for (d,) in conn.execute(
            "SELECT DISTINCT data FROM precos WHERE tipo_mercado = ? AND data < ? "
            "ORDER BY data DESC LIMIT ?",
            (b3_cotahist.MERCADO_A_VISTA, texto, JANELA),
        )
    ]
    return (pregoes[0], pregoes[-1]) if pregoes else None


def _pregoes_antes(conn, texto: str, codigo: str) -> tuple[str | None, str | None]:
    """Primeiro e último pregão à vista do código antes de D (nada depois de D)."""
    return conn.execute(
        "SELECT MIN(data), MAX(data) FROM precos "
        "WHERE codigo_negociacao = ? AND tipo_mercado = ? AND data < ?",
        (codigo, b3_cotahist.MERCADO_A_VISTA, texto),
    ).fetchone()


def tickers_em(conn, dia: date) -> list[dict]:
    """Códigos com negócio à vista nos 63 pregões antes de D (ação, unit e FII), por ISIN.

    Lê só os preços anteriores a D: o primeiro e o último pregão saem até o último pregão
    antes de D, sem revelar negócio (ou deslistagem) posterior.
    """
    texto = _dia(dia)
    janela = _janela(conn, texto)
    if janela is None:
        return []
    referencia, inicio_janela = janela
    fiis = _fiis_com_informe(conn, texto)
    listados = []
    for codigo, isin in conn.execute(
        "SELECT DISTINCT codigo_negociacao, isin FROM precos WHERE tipo_mercado = ? "
        "AND data BETWEEN ? AND ? AND isin IS NOT NULL AND isin != '' "
        "ORDER BY codigo_negociacao, isin",
        (b3_cotahist.MERCADO_A_VISTA, inicio_janela, referencia),
    ):
        classe = classe_do_isin(isin)
        if classe == "FUNDO":
            if isin not in fiis:
                continue
            classe = "FII"
        elif classe not in ("STOCK", "UNIT"):
            continue
        primeiro, ultimo = _pregoes_antes(conn, texto, codigo)
        listados.append(
            {
                "ticker": codigo,
                "isin": isin,
                "classe": classe,
                "primeiro_pregao": primeiro,
                "ultimo_pregao": ultimo,
            }
        )
    return listados


def _fca_entregue_depois(conn, texto: str) -> set[tuple[str, str, int]]:
    """Versões do FCA que o índice da CVM lista com outra data de entrega, em D ou depois.

    O conflito da carga no índice (`conflitos_carga`, DD-57) é a mesma versão com duas
    entregas; só o conteúdo decide a versão, e a entrega vale pela data mais tardia (DD-58):
    a versão só conta como entregue antes de D se todas as datas observadas forem.
    """
    em_duvida = set()
    for cnpj, dt_refer, versao, arquivo in conn.execute(
        "SELECT cnpj, dt_refer, versao, arquivo_json FROM conflitos_carga "
        "WHERE documento = 'FCA' AND tabela = 'fca_entregas'"
    ):
        receb = json.loads(arquivo)[4]
        if not (isinstance(receb, str) and receb and receb < texto):
            em_duvida.add((cnpj, dt_refer, versao))
    return em_duvida


def _fca_por_referencia(conn, texto: str) -> dict[tuple[str, str], list[dict] | None]:
    """(CNPJ, referência) com versão entregue antes de D → linhas `valor_mobiliario`.

    As linhas são as da maior versão entregue antes de D que tenha linhas guardadas (a fonte
    aberta só guarda as da última versão, DD-34); sem nenhuma, `None`.
    """
    entregues: dict[tuple, set[int]] = {}
    em_duvida = _fca_entregue_depois(conn, texto)
    for cnpj, dt_refer, versao in conn.execute(
        "SELECT cnpj, dt_refer, versao FROM fca_entregas WHERE dt_receb < ?", (texto,)
    ):
        if (cnpj, dt_refer, versao) not in em_duvida:
            entregues.setdefault((cnpj, dt_refer), set()).add(versao)
    linhas: dict[tuple, list[dict]] = {}
    for cnpj, dt_refer, versao, texto_linha in conn.execute(
        "SELECT cnpj, dt_refer, versao, linha_json FROM fca_linhas "
        "WHERE parte = 'valor_mobiliario' ORDER BY cnpj, dt_refer, versao, linha_sha256"
    ):
        if versao.isdigit() and int(versao) in entregues.get((cnpj, dt_refer), ()):
            linhas.setdefault((cnpj, dt_refer, int(versao)), []).append(
                json.loads(texto_linha)
            )
    por_referencia = {}
    for (cnpj, dt_refer), versoes in sorted(entregues.items()):
        guardadas = [v for v in versoes if (cnpj, dt_refer, v) in linhas]
        por_referencia[(cnpj, dt_refer)] = (
            linhas[(cnpj, dt_refer, max(guardadas))] if guardadas else None
        )
    return por_referencia


def _negociada_em(linha: dict, texto: str) -> bool:
    """Início de negociação antes de D e sem fim, ou fim em D ou depois."""
    inicio = linha.get("Data_Inicio_Negociacao") or ""
    fim = linha.get("Data_Fim_Negociacao") or ""
    return bool(inicio) and inicio < texto and not (fim and fim < texto)


def companhias_em(conn, dia: date) -> dict:
    """Companhias com ação negociada em mercado organizado em D, pelo FCA entregue antes de D.

    Referência mais recente com versão entregue e sem linhas guardadas vai para `sem_prova`: a
    companhia não é incluída nem excluída em silêncio.
    """
    texto = _dia(dia)
    vigente: dict[str, tuple[str, list[dict] | None]] = {}
    for (cnpj, dt_refer), linhas in _fca_por_referencia(conn, texto).items():
        vigente[cnpj] = (dt_refer, linhas)  # em ordem: fica a referência mais recente
    companhias, sem_prova = [], []
    for cnpj, (dt_refer, linhas) in vigente.items():
        if linhas is None:
            sem_prova.append({"cnpj": cnpj, "referencia_fca": dt_refer})
            continue
        for linha in linhas:
            acao = str(linha.get("Valor_Mobiliario") or "").startswith("Ações")
            # os mesmos mercados organizados da montagem do índice
            mercado = linha.get("Mercado") in montagem._MERCADOS_FCA
            if acao and mercado and _negociada_em(linha, texto):
                companhias.append(
                    {
                        "cnpj": cnpj,
                        "nome": linha.get("Nome_Empresarial"),
                        "valor_mobiliario": linha.get("Valor_Mobiliario"),
                        "codigo": linha.get("Codigo_Negociacao") or None,
                        "inicio_negociacao": linha["Data_Inicio_Negociacao"],
                        "fim_negociacao": linha.get("Data_Fim_Negociacao") or None,
                        "referencia_fca": dt_refer,
                    }
                )
    return {"companhias": companhias, "sem_prova": sem_prova}


CLASSES_DO_UNIVERSO = ("STOCK", "UNIT", "FII")


def _fca_em(
    conn, texto: str, excluir: frozenset[str] = frozenset()
) -> list[tuple[int, pd.DataFrame]]:
    """Linhas do FCA entregue antes de D, por ano, para `montagem.fca_mais_recente`.

    A montagem recebe também as entregas anteriores a D: a referência mais recente entregue
    decide, e uma mais nova sem linhas tira os códigos da anterior (BUG-3-24). A linha sem
    negociação em D recebe uma data de fim e a montagem a trata como encerrada; com negociação
    em D, o fim (em D ou depois) é apagado, porque a montagem só aceita linha sem fim. As
    companhias em `excluir` ficam de fora (`_fca_sem_prova`).
    """
    por_ano: dict[int, list[dict]] = {}
    for (cnpj, dt_refer), linhas in _fca_por_referencia(conn, texto).items():
        if cnpj in excluir:
            continue
        for linha in linhas or ():
            fim = None
            if not _negociada_em(linha, texto):
                fim = linha.get("Data_Fim_Negociacao") or texto
            por_ano.setdefault(int(dt_refer[:4]), []).append(
                linha | {"Data_Fim_Negociacao": fim}
            )
    # vazio vira ausente, como na leitura do CSV oficial
    return [
        (ano, pd.DataFrame(linhas).replace({"": None}))
        for ano, linhas in sorted(por_ano.items())
    ]


def _informe_em(conn, texto: str) -> pd.DataFrame:
    """Linhas do geral do Informe mensal entregues antes de D, como o CSV oficial."""
    linhas = [
        linha_do_informe(t)
        for (t,) in conn.execute(
            "SELECT linha_json FROM fii_informe_linhas WHERE parte = 'geral' "
            "AND data_entrega != '' AND data_entrega < ? ORDER BY dt_refer, versao, linha_sha256",
            (texto,),
        )
    ]
    # sem Informe, a montagem só lê a coluna do ISIN
    return pd.DataFrame(linhas) if linhas else pd.DataFrame(columns=["Codigo_ISIN"])


MOTIVO_FCA_SEM_PROVA = (
    "FCA vigente em D sem os valores na fonte aberta (versão reapresentada depois de D)"
)


def _entregas_vigentes(conn, texto: str) -> dict[tuple[str, str], bool]:
    """(CNPJ, referência) → a versão vigente em D (a maior entregue antes de D) tinha conteúdo
    no arquivo que a registrou (`valores_na_fonte`, DD-34)."""
    vigentes: dict[tuple[str, str], tuple[int, bool]] = {}
    em_duvida = _fca_entregue_depois(conn, texto)
    for cnpj, dt_refer, versao, na_fonte in conn.execute(
        "SELECT cnpj, dt_refer, versao, valores_na_fonte FROM fca_entregas WHERE dt_receb < ?",
        (texto,),
    ):
        if (cnpj, dt_refer, versao) in em_duvida:
            continue
        if versao > vigentes.get((cnpj, dt_refer), (0, False))[0]:
            vigentes[(cnpj, dt_refer)] = (versao, bool(na_fonte))
    return {chave: na_fonte for chave, (_, na_fonte) in vigentes.items()}


def _fca_sem_prova(
    conn, texto: str
) -> tuple[pd.DataFrame, frozenset[str], list[Excecao]]:
    """Entregas para a montagem e as companhias sem prova do FCA em D, com as exceções.

    Referência mais recente sem linhas guardadas: se a versão vigente em D tinha conteúdo na
    fonte, foi entregue sem valores mobiliários (BUG-3-24, regra da montagem); se não tinha (a
    versão foi reapresentada depois de D e a fonte aberta só guarda a última), não há prova: a
    companhia fica de fora, sem voltar à referência anterior, e os códigos da referência
    anterior mais recente com linhas negociadas em D viram exceção com `MOTIVO_FCA_SEM_PROVA`.
    """
    vigentes = _entregas_vigentes(conn, texto)
    por_referencia = _fca_por_referencia(conn, texto)
    recente: dict[str, str] = {}
    for cnpj, dt_refer in vigentes:
        if dt_refer > recente.get(cnpj, ""):
            recente[cnpj] = dt_refer
    sem_prova = {
        cnpj
        for cnpj, dt_refer in recente.items()
        if por_referencia.get((cnpj, dt_refer)) is None
        and not vigentes[(cnpj, dt_refer)]
    }
    excecoes: dict[tuple, Excecao] = {}
    for cnpj in sorted(sem_prova):
        anteriores = sorted(
            r for (c, r), linhas in por_referencia.items() if c == cnpj and linhas
        )
        for linha in por_referencia[(cnpj, anteriores[-1])] if anteriores else ():
            codigo = montagem.normalizar_codigo(linha.get("Codigo_Negociacao") or "")
            if codigo and _negociada_em(linha, texto):
                excecoes.setdefault(
                    (codigo, cnpj),
                    Excecao(
                        codigo,
                        MOTIVO_FCA_SEM_PROVA,
                        cnpj,
                        linha.get("Nome_Empresarial"),
                    ),
                )
    entregas = pd.DataFrame(
        [chave for chave in vigentes if chave[0] not in sem_prova],
        columns=["CNPJ_CIA", "DT_REFER"],
    )
    return entregas, frozenset(sem_prova), list(excecoes.values())


def indice_em(
    conn,
    dia: date,
    cadastro: pd.DataFrame,
    correcoes: Iterable = (),
    identidades_fii: Iterable[dict[str, str]] = (),
) -> Indice:
    """O índice de referência montado só com o que existia antes de D (F3-5).

    A mesma montagem do índice atual (`montagem.montar_indice`), com o FCA válido em D
    (`_fca_em`) e as entregas do FCA anteriores a D (a referência mais recente entregue decide,
    BUG-3-24; sem prova da versão vigente em D, a companhia fica de fora com exceção,
    `_fca_sem_prova`), o Informe entregue antes de D e as cotações dos 63 pregões anteriores a D. O
    cadastro da CVM só existe na versão atual: dá o código CVM e os atributos, não decide quem
    entra (a montagem não o usa para isso).
    """
    texto = _dia(dia)
    entregas, sem_prova, excecoes = _fca_sem_prova(conn, texto)
    fcas = _fca_em(conn, texto, sem_prova)
    fonte = {"arquivo": "banco único", "data": texto}
    fontes = {
        "fca": {str(ano): fonte for ano, _ in fcas},
        "informe_fii": fonte,
        "cotahist": fonte,
    }
    indice = montagem.montar_indice(
        fcas,
        cadastro,
        _informe_em(conn, texto),
        b3_cotahist.cotacoes_ate(conn, dia, JANELA),
        fontes,
        texto,
        correcoes,
        identidades_fii=identidades_fii,
        entregas_fca=entregas,
    )
    indice.excecoes.extend(excecoes)
    return indice


MOTIVO_SEM_IDENTIFICACAO = "ação negociada em D sem o código no FCA entregue antes de D"


def universo_em(conn, dia: date, cadastro: pd.DataFrame, **kwargs) -> dict:
    """Universo em D: STOCK, UNIT e FII do índice em D (`indice_em`), com os pregões antes de D.

    O índice em D só reconhece a companhia pelo código de negociação do FCA, que o FCA antigo
    muitas vezes não traz (a ALL em 2015) e o atual às vezes omite. Os códigos de ação ou unit
    pelo ISIN listados em D (`tickers_em`) que o índice não registrou com classe nenhuma não
    entram em silêncio nem somem: vão para `sem_identificacao`, com o motivo, porque sem CNPJ
    os métodos não têm a CVM; código que o índice registrou como exceção leva o motivo dela.
    """
    texto = _dia(dia)
    indice = indice_em(conn, dia, cadastro, **kwargs)
    identificados = []
    for ticker, registro in sorted(indice.registros.items()):
        if registro.classe in CLASSES_DO_UNIVERSO:
            primeiro, ultimo = _pregoes_antes(conn, texto, ticker)
            identificados.append(
                {
                    "ticker": ticker,
                    "classe": registro.classe,
                    "regra": registro.regra,
                    "cnpj": registro.cnpj,
                    "primeiro_pregao": primeiro,
                    "ultimo_pregao": ultimo,
                }
            )
    excecoes = {e.codigo: e.motivo for e in indice.excecoes}
    sem_identificacao = [
        item | {"motivo": excecoes.get(item["ticker"], MOTIVO_SEM_IDENTIFICACAO)}
        for item in tickers_em(conn, dia)
        if item["ticker"] not in indice.registros
        and item["classe"] in ("STOCK", "UNIT")
    ]
    return {"universo": identificados, "sem_identificacao": sem_identificacao}


def universo_backtest(
    conn,
    dia: date,
    cadastro: pd.DataFrame,
    *,
    presenca_min: float,
    volume_acoes_min: float,
    volume_fii_min: float,
    **kwargs,
) -> dict:
    """Universo em D que passa na liquidez da própria data; os outros, com o motivo.

    `kwargs` (correções e identidades de FII) seguem para `indice_em`.
    """
    cotacoes = b3_cotahist.cotacoes_ate(conn, dia, JANELA)
    lido = universo_em(conn, dia, cadastro, **kwargs)
    elegiveis, fora = [], []
    for item in lido["universo"]:
        bloco = liquidez.metricas(cotacoes, item["ticker"])
        if isinstance(bloco, liquidez.Abstencao):
            # como na cascata: ticker ausente só vale volume zero com a janela coberta
            bloco = {
                "abstencao": bloco.motivo,
                "incompleta": len({c.data for c in cotacoes}) < JANELA,
            }
        volume_min = volume_fii_min if item["classe"] == "FII" else volume_acoes_min
        motivo = liquidez.avaliar(
            bloco, janela=JANELA, presenca_min=presenca_min, volume_min=volume_min
        )
        if motivo is None:
            elegiveis.append(item)
        else:
            fora.append(item | {"motivo": next(iter(motivo.values()))})
    return {
        "elegiveis": elegiveis,
        "fora": fora,
        "sem_identificacao": lido["sem_identificacao"],
    }
