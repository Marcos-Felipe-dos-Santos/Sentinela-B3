"""CSV público do Tesouro Transparente, sem seleção de taxa para métodos.

O download observa um arquivo; ``ler_snapshot`` verifica sua disponibilidade no
instante da análise. TTL do cache e idade da referência são conceitos distintos:
a seleção dos vértices e a idade em dias úteis pertencem ao consumidor (F2B-30).
"""

from __future__ import annotations

import csv
import logging
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

import requests

from sentinela.data import proveniencia
from sentinela.domain.units import RateNominal, RateReal

URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
)
COLUNAS_TAXAS = {
    "taxa_aplicacao": "Taxa Compra Manha",
    "taxa_resgate": "Taxa Venda Manha",
}
_COLUNAS = {"Tipo Titulo", "Data Vencimento", "Data Base", *COLUNAS_TAXAS.values()}
_TIPOS = {
    "Tesouro IPCA+": ("NTN-B Principal", RateReal),
    "Tesouro IPCA+ com Juros Semestrais": ("NTN-B", RateReal),
    "Tesouro Prefixado": ("prefixado", RateNominal),
    "Tesouro Prefixado com Juros Semestrais": ("prefixado", RateNominal),
}
_TTL = 86400
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TituloTesouro:
    nome: str
    tipo: str
    vencimento: date
    data_base: date
    taxa_aplicacao: RateReal | RateNominal
    taxa_resgate: RateReal | RateNominal


@dataclass(frozen=True)
class ArquivoTesouro:
    caminho: Path
    proveniencia: proveniencia.Proveniencia | None
    avisos: tuple[str, ...] = ()

    @property
    def colunas_taxas(self) -> dict[str, str]:
        """Nomes originais preservados no contrato da fonte, junto ao snapshot."""
        return dict(COLUNAS_TAXAS)


def _taxa(texto: str | None) -> float:
    valor = float((texto or "").replace(",", ".")) / 100
    if not math.isfinite(valor) or valor <= -1:
        raise ValueError("taxa inválida: exige valor finito com fator positivo")
    return valor


def ler_csv(texto: str, *, as_of: date) -> tuple[TituloTesouro, ...]:
    """Lê percentuais anuais do layout oficial, sem escolher vencimentos.

    Títulos indexados à Selic ou outros indexadores não representam nenhuma das
    três famílias deste contrato. Linhas elegíveis inválidas não são descartadas.
    """
    leitor = csv.DictReader(StringIO(texto.lstrip("\ufeff")), delimiter=";")
    if not _COLUNAS <= set(leitor.fieldnames or ()):
        raise ValueError("colunas obrigatórias ausentes no CSV do Tesouro")
    titulos: dict[tuple[str, date, date], TituloTesouro] = {}
    for linha in leitor:
        nome = linha["Tipo Titulo"]
        if nome not in _TIPOS:
            continue
        tipo, classe = _TIPOS[nome]
        vencimento = date(*map(int, (linha["Data Vencimento"] or "").split("/")[::-1]))
        data_base = date(*map(int, (linha["Data Base"] or "").split("/")[::-1]))
        if data_base > as_of:
            raise ValueError("data-base futura em relação ao as_of")
        titulo = TituloTesouro(
            nome,
            tipo,
            vencimento,
            data_base,
            classe(_taxa(linha[COLUNAS_TAXAS["taxa_aplicacao"]])),
            classe(_taxa(linha[COLUNAS_TAXAS["taxa_resgate"]])),
        )
        chave = nome, vencimento, data_base
        if chave in titulos and titulos[chave] != titulo:
            raise ValueError("linhas conflitantes para o mesmo título e data-base")
        titulos[chave] = titulo
    if not titulos:
        raise ValueError("CSV sem títulos das famílias previstas")
    return tuple(titulos.values())


def _com_fuso(instante: datetime) -> datetime:
    if instante.tzinfo is None or instante.utcoffset() is None:
        raise ValueError("instante exige fuso horário")
    return instante.astimezone(UTC)


def _dia_local(instante: datetime) -> date:
    return instante.astimezone(ZoneInfo("America/Sao_Paulo")).date()


def ler_snapshot(
    arquivo: ArquivoTesouro, *, as_of: datetime
) -> tuple[TituloTesouro, ...]:
    """Aceita apenas arquivo íntegro e observado até o instante informado.

    Coleta prova disponibilidade observada; não substitui a publicação ausente.
    Sem registro íntegro, o conteúdo permanece no disco, mas não é elegível.
    """
    instante = _com_fuso(as_of)
    registro = arquivo.proveniencia
    if registro is None:
        raise ValueError("proveniência ausente")
    coleta = _com_fuso(datetime.fromisoformat(registro.data_coleta))
    if coleta > instante or arquivo.caminho.stat().st_mtime > instante.timestamp():
        raise ValueError("coleta posterior ao as_of")
    if registro.data_entrega is not None and date.fromisoformat(
        registro.data_entrega
    ) >= _dia_local(instante):
        raise ValueError(
            "publicação posterior ao corte: data sem horário exige fim do dia"
        )
    if proveniencia.hash_sha256(arquivo.caminho) != registro.hash_sha256:
        raise ValueError("conteúdo diverge da proveniência")
    return ler_csv(
        arquivo.caminho.read_text(encoding="utf-8-sig"), as_of=_dia_local(instante)
    )


class TesouroProvider:
    def __init__(self, cache_dir: str | Path = "data/tesouro") -> None:
        self.cache_dir = Path(cache_dir)

    def _snapshot(self, caminho: Path, avisos: tuple[str, ...] = ()) -> ArquivoTesouro:
        registro = proveniencia.registrar_sem_falhar(
            caminho,
            URL,
            "Tesouro Direto",
            None,
            motivo=proveniencia.MOTIVO_SEM_ENTREGA_NA_FONTE,
        )
        return ArquivoTesouro(caminho, registro, avisos)

    def baixar(self, instante: datetime) -> ArquivoTesouro:
        """Obtém observação atual; cache antigo continua identificado como antigo."""
        instante = _com_fuso(instante)
        caminho = self.cache_dir / "precotaxatesourodireto.csv"
        if caminho.exists():
            idade = instante.timestamp() - caminho.stat().st_mtime
            if idade < 0:
                raise ValueError("cache com coleta posterior ao instante")
            if idade < _TTL:
                return self._snapshot(caminho)
        try:
            resposta = requests.get(URL, timeout=60)
            resposta.raise_for_status()
            conteudo = resposta.content
            ler_csv(conteudo.decode("utf-8-sig"), as_of=_dia_local(instante))
        except (requests.RequestException, ValueError) as erro:
            if not caminho.exists():
                raise
            aviso = f"fonte indisponível; usando cache de {proveniencia.data_da_coleta(caminho)}: {erro}"
            logger.warning(aviso)
            return self._snapshot(caminho, (aviso,))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            dir=self.cache_dir, suffix=".tmp", delete=False
        ) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
        try:
            temporario.replace(caminho)
        finally:
            temporario.unlink(missing_ok=True)
        return self._snapshot(caminho)
