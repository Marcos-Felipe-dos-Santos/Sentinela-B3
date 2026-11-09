"""F2B-44: TTL por instante explícito e proveniência dos arquivos IF.data, sem rede."""

import hashlib
import json
import os
from datetime import UTC, date, datetime, timedelta

import pytest
import requests

from sentinela.data import proveniencia
from sentinela.data.providers import ifdata
from tests.regressao.test_bug_2a_19_ifdata_sem_proveniencia import _Resposta
from tests.test_cvm_bancos import CAPITAL_BB

INSTANTE = datetime(2026, 10, 13, 12, tzinfo=UTC)


@pytest.mark.parametrize("instante", [None, date(2026, 10, 13), datetime(2026, 10, 13)])
def test_instante_com_fuso_e_obrigatorio(tmp_path, instante):
    p = ifdata.IFDataProvider(str(tmp_path))
    with pytest.raises(ValueError, match="datetime com fuso"):
        p._buscar("x", as_of=instante)
    with pytest.raises(ValueError, match="datetime com fuso"):
        p.capital(None, date(2026, 10, 13), as_of=instante)


def _cache(tmp_path, valor, instante=INSTANTE):
    arquivo = tmp_path / (hashlib.sha256(b"x").hexdigest() + ".json")
    arquivo.write_text(json.dumps(valor), encoding="utf-8")
    os.utime(arquivo, (instante.timestamp(), instante.timestamp()))
    return arquivo


@pytest.mark.parametrize(
    "idade,consulta", [(0, False), (604799, False), (604800, True), (-1, True)]
)
def test_ttl_limites_e_cache_futuro(tmp_path, monkeypatch, idade, consulta):
    _cache(tmp_path, CAPITAL_BB)
    chamadas = []

    def buscar(url, timeout):
        chamadas.append(url)
        return _Resposta(CAPITAL_BB)

    monkeypatch.setattr(ifdata.requests, "get", buscar)
    p = ifdata.IFDataProvider(str(tmp_path))
    assert p._buscar("x", as_of=INSTANTE + timedelta(seconds=idade)) == CAPITAL_BB
    assert bool(chamadas) is consulta


def test_cache_vazio_legado_nao_impede_nova_consulta(tmp_path, monkeypatch):
    _cache(tmp_path, [])
    chamadas = []

    def buscar(url, timeout):
        chamadas.append(url)
        return _Resposta([])

    monkeypatch.setattr(ifdata.requests, "get", buscar)
    p = ifdata.IFDataProvider(str(tmp_path))
    assert p._buscar("x", as_of=INSTANTE) == []
    assert p._buscar("x", as_of=INSTANTE) == []
    assert len(chamadas) == 2


def test_falha_do_registro_nao_descarta_download(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ifdata.requests, "get", lambda url, timeout: _Resposta(CAPITAL_BB)
    )
    monkeypatch.setattr(proveniencia, "registrar_sem_falhar", lambda *a, **kw: None)
    assert (
        ifdata.IFDataProvider(str(tmp_path))._buscar("x", as_of=INSTANTE) == CAPITAL_BB
    )


def test_cache_antigo_preserva_a_coleta_na_falha_da_fonte(tmp_path, monkeypatch):
    arquivo = _cache(tmp_path, CAPITAL_BB)
    p = ifdata.IFDataProvider(str(tmp_path))
    p._registrar("x")
    original = proveniencia.ler_registro(arquivo)

    def falhar(url, timeout):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(ifdata.requests, "get", falhar)
    assert p._buscar("x", as_of=INSTANTE + timedelta(days=8)) == CAPITAL_BB
    assert proveniencia.ler_registro(arquivo) == original


def test_cascata_encaminha_instante_e_proveniencia(monkeypatch):
    from tests.test_market_engine import _engine

    chamadas = []
    registro = {"documento": "IF.data", "fonte": ifdata.URL_BASE}

    class Fonte:
        def capital(self, cnpj, data_referencia, *, as_of):
            chamadas.append((cnpj, data_referencia, as_of))
            return ifdata.Capital(
                0.15, None, "202606", "C0080329", proveniencia=(registro,)
            )

    motor = _engine(monkeypatch, info={"currentPrice": 20.0})
    motor.ifdata = Fonte()
    dados = {"setor": "Bancos", "modelo_bpp": "banco", "cnpj": "00.000.000/0001-91"}
    instante = datetime(2026, 10, 1, 1, tzinfo=UTC)
    motor._buscar_ifdata(dados, as_of=instante)
    assert chamadas == [(dados["cnpj"], date(2026, 9, 30), instante)]
    assert dados["ifdata"]["proveniencia"] == (registro,)
