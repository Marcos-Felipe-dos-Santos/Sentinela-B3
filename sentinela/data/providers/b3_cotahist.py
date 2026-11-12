"""Séries Históricas da B3 (COTAHIST): cotações diárias, arquivo mensal.

Especificação externa: "Layout do Arquivo — Séries Históricas de Cotações" da B3
(arquivo posicional de 245 caracteres por linha). Só o registro 01 (cotação) é lido;
o 00 (header) e o 99 (trailer) são ignorados. Posições (1-indexadas), conforme o layout:

    TIPREG 1-2 · DATA 3-10 (AAAAMMDD) · CODBDI 11-12 · CODNEG 13-24 · TPMERC 25-27
    ESPECI 40-49 · PREULT 109-121 (fechamento, 11 inteiros + 2 decimais)
    TOTNEG 148-152 · QUATOT 153-170 · VOLTOT 171-188 (16 inteiros + 2 decimais)
    FATCOT 211-217 (1 ou 1000) · CODISI 231-242

O preço é cotado por lote de FATCOT ações: o fechamento devolvido já é por ação.
O parser não lê relógio nem rede; o download recebe o instante atual como parâmetro.
"""

from __future__ import annotations

import json
import logging
import threading
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from cvm_download import baixar_arquivo
from sentinela.data import proveniencia

logger = logging.getLogger(__name__)

URL_MENSAL = (
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_M{mes:02d}{ano}.ZIP"
)
MERCADO_A_VISTA = "010"
_TIPREG_COTACAO = "01"
_TTL_MES_CORRENTE_S = 24 * 3600
_FUSO_B3 = ZoneInfo("America/Sao_Paulo")
# O arquivo do mês só está completo se foi baixado depois do fim do mês, com folga
# para o D-1 e para o feriado de virada.
_MARGEM_FECHAMENTO_S = 3 * 24 * 3600


@dataclass(frozen=True)
class Cotacao:
    data: date
    codigo_negociacao: str
    codbdi: str
    tipo_mercado: str
    especificacao: str
    isin: str
    fechamento: float
    volume_financeiro: float
    quantidade: int
    negocios: int
    fator_cotacao: int


def parsear_linha(linha: str) -> Cotacao | None:
    """Devolve a cotação do registro 01; header, trailer e linha curta viram `None`."""
    if linha[:2] != _TIPREG_COTACAO or len(linha) < 242:
        return None
    fator = int(linha[210:217])
    if fator <= 0:
        raise ValueError(f"fator de cotação inválido: {linha[210:217]!r}")
    return Cotacao(
        data=date(int(linha[2:6]), int(linha[6:8]), int(linha[8:10])),
        codigo_negociacao=linha[12:24].strip(),
        codbdi=linha[10:12],
        tipo_mercado=linha[24:27],
        especificacao=linha[39:49].strip(),
        isin=linha[230:242].strip(),
        fechamento=int(linha[108:121]) / 100 / fator,
        volume_financeiro=int(linha[170:188]) / 100,
        quantidade=int(linha[152:170]),
        negocios=int(linha[147:152]),
        fator_cotacao=fator,
    )


def parsear_linhas(
    linhas: Iterable[str], mercados: tuple[str, ...] = (MERCADO_A_VISTA,)
) -> Iterator[Cotacao]:
    """Cotações dos mercados pedidos (por padrão, só o mercado à vista, 010)."""
    for linha in linhas:
        cotacao = parsear_linha(linha.rstrip("\r\n"))
        if cotacao is not None and cotacao.tipo_mercado in mercados:
            yield cotacao


def ler_zip(
    zip_path: Path, mercados: tuple[str, ...] = (MERCADO_A_VISTA,)
) -> list[Cotacao]:
    """Lê o primeiro arquivo do ZIP mensal da B3. ZIP sem arquivo é ZIP corrompido (F2B-40)."""
    with zipfile.ZipFile(zip_path) as zf:
        nomes = zf.namelist()
        if not nomes:
            raise zipfile.BadZipFile(f"{zip_path}: ZIP sem arquivo")
        nome = nomes[0]
        with zf.open(nome) as f:
            texto = (linha.decode("latin-1") for linha in f)
            return list(parsear_linhas(texto, mercados))


