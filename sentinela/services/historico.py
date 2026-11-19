"""Cascata numa data passada pelo banco único (F3-3d, decisões 1 e 15 de 09/11, DD-62).

`MotorHistorico` é a cascata atual (`MarketEngine`) com as fontes trocadas pelas leituras
ponto-no-tempo do banco, sem nenhuma consulta corrente:

- índice de referência: o índice em D (`universo.indice_em`, F3-5);
- demonstrações da CVM: os ZIPs oficiais remontados como existiam em D (`remontagem`), lidos
  pelo `CVMProvider` de sempre; Informe de FII, idem, pelo `CVMFIIProvider`;
- preço: o fechamento bruto do último pregão antes do dia de D no COTAHIST guardado
  (`precos`, F3-4a); histórico pela série ajustada do banco (`serie_ajustada`, F3-4c);
- liquidez: as cotações dos 63 pregões antes de D (`cotacoes_ate`);
- taxa real: o `series_macro` deste banco em D (`macro.registro_do_banco`, F3-1c);
- IPCA de fim de exercício das janelas: o mesmo `series_macro`, pela data de divulgação do
  IBGE (`macro.ipca_serie_do_banco`, F3-8f).

O bloco do Bazin é o da cascata, com a relação da coleta escolhida pelo leitor ponto-no-tempo
(`b3_proventos.relacao_ate`) e o fechamento do COTAHIST antes de D (F3-8h); o `dy` do FII é o
do Informe guardado, com as versões entregues antes de D (F3-8g). Ficam de fora, com o
motivo, as fontes que só existem como consulta corrente: yfinance, brapi, IF.data, o cache de
fundamentos e o complemento de fundos da B3. Nada muda nos métodos, fórmulas ou
parâmetros (R2): o motor de valuation recebe os mesmos campos da cascata.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from cvm_fii_provider import CVMFIIProvider
from cvm_provider import CVMProvider
from market_engine import MarketEngine
from sentinela.data import liquidez, proventos_b3, rendimento_fii
from sentinela.data.pit import leitura, remontagem, serie_ajustada
from sentinela.data.providers import b3_cotahist, b3_proventos, macro
from sentinela.data.referencia import universo
from sentinela.services.asset_classifier import AssetClassifier

FONTE_PRECO = "B3 COTAHIST (banco único)"
PREGOES_DO_HISTORICO = 300
MOTIVO_SEM_PRECO = "sem pregão do código antes da data no COTAHIST guardado"
MOTIVO_FONTE_CORRENTE = "fonte só disponível como consulta corrente; desligada na data passada"
RISCO_IFDATA = f"Basileia e inadimplência sem fonte histórica (IF.data: {MOTIVO_FONTE_CORRENTE})"
_FUSO = ZoneInfo("America/Sao_Paulo")


_REMONTAGENS: ContextVar[dict | None] = ContextVar("remontagens", default=None)


@contextmanager
def remontagens_compartilhadas() -> Iterator[dict]:
    """Dentro do bloco, os motores sem `remontagens` próprio dividem as remontagens (F3-8e).

    O ZIP de (documento, ano) em D depende só do banco, de D, do modo e da pasta, que estão na
    chave; quem abre o bloco garante que o banco não muda as tabelas da CVM dentro dele.
    """
    memoria: dict = {}
    marca = _REMONTAGENS.set(memoria)
    try:
        yield memoria
    finally:
        _REMONTAGENS.reset(marca)


def _memoria(remontagens: dict | None) -> dict:
    if remontagens is not None:
        return remontagens
    compartilhada = _REMONTAGENS.get()
    return {} if compartilhada is None else compartilhada


def dia_local(as_of: datetime) -> date:
    if as_of.utcoffset() is None:
        raise ValueError("as_of exige fuso horário")
    return as_of.astimezone(_FUSO).date()


class CVMProviderEm(CVMProvider):
    """`CVMProvider` lendo os ZIPs remontados do banco em D, sem rede."""

    por_publicacao = True  # decisão 40: a entrega prova a disponibilidade, não a coleta

    def __init__(
        self,
        conn: sqlite3.Connection,
        as_of: datetime,
        diretorio: Path,
        modo: str,
        remontagens: dict | None = None,
    ):
        super().__init__(cache_dir=str(diretorio / "cache"))
        self._conn, self._as_of, self._dir, self._modo = conn, as_of, diretorio, modo
        self.motivos: dict = {}
        # com `remontagens` compartilhado, análises do mesmo dia remontam uma vez (F3-8e)
        self._zips = _memoria(remontagens)

    def recorte_em(self, as_of: datetime) -> CVMProvider:
        return self  # já é o que existia em D

    def _zip(self, documento: str, ano: int) -> Path:
        chave = ("cia", documento, ano, self._as_of, self._modo, self._dir)
        if chave not in self._zips:
            self._zips[chave] = remontagem.zip_cia_em(
                self._conn, documento, ano, self._as_of, self._dir / documento.lower(),
                modo=self._modo,
            )  # fmt: skip
        caminho, motivos = self._zips[chave]
        self.motivos.update(motivos)
        return caminho

    def baixar_dfp(self, ano: int) -> Path:
        return self._zip("DFP", ano)

    def baixar_itr(self, ano: int) -> Path:
        return self._zip("ITR", ano)


class CVMFIIProviderEm(CVMFIIProvider):
    """`CVMFIIProvider` lendo o Informe remontado do banco em D, sem rede."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        as_of: datetime,
        diretorio: Path,
        modo: str,
        remontagens: dict | None = None,
    ):
        super().__init__(cache_dir=str(diretorio / "cache_fii"))
        self._conn, self._as_of, self._dir, self._modo = conn, as_of, diretorio, modo
        self._zips = _memoria(remontagens)

    def baixar_informe(self, ano: int) -> Path:
        chave = ("fii", "INFORME", ano, self._as_of, self._modo, self._dir)
        if chave not in self._zips:
            self._zips[chave] = remontagem.zip_informe_em(
                self._conn, ano, self._as_of, self._dir / "fii", modo=self._modo
            )
        return self._zips[chave]


