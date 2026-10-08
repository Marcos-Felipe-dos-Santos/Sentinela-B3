"""Download dos arquivos oficiais e construção do índice (F2A-1).

Rede só de leitura (CVM e B3), com cache e TTL. Se a rede falha, vale o arquivo ou o
índice já salvo, com aviso. O instante atual entra como parâmetro: o módulo não lê relógio.
"""

from __future__ import annotations

import io
import logging
import os
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from sentinela.data.providers import b3_cotahist
from sentinela.data.referencia.indice import carregar_indice, salvar_indice
from sentinela.data.referencia.montagem import montar_indice
from sentinela.data.referencia.registro import Indice

logger = logging.getLogger(__name__)

URL_CADASTRO = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
URL_FCA = (
    "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{ano}.zip"
)
URL_INFORME = (
    "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ano}.zip"
)
TTL_SEGUNDOS = 7 * 24 * 3600
MESES_COTAHIST = 3


def _baixar_com_ttl(url: str, destino: Path, agora: datetime, eh_zip: bool) -> Path:
    """Baixa com TTL de 7 dias; com a rede fora, vale a cópia antiga, com aviso."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and agora.timestamp() - destino.stat().st_mtime < TTL_SEGUNDOS:
        return destino
    temporario = destino.with_suffix(".tmp")
    try:
        resposta = requests.get(url, timeout=120)
        resposta.raise_for_status()
        temporario.write_bytes(resposta.content)
        if eh_zip:
            with zipfile.ZipFile(temporario) as zf:
                zf.testzip()
        os.replace(temporario, destino)
    except (requests.RequestException, zipfile.BadZipFile):
        temporario.unlink(missing_ok=True)
        if not destino.exists():
            raise
        logger.warning("Falha ao baixar %s; usando a cópia antiga", url)
    return destino


def baixar_csv(url: str, destino: Path, agora: datetime) -> Path:
    return _baixar_com_ttl(url, destino, agora, eh_zip=False)


def baixar_zip(url: str, destino: Path, agora: datetime) -> Path:
    return _baixar_com_ttl(url, destino, agora, eh_zip=True)


def _nao_entregue(erro: Exception) -> bool:
    """Só o HTTP 404 quer dizer que o arquivo do ano ainda não existe; o resto é falha de rede."""
    resposta = getattr(erro, "response", None)
    return (
        isinstance(erro, requests.HTTPError)
        and resposta is not None
        and resposta.status_code == 404
    )


def _ler_csv(origem) -> pd.DataFrame:
    return pd.read_csv(origem, sep=";", encoding="latin-1", dtype=str)


def _ler_do_zip(caminho: Path, nome: str) -> pd.DataFrame:
    with zipfile.ZipFile(caminho) as zf:
        return _ler_csv(io.BytesIO(zf.read(nome)))


def _data_do_arquivo(caminho: Path) -> str:
    """Data em que o arquivo local foi baixado (mtime), em UTC."""
    return datetime.fromtimestamp(caminho.stat().st_mtime, tz=UTC).date().isoformat()


def _zip_do_ano(modelo: str, nome_csv: str, ano: int, cache: Path, agora: datetime):
    """(caminho, DataFrame) do zip do ano, ou `None` se o ano ainda não foi entregue (HTTP 404).

    Qualquer outra falha (rede, zip ilegível, CSV ausente) sobe: o chamador volta para o
    índice salvo.
    """
    destino = cache / f"{Path(modelo).stem.split('{')[0]}{ano}.zip"
    try:
        caminho = baixar_zip(modelo.format(ano=ano), destino, agora)
    except requests.HTTPError as erro:
        if _nao_entregue(erro):
            logger.warning("Arquivo de %d ainda não entregue: %s", ano, modelo)
            return None
        raise
    return caminho, _ler_do_zip(caminho, nome_csv.format(ano=ano))


def _meses_recentes(agora: datetime, quantidade: int) -> list[tuple[int, int]]:
    """Os `quantidade` últimos meses fechados: o laço começa no mês anterior ao de `agora`."""
    ano, mes = agora.year, agora.month
    meses = []
    for _ in range(quantidade):
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
        meses.append((ano, mes))
    return meses


@dataclass
class Fontes:
    fcas: list
    cadastro: pd.DataFrame
    informe: pd.DataFrame
    cotacoes: list
    meta: dict
    data: str


def carregar_fontes(agora: datetime, pasta_dados: Path) -> Fontes:
    """Baixa (ou lê do cache) os arquivos oficiais."""
    cache = pasta_dados / "fontes"
    data = agora.date().isoformat()
    cadastro_csv = baixar_csv(URL_CADASTRO, cache / "cad_cia_aberta.csv", agora)
    cadastro = _ler_csv(cadastro_csv)
    fcas, fonte_fca = [], {}
    for ano in (agora.year - 1, agora.year):
        lido = _zip_do_ano(
            URL_FCA, "fca_cia_aberta_valor_mobiliario_{ano}.csv", ano, cache, agora
        )
        if lido is None:
            continue
        caminho, df = lido
        fcas.append((ano, df))
        fonte_fca[str(ano)] = {
            "arquivo": caminho.name,
            "data": _data_do_arquivo(caminho),
        }
    if not fcas:
        raise FileNotFoundError("Nenhum FCA disponível")
    informes, arquivos_informe, datas_informe = [], [], []
    for ano in (agora.year - 1, agora.year):
        lido = _zip_do_ano(
            URL_INFORME, "inf_mensal_fii_geral_{ano}.csv", ano, cache, agora
        )
        if lido is None:
            continue
        informes.append(lido[1])
        arquivos_informe.append(lido[0].name)
        datas_informe.append(_data_do_arquivo(lido[0]))
    if not informes:
        raise FileNotFoundError("Nenhum Informe Mensal de FII disponível")
    informe = pd.concat(informes, ignore_index=True)
    cotacoes, arquivos_cotahist, datas_cotahist = [], [], []
    for ano, mes in _meses_recentes(agora, MESES_COTAHIST):
        try:
            caminho = b3_cotahist.baixar_mes(ano, mes, agora, pasta_dados / "cotahist")
        except requests.HTTPError as erro:
            if not _nao_entregue(erro):
                raise
            logger.warning("COTAHIST %02d/%d ainda não publicado", mes, ano)
            continue
        cotacoes += b3_cotahist.ler_zip(caminho)
        arquivos_cotahist.append(caminho.name)
        datas_cotahist.append(_data_do_arquivo(caminho))
    if not cotacoes:
        raise FileNotFoundError("Nenhum COTAHIST disponível")
    fontes = {
        "fca": fonte_fca,
        "cadastro": {
            "arquivo": cadastro_csv.name,
            "data": _data_do_arquivo(cadastro_csv),
        },
        "informe_fii": {
            "arquivo": ", ".join(arquivos_informe),
            "data": max(datas_informe),
        },
        "cotahist": {
            "arquivo": ", ".join(arquivos_cotahist),
            "data": max(datas_cotahist),
        },
    }
    return Fontes(fcas, cadastro, informe, cotacoes, fontes, data)


def construir_indice(agora: datetime, pasta_dados: Path) -> Indice:
    """Baixa as fontes e monta o índice (não grava)."""
    f = carregar_fontes(agora, pasta_dados)
    return montar_indice(f.fcas, f.cadastro, f.informe, f.cotacoes, f.meta, f.data)


def obter_indice(agora: datetime, pasta_dados: Path) -> Indice:
    """Índice salvo, se ainda dentro do TTL; senão reconstrói; se a rede falha, vale o salvo."""
    pasta = pasta_dados / "referencia"
    caminho = pasta / "indice.json"
    try:
        salvo = carregar_indice(pasta)
    except (ValueError, KeyError, TypeError):
        logger.warning("Índice salvo ilegível em %s; será reconstruído", caminho)
        salvo = None
    if salvo is not None and agora.timestamp() - caminho.stat().st_mtime < TTL_SEGUNDOS:
        return salvo
    try:
        novo = construir_indice(agora, pasta_dados)
    except (
        requests.RequestException,
        OSError,
        FileNotFoundError,
        zipfile.BadZipFile,
        KeyError,
        ValueError,
    ):
        if salvo is None:
            raise
        logger.warning(
            "Falha ao reconstruir o índice; usando o salvo de %s", salvo.gerado_em
        )
        return salvo
    salvar_indice(novo, pasta)
    return novo
