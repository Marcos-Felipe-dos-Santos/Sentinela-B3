"""Relação de proventos em dinheiro da B3, empresas listadas (F2B-31; ficha Bazin 1.2, §2).

Serviço CompanyCall de `sistemaswebb3-listados.b3.com.br`, conferido em 20/10/2026 (contrato
D18 em `tests/fixtures/contratos/b3_proventos_lren_2026.json`). Os parâmetros vão em JSON,
codificados em base64, no fim do caminho:
- `GetDetail` pelo código CVM: nome de pregão (`tradingName`), código do emissor
  (`issuingCompany`) e os ISINs da companhia (`otherCodes`, `[{"code", "isin"}]`);
- `GetListedCashDividends` pelo nome de pregão transformado pela regra fixa da decisão 30
  (`nome_de_consulta`: "S/A", "S.A." e "S.A" → "SA"), paginado: `page.totalRecords` e
  `page.totalPages`, e em `results` um registro por evento e espécie (`typeStock`,
  `corporateAction`, `valueCash`, `lastDatePriorEx`, `dateApproval`, `quotedPerShares`).
  O serviço aceita no máximo 120 por página: com 500 a resposta vem sem registros e com
  `totalRecords` nulo;
- `GetListedSupplementCompany` pelo código do emissor: `stockDividends`, os eventos em
  ações (`label`, `lastDatePrior`, `factor`, `isinCode`), e `cashDividends`, os proventos
  em dinheiro recentes com o ISIN (`label`, `lastDatePrior`, `rate`, `isinCode`). Esta lista
  não cobre a janela inteira (a da Klabin, em 20/10/2026, só tinha novembro e dezembro de
  2025), mas é a conferência de que a relação lida pelo nome de pregão é a do emissor: a
  busca pelo nome falha com barra ("AMBEV S/A" devolve zero registros; "AMBEV SA", 40;
  "AMBEV", 134, de um homônimo de 2000 a 2013).

A relação pelo nome só vale com a conferência da identidade do emissor (decisão 33, em
`proventos_b3.conferir_emissor`): o motivo da falha fica em `Relacao.identidade`, e a
cascata abstém por ele. O provedor sempre preenche `identidade`; o padrão `None` só serve
a quem monta uma `Relacao` à mão.

Os registros voltam literais; a conta é de `sentinela.data.proventos_b3`. Cache somente
da mesma coleta explícita completa; outro instante volta à fonte, sem criar observação.
`agora` é o instante da coleta (sem leitura de relógio aqui).
"""

from __future__ import annotations

import base64
import calendar
import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import requests

from sentinela.data import fatores_acoes_b3, proventos_b3
from sentinela.data.cache_leitura import CacheCopia, IdentidadeLeitor

URL_BASE = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall"
POR_PAGINA = 120
MAX_PAGINAS = 50
TIMEOUT = 30
# Decisão 30: "S/A", "S.A." e "S.A" isolados viram "SA"; o resto do nome não muda.
_SOCIEDADE_ANONIMA = re.compile(r"(?<![A-Z0-9])S[/.]A\.?(?![A-Z0-9])")
TAMANHO_ISIN = 12


def url(metodo: str, parametros: dict) -> str:
    """URL do serviço com os parâmetros em JSON codificado em base64."""
    codificado = base64.b64encode(json.dumps(parametros).encode()).decode()
    return f"{URL_BASE}/{metodo}/{codificado}"


def nome_de_consulta(nome: str) -> str:
    """Nome de pregão do GetDetail pela regra fixa da decisão 30, para a relação."""
    return _SOCIEDADE_ANONIMA.sub("SA", nome)


def _isins(detalhe: dict) -> tuple[str, ...]:
    """ISINs de `otherCodes`; forma inesperada não traz ISIN (a conferência abstém)."""
    codigos = detalhe.get("otherCodes")
    if not isinstance(codigos, list):
        return ()
    return tuple(
        c["isin"]
        for c in codigos
        if isinstance(c, dict)
        and isinstance(c.get("isin"), str)
        and len(c["isin"]) == TAMANHO_ISIN
    )


