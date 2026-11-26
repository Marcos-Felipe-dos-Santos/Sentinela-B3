"""Proveniência temporal dos dados coletados (F2A-32; ADR-0003, D16).

Cada arquivo baixado ganha um registro ao lado (`<arquivo>.proveniencia.json`): de quando é
o dado, quando a fonte o entregou, quando foi coletado, de qual documento e versão, de onde
veio e o hash do conteúdo. Sem a data de entrega, o campo fica `None` com o motivo; a data
da coleta nunca ocupa o lugar dela.

A data da coleta é a do arquivo local (mtime, em UTC): o módulo não lê relógio nem rede. O arquivo
baixado pela própria análise de hoje é lido, só nela, no instante das coletas da execução
(`coleta_da_execucao`, BUG-4-10); o arquivo e o registro ao lado guardam o mtime real.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)

DOCUMENTOS = frozenset(
    {
        "DFP",
        "ITR",
        "FCA",
        "Informe Mensal",
        "COTAHIST",
        "Cadastro",
        "Tesouro Direto",
        "IF.data",
    }
)
SUFIXO = ".proveniencia.json"
MOTIVO_ARQUIVO_AGREGADO = (
    "arquivo com vários documentos: a entrega de cada um está no próprio arquivo"
)
MOTIVO_SEM_ENTREGA_NA_FONTE = "a fonte não informa a data de entrega"
MOTIVO_DOCUMENTO_FORA_DO_INDICE = "documento fora do índice de entregas do arquivo"
MOTIVO_ENTREGA_ILEGIVEL = (
    "a fonte informa a data de entrega, mas ela não foi lida no arquivo"
)
_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BLOCO_HASH = 1 << 20


@dataclass
class _Execucao:
    instante: datetime
    as_of: datetime
    baixados: dict[str, str] = field(default_factory=dict)
    # destino → cópia privada dos bytes que esta execução baixou (BUG-4-24)
    copias: dict[str, Path] = field(default_factory=dict)
    identidade: str = field(default_factory=lambda: uuid.uuid4().hex)


_EXECUCAO: ContextVar[_Execucao | None] = ContextVar("coleta_da_execucao", default=None)


@contextmanager
def coleta_da_execucao(
    instante: datetime | None, as_of: datetime | None = None
) -> Iterator[None]:
    """Arquivo baixado dentro do bloco é lido como coletado em `instante` (BUG-4-10).

    Na análise de hoje, o download acontece dentro da análise: o arquivo baixado agora entra no
    instante das coletas da execução, `min(as_of, relógio)` (BUG-3-63). Só esta execução o lê
    assim; o arquivo, o registro ao lado e as outras execuções ficam com o mtime real. Sem
    instante (data passada ou sem as_of), nada muda. O registro lido assim traz também o clique
    (`as_of`, ou o próprio instante) e o `mtime` real do download (F4-A10).
    """
    execucao = None if instante is None else _Execucao(instante, as_of or instante)
    marca = _EXECUCAO.set(execucao)
    try:
        yield
    finally:
        _EXECUCAO.reset(marca)


PASTA_DA_EXECUCAO = ".execucao"
VALIDADE_DAS_COPIAS_S = 24 * 3600


def marcar_baixado(
    caminho: Path,
    sha256: str,
    temporario: Path | None = None,
    *,
    publicar: Callable[[], None] | None = None,
) -> None:
    """Vincula à execução o hash dos bytes que ela própria gravou (BUG-4-16/24).

    A cópia privada usa o temporário validado. Se houver publicação pendente,
    ela precisa terminar antes de o contexto oferecer a cópia ao consumidor.
    """
    destino = Path(caminho)
    execucao = _EXECUCAO.get()
    privado = None
    if execucao is not None and temporario is not None:
        raiz = destino.parent / PASTA_DA_EXECUCAO
        _limpar_copias_antigas(raiz)
        # Um novo conteúdo nunca ocupa o caminho de um ZIP já entregue ao leitor.
        privado = raiz / execucao.identidade / sha256 / destino.name
        privado.parent.mkdir(parents=True, exist_ok=True)
        privado.unlink(missing_ok=True)
        try:
            privado.hardlink_to(temporario)
        except OSError:
            shutil.copy2(temporario, privado)
    if publicar is not None:
        publicar()
    if execucao is not None:
        chave = str(destino.resolve())
        execucao.baixados[chave] = sha256
        if privado is not None:
            execucao.baixados[str(privado.resolve())] = sha256
            execucao.copias[chave] = privado


def caminho_da_execucao(caminho: Path) -> Path:
    """A cópia privada dos bytes que esta execução baixou para `caminho`, ou o próprio caminho."""
    execucao = _EXECUCAO.get()
    if execucao is None:
        return caminho
    return execucao.copias.get(str(Path(caminho).resolve()), caminho)


def _limpar_copias_antigas(raiz: Path) -> None:
    """Remove as cópias privadas de execuções com mais de um dia."""
    try:
        pastas = list(raiz.iterdir())
    except OSError:
        return
    limite = time.time() - VALIDADE_DAS_COPIAS_S
    for pasta in pastas:
        try:
            if pasta.is_dir() and pasta.stat().st_mtime < limite:
                shutil.rmtree(pasta)
        except OSError:
            continue


def _lido_na_execucao(
    caminho: Path, registro: Proveniencia, consumido: str | None = None
) -> Proveniencia:
    """O registro com a coleta da execução, se foi ela que baixou estes mesmos bytes.

    `consumido` é o hash dos bytes que o consumidor leu; se não bater com o marcado por esta
    execução, o arquivo não é tratado como dela (BUG-4-24) e vale a coleta real.
    """
    execucao = _EXECUCAO.get()
    if execucao is None:
        return registro
    marcado = execucao.baixados.get(str(caminho.resolve()))
    if (
        marcado is None
        or marcado != registro.hash_sha256
        or marcado != hash_sha256(caminho)
        or (consumido is not None and consumido != marcado)
    ):
        return registro
    coleta = execucao.instante.astimezone(UTC).isoformat(timespec="seconds")
    return ProvenienciaDaExecucao(
        **{**registro.para_dict(), "data_coleta": min(coleta, registro.data_coleta)},
        as_of_analise=execucao.as_of.isoformat(),
        baixado_em=registro.data_coleta,
    )


@dataclass(frozen=True)
class Proveniencia:
    periodo_referencia: str | None
    data_entrega: str | None
    motivo_sem_entrega: str | None
    data_coleta: str
    documento: str
    versao: str | None
    fonte: str
    hash_sha256: str

    def __post_init__(self) -> None:
        if self.documento not in DOCUMENTOS:
            raise ValueError(f"documento desconhecido: {self.documento!r}")
        if (self.data_entrega is None) == (self.motivo_sem_entrega is None):
            raise ValueError(
                "informe a data de entrega ou o motivo da falta, não os dois"
            )
        if self.data_entrega is not None and not _DATA_ISO.match(self.data_entrega):
            raise ValueError(
                f"data de entrega fora do formato AAAA-MM-DD: {self.data_entrega!r}"
            )
        if not self.data_coleta:
            raise ValueError("data da coleta obrigatória")
        if not self.fonte:
            raise ValueError("fonte obrigatória")
        if not re.fullmatch(r"[0-9a-f]{64}", self.hash_sha256):
            raise ValueError("hash SHA-256 inválido")

    def para_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def de_dict(dados: dict) -> Proveniencia:
        return Proveniencia(**dados)

    def do_documento(
        self, periodo: str | None, versao: str | None, entrega: str | None, motivo: str
    ) -> Proveniencia:
        """O registro de um documento dentro do arquivo: período, versão e entrega dele.

        Sem entrega, vale `motivo`; a coleta, a fonte e o hash continuam os do arquivo.
        """
        return replace(
            self,
            periodo_referencia=periodo,
            versao=versao,
            data_entrega=entrega,
            motivo_sem_entrega=None if entrega is not None else motivo,
        )


@dataclass(frozen=True)
class ProvenienciaDaExecucao(Proveniencia):
    """O registro do arquivo baixado pela análise de hoje, como ela o lê (F4-A10).

    `data_coleta` é a coleta da execução, a que as guardas leem; `as_of_analise` é o clique da
    análise e `baixado_em`, o instante real do download (o mtime). O registro gravado ao lado
    do arquivo continua um `Proveniencia`, sem esses campos.
    """

    as_of_analise: str = ""
    baixado_em: str = ""


def hash_sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with open(caminho, "rb") as f:
        while bloco := f.read(_BLOCO_HASH):
            resumo.update(bloco)
    return resumo.hexdigest()


def data_da_coleta(caminho: Path) -> str:
    """Instante em que o arquivo local foi gravado (mtime), em UTC, ISO 8601."""
    return datetime.fromtimestamp(caminho.stat().st_mtime, tz=UTC).isoformat(
        timespec="seconds"
    )


def caminho_lateral(caminho: Path) -> Path:
    return caminho.with_name(caminho.name + SUFIXO)


def ler_registro(caminho: Path) -> Proveniencia | None:
    """O registro gravado ao lado do arquivo, se ainda corresponde a ele (mesmo mtime e tamanho)."""
    lateral = caminho_lateral(caminho)
    try:
        stat = caminho.stat()
        bruto = json.loads(lateral.read_text(encoding="utf-8"))
        if bruto["mtime_ns"] != stat.st_mtime_ns or bruto["tamanho"] != stat.st_size:
            return None
        return Proveniencia.de_dict(bruto["registro"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def registrar_arquivo(
    caminho: Path,
    fonte: str,
    documento: str,
    periodo: str | None,
    entrega: str | None = None,
    motivo: str = MOTIVO_ARQUIVO_AGREGADO,
    consumido: str | None = None,
) -> Proveniencia:
    """Grava (ou reaproveita) o registro do arquivo baixado e o devolve.

    O registro gravado vale enquanto o arquivo não muda e descreve a mesma fonte e documento;
    download novo gera registro novo, com hash e coleta novos.
    """
    caminho = Path(caminho)
    existente = ler_registro(caminho)
    if (
        existente is not None
        and existente.fonte == fonte
        and existente.documento == documento
        and existente.periodo_referencia == periodo
        and existente.data_entrega == entrega
        and existente.motivo_sem_entrega == (None if entrega is not None else motivo)
    ):
        return _lido_na_execucao(caminho, existente, consumido)
    # A publicação troca o caminho, mas o arquivo aberto mantém a identidade
    # do conteúdo para o mtime e o hash, mesmo com outra publicação concorrente.
    with caminho.open("rb") as origem:
        stat = os.fstat(origem.fileno())
        resumo = hashlib.file_digest(origem, "sha256").hexdigest()
    registro = Proveniencia(
        periodo_referencia=periodo,
        data_entrega=entrega,
        motivo_sem_entrega=None if entrega is not None else motivo,
        data_coleta=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(
            timespec="seconds"
        ),
        documento=documento,
        versao=None,
        fonte=fonte,
        hash_sha256=resumo,
    )
    lateral = caminho_lateral(caminho)
    temporario: Path | None = None
    try:
        # Nome exclusivo por gravação e mesmo diretório para manter a troca atômica.
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=lateral.parent,
            prefix=lateral.name + ".",
            suffix=".tmp",
            delete=False,
        ) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(
                json.dumps(
                    {
                        "mtime_ns": stat.st_mtime_ns,
                        "tamanho": stat.st_size,
                        "registro": registro.para_dict(),
                    },
                    ensure_ascii=False,
                    indent=1,
                )
            )
        temporario.replace(lateral)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)
    return _lido_na_execucao(caminho, registro, consumido)


def registrar_sem_falhar(
    caminho: Path,
    fonte: str,
    documento: str,
    periodo: str | None,
    entrega: str | None = None,
    motivo: str = MOTIVO_ARQUIVO_AGREGADO,
    consumido: str | None = None,
) -> Proveniencia | None:
    """`registrar_arquivo` para quem acabou de baixar: falha de disco no registro vira aviso.

    O download que deu certo não cai por causa do arquivo lateral.
    """
    try:
        return registrar_arquivo(
            caminho, fonte, documento, periodo, entrega, motivo, consumido
        )
    except OSError as erro:
        logger.warning("Proveniência de %s não gravada: %s", caminho, erro)
        return None


def _identidade_da_coluna(coluna: str, valor: object) -> str:
    """Remove só espaços externos do CNPJ; não aproxima identificadores diferentes."""
    texto = str(valor)
    return texto.strip() if coluna in ("CNPJ_CIA", "CNPJ_Fundo_Classe") else texto


def entrega_no_indice(
    linhas: list[dict], documento: dict[str, str | None], coluna: str = "DT_RECEB"
) -> str | None:
    """Data de entrega do documento nas linhas do índice de entregas do arquivo.

    `documento` diz as colunas e os valores que identificam o documento. Na CVM, o índice é
    o CSV `<doc>_cia_aberta_<ano>.csv` do ZIP (DFP, ITR e FCA), com `CNPJ_CIA`, `DT_REFER`,
    `VERSAO` e `DT_RECEB`; no Informe Mensal de FII, o `inf_mensal_fii_geral`, com
    `Data_Entrega`. Data fora do formato AAAA-MM-DD conta como ausente. Documento sem algum
    dos valores que o identificam não é procurado: devolve `None`.
    """
    if any(valor is None for valor in documento.values()):
        return None
    for linha in linhas:
        if all(
            _identidade_da_coluna(k, linha.get(k)) == _identidade_da_coluna(k, v)
            for k, v in documento.items()
        ):
            entrega = str(linha.get(coluna) or "").strip()
            return entrega if _DATA_ISO.match(entrega) else None
    return None
