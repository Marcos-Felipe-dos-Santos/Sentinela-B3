"""CSV público do Tesouro Transparente, sem seleção de taxa para métodos.

O download observa um arquivo; cache hit devolve apenas esse envelope, sem
validar novamente o CSV. O consumidor deve chamar ``ler_snapshot`` antes de usar
o conteúdo: esse leitor verifica integridade, disponibilidade e formato no
instante da análise. O envelope sozinho não certifica elegibilidade. TTL do cache e idade da referência são conceitos distintos:
a seleção dos vértices e a idade em dias úteis pertencem ao consumidor (F2B-30).
"""

from __future__ import annotations

import csv
import logging
import math
import os
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

import requests

from sentinela.data import proveniencia
from sentinela.data.taxas import ANO_MIN_NTNB
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
    taxa_aplicacao: RateReal | RateNominal | None
    taxa_resgate: RateReal | RateNominal | None
    pu_aplicacao: float | None = None
    pu_resgate: float | None = None
    motivo_aplicacao: str | None = None
    motivo_resgate: str | None = None


@dataclass(frozen=True)
class ArquivoTesouro:
    caminho: Path
    proveniencia: proveniencia.Proveniencia | None
    avisos: tuple[str, ...] = ()

    @property
    def colunas_taxas(self) -> dict[str, str]:
        """Nomes originais preservados no contrato da fonte, junto ao snapshot."""
        return dict(COLUNAS_TAXAS)


def _pu(texto: str | None) -> float | None:
    if texto is None:
        return None
    valor = float(texto.replace(",", "."))
    if not math.isfinite(valor) or valor < 0:
        raise ValueError("PU inválido")
    return valor


def _taxa(texto: str | None) -> float:
    valor = float((texto or "").replace(",", ".")) / 100
    if not math.isfinite(valor) or valor <= -1:
        raise ValueError("taxa inválida: exige valor finito com fator positivo")
    return valor


def ler_csv(
    texto: str, *, as_of: date, validar_aplicacao: bool = True
) -> tuple[TituloTesouro, ...]:
    """Lê percentuais anuais do layout oficial, sem escolher vencimentos.

    Títulos indexados à Selic ou outros indexadores não representam nenhuma das
    três famílias deste contrato. as_of é o dia civil local: referência só com
    data entra depois do seu fim. Linhas posteriores ficam fora da seleção sem
    invalidar o arquivo cumulativo. Não escolhe a cesta/vértices do F2B-30.
    O modo estrito mantém o contrato de validação isolada. O leitor de snapshot
    e o download preservam linhas inválidas com motivo (validar_aplicacao=False),
    para a seleção vetar somente a cesta a que pertencem.
    PU e taxa de aplicação ambos nulos indicam ausência de oferta; a observação
    fica preservada com taxa_aplicacao=None e motivo, não vira taxa zero.
    """
    leitor = csv.DictReader(StringIO(texto.lstrip("\ufeff")), delimiter=";")
    if not _COLUNAS <= set(leitor.fieldnames or ()):
        raise ValueError("colunas obrigatórias ausentes no CSV do Tesouro")
    titulos: dict[tuple[str, date, date], TituloTesouro] = {}
    familia_presente = False
    for linha in leitor:
        nome = linha["Tipo Titulo"]
        if nome not in _TIPOS:
            continue
        familia_presente = True
        tipo, classe = _TIPOS[nome]
        data_base = date(*map(int, (linha["Data Base"] or "").split("/")[::-1]))
        if data_base >= as_of:
            continue
        vencimento = date(*map(int, (linha["Data Vencimento"] or "").split("/")[::-1]))
        pu_aplicacao = None
        taxa_aplicacao = None
        motivo_aplicacao = None
        try:
            pu_aplicacao = _pu(linha.get("PU Compra Manha"))
            valor_aplicacao = _taxa(linha[COLUNAS_TAXAS["taxa_aplicacao"]])
            if valor_aplicacao == 0 and pu_aplicacao == 0:
                motivo_aplicacao = "sem oferta de aplicação na data-base"
            elif valor_aplicacao != 0 and pu_aplicacao == 0:
                raise ValueError("par de aplicação inválido: taxa não zero com PU zero")
            else:
                taxa_aplicacao = classe(valor_aplicacao)
        except ValueError as erro:
            if validar_aplicacao:
                raise
            motivo_aplicacao = str(erro)
        pu_resgate = None
        taxa_resgate = None
        motivo_resgate = None
        try:
            pu_resgate = _pu(linha.get("PU Venda Manha"))
            valor_resgate = _taxa(linha[COLUNAS_TAXAS["taxa_resgate"]])
            if pu_resgate is None:
                motivo_resgate = "par de resgate inválido: PU ausente"
            elif pu_resgate == 0:
                if valor_resgate == 0:
                    motivo_resgate = "sem oferta de resgate na data-base"
                else:
                    motivo_resgate = (
                        "par de resgate inválido: taxa não zero com PU zero"
                    )
            else:
                taxa_resgate = classe(valor_resgate)
        except ValueError as erro:
            motivo_resgate = f"par de resgate inválido: {erro}"
        titulo = TituloTesouro(
            nome,
            tipo,
            vencimento,
            data_base,
            taxa_aplicacao,
            taxa_resgate,
            pu_aplicacao,
            pu_resgate,
            motivo_aplicacao,
            motivo_resgate,
        )
        chave = nome, vencimento, data_base
        if chave in titulos and titulos[chave] != titulo:
            if validar_aplicacao:
                raise ValueError("linhas conflitantes para o mesmo título e data-base")
            anterior = titulos[chave]
            if (
                anterior.taxa_aplicacao,
                anterior.pu_aplicacao,
                anterior.motivo_aplicacao,
            ) != (titulo.taxa_aplicacao, titulo.pu_aplicacao, titulo.motivo_aplicacao):
                titulo = replace(
                    titulo,
                    taxa_aplicacao=None,
                    motivo_aplicacao="linhas conflitantes no par de aplicação",
                )
            if (
                anterior.taxa_resgate,
                anterior.pu_resgate,
                anterior.motivo_resgate,
            ) != (titulo.taxa_resgate, titulo.pu_resgate, titulo.motivo_resgate):
                titulo = replace(
                    titulo,
                    taxa_resgate=None,
                    motivo_resgate="linhas conflitantes no par de resgate",
                )
        titulos[chave] = titulo
    if not familia_presente:
        raise ValueError("CSV sem títulos das famílias previstas")
    return tuple(titulos.values())