class ReferenciaEm:
    """Índice de referência em D (`universo.indice_em`), com a mesma interface da carga atual."""

    def __init__(self, conn: sqlite3.Connection, dia: date, cadastro: pd.DataFrame):
        self._conn, self._dia, self._cadastro = conn, dia, cadastro
        self._indice = None

    def indice(self, _instante: datetime):
        if self._indice is None:
            self._indice = universo.indice_em(self._conn, self._dia, self._cadastro)
        return self._indice


class MotorHistorico(MarketEngine):
    """A cascata em D pelo banco único; as fontes correntes não são consultadas."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        as_of: datetime,
        diretorio: Path,
        cadastro: pd.DataFrame,
        *,
        modo: str = leitura.ESTRITO,
        remontagens: dict | None = None,
    ):
        # Sem `super().__init__`: ele cria os provedores correntes (rede, cache em disco).
        if modo not in leitura.MODOS:
            raise ValueError(f"modo desconhecido: {modo!r}")
        self.conn, self.as_of, self.modo = conn, as_of, modo
        self.dia = dia_local(as_of)
        self.cvm = CVMProviderEm(conn, as_of, diretorio, modo, remontagens)
        self.cvm_fii = CVMFIIProviderEm(conn, as_of, diretorio, modo, remontagens)
        self.referencia = ReferenciaEm(conn, self.dia, cadastro)
        self.asset_classifier = AssetClassifier()
        self.brapi = None
        self.ifdata = None
        self.cotahist = None
        self.b3_proventos = None
        self.b3_fundos = None
        self.database = None

    def _data_passada(self, as_of: datetime | None) -> bool:
        """O serviço só monta este motor para D anterior ao seu `hoje`; o relógio do sistema
        não decide a disponibilidade da análise (BUG-3-58)."""
        return as_of is not None

    def buscar_dados_ticker_em(self, ticker: str, as_of: datetime) -> dict[str, Any] | None:
        if dia_local(as_of) != self.dia:
            raise ValueError("o motor histórico só responde pela data em que foi montado")
        dados = self.buscar_dados_ticker(ticker, as_of=as_of)
        if dados is not None:
            dados["modo_historico"] = self.modo
            if self.modo == leitura.EXPLORATORIO:
                dados.setdefault("riscos_dados", []).append(leitura.AVISO_EXPLORATORIO)
            for (cnpj, dt_refer), motivo in sorted(self.cvm.motivos.items()):
                if cnpj == dados.get("cnpj"):
                    dados.setdefault("riscos_dados", []).append(
                        f"documento da CVM de {dt_refer} fora da leitura: {motivo}"
                    )
        return dados

    # 1. preço e histórico: o COTAHIST guardado, no lugar do yfinance.
    def _buscar_yfinance(self, ticker: str, dados: dict[str, Any]) -> bool:
        cotacoes = b3_cotahist.cotacoes_do_codigo_ate(
            self.conn, ticker, self.dia, PREGOES_DO_HISTORICO
        )
        if not cotacoes:
            dados.setdefault("riscos_dados", []).append(f"{MOTIVO_SEM_PRECO} ({ticker})")
            return False
        ultima = max(cotacoes, key=lambda c: c.data)
        pregao = b3_cotahist.ultimo_pregao_antes(self.conn, self.dia)
        if pregao is not None and ultima.data < pregao:
            dados.setdefault("riscos_dados", []).append(
                f"último negócio de {ticker} em {ultima.data.isoformat()}, antes do último "
                f"pregão anterior à data ({pregao.isoformat()})"
            )
        dados["preco_atual"] = ultima.fechamento
        dados["fonte_preco"] = FONTE_PRECO
        dados["data_preco"] = ultima.data.isoformat()
        dados["fechamentos_brutos"] = {
            c.data.isoformat(): c.fechamento for c in sorted(cotacoes, key=lambda c: c.data)
        }
        emissor = ticker[:4]
        ajustada = serie_ajustada.serie_do_banco(
            self.conn, ticker, emissor, self.dia, PREGOES_DO_HISTORICO
        )
        serie = ajustada.get("serie") or []
        bloqueados = [i for i, p in enumerate(serie) if p.get("ajustado") is None]
        if bloqueados:  # só o trecho depois do último intervalo sem ajuste possível
            serie = serie[bloqueados[-1] + 1 :]
        dados["historico"] = (
            pd.DataFrame(
                {"Close": [p["ajustado"] for p in serie]},
                index=pd.to_datetime([p["data"] for p in serie]),
            )
            if serie
            else pd.DataFrame()
        )
        if ajustada.get("motivo"):
            dados.setdefault("riscos_dados", []).append(
                f"série ajustada indisponível: {ajustada['motivo']}"
            )
        return True

    def _buscar_brapi(self, ticker: str, dados: dict[str, Any]) -> bool:
        return False

    def _buscar_ifdata(self, dados: dict[str, Any], *, as_of: datetime) -> None:
        if dados.get("modelo_bpp") == "banco":
            dados.setdefault("riscos_dados", []).append(RISCO_IFDATA)

    def _buscar_proventos_b3(self, ticker, dados, *, as_of=None) -> None:
        """O bloco do Bazin da cascata pelo banco e pelo preço do COTAHIST de D (F3-8h).

        O escopo é o da cascata corrente. No lugar do yfinance, os fechamentos brutos do
        COTAHIST guardado (`_buscar_yfinance` deste motor); no lugar da coleta corrente, a
        relação da coleta escolhida pelo leitor ponto-no-tempo (`b3_proventos.relacao_ate`); os
        pregões da data ex, do banco. A conta, com o as_of, é do motor (`proventos_b3.entradas`).
        """
        if dados.get("classe_ativo") not in ("STOCK", "UNIT"):
            return
        modelo = dados.get("modelo_bpp")
        if modelo != "empresa":
            dados["proventos_b3"] = {
                "abstencao": f"fora do escopo do Bazin: modelo {modelo}"
                if modelo
                else "modelo empresa não demonstrado no BPP consolidado"
            }
            return
        fechamentos = dados.get("fechamentos_brutos")
        if (
            dados.get("fonte_preco") != FONTE_PRECO
            or not isinstance(fechamentos, dict)
            or not fechamentos
        ):
            dados["proventos_b3"] = {"abstencao": proventos_b3.MOTIVO_PRECO}
            return
        anteriores = [
            date.fromisoformat(d) for d in fechamentos if date.fromisoformat(d) < self.dia
        ]
        if not anteriores:
            dados["proventos_b3"] = {"abstencao": proventos_b3.MOTIVO_PRECO_NAO_ENCERRADO}
            return
        relacao = b3_proventos.relacao_ate(self.conn, ticker[:4], self.dia, ticker=ticker)
        if "abstencao" in relacao:
            dados["proventos_b3"] = {"abstencao": relacao["abstencao"]}
            return
        pregoes = b3_proventos.pregoes_da_data_ex(
            self.conn, relacao["registros"], max(anteriores)
        )
        dados["proventos_b3"] = {
            **relacao,
            "fechamentos": fechamentos,
            "pregoes": pregoes,
            "conferencia_yfinance": None,
        }

    def _buscar_liquidez(self, ticker: str, dados: dict[str, Any]) -> None:
        """As regras da cascata corrente sobre os pregões guardados antes de D."""
        cotacoes = b3_cotahist.cotacoes_ate(self.conn, self.dia)
        resultado = liquidez.metricas(cotacoes, ticker)
        dados["liquidez"] = (
            {"abstencao": resultado.motivo, "meses_ausentes": []}
            if isinstance(resultado, liquidez.Abstencao)
            else resultado
        )
        if (
            isinstance(resultado, liquidez.Abstencao)
            and resultado.motivo == liquidez.MOTIVO_TICKER_AUSENTE
        ):
            # a ausência só vale como zero se o banco cobrir a janela, como na corrente
            pregoes = len({c.data for c in cotacoes})
            dados["liquidez"]["incompleta"] = pregoes < max(liquidez.JANELAS)

    def _buscar_rendimento_fii(self, ticker, dados, *, as_of=None) -> None:
        super()._buscar_rendimento_fii(ticker, dados, as_of=as_of)
        if self._is_fii_ticker(ticker, dados) and dados.get("cnpj"):
            dados["b3_fundo"] = {
                "abstencao": f"complemento da B3 do fundo: {MOTIVO_FONTE_CORRENTE}"
            }
            self._dy_do_informe(dados)

    def _dy_do_informe(self, dados: dict[str, Any]) -> None:
        """O `dy` do FII pelo Informe guardado, no lugar do yfinance e da brapi (F3-8g).

        A conta é a do `rendimento_fii.rendimento_12_meses` (ficha FII 1.3), com as versões
        entregues antes do dia de D e o fechamento do COTAHIST antes de D; sem prova, o campo
        fica de fora e o motivo vai a `riscos_dados`.
        """
        informe = dados.get("informe_fii")
        if not isinstance(informe, dict) or "registros" not in informe:
            return  # a abstenção do Informe já está no bloco e nos riscos
        if dados.get("fonte_preco") != FONTE_PRECO:
            medida = rendimento_fii.Abstencao(rendimento_fii.MOTIVO_PRECO)
        else:
            medida = rendimento_fii.dy_entregue_ate(
                informe["registros"], dados.get("preco_atual"), self.dia
            )
        if isinstance(medida, rendimento_fii.Abstencao):
            dados.setdefault("riscos_dados", []).append(
                f"DY do FII pelo Informe: {medida.motivo}"
            )
            return
        dados["dy"] = medida["dy"]
        dados.setdefault("proveniencia", {})["dy"] = medida["conversao"]
        self._record_field_sources(dados, ("dy",), "CVM")

    def _contexto_janelas(self, dados, instante, *, coletado_em=None) -> None:
        exercicios = (dados.get("serie_cvm") or {}).get("exercicios") or []
        if len(exercicios) == 5 and not dados.get("ipca_serie"):  # a condição da cascata
            # F3-8f: o IPCA divulgado até D no `series_macro`, nunca o SIDRA corrente
            try:
                dados["ipca_serie"] = macro.ipca_serie_do_banco(self.conn, exercicios, instante)
            except sqlite3.Error as erro:
                dados["ipca_serie"] = {"abstencao": f"series_macro indisponível: {erro}"}
        super()._contexto_janelas(dados, instante, coletado_em=coletado_em)

    def _buscar_taxa_real(self, dados: dict[str, Any], *, as_of: datetime | None = None) -> None:
        """Taxa real em D pelo `series_macro` deste banco (F3-1c), não pela fonte corrente."""
        try:
            dados["taxa_real"] = macro.registro_do_banco(
                self.conn, self.as_of, dados.get("janela_contabil_cvm")
            )
        except sqlite3.Error as erro:
            dados["taxa_real"] = {"abstencao": f"series_macro indisponível: {erro}"}


CADASTRO = Path("data/fontes/cad_cia_aberta.csv")
DIRETORIO = Path("data/cache/historico")


def motor_do_banco(conn: sqlite3.Connection, as_of: datetime) -> MotorHistorico:
    """O motor da produção: banco único aberto pelo serviço e o cadastro da CVM guardado.

    O cadastro é o único que a CVM publica (o atual, L1); o índice em D usa dele a identidade
    e as datas de registro e cancelamento. Os ZIPs remontados ficam em `data/cache/historico/`.
    """
    cadastro = (
        pd.read_csv(CADASTRO, sep=";", encoding="latin-1", dtype=str)
        if CADASTRO.is_file()
        else pd.DataFrame(columns=["CNPJ_CIA", "DENOM_SOCIAL", "SIT", "CD_CVM",
                                   "SETOR_ATIV", "CONTROLE_ACIONARIO"])
    )  # fmt: skip
    return MotorHistorico(conn, as_of, DIRETORIO / dia_local(as_of).isoformat(), cadastro)
