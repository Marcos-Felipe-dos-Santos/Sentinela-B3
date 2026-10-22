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
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from pathlib import Path

import requests

from sentinela.data import proveniencia
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
    proveniencia: tuple[dict, ...] = ()


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

    def _arquivo(self, caminho: str) -> Path:
        return self.cache_dir / f"{hashlib.sha256(caminho.encode()).hexdigest()}.json"

    def _registrar(self, caminho: str) -> proveniencia.Proveniencia | None:
        arquivo = self._arquivo(caminho)
        if not arquivo.exists():
            return None
        periodo = re.search(r"@AnoMes=(\d{6})", caminho)
        return proveniencia.registrar_sem_falhar(
            arquivo,
            f"{URL_BASE}/{caminho}",
            "IF.data",
            periodo.group(1) if periodo else None,
            motivo=proveniencia.MOTIVO_SEM_ENTREGA_NA_FONTE,
        )

    def _buscar(self, caminho: str, *, as_of: datetime) -> list[dict]:
        """Cache por caminho; validade contra `as_of` explícito, com fuso, nunca relógio.

        Coleta é o mtime real do arquivo local; `as_of` não é gravado como coleta.
        Resposta vazia não é persistida. Na falha da rede, a cópia antiga continua
        disponível com aviso e com a proveniência original.
        """
        if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
            raise ValueError("as_of deve ser datetime com fuso")
        arquivo = self._arquivo(caminho)
        if arquivo.exists():
            idade = as_of.timestamp() - arquivo.stat().st_mtime
            if 0 <= idade < self.ttl_segundos:
                valor = json.loads(arquivo.read_text(encoding="utf-8"))
                if valor:
                    self._registrar(caminho)
                    return valor
        try:
            resposta = requests.get(f"{URL_BASE}/{caminho}", timeout=60)
            resposta.raise_for_status()
            valor = resposta.json().get("value", [])
        except (requests.RequestException, ValueError) as exc:
            if arquivo.exists():
                logger.warning("IF.data indisponível, usando o cache antigo: %s", exc)
                self._registrar(caminho)
                return json.loads(arquivo.read_text(encoding="utf-8"))
            raise
        if valor:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            temporario = arquivo.with_suffix(".tmp")
            temporario.write_text(
                json.dumps(valor, ensure_ascii=False), encoding="utf-8"
            )
            temporario.replace(arquivo)
            self._registrar(caminho)
        return valor

    def capital(
        self, cnpj: str | None, data_referencia: date, *, as_of: datetime
    ) -> Capital:
        """Capital e proveniência de cada arquivo efetivamente consultado."""
        if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
            raise ValueError("as_of deve ser datetime com fuso")
        registros = []

        def buscar(caminho: str) -> list[dict]:
            valor = self._buscar(caminho, as_of=as_of)
            registro = self._registrar(caminho) if valor else None
            if registro is not None:
                registros.append(registro.para_dict())
            return valor

        resultado = ler_capital(cnpj, data_referencia, buscar)
        return replace(resultado, proveniencia=tuple(registros))