@dataclass(frozen=True)
class CestaTesouro:
    """Ofertas na última referência, antes da guarda de idade do F2B-30."""

    data_base: date | None
    titulos: tuple[TituloTesouro, ...]
    proveniencia: dict
    motivo: str | None = None


def selecionar_ofertas(titulos: tuple[TituloTesouro, ...]) -> CestaTesouro:
    """Seleciona a referência antes de excluir sentinelas, sem data alternativa.

    A proveniência derivada não altera o hash do arquivo original. As observações
    sem oferta continuam disponíveis no resultado de ler_csv/ler_snapshot.
    """
    elegiveis = tuple(
        t
        for t in titulos
        if t.tipo in {"NTN-B", "NTN-B Principal"}
        and t.vencimento >= date(ANO_MIN_NTNB, 1, 1)
    )
    base = max((t.data_base for t in elegiveis), default=None)
    referencia = tuple(t for t in elegiveis if t.data_base == base)
    excluidos = sum(
        t.motivo_aplicacao == "sem oferta de aplicação na data-base" for t in referencia
    )
    ofertas = tuple(
        t
        for t in referencia
        if t.motivo_aplicacao != "sem oferta de aplicação na data-base"
    )
    registro = {
        "data_base": base.isoformat() if base else None,
        "excluidos_sem_oferta": excluidos,
        "resgate_ausente": tuple(
            {
                "titulo": t.nome,
                "vencimento": t.vencimento.isoformat(),
                "motivo": t.motivo_resgate,
            }
            for t in referencia
            if t.motivo_resgate
        ),
    }
    motivo = None
    if base is None:
        motivo = "cesta vazia: nenhum título elegível"
    elif not ofertas:
        motivo = "cesta vazia: todos os títulos elegíveis sem oferta"
    elif any(t.taxa_aplicacao is None or t.pu_aplicacao is None for t in ofertas):
        motivo = "cesta inválida: par de aplicação ausente"
    if ofertas:
        invalidos = [t.motivo_aplicacao for t in ofertas if t.motivo_aplicacao]
        if invalidos:
            motivo = invalidos[0]
    return CestaTesouro(base, ofertas, registro, motivo)


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
        arquivo.caminho.read_text(encoding="utf-8-sig"),
        as_of=_dia_local(instante),
        validar_aplicacao=False,
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
        """Observação lógica da requisição = instante explícito do chamador.

        O chamador fornece o instante desta requisição, não uma data histórica
        simulada. Após download íntegro, o mtime recebe esse instante, preservado
        na proveniência. Assim baixar(t) pode ser lido em as_of=t. Cache anterior
        mantém sua coleta original; gravação no disco não é nova observação.
        """
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
            ler_csv(
                conteudo.decode("utf-8-sig"),
                as_of=_dia_local(instante),
                validar_aplicacao=False,
            )
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
        os.utime(caminho, (instante.timestamp(), instante.timestamp()))
        return self._snapshot(caminho)