def obter_json(endereco: str) -> tuple[Any, dict]:
    """Corpo JSON e a fonte (URL, bytes e SHA-256 da resposta)."""
    resposta = requests.get(endereco, timeout=TIMEOUT)
    resposta.raise_for_status()
    corpo = resposta.content
    return json.loads(corpo), {
        "url": endereco,
        "bytes": len(corpo),
        "sha256": hashlib.sha256(corpo).hexdigest(),
    }


@dataclass(frozen=True)
class Relacao:
    nome_pregao: str
    emissor: str
    registros: tuple[dict, ...]
    total: int | None
    eventos_acoes: tuple[dict, ...]
    dinheiro_complemento: tuple[dict, ...]
    fontes: tuple[dict, ...]
    coleta: str
    isins: tuple[str, ...] = ()
    identidade: str | None = None


_COLETAS: CacheCopia[Relacao] = CacheCopia()


def coletar(
    cd_cvm: int | str,
    agora: datetime,
    obter: Callable[[str], tuple[Any, dict]] = obter_json,
) -> Relacao:
    """Reutiliza somente a mesma coleta explícita; outra observação volta à fonte."""
    chave = (str(cd_cvm), agora.isoformat(), IdentidadeLeitor(obter))
    existente = _COLETAS.buscar(chave)
    if existente is not None:
        return existente
    relacao = _coletar_sem_cache(cd_cvm, agora, obter)
    if type(relacao.total) is int and relacao.total == len(relacao.registros):
        _COLETAS.guardar(chave, relacao)
    return relacao


def _coletar_sem_cache(
    cd_cvm: int | str,
    agora: datetime,
    obter: Callable[[str], tuple[Any, dict]] = obter_json,
) -> Relacao:
    """Todas as páginas de proventos em dinheiro e os eventos em ações do emissor.

    Cadastro sem nome de pregão ou emissor, ou complemento fora do leiaute: `ValueError`;
    página da relação que não é objeto com a lista `results`: `TypeError`.
    """
    detalhe, fonte = obter(
        url("GetDetail", {"codeCVM": str(cd_cvm), "language": "pt-br"})
    )
    nome = detalhe.get("tradingName") if isinstance(detalhe, dict) else None
    emissor = detalhe.get("issuingCompany") if isinstance(detalhe, dict) else None
    if not nome or not emissor or not isinstance(nome, str):
        raise ValueError("cadastro da B3 sem nome de pregão ou código do emissor")
    nome = nome_de_consulta(nome)
    isins = _isins(detalhe)
    fontes, registros, total = [fonte], [], None
    for pagina in range(1, MAX_PAGINAS + 1):
        corpo, fonte = obter(
            url(
                "GetListedCashDividends",
                {
                    "language": "pt-br",
                    "pageNumber": pagina,
                    "pageSize": POR_PAGINA,
                    "tradingName": nome,
                },
            )
        )
        fontes.append(fonte)
        if not isinstance(corpo, dict) or not isinstance(corpo.get("results"), list):
            raise TypeError("relação de proventos da B3 fora do leiaute")
        pagina_info = corpo.get("page") or {}
        if pagina == 1:
            total = pagina_info.get("totalRecords")
        registros.extend(corpo["results"])
        paginas = pagina_info.get("totalPages")
        if not isinstance(paginas, int) or pagina >= paginas:
            break
    complemento, fonte = obter(
        url(
            "GetListedSupplementCompany",
            {"issuingCompany": emissor, "language": "pt-br"},
        )
    )
    fontes.append(fonte)
    if (
        not isinstance(complemento, list)
        or not complemento
        or not isinstance(complemento[0], dict)
        or not isinstance(complemento[0].get("stockDividends"), list)
        or not isinstance(complemento[0].get("cashDividends"), list)
    ):
        raise ValueError("complemento da B3 sem eventos em ações ou em dinheiro")
    return Relacao(
        nome_pregao=nome,
        emissor=emissor,
        registros=tuple(registros),
        total=total,
        eventos_acoes=tuple(complemento[0]["stockDividends"]),
        dinheiro_complemento=tuple(complemento[0]["cashDividends"]),
        fontes=tuple(fontes),
        coleta=agora.isoformat(),
        isins=isins,
        identidade=proventos_b3.conferir_emissor(
            registros, complemento[0]["cashDividends"], isins
        ),
    )


