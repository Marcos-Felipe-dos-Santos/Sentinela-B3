"""IF.data do Banco Central: índice de Basileia do conglomerado prudencial (F2A-9, P5).

Especificação externa: o serviço OData IFDATA v1 do BCB (Olinda), conferido no F2A-16
(`docs/decisoes/fontes-fase2a.md`, seção 5):
- `IfDataCadastro(AnoMes)` filtrado por `CnpjInstituicaoLider` (os 8 primeiros dígitos do
  CNPJ) traz `CodInst`, `NomeInstituicao` e `Td`; os relatórios de capital estão no
  conglomerado prudencial (`Td = C`, nome com "PRUDENCIAL"), não na instituição;
- `IfDataValores(AnoMes, TipoInstituicao=1, Relatorio='5')` (Informações de Capital) traz
  linhas `NomeColuna`/`Saldo`; o índice de Basileia é a coluna "Índice de Basileia", em razão
  (0,1513 no BB em 12/2025).

- `IfDataValores(..., Relatorio='16')` (carteira de crédito ativa) traz, por `Conta`, a
  "Inadimplência" (148834, carteira ativa inadimplida arrastada) e o "Total Geral" (24454).
  A inadimplência é a razão das duas, no mesmo conglomerado e data-base do capital, só para
  leitura (F2B-32; ficha bancos 1.1, §2 e §3); conta ausente ou razão fora de [0; 1] fica
  `None`, com o motivo.

A data de referência é parâmetro; nada de rede no import nem `config`.
Download com cache em `data/ifdata/`, com TTL; se a rede falha, vale o cache existente, com
aviso no log.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests

from sentinela.data import proveniencia
from sentinela.data.contas_cvm import normalizar_descricao

logger = logging.getLogger(__name__)

URL_BASE = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"
FONTE = (
    "BCB IF.data (Olinda), relatórios 5 (Informações de Capital) e 16 (carteira de "
    "crédito ativa), conglomerado prudencial"
)
TTL_SEGUNDOS = 7 * 24 * 3600
DATAS_BASE_TENTADAS = 4
MOTIVO_SEM_INADIMPLENCIA = (
    "inadimplência não lida: sem conglomerado ou data-base com capital no IF.data"
)
MOTIVO_CARTEIRA_AUSENTE = (
    "relatório 16 sem as contas 148834 (Inadimplência) e 24454 (Total Geral)"
)
MOTIVO_CARTEIRA_FORA_DO_DOMINIO = (
    "fora do domínio: carteira inadimplida e Total Geral sem razão em [0; 1]"
)
CONTA_INADIMPLENCIA = ("148834", "inadimplencia")
CONTA_TOTAL_GERAL = ("24454", "total geral")
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


@dataclass(frozen=True)
class CalendarioPublicacoes:
    """Datas efetivas já conferidas na fonte oficial, não prazos ou datas-base.

    Sem produtor oficial verificado, o consumidor deixa o calendário ausente.
    A proveniência refere-se ao arquivo que demonstra as datas, não ao relatório16.
    """

    publicacoes: Mapping[str, date]
    proveniencia: proveniencia.Proveniencia


def _motivo_publicacao(
    calendario: CalendarioPublicacoes | None,
    data_base: str,
    corte: date,
    instante: datetime | None,
) -> str | None:
    """Sem hora oficial da divulgação, só admitir após o dia local de publicação."""
    if calendario is None:
        return "calendário oficial de publicação IF.data indisponível"
    if instante is not None:
        corte = min(corte, instante.astimezone(ZoneInfo("America/Sao_Paulo")).date())
    registro = calendario.proveniencia
    host = urlsplit(registro.fonte).hostname or ""
    if registro.documento != "IF.data" or not (
        host == "bcb.gov.br" or host.endswith(".bcb.gov.br")
    ):
        return "calendário de publicação sem fonte oficial IF.data demonstrada"
    try:
        coleta = datetime.fromisoformat(registro.data_coleta)
        if coleta.utcoffset() is None:
            return "coleta do calendário de publicação sem fuso horário"
        futura = (
            coleta > instante
            if instante is not None
            else coleta.astimezone(ZoneInfo("America/Sao_Paulo")).date() > corte
        )
        if futura:
            return "calendário de publicação com coleta posterior ao corte"
    except ValueError:
        return "coleta do calendário de publicação inválida"
    publicada = calendario.publicacoes.get(data_base)
    if type(publicada) is not date:
        return "publicação da data-base não demonstrada no calendário oficial"
    if publicada >= corte:
        return "publicação posterior ao corte ou no mesmo dia sem hora demonstrada"
    if publicada > coleta.astimezone(ZoneInfo("America/Sao_Paulo")).date():
        return "publicação efetiva não demonstrada: calendário coletado antes da data informada"
    return None


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


def caminho_carteira(ano_mes: str, codinst: str) -> str:
    return caminho_capital(ano_mes, codinst).replace(
        "@Relatorio='5'", "@Relatorio='16'"
    )


def _saldo_da_conta(linhas: list[dict], conta: tuple[str, str]) -> object:
    for linha in linhas:
        if (
            str(linha.get("Conta")) == conta[0]
            and normalizar_descricao(linha.get("NomeColuna")) == conta[1]
        ):
            return linha.get("Saldo")
    return None


def inadimplencia(linhas: list[dict]) -> tuple[float | None, str | None]:
    """(razão 148834 ÷ 24454, `None`) ou (`None`, motivo); a razão fica em [0; 1]."""
    brutos = [
        _saldo_da_conta(linhas, c) for c in (CONTA_INADIMPLENCIA, CONTA_TOTAL_GERAL)
    ]
    if any(b is None for b in brutos):
        return None, MOTIVO_CARTEIRA_AUSENTE
    try:
        numerador, total = (float(b) for b in brutos)
    except (TypeError, ValueError):
        return None, MOTIVO_CARTEIRA_FORA_DO_DOMINIO
    if not (math.isfinite(numerador) and math.isfinite(total)) or total <= 0:
        return None, MOTIVO_CARTEIRA_FORA_DO_DOMINIO
    razao = numerador / total
    if not 0 <= razao <= 1:
        return None, MOTIVO_CARTEIRA_FORA_DO_DOMINIO
    return razao, None


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
    cnpj: str | None,
    data_referencia: date,
    buscar: Callable[[str], list[dict]],
    *,
    calendario: CalendarioPublicacoes | None = None,
    as_of: datetime | None = None,
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
            motivo_publicacao = _motivo_publicacao(
                calendario, ano_mes, data_referencia, as_of
            )
            registros_calendario = (
                (calendario.proveniencia.para_dict(),) if calendario is not None else ()
            )
            if motivo_publicacao is not None:
                return Capital(
                    valor,
                    None,
                    ano_mes,
                    codinst,
                    motivos={"inadimplencia": motivo_publicacao},
                    proveniencia=registros_calendario,
                )
            try:
                razao, motivo_carteira = inadimplencia(
                    buscar(caminho_carteira(ano_mes, codinst))
                )
            except (
                requests.RequestException,
                ValueError,
                OSError,
                TypeError,
                AttributeError,
                KeyError,
            ) as exc:
                # BUG-2B-45: a carteira é só leitura; a falha dela não derruba a Basileia.
                razao, motivo_carteira = None, f"relatório 16 indisponível: {exc}"
            motivos = {"inadimplencia": motivo_carteira} if motivo_carteira else {}
            return Capital(
                valor,
                razao,
                ano_mes,
                codinst,
                motivos=motivos,
                proveniencia=registros_calendario,
            )
        motivo = MOTIVO_SEM_BASILEIA
    return Capital(None, None, None, None, motivos={**motivos, "basileia": motivo})


class IFDataProvider:
    def __init__(
        self,
        cache_dir: str = "data/ifdata",
        ttl_segundos: int = TTL_SEGUNDOS,
        *,
        calendario: CalendarioPublicacoes | None = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl_segundos = ttl_segundos
        self.calendario = calendario

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

        resultado = ler_capital(
            cnpj, data_referencia, buscar, calendario=self.calendario, as_of=as_of
        )
        return replace(
            resultado, proveniencia=tuple(registros) + resultado.proveniencia
        )