def data_de_geracao(zip_path: Path) -> str | None:
    """Data de geração do arquivo, no header (registro 00, posições 24-31), em AAAA-MM-DD.

    É a data de entrega que o COTAHIST informa. Arquivo ilegível ou header fora do layout
    devolve `None`.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf, zf.open(zf.namelist()[0]) as f:
            header = f.readline().decode("latin-1")
        if header[:2] != "00":
            return None
        return date(
            int(header[23:27]), int(header[27:29]), int(header[29:31])
        ).isoformat()
    except (OSError, zipfile.BadZipFile, IndexError, ValueError):
        return None


def _tem_arquivo(destino: Path) -> bool:
    """O ZIP abre e traz ao menos um arquivo (F2B-40: o vazio não é a cópia definitiva)."""
    try:
        with zipfile.ZipFile(destino) as zf:
            return bool(zf.namelist())
    except (OSError, zipfile.BadZipFile):
        return False


def _completo(destino: Path, ano: int, mes: int) -> bool:
    """O ZIP foi baixado depois do fim do mês (mais a folga) e traz o arquivo: não muda mais."""
    proximo = date(ano + (mes == 12), mes % 12 + 1, 1)
    fim = datetime(proximo.year, proximo.month, 1, tzinfo=_FUSO_B3).timestamp()
    return destino.stat().st_mtime >= fim + _MARGEM_FECHAMENTO_S and _tem_arquivo(
        destino
    )


def baixar_mes(
    ano: int,
    mes: int,
    agora: datetime,
    cache_dir: str | Path = "data/cotahist",
    *,
    permitir_cache_antigo: bool = True,
) -> Path:
    """Baixa o ZIP do mês.

    Uma cópia baixada depois do fim do mês (mais a folga) nunca expira. Qualquer
    outra, inclusive a de um mês já fechado baixada com o mês em curso, expira em um
    dia, porque ainda lhe faltam pregões. `agora` é o instante de referência (sem
    leitura de relógio aqui; é lido no fuso da B3). Se a rede falha e há cópia antiga,
    vale a cópia, com aviso, quando `permitir_cache_antigo` é verdadeiro. O coletor
    de liquidez recusa essa reserva para sinalizar falha de cobertura ao gate.
    """
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    destino = cache / f"COTAHIST_M{mes:02d}{ano}.ZIP"
    url = URL_MENSAL.format(ano=ano, mes=mes)
    if not destino.exists():
        return baixar_arquivo(url, destino)
    local = agora.astimezone(_FUSO_B3)
    if (ano, mes) < (local.year, local.month) and _completo(destino, ano, mes):
        return destino
    if agora.timestamp() - destino.stat().st_mtime < _TTL_MES_CORRENTE_S:
        return destino
    antigo = destino.with_suffix(".old")
    destino.replace(antigo)
    try:
        baixado = baixar_arquivo(url, destino)
    except (requests.RequestException, OSError, zipfile.BadZipFile):
        antigo.replace(destino)
        if not permitir_cache_antigo:
            raise
        logger.warning(
            "COTAHIST %02d/%d: falha no download, usando cópia antiga", mes, ano
        )
        return destino
    except BaseException:
        antigo.replace(destino)
        raise
    antigo.unlink()
    return baixado


# ── Meses recentes (F2A-26) ──────────────────────────────────────────────────

# O mês corrente e os três anteriores: costumam cobrir 63 pregões; nos primeiros dias do
# mês, ou com feriados, a janela pode ficar incompleta (e vem marcada).
MESES_RECENTES = 4
ESPERA_APOS_FALHA_S = 3600  # mês que falhou não é tentado de novo por uma hora
_CACHE_LEITURA_MAX = 6
_cache_leitura: dict[tuple, list[Cotacao]] = {}
_trava_leitura = threading.Lock()
_travas_mes: dict[tuple, threading.Lock] = {}
_falhas: dict[tuple, float] = {}


def meses_ate(ano: int, mes: int, quantos: int) -> list[tuple[int, int]]:
    """Os `quantos` meses até (ano, mês), do mais antigo ao mais recente."""
    meses = []
    for _ in range(quantos):
        meses.append((ano, mes))
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    return meses[::-1]


def ler_zip_em_cache(zip_path: Path) -> list[Cotacao]:
    """`ler_zip` com memória por processo; a chave inclui mtime e tamanho do arquivo."""
    stat = Path(zip_path).stat()
    chave = (str(Path(zip_path).resolve()), stat.st_mtime_ns, stat.st_size)
    with _trava_leitura:
        if chave in _cache_leitura:
            return _cache_leitura[chave]
    cotacoes = ler_zip(zip_path)
    with _trava_leitura:
        _cache_leitura[chave] = cotacoes
        while len(_cache_leitura) > _CACHE_LEITURA_MAX:
            _cache_leitura.pop(next(iter(_cache_leitura)))
    return cotacoes


@dataclass(frozen=True)
class Coleta:
    """Cotações dos meses obtidos e os meses que faltaram ("MM/AAAA")."""

    cotacoes: list[Cotacao]
    meses_ausentes: tuple[str, ...]


class HistoricoRecente:
    """Cotações do mercado à vista dos meses recentes, para a liquidez da cascata."""

    def __init__(
        self, cache_dir: str | Path = "data/cotahist", meses: int = MESES_RECENTES
    ):
        self.cache_dir = cache_dir
        self.meses = meses

    def coletar(self, agora: datetime) -> Coleta:
        """Uma trava por mês cobre download e leitura (a comparação setorial chama a cascata
        em várias threads). Mês que não baixa nem abre vai para `meses_ausentes` e não é
        tentado de novo por `ESPERA_APOS_FALHA_S`, contados a partir de `agora`.
        """
        local = agora.astimezone(_FUSO_B3)
        instante = agora.timestamp()
        cotacoes: list[Cotacao] = []
        ausentes: list[str] = []
        for ano, mes in meses_ate(local.year, local.month, self.meses):
            chave = (str(Path(self.cache_dir).resolve()), ano, mes)
            with _trava_leitura:
                trava = _travas_mes.setdefault(chave, threading.Lock())
            with trava:
                # A falha é consultada já com a trava: quem esperava na fila não repete o
                # download que a thread anterior acabou de ver falhar.
                with _trava_leitura:
                    falha = _falhas.get(chave)
                if falha is not None and instante - falha < ESPERA_APOS_FALHA_S:
                    ausentes.append(f"{mes:02d}/{ano}")
                    continue
                try:
                    cotacoes += ler_zip_em_cache(
                        baixar_mes(
                            ano, mes, agora, self.cache_dir, permitir_cache_antigo=False
                        )
                    )
                except (
                    requests.RequestException,
                    OSError,
                    zipfile.BadZipFile,
                    ValueError,
                ) as exc:
                    with _trava_leitura:
                        _falhas[chave] = instante
                    ausentes.append(f"{mes:02d}/{ano}")
                    logger.warning("COTAHIST %02d/%d indisponível: %s", mes, ano, exc)
                    continue
            with _trava_leitura:
                _falhas.pop(chave, None)
        return Coleta(cotacoes, tuple(ausentes))


# --- Histórico longo no banco único (F3-4a) ---------------------------------------------------

# Campos numéricos do registro 01 como o arquivo os declara (posições 0-indexadas do layout).
_NUMEROS = (
    ("abertura_centavos", 56, 69),
    ("maxima_centavos", 69, 82),
    ("minima_centavos", 82, 95),
    ("media_centavos", 95, 108),
    ("fechamento_centavos", 108, 121),
    ("negocios", 147, 152),
    ("quantidade", 152, 170),
    ("volume_centavos", 170, 188),
    ("fator_cotacao", 210, 217),
)
_CHAVE = ("data", "codigo_negociacao", "tipo_mercado", "codbdi", "prazo")
_DADOS = ("especificacao", "isin", *(nome for nome, _, _ in _NUMEROS))
LIMITE_REGISTROS = 100


class LinhaRecusada(ValueError):
    """Registro 01 ilegível: recusado com o motivo, sem derrubar a carga."""


def registro_bruto(linha: str) -> dict | None:
    """Campos do registro 01 como o arquivo declara, para a tabela `precos`; outro registro, `None`."""
    if linha[:2] != _TIPREG_COTACAO:
        return None
    if len(linha) < 242:
        raise LinhaRecusada(f"registro 01 truncado: {len(linha)} caracteres")
    for nome, inicio, fim in (("DATA", 2, 10), *_NUMEROS):
        campo = linha[inicio:fim]
        if not (campo.isascii() and campo.isdigit()):  # sem sinal, espaço ou `_`
            raise LinhaRecusada(f"campo ilegível: {nome} {campo!r}")
    try:
        dia = date(int(linha[2:6]), int(linha[6:8]), int(linha[8:10]))
    except ValueError as erro:
        raise LinhaRecusada(f"campo ilegível: {erro}") from None
    numeros = {nome: int(linha[inicio:fim]) for nome, inicio, fim in _NUMEROS}
    if numeros["fator_cotacao"] <= 0:
        raise LinhaRecusada(f"fator de cotação inválido: {linha[210:217]!r}")
    return {
        "data": dia.isoformat(),
        "codigo_negociacao": linha[12:24].strip(),
        "tipo_mercado": linha[24:27],
        "codbdi": linha[10:12],
        "prazo": linha[49:52].strip(),
        "especificacao": linha[39:49].strip() or None,
        "isin": linha[230:242].strip() or None,
        **numeros,
    }


def _gravar(conn, registro: dict, prov: tuple, resumo: dict) -> None:
    chave = tuple(registro[c] for c in _CHAVE)
    dados = tuple(registro[c] for c in _DADOS)
    onde = " AND ".join(f"{c} = ?" for c in _CHAVE)
    gravado = conn.execute(
        f"SELECT {', '.join(_DADOS)} FROM precos WHERE {onde}", chave
    ).fetchone()
    if gravado is None:
        colunas = (*_CHAVE, *_DADOS, "fonte", "coleta", "hash_sha256")
        conn.execute(
            f"INSERT INTO precos ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})",
            (*chave, *dados, *prov),
        )
        resumo["inseridas"] += 1
    elif tuple(gravado) == dados:
        resumo["repetidas"] += 1
    else:
        resumo["total_conflitos"] += 1
        if len(resumo["conflitos"]) < LIMITE_REGISTROS:
            resumo["conflitos"].append(dict(zip(_CHAVE, chave, strict=True)))


def carregar(
    conn,
    arquivo: Path | str,
    *,
    fonte: str,
    coleta: str,
    mercados: tuple[str, ...] = (MERCADO_A_VISTA,),
) -> dict:
    """Grava em `precos` o COTAHIST (anual ou mensal, layout oficial), num `SAVEPOINT`.

    Idempotente pelo hash do arquivo (`cargas_cotahist`): o mesmo arquivo não é lido de
    novo. Só inserção: linha já gravada com os mesmos números é repetida; com números
    diferentes, fica a gravada e o caso vai a `conflitos`. Registro ilegível é recusado com
    o motivo, sem derrubar a carga. Só os mercados pedidos (por padrão, o à vista, 010).
    """
    if not fonte or not coleta:
        raise ValueError("fonte e coleta são obrigatórias")
    arquivo = Path(arquivo)
    hash_ = proveniencia.hash_sha256(arquivo)
    if conn.execute(
        "SELECT 1 FROM cargas_cotahist WHERE hash_sha256 = ?", (hash_,)
    ).fetchone():
        return {"hash_sha256": hash_, "ja_carregado": True}
    resumo = {
        "hash_sha256": hash_, "ja_carregado": False, "inseridas": 0, "repetidas": 0,
        "total_conflitos": 0, "conflitos": [], "total_recusadas": 0, "recusadas": [],
    }  # fmt: skip
    conn.execute("SAVEPOINT carga_cotahist")
    try:
        with zipfile.ZipFile(arquivo) as zf:
            nomes = zf.namelist()
            if not nomes:
                raise zipfile.BadZipFile(f"{arquivo}: ZIP sem arquivo")
            with zf.open(nomes[0]) as f:
                for numero, bruta in enumerate(f, start=1):
                    try:
                        registro = registro_bruto(
                            bruta.decode("latin-1").rstrip("\r\n")
                        )
                    except LinhaRecusada as motivo:
                        resumo["total_recusadas"] += 1
                        if len(resumo["recusadas"]) < LIMITE_REGISTROS:
                            resumo["recusadas"].append(
                                {"linha": numero, "motivo": str(motivo)}
                            )
                        continue
                    if registro is not None and registro["tipo_mercado"] in mercados:
                        _gravar(conn, registro, (fonte, coleta, hash_), resumo)
        conn.execute(
            "INSERT INTO cargas_cotahist (hash_sha256, arquivo, data_geracao, fonte, coleta, "
            "resumo_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                hash_,
                arquivo.name,
                data_de_geracao(arquivo),
                fonte,
                coleta,
                json.dumps(resumo),
            ),
        )
    except BaseException:
        if conn.in_transaction:  # o SQLite pode já ter desfeito tudo (disco cheio, E/S)
            conn.execute("ROLLBACK TO carga_cotahist")
            conn.execute("RELEASE carga_cotahist")
        raise
    conn.execute("RELEASE carga_cotahist")
    return resumo


def cotacoes_ate(conn, dia: date, pregoes: int = 63) -> list[Cotacao]:
    """Cotações do mercado à vista nos últimos `pregoes` pregões anteriores ao dia (F3-4a).

    O pregão do próprio dia fica fora (só se completa depois do fechamento): nada de depois
    de D entra. Mesmo formato do `ler_zip`, para `liquidez.metricas` e as regras da 2B. Recebe o
    dia local de D (`date`), não um instante: com `datetime`, o texto ISO deixaria o próprio dia
    passar pela comparação.
    """
    if isinstance(dia, datetime) or not isinstance(dia, date):
        raise TypeError("cotacoes_ate recebe o dia local de D (date), não um instante")
    if pregoes < 1:
        raise ValueError(f"pregoes deve ser positivo: {pregoes}")
    datas = [
        d
        for (d,) in conn.execute(
            "SELECT DISTINCT data FROM precos WHERE tipo_mercado = ? AND data < ? "
            "ORDER BY data DESC LIMIT ?",
            (MERCADO_A_VISTA, dia.isoformat(), pregoes),
        )
    ]
    if not datas:
        return []
    return [
        Cotacao(
            data=date.fromisoformat(d),
            codigo_negociacao=codigo,
            codbdi=codbdi,
            tipo_mercado=mercado,
            especificacao=especificacao or "",
            isin=isin or "",
            fechamento=fechamento / 100 / fator,
            volume_financeiro=volume / 100,
            quantidade=quantidade,
            negocios=negocios,
            fator_cotacao=fator,
        )
        for (
            d, codigo, codbdi, mercado, especificacao, isin, fechamento, volume, quantidade,
            negocios, fator,
        ) in conn.execute(
            "SELECT data, codigo_negociacao, codbdi, tipo_mercado, especificacao, isin, "
            "fechamento_centavos, volume_centavos, quantidade, negocios, fator_cotacao "
            "FROM precos WHERE tipo_mercado = ? AND data >= ? AND data < ? "
            "ORDER BY data, codigo_negociacao, codbdi, prazo",
            (MERCADO_A_VISTA, min(datas), dia.isoformat()),
        )
    ]  # fmt: skip
