"""F3-8b [e2e]: fontes públicas D18 → produtores → serviço → backtest/persistência.

DFP2021/FCA2021 deABEV, COTAHIST2021–2023, B3/SGS/Tesouro/Focus/IBGE reais.
Nenhuma chave final da cascata é injetada. Um ativo não forma quintil: prova o
caminho numérico com o motivo e contagem reais; 25/27 e os cortes estão no contrato.
A identidade foi escolhida pela fixture pública Gordon, não pelo retorno posterior.
"""

import hashlib
import json
import os
import sqlite3
import zipfile
from collections import Counter
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from backtesting import backtest_pit
from sentinela.data.macro_por_data import data_sgs
from sentinela.data.pit import carga_cvm
from sentinela.data.providers import (
    b3_cotahist,
    b3_indices,
    b3_proventos,
    macro,
    tesouro,
)
from sentinela.data.store import migracoes, resultados

PASTA = Path(__file__).parent / "fixtures" / "backtest_pit"
B3 = PASTA / "b3_proventos_abev_2026.json"
D = date(2022, 3, 31)
T = date(2023, 3, 31)
COLETA = datetime(2026, 11, 13, 15, tzinfo=UTC)


def _hash(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def test_recortes_publicos_com_fontes_e_hashes_verificaveis():
    meta = json.loads((PASTA / "proveniencia.json").read_text())
    for nome, item in meta["arquivos"].items():
        caminho = B3 if nome == B3.name else PASTA / nome
        assert _hash(caminho.read_bytes()) == item["sha256_recorte"]
        if "sha256_original" in item:
            assert len(item["sha256_original"]) == 64
    # Verificação independente do leiaute COTAHIST: PREULT(109–121)/100/FATCOT(211–217).
    with zipfile.ZipFile(PASTA / "COTAHIST_A2022.ZIP") as z:
        linhas = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    anterior = next(l for l in linhas if l.startswith("0120220330"))
    assert int(anterior[108:121]) / 100 / int(anterior[210:217]) == 15.17


def _provedor_macro(tmp_path, monkeypatch):
    with zipfile.ZipFile(PASTA / "macro_2022.zip") as z:
        catalogo = json.loads(z.read("catalogo.json"))
        snapshots = {
            url: json.loads(z.read(nome))
            for url, nome in catalogo.items()
            if isinstance(nome, str)
        }
        sidra = z.read("sidra_1737_v63.json").decode()
        sgs = {
            12: json.loads(z.read("sgs_12_2020.json")),
            432: json.loads(z.read("sgs_432_2010.json"))
            + json.loads(z.read("sgs_432_2020.json")),
        }
        texto_tesouro = z.read("precotaxatesourodireto.csv").decode()
    caminho = tmp_path / "tesouro.csv"
    caminho.write_text(texto_tesouro)
    os.utime(caminho, (COLETA.timestamp(), COLETA.timestamp()))
    monkeypatch.setattr(
        tesouro.TesouroProvider,
        "baixar",
        lambda self, instante: self._snapshot(caminho),
    )
    provedor = macro.MacroProvider(cache_dir=tmp_path / "macro")

    def baixar(url, instante):
        if url in snapshots:
            return macro.SnapshotMacro(**snapshots[url])
        if "/1737/" in url:
            # Recorte da resposta SIDRA pública, sem fabricar observação ou valor.
            corpo = sidra
        elif "bcdata.sgs." in url:
            q = parse_qs(urlparse(url).query)
            inicio = data_sgs(q["dataInicial"][0])
            fim = data_sgs(q["dataFinal"][0])
            serie = int(url.split("bcdata.sgs.")[1].split("/")[0])
            por_dia = {r["data"]: r for r in sgs[serie]}
            itens = [
                r for r in por_dia.values() if inicio <= data_sgs(r["data"]) <= fim
            ]
            corpo = json.dumps(itens)
        else:
            raise AssertionError(f"fonte não prevista na fixture pública: {url}")
        return macro.SnapshotMacro(
            corpo, url, instante.isoformat(), _hash(corpo.encode())
        )

    monkeypatch.setattr(provedor, "baixar", baixar)
    return provedor


@pytest.fixture
def banco_publico(tmp_path, monkeypatch):
    import requests

    def sem_rede(*args, **kwargs):
        raise AssertionError("rede consultada durante o backtest")

    monkeypatch.setattr(requests.sessions.Session, "request", sem_rede)
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        for tipo in ("DFP", "FCA"):
            carga_cvm.carregar(
                conn,
                PASTA / f"{tipo.lower()}_cia_aberta_2021.zip",
                tipo=tipo,
                fonte=f"CVM {tipo}2021; proveniencia.json",
                coleta=COLETA.isoformat(),
            )
        for ano in (2021, 2022, 2023):
            b3_cotahist.carregar(
                conn,
                PASTA / f"COTAHIST_A{ano}.ZIP",
                fonte=f"B3 COTAHIST{ano}; proveniencia.json",
                coleta=COLETA.isoformat(),
            )
        provedor = _provedor_macro(tmp_path, monkeypatch)
        resumo = macro.gravar_series(
            conn,
            provedor,
            coleta=COLETA,
            datas=[D],
            janela=(date(2021, 1, 1), date(2021, 12, 31)),
        )
        assert resumo["ipca"] > 12 and resumo["tesouro"] > 0 and resumo["focus"] > 0
        with zipfile.ZipFile(PASTA / "macro_2022.zip") as z:
            for ano in (2022, 2023):
                corpo = z.read(f"ibov_{ano}.json")
                b3_indices.gravar_ibovespa(
                    conn,
                    b3_indices.ler(json.loads(corpo), ano),
                    {
                        "url": f"B3 IndexCall/GetPortfolioDay ano{ano}; adicionais.json",
                        "sha256": _hash(corpo),
                    },
                    COLETA,
                )
        macro.gravar_cdi(conn, provedor, date(2023, 12, 31), COLETA)
        fixture = json.loads(B3.read_text())
        por_url = {f["url"]: f for f in fixture["fontes"]}

        def obter(url):
            nome = url.split("/CompanyCall/")[1].split("/")[0] + ".json"
            return json.loads(fixture["membros"][nome]), por_url[url]

        relacao = b3_proventos.coletar(23264, COLETA, obter)
        assert relacao.identidade is None
        b3_proventos.gravar_proventos(conn, relacao, 23264)
        b3_proventos.gravar_eventos(conn, relacao, 23264)
        yield conn


def test_fontes_reais_servico_lente_retorno_e_recalculo_imutavel(
    banco_publico, tmp_path, monkeypatch
):
    cadastro = pd.read_csv(
        PASTA / "cad_cia_aberta_abev.csv", sep=";", encoding="latin-1", dtype=str
    )
    executor = backtest_pit.BacktestPIT(
        banco_publico, cadastro, hoje=date(2026, 11, 13), cache_dir=tmp_path / "pit"
    )
    primeiro = executor.executar([D], horizontes=(12,), modo="estrito")
    registros_primeiros = resultados.buscar(banco_publico, "ABEV3")
    segundo = executor.executar([D], horizontes=(12,), modo="estrito")
    registros_segundos = resultados.buscar(banco_publico, "ABEV3")
    assert primeiro["hash_insumos"] == segundo["hash_insumos"]
    assert primeiro["hash_resultado"] == segundo["hash_resultado"]
    assert primeiro["observacoes"] == segundo["observacoes"]
    gordon = next(o for o in primeiro["observacoes"] if o["lente"] == "Gordon")
    assert gordon["D"] == D.isoformat() and gordon["fim"] == T.isoformat()
    oracle = json.loads((PASTA / "retorno_esperado.json").read_text())
    assert gordon["preco_lente"] == pytest.approx(oracle["preco_lente"])
    assert gordon["preco_entrada"] == pytest.approx(oracle["preco_entrada"])
    assert gordon["abstencao_retorno"] is None, gordon
    assert gordon["retorno_total"] == pytest.approx(oracle["retorno_total"], abs=1e-12)
    assert gordon["retorno_ibov"] == pytest.approx(oracle["retorno_ibov"], abs=1e-12)
    assert gordon["retorno_cdi"] == pytest.approx(oracle["retorno_cdi"], abs=1e-12)
    assert gordon["valor"] > 0
    assert gordon["abstencao_retorno"] is None
    # O grupo é formado pelo mesmo caminho; um ativo não autoriza quintil artificial.
    grupo = next(g for g in primeiro["grupos"] if g["lente"] == "Gordon")
    assert grupo["elegiveis"] == 1 and grupo["quintis"] == {}
    assert grupo["motivo"] == "menos de 25 ativos elegíveis"
    assert grupo["mediana_retorno"] == gordon["retorno_total"]
    resumo = next(
        r
        for r in primeiro["resumo"]["lentes"]
        if (r["lente"], r["horizonte"], r["modo"]) == ("Gordon", 12, "estrito")
    )
    assert resumo["universo_elegivel"] == 1 and resumo["com_valor"] == 1
    assert resumo["cobertura"] == 1
    assert resumo["quintis"]["Q1"]["n_datas_com_retorno"] == 0
    assert "score" not in primeiro["resumo"]
    assert len(registros_primeiros) == 5
    assert Counter(r.tipo for r in registros_segundos) == {
        "original": 5,
        "recalculo": 5,
    }
    for registro in registros_primeiros:
        atuais = [r for r in registros_segundos if r.metodo == registro.metodo]
        originais = [r for r in atuais if r.tipo == "original"]
        recalculos = [r for r in atuais if r.tipo == "recalculo"]
        assert len(originais) == len(recalculos) == 1
        assert originais[0].hash_resultado == registro.hash_resultado
    assert "score_final" not in gordon and "fair_value" not in gordon