# --- Eventos em ações no banco único (F3-4b) --------------------------------------------------


def _fator_ou_motivo(evento: dict) -> tuple[float | None, str | None]:
    """Fator multiplicativo oficial (`fatores_acoes_b3._fator`) ou o motivo da falta."""
    try:
        return fatores_acoes_b3._fator(evento), None
    except (ValueError, TypeError) as erro:
        return None, str(erro)


def gravar_eventos(conn, relacao: Relacao, cd_cvm: int | str) -> dict:
    """Grava os eventos em ações do complemento em `eventos_societarios`, num `SAVEPOINT`.

    Cada evento é identificado pelo hash do seu JSON; já gravado, conta como repetido e fica
    a primeira coleta que o viu. A fonte e o hash são os da resposta do complemento (a última
    da coleta). Evento sem conversão documentada entra sem fator, com o motivo.
    """
    complemento = relacao.fontes[-1]
    if "GetListedSupplementCompany" not in str(complemento.get("url")):
        raise ValueError("a última fonte da coleta não é a resposta do complemento")
    prov = (complemento["url"], relacao.coleta, complemento["sha256"])
    resumo = {"inseridos": 0, "repetidos": 0, "sem_fator": 0}
    conn.execute("SAVEPOINT eventos_b3")
    try:
        for evento in relacao.eventos_acoes:
            texto = json.dumps(evento, ensure_ascii=False, sort_keys=True)
            linha = hashlib.sha256(texto.encode("utf-8")).hexdigest()
            if conn.execute(
                "SELECT 1 FROM eventos_societarios WHERE emissor = ? AND linha_sha256 = ?",
                (relacao.emissor, linha),
            ).fetchone():
                resumo["repetidos"] += 1
                continue
            fator, motivo = _fator_ou_motivo(evento)
            datas = [
                proventos_b3.ler_data(evento.get(c))
                for c in ("lastDatePrior", "approvedOn")
            ]
            conn.execute(
                "INSERT INTO eventos_societarios (emissor, linha_sha256, cd_cvm, rotulo, isin, "
                "ativo_emitido, data_com, aprovacao, fator_declarado, fator, motivo_sem_fator, "
                "linha_json, fonte, coleta, hash_sha256) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    relacao.emissor,
                    linha,
                    str(cd_cvm),
                    str(evento.get("label") or ""),
                    evento.get("isinCode"),
                    evento.get("assetIssued"),
                    *(d.isoformat() if d else None for d in datas),
                    evento.get("factor"),
                    fator,
                    motivo,
                    texto,
                    *prov,
                ),
            )
            resumo["inseridos"] += 1
            resumo["sem_fator"] += fator is None
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK TO eventos_b3")
            conn.execute("RELEASE eventos_b3")
        raise
    conn.execute("RELEASE eventos_b3")
    return resumo


CALENDARIO_MAXIMO_DIAS = 10
MOTIVO_SEM_CALENDARIO = (
    "pregões guardados não cobrem a data com (data ex não demonstrada)"
)
MOTIVO_SEM_DATAS = "aprovação ou data com ilegível"
MOTIVO_CONFLITO = "eventos em ações conflitantes na mesma data com"
MOTIVO_NAO_EFETIVADO = "data com em D ou depois: evento aprovado e ainda não efetivado"


