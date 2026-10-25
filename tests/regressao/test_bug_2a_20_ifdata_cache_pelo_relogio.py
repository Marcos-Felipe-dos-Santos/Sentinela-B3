"""BUG-2A-20: cache do IF.data medido pelo relógio, e a resposta vazia guardada.

`IFDataProvider._buscar` mede a validade do cache com `time.time()`, e não com o instante de
referência recebido; e grava a resposta vazia (`value: []`, data-base ainda não publicada
pelo BCB), que é reaproveitada por até 7 dias sem nova consulta. Origem: 2ª passada do
Gemini (15/10/2026), conferida pelo Claude no código em 18/10/2026.
"""

import hashlib
import json
import os
import time
from datetime import UTC, date, datetime, timedelta

import pytest

from sentinela.data.providers import ifdata
from tests.regressao.test_bug_2a_19_ifdata_sem_proveniencia import _get_falso, _Resposta
from tests.test_cvm_bancos import CADASTRO_BB, CAPITAL_BB

MOTIVO = (
    "BUG-2A-20 · cache do IF.data medido pelo relógio e resposta vazia guardada por 7 dias "
    "· corrige: F2B-44"
)


def test_cache_do_ifdata_nao_le_o_relogio(tmp_path, monkeypatch):
    # O cache da data-base mais recente (202609, para 13/10/2026) existe; o provedor não pode
    # consultar o relógio para decidir se ele vale.
    for caminho, valor in (
        (ifdata.caminho_cadastro("202609", "00000000"), CADASTRO_BB),
        (ifdata.caminho_capital("202609", "C0080329"), CAPITAL_BB),
    ):
        arquivo = tmp_path / f"{hashlib.sha256(caminho.encode()).hexdigest()}.json"
        arquivo.write_text(json.dumps(valor), encoding="utf-8")
    provedor = ifdata.IFDataProvider(cache_dir=str(tmp_path))
    monkeypatch.setattr(ifdata.requests, "get", _get_falso)

    def _relogio():
        raise AssertionError("o provedor leu o relógio")

    monkeypatch.setattr(time, "time", _relogio)
    capital = provedor.capital(
        "00.000.000/0001-91",
        date(2026, 10, 13),
        as_of=datetime(2026, 10, 13, 12, tzinfo=UTC),
    )
    assert capital.basileia == pytest.approx(0.151297835513664)


def test_resposta_vazia_do_ifdata_nao_e_guardada(tmp_path, monkeypatch):
    pedidos = []

    def _get_vazio(url, timeout):
        pedidos.append(url)
        return _Resposta([])

    monkeypatch.setattr(ifdata.requests, "get", _get_vazio)
    provedor = ifdata.IFDataProvider(cache_dir=str(tmp_path))
    provedor.capital(
        "00.000.000/0001-91",
        date(2026, 10, 13),
        as_of=datetime(2026, 10, 13, 12, tzinfo=UTC),
    )
    primeira = len(pedidos)
    provedor.capital(
        "00.000.000/0001-91",
        date(2026, 10, 13),
        as_of=datetime(2026, 10, 13, 12, tzinfo=UTC),
    )
    assert primeira == ifdata.DATAS_BASE_TENTADAS
    assert len(pedidos) == 2 * primeira


def test_cache_expira_no_instante_explicito_apos_sete_dias(tmp_path, monkeypatch):
    inicio = datetime(2026, 10, 13, 12, tzinfo=UTC)
    for caminho, valor in (
        (ifdata.caminho_cadastro("202609", "00000000"), CADASTRO_BB),
        (ifdata.caminho_capital("202609", "C0080329"), CAPITAL_BB),
        # F2B-32: a carteira (relatório 16) também fica no cache e também expira.
        (ifdata.caminho_carteira("202609", "C0080329"), [{"Conta": "24454"}]),
    ):
        arquivo = tmp_path / f"{hashlib.sha256(caminho.encode()).hexdigest()}.json"
        arquivo.write_text(json.dumps(valor), encoding="utf-8")
        os.utime(arquivo, (inicio.timestamp(), inicio.timestamp()))
    pedidos = []

    def buscar(url, timeout):
        pedidos.append(url)
        return _get_falso(url, timeout)

    monkeypatch.setattr(ifdata.requests, "get", buscar)
    capital = ifdata.IFDataProvider(cache_dir=str(tmp_path)).capital(
        "00.000.000/0001-91",
        date(2026, 10, 13),
        as_of=inicio + timedelta(days=7, seconds=1),
    )
    assert capital.basileia == pytest.approx(0.151297835513664)
    assert len(pedidos) == 3
    assert any("IfDataCadastro" in u for u in pedidos)
    assert any("IfDataValores" in u for u in pedidos)
