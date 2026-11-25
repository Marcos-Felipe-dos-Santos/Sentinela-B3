"""BUG-4-10: na análise de hoje, o arquivo baixado pela própria execução cai depois do as_of.

O BUG-3-63 decidiu o instante das coletas da execução, `min(as_of, relógio)`, mas só para as
coletas que o `MarketEngine` carimba. O ZIP da CVM e o do Informe Mensal cujo cache de 7 dias
venceu, e o relatório do IF.data, são baixados durante a análise e registram como coleta o
`mtime` real do arquivo, segundos depois do clique: as guardas (coleta ≤ as_of) rejeitam a
coleta da própria execução (pedido do Marcos de 23/11; achado 4 do Gemini, parte do IF.data).

Arranjo: `MarketEngine.buscar_dados_ticker(as_of=AGORA)` real, com o relógio do motor e do
download 3 s depois do clique. Só as etapas sob teste consultam as fontes; as outras ficam
inertes. O HTTP é simulado no `requests.get`, e o `mtime` dos arquivos já em cache é fixado pelo
teste. Respostas do IF.data no formato OData (chamada de controle do BB); ZIPs sintéticos.
Nenhum valor é dado de mercado.
"""

import io
import json
import os
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
import requests

import cvm_download
import market_engine
from cvm_fii_provider import CVMFIIProvider
from cvm_provider import CVMProvider
from market_engine import MarketEngine
from sentinela.data import proveniencia
from sentinela.data.providers import ifdata
from tests.apoio_ifdata_calendario import calendario_sintetico
from tests.test_cvm_bancos import CADASTRO_BB, CAPITAL_BB
from tests.test_ifdata_inadimplencia import CARTEIRA_BB
from valuation_engine import ValuationEngine

AGORA = datetime(
    2026, 9, 15, 15, 0, tzinfo=UTC
)  # o clique; 06/2026 é a data-base do IF.data
DEPOIS = AGORA + timedelta(seconds=3)  # o relógio enquanto a cascata baixa
OUTRA_EXECUCAO = AGORA + timedelta(
    seconds=30
)  # coleta de outra análise, depois do clique
CNPJ_BANCO = "00.000.000/0001-91"
URL_DFP = (
    "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2026.zip"
)
URL_INFORME = (
    "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_2026.zip"
)
RESPOSTAS_IFDATA = {
    "@AnoMes=202606&$filter=Cnpj": CADASTRO_BB,
    "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='5'": CAPITAL_BB,
    "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='16'": CARTEIRA_BB,
}


class _Relogio(datetime):
    """`datetime` do `market_engine` e do `cvm_download`: o relógio da execução."""

    atual = DEPOIS

    @classmethod
    def now(cls, tz=None):
        return (
            cls.atual.astimezone(tz)
            if tz
            else cls.atual.astimezone().replace(tzinfo=None)
        )


def _zip(nome: str) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as arquivo:
        arquivo.writestr(nome, "CNPJ_CIA;DT_REFER\n")
    return memoria.getvalue()


class _Download:
    """Resposta em partes do `requests.get(..., stream=True)` do `cvm_download`."""

    def __init__(self, corpo: bytes):
        self.corpo = corpo

    def __enter__(self):
        return self

    def __exit__(self, *erro):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield self.corpo


class _OData:
    def __init__(self, valor):
        self.valor = valor

    def raise_for_status(self):
        return None

    def json(self):
        return {"value": self.valor}


def _http(*, ifdata_no_ar=True):
    def get(endereco, *args, **kwargs):
        if endereco.startswith(ifdata.URL_BASE):
            if not ifdata_no_ar:
                raise requests.ConnectionError("IF.data fora do ar no teste")
            for chave, valor in RESPOSTAS_IFDATA.items():
                if chave in endereco:
                    return _OData(valor)
            return _OData([])
        if "dfp_cia_aberta_2026.zip" in endereco:
            return _Download(_zip("dfp_cia_aberta_2026.csv"))
        if "inf_mensal_fii_2026.zip" in endereco:
            return _Download(_zip("inf_mensal_fii_geral_2026.csv"))
        raise requests.ConnectionError(f"fora do ar no teste: {endereco}")

    return get