def _data_ex(conn, data_com: str, dia: date) -> str | None:
    """Primeiro pregão depois da data com, só com prova de calendário (DD-48).

    Exige um pregão guardado até a data com e o seguinte, os dois a até
    `CALENDARIO_MAXIMO_DIAS` dela, e o seguinte antes do dia de D: sem pregões guardados em
    volta da data com, o primeiro pregão guardado depois dela não é a data ex.
    """
    anterior, posterior = conn.execute(
        "SELECT (SELECT MAX(data) FROM precos WHERE tipo_mercado = '010' AND data <= ?), "
        "(SELECT MIN(data) FROM precos WHERE tipo_mercado = '010' AND data > ? AND data < ?)",
        (data_com, data_com, dia.isoformat()),
    ).fetchone()
    com = date.fromisoformat(data_com)
    if anterior is None or posterior is None:
        return None
    if (com - date.fromisoformat(anterior)).days > CALENDARIO_MAXIMO_DIAS:
        return None
    if (date.fromisoformat(posterior) - com).days > CALENDARIO_MAXIMO_DIAS:
        return None
    return posterior


def eventos_ate(conn, emissor: str, dia: date) -> dict:
    """Eventos em ações do emissor conhecidos antes do dia local de D (F3-4b, DD-48).

    Vale o evento aprovado antes do dia de D. Vão para `sem_prova`, com o motivo, os de
    aprovação ou data com ilegível e os conflitantes (mesmo rótulo, ISIN, ativo e data com
    com fatores diferentes); o mesmo evento em outra forma conta uma vez. A data ex é o
    primeiro pregão do mercado à vista depois da data com, só com prova de calendário
    (`_data_ex`); sem ela, fica nula com `motivo_data_ex`, e evento com data com em D ou depois
    sai com o motivo de não efetivado. O mesmo evento com aprovação legível numa forma e
    ilegível noutra aparece nas duas listas. Recebe o dia (`date`).
    """
    if isinstance(dia, datetime) or not isinstance(dia, date):
        raise TypeError("eventos_ate recebe o dia local de D (date), não um instante")
    por_evento: dict[tuple, list[dict]] = {}
    sem_prova = []
    for (
        rotulo, isin, emitido, data_com, aprovacao, declarado, fator, motivo, fonte, coleta,
        hash_,
    ) in conn.execute(
        "SELECT rotulo, isin, ativo_emitido, data_com, aprovacao, fator_declarado, fator, "
        "motivo_sem_fator, fonte, coleta, hash_sha256 FROM eventos_societarios "
        "WHERE emissor = ? ORDER BY data_com, rotulo, isin, coleta, linha_sha256",
        (emissor,),
    ):  # fmt: skip
        evento = {
            "rotulo": rotulo, "isin": isin, "ativo_emitido": emitido, "data_com": data_com,
            "aprovacao": aprovacao, "fator_declarado": declarado, "fator": fator,
            "motivo_sem_fator": motivo,
            "proveniencia": {"fonte": fonte, "coleta": coleta, "hash_sha256": hash_},
        }  # fmt: skip
        if aprovacao is None or data_com is None:
            sem_prova.append(evento | {"motivo": MOTIVO_SEM_DATAS})
        elif aprovacao < dia.isoformat():
            por_evento.setdefault((rotulo, isin, emitido, data_com), []).append(evento)
    vistos = []
    for (_, _, _, data_com), mesmos in por_evento.items():
        if len({(e["fator"], e["motivo_sem_fator"]) for e in mesmos}) > 1:
            sem_prova.extend(e | {"motivo": MOTIVO_CONFLITO} for e in mesmos)
            continue
        if data_com >= dia.isoformat():
            vistos.append(
                mesmos[0] | {"data_ex": None, "motivo_data_ex": MOTIVO_NAO_EFETIVADO}
            )
            continue
        data_ex = _data_ex(conn, data_com, dia)
        vistos.append(
            mesmos[0]
            | {
                "data_ex": data_ex,
                "motivo_data_ex": None if data_ex else MOTIVO_SEM_CALENDARIO,
            }
        )
    return {"eventos": vistos, "sem_prova": sem_prova}


# --- Proventos em dinheiro no banco único (F3-7a) ---------------------------------------------

