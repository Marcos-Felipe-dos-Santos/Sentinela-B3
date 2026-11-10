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
import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from sentinela.data import proventos_b3
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
