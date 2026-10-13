"""IF.data do Banco Central: índice de Basileia do conglomerado prudencial (F2A-9, P5).

Especificação externa: o serviço OData IFDATA v1 do BCB (Olinda), conferido no F2A-16
(`docs/decisoes/fontes-fase2a.md`, seção 5):
- `IfDataCadastro(AnoMes)` filtrado por `CnpjInstituicaoLider` (os 8 primeiros dígitos do
  CNPJ) traz `CodInst`, `NomeInstituicao` e `Td`; os relatórios de capital estão no
  conglomerado prudencial (`Td = C`, nome com "PRUDENCIAL"), não na instituição;
- `IfDataValores(AnoMes, TipoInstituicao=1, Relatorio='5')` (Informações de Capital) traz
  linhas `NomeColuna`/`Saldo`; o índice de Basileia é a coluna "Índice de Basileia", em razão
  (0,1513 no BB em 12/2025).

A inadimplência não tem relatório conhecido no IF.data (F2A-16): fica `None`, com a
limitação declarada. A data de referência é parâmetro; nada de rede no import nem `config`.
Download com cache em `data/ifdata/`, com TTL; se a rede falha, vale o cache existente, com
aviso no log.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests

from sentinela.data.contas_cvm import normalizar_descricao

logger = logging.getLogger(__name__)

URL_BASE = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"
FONTE = "BCB IF.data (Olinda), relatório 5 (Informações de Capital), conglomerado prudencial"
TTL_SEGUNDOS = 7 * 24 * 3600
DATAS_BASE_TENTADAS = 4
MOTIVO_SEM_INADIMPLENCIA = (
    "inadimplência sem relatório conhecido no IF.data (F2A-16); limitação declarada"
)
MOTIVO_SEM_CONGLOMERADO = (
    "conglomerado prudencial não encontrado no cadastro do IF.data"
)
MOTIVO_SEM_BASILEIA = "índice de Basileia ausente no relatório de capital do IF.data"
MOTIVO_CNPJ_INVALIDO = "CNPJ sem os 8 dígitos da raiz"


@dataclass(frozen=True)
class Capital:
    basileia: float | None
    inadimplencia: float | None
    data_base: str | None
    codinst: str | None
    fonte: str = FONTE
    motivos: dict[str, str] = field(default_factory=dict)


def raiz_do_cnpj(cnpj: str | None) -> str | None:
    digitos = re.sub(r"\D", "", cnpj or "")
    return digitos[:8] if len(digitos) >= 8 else None


def datas_base(data_referencia: date, quantas: int = DATAS_BASE_TENTADAS) -> list[str]:
    """`AnoMes` dos fins de trimestre anteriores à data, do mais recente ao mais antigo."""
    ano, mes = data_referencia.year, data_referencia.month
    trimestre = (mes - 1) // 3  # fins de trimestre já encerrados no ano
    datas = []
    while len(datas) < quantas:
        if trimestre == 0:
            ano, trimestre = ano - 1, 4
        datas.append(f"{ano}{trimestre * 3:02d}")
        trimestre -= 1
    return datas


def caminho_cadastro(ano_mes: str, raiz: str) -> str:
    return (
        f"IfDataCadastro(AnoMes=@AnoMes)?@AnoMes={ano_mes}"
        f"&$filter=CnpjInstituicaoLider eq '{raiz}'&$format=json"
    )


def caminho_capital(ano_mes: str, codinst: str) -> str:
    return (
        "IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)"
        f"?@AnoMes={ano_mes}&@TipoInstituicao=1&@Relatorio='5'"
        f"&$filter=CodInst eq '{codinst}'&$format=json"
    )


def codinst_prudencial(cadastro: list[dict], raiz: str) -> str | None:
    for linha in cadastro:
        if (
            linha.get("CnpjInstituicaoLider") == raiz
            and linha.get("Td") == "C"
            and "PRUDENCIAL" in str(linha.get("NomeInstituicao", "")).upper()
        ):
            return linha.get("CodInst")
    return None


def basileia(linhas: list[dict]) -> float | None:
    """O índice de Basileia do relatório de capital, em razão; `None` sem a coluna ou o número."""
    for linha in linhas:
        if normalizar_descricao(linha.get("NomeColuna")).startswith(
            "indice de basileia"
        ):
            try:
                valor = float(linha.get("Saldo"))
            except (TypeError, ValueError):
                return None
            return valor if math.isfinite(valor) else None
    return None


def ler_capital(
    cnpj: str | None, data_referencia: date, buscar: Callable[[str], list[dict]]
) -> Capital:
    """Basileia da data-base mais recente com dado, entre as `DATAS_BASE_TENTADAS` anteriores."""
    raiz = raiz_do_cnpj(cnpj)
    motivos = {"inadimplencia": MOTIVO_SEM_INADIMPLENCIA}
    if raiz is None:
        return Capital(
            None,
            None,
            None,
            None,
            motivos={**motivos, "basileia": MOTIVO_CNPJ_INVALIDO},
        )
    motivo = MOTIVO_SEM_CONGLOMERADO
    for ano_mes in datas_base(data_referencia):
        codinst = codinst_prudencial(buscar(caminho_cadastro(ano_mes, raiz)), raiz)
        if codinst is None:
            continue
        valor = basileia(buscar(caminho_capital(ano_mes, codinst)))
        if valor is not None:
            return Capital(valor, None, ano_mes, codinst, motivos=motivos)
        motivo = MOTIVO_SEM_BASILEIA
    return Capital(None, None, None, None, motivos={**motivos, "basileia": motivo})


class IFDataProvider:
    def __init__(
        self, cache_dir: str = "data/ifdata", ttl_segundos: int = TTL_SEGUNDOS
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl_segundos = ttl_segundos

    def _buscar(self, caminho: str) -> list[dict]:
        """`value` da resposta OData, com cache por caminho; sem rede, vale o cache antigo."""
        arquivo = (
            self.cache_dir / f"{hashlib.sha256(caminho.encode()).hexdigest()}.json"
        )
        if (
            arquivo.exists()
            and time.time() - arquivo.stat().st_mtime < self.ttl_segundos
        ):
            return json.loads(arquivo.read_text(encoding="utf-8"))
        try:
            resposta = requests.get(f"{URL_BASE}/{caminho}", timeout=60)
            resposta.raise_for_status()
            valor = resposta.json().get("value", [])
        except (requests.RequestException, ValueError) as exc:
            if arquivo.exists():
                logger.warning("IF.data indisponível, usando o cache antigo: %s", exc)
                return json.loads(arquivo.read_text(encoding="utf-8"))
            raise
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporario = arquivo.with_suffix(".tmp")
        temporario.write_text(json.dumps(valor, ensure_ascii=False), encoding="utf-8")
        temporario.replace(arquivo)
        return valor

    def capital(self, cnpj: str | None, data_referencia: date) -> Capital:
        return ler_capital(cnpj, data_referencia, self._buscar)