MOTIVO_PROVENTO_IDENTIDADE = "identidade do emissor não comprovada na coleta"
MOTIVO_PROVENTO_INCOMPLETA = "relação de proventos incompleta na coleta"
MOTIVO_PROVENTO_SEM_COLETA = "sem coleta da relação de proventos do emissor"
MOTIVO_PROVENTO_SEM_DATAS = "data com ou aprovação ilegível"


def _pagina_do_registro(relacao: Relacao, indice: int) -> dict:
    """Fonte da página da relação que devolveu o registro `indice` (120 por página)."""
    fonte = relacao.fontes[1 + indice // POR_PAGINA]
    if "GetListedCashDividends" not in str(fonte.get("url")):
        raise ValueError("as fontes da coleta não seguem as páginas da relação")
    return fonte


def gravar_proventos(conn, relacao: Relacao, cd_cvm: int | str) -> dict:
    """Grava a coleta e os registros da relação em `proventos`, num `SAVEPOINT`.

    A coleta (total declarado, registros lidos, identidade do emissor) vai sempre para
    `proventos_coletas`, e cada registro que ela trouxe para `proventos_vistos`; o registro é
    identificado pelo hash do seu JSON e, já gravado, conta como repetido (fica a primeira
    coleta que o viu), com a fonte da sua página. JSON idêntico repetido na mesma relação conta
    uma vez (`duplicados_na_coleta`). Coleta sem fuso é recusada. O complemento em dinheiro
    do GetListedSupplementCompany vai para `proventos_complemento` (F3-8d-fix, decisão 43),
    para a leitura refazer a decisão 33; coleta cuja última fonte não é ele é recusada.
    """
    if datetime.fromisoformat(relacao.coleta).utcoffset() is None:
        raise ValueError("coleta exige fuso horário")
    detalhe = relacao.fontes[0]
    resumo = {"inseridos": 0, "repetidos": 0, "duplicados_na_coleta": 0}
    conn.execute("SAVEPOINT proventos_b3")
    try:
        conn.execute(
            "INSERT INTO proventos_coletas (emissor, coleta, cd_cvm, nome_pregao, total, "
            "registros, identidade, isins_json, fonte, hash_sha256) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                relacao.emissor,
                relacao.coleta,
                str(cd_cvm),
                relacao.nome_pregao,
                relacao.total if type(relacao.total) is int else None,
                len(relacao.registros),
                relacao.identidade,
                json.dumps(list(relacao.isins)),
                detalhe["url"],
                detalhe["sha256"],
            ),
        )
        complemento = relacao.fontes[-1]
        if "GetListedSupplementCompany" not in str(complemento.get("url")):
            raise ValueError("a última fonte da coleta não é o complemento da B3")
        conn.execute(
            "INSERT INTO proventos_complemento (emissor, coleta, dinheiro_json, fonte, "
            "hash_sha256) VALUES (?, ?, ?, ?, ?)",
            (
                relacao.emissor,
                relacao.coleta,
                json.dumps(list(relacao.dinheiro_complemento), ensure_ascii=False),
                complemento["url"],
                complemento["sha256"],
            ),
        )
        for indice, registro in enumerate(relacao.registros):
            texto = json.dumps(registro, ensure_ascii=False, sort_keys=True)
            linha = hashlib.sha256(texto.encode("utf-8")).hexdigest()
            if conn.execute(
                "SELECT 1 FROM proventos_vistos WHERE emissor = ? AND coleta = ? "
                "AND linha_sha256 = ?",
                (relacao.emissor, relacao.coleta, linha),
            ).fetchone():
                resumo["duplicados_na_coleta"] += 1  # JSON idêntico na mesma relação
                continue
            conn.execute(
                "INSERT INTO proventos_vistos (emissor, coleta, linha_sha256) VALUES (?, ?, ?)",
                (relacao.emissor, relacao.coleta, linha),
            )
            if conn.execute(
                "SELECT 1 FROM proventos WHERE emissor = ? AND linha_sha256 = ?",
                (relacao.emissor, linha),
            ).fetchone():
                resumo["repetidos"] += 1
                continue
            pagina = _pagina_do_registro(relacao, indice)
            datas = [
                proventos_b3.ler_data(registro.get(c))
                for c in ("lastDatePriorEx", "dateApproval")
            ]
            conn.execute(
                "INSERT INTO proventos (emissor, linha_sha256, cd_cvm, especie, natureza, "
                "data_com, aprovacao, valor_bruto, cotado_por, linha_json, fonte, coleta, "
                "hash_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    relacao.emissor,
                    linha,
                    str(cd_cvm),
                    registro.get("typeStock"),
                    registro.get("corporateAction"),
                    *(d.isoformat() if d else None for d in datas),
                    registro.get("valueCash"),
                    registro.get("quotedPerShares"),
                    texto,
                    pagina["url"],
                    relacao.coleta,
                    pagina["sha256"],
                ),
            )
            resumo["inseridos"] += 1
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK TO proventos_b3")
            conn.execute("RELEASE proventos_b3")
        raise
    conn.execute("RELEASE proventos_b3")
    return resumo