def _instante(registro: proveniencia.Proveniencia | dict) -> datetime:
    coleta = (
        registro.data_coleta
        if hasattr(registro, "data_coleta")
        else registro["data_coleta"]
    )
    return datetime.fromisoformat(coleta)


def _vencido(caminho, corpo: bytes) -> None:
    """Arquivo de outra execução, de mais de 7 dias antes do clique: o cache venceu."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(corpo)
    antigo = (AGORA - timedelta(days=8)).timestamp()
    os.utime(caminho, (antigo, antigo))


@pytest.fixture
def motor(tmp_path, monkeypatch):
    """O `MarketEngine` real com as etapas fora do teste inertes e o preço já obtido."""
    _Relogio.atual = DEPOIS
    monkeypatch.setattr(market_engine, "datetime", _Relogio)
    monkeypatch.setattr(cvm_download, "datetime", _Relogio)
    monkeypatch.setattr(requests, "get", _http())
    engine = MarketEngine()
    engine.cvm = CVMProvider(cache_dir=str(tmp_path / "cvm"))
    engine.cvm_fii = CVMFIIProvider(cache_dir=str(tmp_path / "cvm_fii"))
    engine.ifdata = ifdata.IFDataProvider(
        str(tmp_path / "ifdata"), calendario=calendario_sintetico()
    )
    coletado: dict = {}

    def referencia(ticker, dados):
        dados.update(
            {
                "classe_ativo": "STOCK",
                "especie": "ON",
                "cnpj": CNPJ_BANCO,
                "cd_cvm": 1023,
            }
        )

    def preco(ticker, dados):
        dados.update({"fonte_preco": "yfinance", "preco_atual": 20.0})

    def cvm(ticker, dados, *, as_of=None):
        dados["modelo_bpp"] = "banco"
        if coletado.get("baixar_dfp"):
            caminho = engine.cvm.baixar_dfp(2026)
            # a leitura das guardas da CVM (`composicao_vigente`, `proveniencia_do_documento`)
            coletado["caminho_dfp"] = caminho
            coletado["dfp"] = proveniencia.registrar_arquivo(
                caminho, URL_DFP, "DFP", "2026"
            )

    def cvm_fii(ticker, dados, *, as_of=None):
        if coletado.get("baixar_informe"):
            caminho = engine.cvm_fii.baixar_informe(2026)
            # a leitura da guarda do Informe (`obter_rendimentos_fii`)
            coletado["informe"] = proveniencia.registrar_arquivo(
                caminho, URL_INFORME, "Informe Mensal", "2026"
            )

    inerte = lambda *args, **kwargs: None
    monkeypatch.setattr(engine, "_aplicar_referencia", referencia)
    monkeypatch.setattr(engine, "_buscar_yfinance", preco)
    monkeypatch.setattr(engine, "_buscar_cvm", cvm)
    monkeypatch.setattr(engine, "_buscar_cvm_fii", cvm_fii)
    for etapa in (
        "_buscar_brapi",
        "_buscar_rendimento_fii",
        "_buscar_proventos_b3",
        "_buscar_liquidez",
        "_buscar_taxa_real",
        "_contexto_janelas",
    ):
        monkeypatch.setattr(engine, etapa, inerte)
    engine.coletado = coletado
    return engine


def test_zip_da_cvm_vencido_baixado_na_execucao_entra_no_as_of(motor):
    _vencido(motor.cvm._cache_path("dfp_2026.zip"), _zip("antigo.csv"))
    motor.coletado["baixar_dfp"] = True

    motor.buscar_dados_ticker("BBAS3", as_of=AGORA)

    assert _instante(motor.coletado["dfp"]) == AGORA


def test_informe_vencido_baixado_na_execucao_entra_no_as_of(motor):
    _vencido(motor.cvm_fii._cache_path("inf_mensal_fii_2026.zip"), _zip("antigo.csv"))
    motor.coletado["baixar_informe"] = True

    motor.buscar_dados_ticker("BBAS3", as_of=AGORA)

    assert _instante(motor.coletado["informe"]) == AGORA


def test_outra_execucao_le_o_mesmo_zip_pelo_instante_real_do_download(motor):
    """O instante da execução não fica no cache: quem lê o arquivo depois vê o download real."""
    _vencido(motor.cvm._cache_path("dfp_2026.zip"), _zip("antigo.csv"))
    motor.coletado["baixar_dfp"] = True

    motor.buscar_dados_ticker("BBAS3", as_of=AGORA)
    fora = proveniencia.registrar_arquivo(
        motor.coletado["caminho_dfp"], URL_DFP, "DFP", "2026"
    )

    assert _instante(motor.coletado["dfp"]) == AGORA
    assert _instante(fora) > DEPOIS


def test_zip_de_outra_execucao_depois_do_as_of_continua_posterior(motor):
    caminho = motor.cvm._cache_path("dfp_2026.zip")
    _vencido(caminho, _zip("dfp_cia_aberta_2026.csv"))
    os.utime(caminho, (OUTRA_EXECUCAO.timestamp(), OUTRA_EXECUCAO.timestamp()))
    motor.coletado["baixar_dfp"] = True

    motor.buscar_dados_ticker("BBAS3", as_of=AGORA)

    assert _instante(motor.coletado["dfp"]) == OUTRA_EXECUCAO


def test_data_passada_mantem_o_instante_real_do_download(motor):
    _Relogio.atual = AGORA + timedelta(days=30)  # a análise de uma data passada
    _vencido(motor.cvm._cache_path("dfp_2026.zip"), _zip("antigo.csv"))
    motor.coletado["baixar_dfp"] = True

    motor.buscar_dados_ticker("BBAS3", as_of=AGORA)

    assert _instante(motor.coletado["dfp"]) > AGORA + timedelta(days=30)


def _bancos(motor):
    dados = motor.buscar_dados_ticker("BBAS3", as_of=AGORA)
    return dados, ValuationEngine().processar(dados, as_of=AGORA)


def test_ifdata_baixado_na_execucao_mostra_a_inadimplencia(motor):
    dados, resultado = _bancos(motor)

    assert all(_instante(r) <= AGORA for r in dados["ifdata"]["proveniencia"])
    assert resultado["inadimplencia_ifdata"].startswith(
        "inadimplência IF.data (carteira ativa inadimplida arrastada ÷ Total Geral"
    )


def test_ifdata_de_outra_execucao_depois_do_as_of_abstem_o_contexto(motor, monkeypatch):
    for caminho, valor in RESPOSTAS_IFDATA.items():
        endereco = next(
            c
            for c in (
                ifdata.caminho_cadastro("202606", ifdata.raiz_do_cnpj(CNPJ_BANCO)),
                ifdata.caminho_capital("202606", "C0080329"),
                ifdata.caminho_carteira("202606", "C0080329"),
            )
            if caminho in c
        )
        arquivo = motor.ifdata._arquivo(endereco)
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps(valor), encoding="utf-8")
        os.utime(arquivo, (OUTRA_EXECUCAO.timestamp(), OUTRA_EXECUCAO.timestamp()))
    monkeypatch.setattr(requests, "get", _http(ifdata_no_ar=False))

    _, resultado = _bancos(motor)

    assert resultado["inadimplencia_ifdata"] == (
        "inadimplência IF.data não informada: coleta não demonstrada até o as_of"
    )


def test_lente_bancos_igual_com_e_sem_a_coleta_do_ifdata(motor, monkeypatch):
    _, com_coleta = _bancos(motor)
    monkeypatch.setattr(requests, "get", _http(ifdata_no_ar=False))
    motor.ifdata = ifdata.IFDataProvider(
        str(motor.cvm.cache_dir / "outro_ifdata"), calendario=calendario_sintetico()
    )

    _, sem_coleta = _bancos(motor)

    assert com_coleta["lentes"] == sem_coleta["lentes"]
