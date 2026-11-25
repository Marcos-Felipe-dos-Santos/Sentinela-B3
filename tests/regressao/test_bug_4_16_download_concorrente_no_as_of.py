"""BUG-4-16: download concorrente pode atribuir à execução um arquivo publicado por outra.

O F4-A09 (DD-97) marcava o arquivo baixado pela execução pelo `stat` lido depois de publicá-lo,
e o download da CVM e o do IF.data usavam um temporário de nome fixo por destino. Se outra
execução B publicasse o mesmo destino no intervalo, a execução A registrava a identidade do
arquivo de B e o aceitava com a hora de A; e dois downloads do mesmo destino dividiam o
temporário (bloqueador 2 da auditoria R2 do bloco 0, `docs/loop/auditorias/bloco0-codex.md`).

Arranjo: A roda dentro de `coleta_da_execucao`; B roda num contexto vazio (outra execução),
intercalado com A por dublês de `os.replace`/`Path.replace` e do corpo da resposta. Bytes
distintos em A e B; ZIPs e respostas OData sintéticos.
"""

import contextvars
import io
import os
import pathlib
import zipfile
from datetime import UTC, datetime, timedelta

import requests

import cvm_download
from sentinela.data import proveniencia
from sentinela.data.providers import ifdata
from tests.apoio_ifdata_calendario import calendario_sintetico

AS_OF = datetime(2026, 9, 15, 15, 0, tzinfo=UTC)
URL = "https://dados.cvm.gov.br/teste/dfp_cia_aberta_2026.zip"


def _zip(conteudo: str) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as arquivo:
        arquivo.writestr("dados.csv", conteudo)
    return memoria.getvalue()


class _Resposta:
    def __init__(self, corpo: bytes, durante=None):
        self.corpo, self.durante = corpo, durante

    def __enter__(self):
        return self

    def __exit__(self, *erro):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        meio = len(self.corpo) // 2
        yield self.corpo[:meio]
        if self.durante is not None:
            self.durante()
        yield self.corpo[meio:]


def _outra_execucao(funcao, *args):
    """Roda `funcao` como outra análise: contexto novo, sem a coleta da execução A."""
    return contextvars.Context().run(funcao, *args)


def _registro(caminho):
    return proveniencia.registrar_arquivo(caminho, URL, "DFP", "2026")


def test_cvm_publicado_por_outra_execucao_antes_da_marcacao_nao_entra_no_as_of(
    tmp_path, monkeypatch
):
    destino = tmp_path / "dfp_2026.zip"
    corpos = iter([_zip("A"), _zip("B")])
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(next(corpos)))
    replace_real = os.replace
    feito = []

    def replace_e_b_publica(origem, alvo):
        replace_real(origem, alvo)
        if not feito:
            feito.append(True)
            _outra_execucao(cvm_download.baixar_arquivo, URL, destino)

    monkeypatch.setattr(cvm_download.os, "replace", replace_e_b_publica)
    monkeypatch.setattr(
        cvm_download, "is_fresh", lambda caminho: False
    )  # B baixa de novo
    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        cvm_download.baixar_arquivo(URL, destino)
        registro = _registro(destino)

    assert type(registro) is proveniencia.Proveniencia
    assert datetime.fromisoformat(registro.data_coleta) > AS_OF


def test_cvm_downloads_do_mesmo_destino_nao_dividem_o_temporario(tmp_path, monkeypatch):
    destino = tmp_path / "dfp_2026.zip"
    corpo_a, corpo_b = _zip("A" * 64), _zip("B" * 64)

    def b_no_meio():
        monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(corpo_b))
        _outra_execucao(cvm_download.baixar_arquivo, URL, destino)

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(corpo_a, b_no_meio))
    cvm_download.baixar_arquivo(URL, destino)

    assert destino.read_bytes() == corpo_a
    assert not list(tmp_path.glob("*.tmp"))


def test_cvm_baixado_pela_propria_execucao_continua_no_as_of(tmp_path, monkeypatch):
    """Controle do F4-A09: sem concorrência, a execução aceita o próprio download."""
    destino = tmp_path / "dfp_2026.zip"
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(_zip("A")))
    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        cvm_download.baixar_arquivo(URL, destino)
        registro = _registro(destino)

    assert datetime.fromisoformat(registro.data_coleta) == AS_OF


class _OData:
    def __init__(self, valor):
        self.valor = valor

    def raise_for_status(self):
        return None

    def json(self):
        return {"value": self.valor}


def test_ifdata_publicado_por_outra_execucao_antes_da_marcacao_nao_entra_no_as_of(
    tmp_path, monkeypatch
):
    provedor = ifdata.IFDataProvider(str(tmp_path), calendario=calendario_sintetico())
    caminho = "Teste(AnoMes=@AnoMes)?@AnoMes=202606"
    respostas = iter([[{"x": "A"}], [{"x": "B"}]])
    monkeypatch.setattr(requests, "get", lambda *a, **k: _OData(next(respostas)))
    replace_real = pathlib.Path.replace
    feito = []

    def replace_e_b_publica(origem, alvo):
        resultado = replace_real(origem, alvo)
        if not feito:
            feito.append(True)
            outro = ifdata.IFDataProvider(
                str(tmp_path), calendario=calendario_sintetico()
            )
            outro.ttl_segundos = 0
            _outra_execucao(
                lambda: outro._buscar(caminho, as_of=AS_OF + timedelta(days=1))
            )
        return resultado

    monkeypatch.setattr(pathlib.Path, "replace", replace_e_b_publica)
    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        provedor._buscar(caminho, as_of=AS_OF)
        registro = provedor._registrar(caminho)

    assert type(registro) is proveniencia.Proveniencia
    assert datetime.fromisoformat(registro.data_coleta) > AS_OF


def test_ifdata_downloads_do_mesmo_destino_usam_temporarios_distintos(
    tmp_path, monkeypatch
):
    provedor = ifdata.IFDataProvider(str(tmp_path), calendario=calendario_sintetico())
    provedor.ttl_segundos = 0
    caminho = "Teste(AnoMes=@AnoMes)?@AnoMes=202606"
    monkeypatch.setattr(requests, "get", lambda *a, **k: _OData([{"x": "A"}]))
    replace_real = pathlib.Path.replace
    temporarios = []

    def anotar(origem, alvo):
        if pathlib.Path(alvo) == provedor._arquivo(caminho):
            temporarios.append(pathlib.Path(origem).name)
        return replace_real(origem, alvo)

    monkeypatch.setattr(pathlib.Path, "replace", anotar)
    provedor._buscar(caminho, as_of=AS_OF)
    provedor._buscar(caminho, as_of=AS_OF + timedelta(days=1))

    assert len(temporarios) == 2
    assert temporarios[0] != temporarios[1]