MOTIVO_COMPLEMENTO_NAO_GUARDADO = (
    "complemento da coleta não guardado para conferir o ISIN do ticker no pregão"
)


def isin_no_pregao(conn, ticker: str, dia: date) -> str | None:
    """CODISI do último pregão à vista do código antes do dia (COTAHIST guardado)."""
    linha = conn.execute(
        "SELECT isin FROM precos WHERE codigo_negociacao = ? AND tipo_mercado = ? "
        "AND data < ? AND isin IS NOT NULL AND isin != '' ORDER BY data DESC LIMIT 1",
        (ticker, "010", dia.isoformat()),
    ).fetchone()
    return linha[0] if linha else None


def _identidade_com_o_pregao(
    conn, emissor: str, coleta: str, identidade: str, ticker: str | None, dia: date
) -> str | None:
    """Decisão 43 (DD-74): a decisão 33 inteira de novo, com o ISIN do ticker no pregão.

    O ISIN do CODISI soma aos da companhia no GetDetail só se o código do emissor (posições
    3 a 6) for o de um deles; as partes (a) a (d) são as de `conferir_emissor`, com a
    relação e o complemento da própria coleta. Sem ISIN novo, fica o motivo gravado.
    """
    isin = isin_no_pregao(conn, ticker, dia) if ticker else None
    (isins_json,) = conn.execute(
        "SELECT isins_json FROM proventos_coletas WHERE emissor = ? AND coleta = ?",
        (emissor, coleta),
    ).fetchone()
    isins = tuple(json.loads(isins_json))
    if isin is None or isin in isins or isin[2:6] not in {i[2:6] for i in isins}:
        return identidade
    complemento = conn.execute(
        "SELECT dinheiro_json FROM proventos_complemento WHERE emissor = ? AND coleta = ?",
        (emissor, coleta),
    ).fetchone()
    if complemento is None:
        return MOTIVO_COMPLEMENTO_NAO_GUARDADO
    registros = [
        json.loads(texto)
        for (texto,) in conn.execute(
            "SELECT p.linha_json FROM proventos_vistos v JOIN proventos p "
            "ON p.emissor = v.emissor AND p.linha_sha256 = v.linha_sha256 "
            "WHERE v.emissor = ? AND v.coleta = ? ORDER BY p.linha_sha256",
            (emissor, coleta),
        )
    ]
    return proventos_b3.conferir_emissor(
        registros, json.loads(complemento[0]), (*isins, isin)
    )


def proventos_ate(
    conn,
    emissor: str,
    dia: date,
    *,
    por_publicacao: bool = False,
    ticker: str | None = None,
) -> dict:
    """Proventos em dinheiro conhecidos antes do dia local de D, com a data ex demonstrada.

    Vale a relação da coleta mais recente do emissor feita antes do dia de D em São Paulo
    (só os registros que ela trouxe, `proventos_vistos`); sem coleta, ou com identidade não
    comprovada ou relação incompleta nela, abstém com o motivo (`abstencao`). Registro com
    aprovação ou data com em D ou depois ainda não era conhecido ou efetivado em D e fica de
    fora; data ilegível ou data ex sem calendário vão para `sem_prova`, com o motivo.

    `por_publicacao` (decisão 40, data passada): a coleta deixa de ser critério; vale a coleta
    mais recente do emissor, de qualquer data, e a disponibilidade em D é a da aprovação e da
    data com de cada registro, anteriores a D (o filtro acima).

    `ticker` (decisão 43): com identidade não comprovada na coleta, a conferência é refeita
    com o ISIN do ticker no último pregão antes do dia (`_identidade_com_o_pregao`).
    """
    if isinstance(dia, datetime) or not isinstance(dia, date):
        raise TypeError("proventos_ate recebe o dia local de D (date), não um instante")
    texto = dia.isoformat()
    anteriores = [
        linha
        for linha in conn.execute(
            "SELECT coleta, total, registros, identidade FROM proventos_coletas "
            "WHERE emissor = ?",
            (emissor,),
        )
        if por_publicacao
        or datetime.fromisoformat(linha[0]).astimezone(proventos_b3.FUSO).date() < dia
    ]
    coleta = (
        max(anteriores, key=lambda linha: datetime.fromisoformat(linha[0]))
        if anteriores
        else None
    )
    if coleta is None:
        return {"abstencao": MOTIVO_PROVENTO_SEM_COLETA}
    instante, total, registros, identidade = coleta
    if identidade is not None:
        identidade = _identidade_com_o_pregao(
            conn, emissor, instante, identidade, ticker, dia
        )
    if identidade is not None:
        return {"abstencao": f"{MOTIVO_PROVENTO_IDENTIDADE}: {identidade}"}
    if total != registros:
        return {"abstencao": MOTIVO_PROVENTO_INCOMPLETA}
    da_coleta = {
        chave
        for (chave,) in conn.execute(
            "SELECT linha_sha256 FROM proventos_vistos WHERE emissor = ? AND coleta = ?",
            (emissor, instante),
        )
    }
    proventos, sem_prova = [], []
    for linha in conn.execute(
        "SELECT especie, natureza, data_com, aprovacao, valor_bruto, cotado_por, fonte, "
        "hash_sha256, linha_sha256 FROM proventos WHERE emissor = ? "
        "ORDER BY data_com, linha_sha256",
        (emissor,),
    ):
        (
            especie,
            natureza,
            data_com,
            aprovacao,
            valor,
            cotado,
            fonte,
            hash_,
            chave,
        ) = linha
        if chave not in da_coleta:  # fora da relação da coleta escolhida
            continue
        item = {
            "especie": especie,
            "natureza": natureza,
            "data_com": data_com,
            "aprovacao": aprovacao,
            "valor_bruto": valor,
            "cotado_por": cotado,
            "fonte": fonte,
            "hash_sha256": hash_,
            "linha_sha256": chave,
        }
        if data_com is None or aprovacao is None:
            sem_prova.append(item | {"motivo": MOTIVO_PROVENTO_SEM_DATAS})
            continue
        if aprovacao >= texto or data_com >= texto:
            continue
        data_ex = _data_ex(conn, data_com, dia)
        if data_ex is None:
            sem_prova.append(item | {"motivo": MOTIVO_SEM_CALENDARIO})
            continue
        proventos.append(item | {"data_ex": data_ex})
    return {"proventos": proventos, "sem_prova": sem_prova, "coleta": instante}


# --- Bloco do Bazin no motor histórico (F3-8h) ------------------------------------------------


def relacao_ate(conn, emissor: str, dia: date, *, ticker: str | None = None) -> dict:
    """A relação da B3 como a cascata a entrega ao Bazin, pela coleta do `proventos_ate`.

    A coleta é a que `proventos_ate` escolhe numa data passada (decisão 40, com a identidade
    refeita pelo ISIN do pregão, decisão 43); sem ela, ou abstida, devolve o motivo. Os
    registros são os literais da coleta (`linha_json` dos `proventos_vistos`), com o total
    declarado, sem os aprovados em D ou depois (a regra estrita do `proventos_ate`; o total
    desconta os retirados); a data com de cada registro é conferida na série
    (`proventos_b3.serie_12_meses`), como na cascata. O complemento em dinheiro é o da mesma
    coleta (sem ele, abstém); os eventos em ações são todos os guardados do emissor.
    """
    lidos = proventos_ate(conn, emissor, dia, por_publicacao=True, ticker=ticker)
    if "abstencao" in lidos:
        return {"abstencao": lidos["abstencao"]}
    coleta = lidos["coleta"]
    complemento = conn.execute(
        "SELECT dinheiro_json FROM proventos_complemento WHERE emissor = ? AND coleta = ?",
        (emissor, coleta),
    ).fetchone()
    if complemento is None:
        return {"abstencao": MOTIVO_COMPLEMENTO_NAO_GUARDADO}
    nome, total, fonte, hash_ = conn.execute(
        "SELECT nome_pregao, total, fonte, hash_sha256 FROM proventos_coletas "
        "WHERE emissor = ? AND coleta = ?",
        (emissor, coleta),
    ).fetchone()
    lidos_da_coleta = [
        json.loads(texto)
        for (texto,) in conn.execute(
            "SELECT p.linha_json FROM proventos_vistos v JOIN proventos p "
            "ON p.emissor = v.emissor AND p.linha_sha256 = v.linha_sha256 "
            "WHERE v.emissor = ? AND v.coleta = ? ORDER BY p.linha_sha256",
            (emissor, coleta),
        )
    ]
    # decisão 40, como no `proventos_ate`: aprovação em D ou depois ainda não era conhecida
    registros = [r for r in lidos_da_coleta if not _aprovado_em_d_ou_depois(r, dia)]
    eventos = [
        json.loads(texto)
        for (texto,) in conn.execute(
            "SELECT linha_json FROM eventos_societarios WHERE emissor = ? "
            "ORDER BY linha_sha256",
            (emissor,),
        )
    ]
    return {
        "registros": registros,
        "total": total - (len(lidos_da_coleta) - len(registros)),  # conferido no leitor
        "eventos_acoes": eventos,
        "dinheiro_complemento": json.loads(complemento[0]),
        "coleta": coleta,
        "aprovacao_antes_de_d": True,  # a marca que `proventos_b3.entradas` exige (DD-65)
        "proveniencia": {
            "fonte": "B3, relação de proventos em dinheiro (CompanyCall)",
            "nome_pregao": nome,
            "coleta": coleta,
            "detalhe": {"url": fonte, "sha256": hash_},
            "banco": "proventos",
        },
    }


def _aprovado_em_d_ou_depois(registro: dict, dia: date) -> bool:
    """Aprovação legível em D ou depois; a ilegível fica para a série abster."""
    aprovacao = proventos_b3.ler_data(registro.get("dateApproval"))
    return aprovacao is not None and aprovacao >= dia


def pregoes_da_data_ex(conn, registros, referencia: date) -> list[str] | None:
    """Pregões guardados em torno do início da janela, se alguma data com cair nele.

    A regra de `MarketEngine._pregoes_da_data_ex`, com o COTAHIST do banco (mercado à vista)
    no lugar do download: os meses do limite e do início da janela. `None` quando nenhuma
    data ex depende do calendário.
    """
    inicio = proventos_b3.inicio_da_janela(referencia)
    limite = inicio - proventos_b3.FOLGA_SEM_PREGAO
    datas = {
        proventos_b3.ler_data(r.get("lastDatePriorEx"))
        for r in registros
        if isinstance(r, dict)
    }
    if not any(d is not None and limite < d < inicio for d in datas):
        return None
    primeiro = date(limite.year, limite.month, 1)
    ultimo = date(
        inicio.year, inicio.month, calendar.monthrange(inicio.year, inicio.month)[1]
    )
    return [
        dia
        for (dia,) in conn.execute(
            "SELECT DISTINCT data FROM precos WHERE tipo_mercado = '010' "
            "AND data >= ? AND data <= ? ORDER BY data",
            (primeiro.isoformat(), ultimo.isoformat()),
        )
    ]
