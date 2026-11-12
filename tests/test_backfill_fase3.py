"""F3-7b: o script de backfill com fontes falsas (sem rede), sobre as fixtures oficiais.

O download devolve as fixtures oficiais da CVM (FCA de 2015, recortes do L1) e um COTAHIST anual
no leiaute oficial; a B3 responde com os contratos da Lojas Renner (D18) e do Ibovespa de 2024;
o CDI vem do recorte oficial do SGS 12. O que não tem fixture falha como falha de rede.
"""

import json
import shutil
import sqlite3
import sys
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import requests
from test_calendario_proventos import _anual
from test_eventos_societarios import _obter
from test_proventos_benchmarks import URLS_IBOV, _ibov, _obter_ibov, _ProvedorSGS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backfill_fase3 as bf

from sentinela.data.store import migracoes

FIXTURES = Path(__file__).parent / "fixtures" / "pit_cvm"
AGORA = datetime(2026, 11, 12, 15, tzinfo=UTC)


class _Rede:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path
        self.pedidos = []

    def baixar(self, url, destino):
        self.pedidos.append(url)
        nome = url.rsplit("/", 1)[1]
        if nome == "fca_cia_aberta_2015.zip":
            shutil.copy(FIXTURES / "fca_cia_aberta_2015_all.zip", destino)
            return destino
        if nome == "COTAHIST_A2015.ZIP":
            return _anual(destino.parent, 2015, date(2016, 1, 4))
        raise requests.HTTPError(f"404 {url}")

    def obter_b3(self, endereco):
        if endereco in URLS_IBOV.values():
            return _obter_ibov(endereco)
        if "IndexCall" in endereco:
            raise requests.HTTPError(f"404 {endereco}")
        return _obter()(endereco)


class _Macro(_ProvedorSGS):
    """Só o SGS 12: a série da taxa real (`gravar_series`) falha sem os outros insumos."""


def _backfill(tmp_path, rede, conn, **kw):
    dormidas = []
    fontes = bf.Fontes(
        baixar=rede.baixar, macro=_Macro(), obter_b3=rede.obter_b3, agora=lambda: AGORA,
        pausa=0.5, dormir=dormidas.append,
    )  # fmt: skip
    executor = bf.Backfill(conn, tmp_path / "brutos", tmp_path / "saida", fontes, **kw)
    return executor, dormidas


@pytest.fixture
def conn(tmp_path):
    with closing(sqlite3.connect(tmp_path / "s.db")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _por_etapa(relatorio):
    return {r["etapa"]: r for r in relatorio}


def test_backfill_carrega_registra_e_marca_o_estado(tmp_path, conn):
    rede = _Rede(tmp_path)
    executor, dormidas = _backfill(tmp_path, rede, conn, de=2015, ate=2015)
    relatorio = _por_etapa(executor.executar([8133]))
    assert set(relatorio) >= {
        "FCA:2015", "DFP:2015", "ITR:2015", "COTAHIST:2015", "macro", "cdi", "IBOV:2015",
        "proventos:8133", "universo", "cobertura_proventos", "espaco",
    }  # fmt: skip
    assert "FII_INFORME:2015" not in relatorio  # o Informe aberto começa em 2016 (L1)
    fca = relatorio["FCA:2015"]
    assert fca["arquivos"][0]["arquivo"] == "fca_cia_aberta_2015.zip"
    assert len(fca["arquivos"][0]["sha256"]) == 64 and "falha" not in fca
    assert fca["resumo"]["tipo"] == "FCA"
    assert relatorio["DFP:2015"]["falha"].startswith("HTTPError: 404")
    assert relatorio["COTAHIST:2015"]["resumo"]["inseridas"] > 200
    assert relatorio["macro"]["falha"]  # sem os insumos da taxa real no provedor falso
    assert relatorio["cdi"]["resumo"] == {"inseridos": 82, "repetidos": 0}
    assert relatorio["IBOV:2015"]["falha"].startswith("HTTPError")
    assert relatorio["proventos:8133"]["proventos"]["inseridos"] == 99
    assert relatorio["proventos:8133"][
        "identidade"
    ]  # PN sem ISIN (DD-06): lacuna registrada
    assert relatorio["universo"]["resumo"]["listagens"] >= 1
    assert relatorio["cobertura_proventos"]["resumo"] == {
        "2015": {
            "companhias": 0,
            "com_proventos": 0,
            "com_identidade": 0,
        }  # a ALL deslistou em abril de 2015
    }
    espaco = relatorio["espaco"]
    assert espaco["brutos_bytes"] > 0 and espaco["banco_bytes"] > 0
    assert espaco["projecao_brutos_bytes"] == bf.PROJECAO_BRUTOS
    estado = json.loads(
        (tmp_path / "saida" / "estado.json").read_text(encoding="utf-8")
    )
    assert estado["FCA:2015"] == "ok" and "DFP:2015" not in estado
    assert (
        set(dormidas) == {0.5} and len(dormidas) == len(rede.pedidos) + 4 - 1
    )  # 4 da B3
    salvo = json.loads(
        (tmp_path / "saida" / "relatorio.json").read_text(encoding="utf-8")
    )
    assert [r["etapa"] for r in salvo] == list(relatorio)


def test_retoma_sem_refazer_o_que_terminou(tmp_path, conn):
    rede = _Rede(tmp_path)
    executor, _ = _backfill(tmp_path, rede, conn, de=2015, ate=2015)
    executor.executar([8133])
    primeiro = list(rede.pedidos)
    rede.pedidos.clear()
    de_novo, _ = _backfill(tmp_path, rede, conn, de=2015, ate=2015)
    relatorio = _por_etapa(de_novo.executar([8133]))
    assert "fca_cia_aberta_2015.zip" in " ".join(primeiro)
    assert all(
        "fca_cia_aberta_2015" not in u and "COTAHIST_A2015" not in u
        for u in rede.pedidos
    )
    assert any(
        "dfp_cia_aberta_2015" in u for u in rede.pedidos
    )  # a falha é tentada de novo
    assert "FCA:2015" not in relatorio and "DFP:2015" in relatorio
    assert conn.execute("SELECT COUNT(*) FROM proventos_coletas").fetchone() == (1,)


def test_ibovespa_do_ano_com_fixture(tmp_path, conn):
    rede = _Rede(tmp_path)
    executor, _ = _backfill(tmp_path, rede, conn, de=2024, ate=2024)
    registro = executor._ibovespa(2024)
    assert registro["resumo"]["inseridos"] == 251 and registro["lacuna"] is None
    assert registro["arquivos"][0]["sha256"] == _ibov()["sha256_original"]


def test_volume_acima_do_limite_para(tmp_path, conn, monkeypatch):
    monkeypatch.setattr(bf, "LIMITE_BRUTOS", 10)
    executor, _ = _backfill(tmp_path, _Rede(tmp_path), conn, de=2015, ate=2015)
    with pytest.raises(bf.VolumeExcedido, match="acima de 100 GB"):
        executor.executar([])
    assert (
        json.loads((tmp_path / "saida" / "estado.json").read_text())["FCA:2015"] == "ok"
    )


def test_relogio_sem_fuso_recusado(tmp_path, conn):
    fontes = bf.Fontes(agora=lambda: datetime(2026, 1, 1))  # noqa: DTZ001
    with pytest.raises(ValueError, match="exige fuso"):
        bf.Backfill(conn, tmp_path, tmp_path / "saida", fontes)


def test_datas_mensais_ate_o_mes_anterior():
    datas = bf._datas_mensais(2024, date(2024, 3, 15))
    assert datas == [date(2024, 1, 31), date(2024, 2, 29)]
    assert bf._datas_mensais(2024, date(2024, 1, 1)) == []
    assert bf._datas_mensais(2023, date(2024, 1, 10))[-1] == date(2023, 12, 31)


def test_companhias_do_indice(tmp_path):
    indice = tmp_path / "indice.json"
    indice.write_text(json.dumps({"registros": {
        "TSTA3": {"classe": "STOCK", "cd_cvm": 20},
        "TSTA4": {"classe": "STOCK", "cd_cvm": 20},
        "TSTU11": {"classe": "UNIT", "cd_cvm": 10},
        "TSTF11": {"classe": "FII", "cd_cvm": 30},
        "TSTB3": {"classe": "STOCK", "cd_cvm": None},
    }}))  # fmt: skip
    assert bf.companhias_do_indice(indice) == [10, 20]


# --- Guarda do banco real (política §3, caso 3) ---------------------------------------------


def _backup(tmp_path, nome, contagens, iguais=True):
    caminho = tmp_path / "backup.json"
    caminho.write_text(json.dumps([
        {"origem": "outro.db", "ausente": True},
        {"origem": f"x/{nome}", "destino": "d", "sha256": "h", "contagens_antes": contagens,
         "contagens_depois": contagens, "iguais": iguais, "restauracao_iguais": True},
    ]))  # fmt: skip
    return caminho


def test_banco_vazio_ou_ausente_migra_sem_backup(tmp_path):
    bf.conferir_backup(tmp_path / "nao.db", None)
    with closing(sqlite3.connect(tmp_path / "vazio.db")) as conexao:
        conexao.execute("CREATE TABLE t (x)")
    bf.conferir_backup(tmp_path / "vazio.db", None)


def test_banco_com_dados_exige_backup_verificado_e_atual(tmp_path):
    banco = tmp_path / "real.db"
    with closing(sqlite3.connect(banco)) as conexao:
        conexao.execute("CREATE TABLE t (x)")
        conexao.execute("INSERT INTO t VALUES (1)")
        conexao.commit()
    with pytest.raises(RuntimeError, match="informe o backup.json verificado"):
        bf.conferir_backup(banco, None)
    bf.conferir_backup(banco, _backup(tmp_path, "real.db", {"t": 1}))
    with pytest.raises(RuntimeError, match="mudou depois do backup"):
        bf.conferir_backup(banco, _backup(tmp_path, "real.db", {"t": 2}))
    with pytest.raises(RuntimeError, match="sem cópia verificada"):
        bf.conferir_backup(banco, _backup(tmp_path, "real.db", {"t": 1}, iguais=False))
    with pytest.raises(RuntimeError, match="sem cópia verificada"):
        bf.conferir_backup(banco, _backup(tmp_path, "outro_nome.db", {"t": 1}))


def test_cobertura_separa_coleta_e_identidade_conferida(tmp_path, conn, monkeypatch):
    for cnpj, cd in (("01", "10"), ("02", "20"), ("03", "030"), ("04", "40")):
        conn.execute(
            "INSERT INTO fca_entregas (cnpj, dt_refer, versao, cd_cvm, dt_receb,"
            " valores_na_fonte, fonte, coleta, hash_sha256)"
            " VALUES (?, '2024-01-01', 1, ?, '2024-02-01', 1, 'f', 'c', 'h')", (cnpj, cd),
        )  # fmt: skip
    coletas = (
        ("A", "c1", "10", None),
        ("B", "c1", "20", None),
        ("B", "c2", "20", "sem ISIN"),
        ("C", "c1", "30", None),
    )  # fmt: skip  (a coleta mais recente de B não conferiu a identidade)
    for emissor, coleta, cd, identidade in coletas:
        conn.execute(
            "INSERT INTO proventos_coletas VALUES (?, ?, ?, 'N', 1, 1, ?, '[]', 'f', 'h')",
            (emissor, coleta, cd, identidade),
        )  # fmt: skip
    dias = []

    def companhias_em(_conn, dia):
        dias.append(dia)
        cnpjs = ("01", "02", "03", "04") if dia.year == 2024 else ("01",)
        return {"companhias": [{"cnpj": c} for c in cnpjs]}

    monkeypatch.setattr(bf.universo, "companhias_em", companhias_em)
    executor, _ = _backfill(tmp_path, _Rede(tmp_path), conn, de=2023, ate=2026)
    resumo = executor._cobertura_proventos()["resumo"]
    assert resumo["2024"] == {"companhias": 4, "com_proventos": 3, "com_identidade": 2}
    assert resumo["2023"] == {"companhias": 1, "com_proventos": 1, "com_identidade": 1}
    assert dias == [
        date(2023, 12, 31),
        date(2024, 12, 31),
        date(2025, 12, 31),
        AGORA.date(),
    ]


def test_informe_sem_linha_gravada_falha_e_desfaz_o_registro(tmp_path, conn):
    informe = tmp_path / "sem_cnpj.zip"  # o recorte de 2017 com o CNPJ do fundo apagado
    with (
        zipfile.ZipFile(FIXTURES / "inf_mensal_fii_2017.zip") as zi,
        zipfile.ZipFile(informe, "w") as zo,
    ):
        for nome in zi.namelist():
            zo.writestr(nome, zi.read(nome).replace(b"00.332.266/0001-31", b""))

    class _RedeInforme(_Rede):
        def baixar(self, url, destino):
            self.pedidos.append(url)
            shutil.copy(informe, destino)
            return destino

    executor, _ = _backfill(tmp_path, _RedeInforme(tmp_path), conn, de=2017, ate=2017)
    executor.etapa("FII_INFORME:2017", lambda: executor._zip("FII_INFORME", 2017))
    (registro,) = executor.relatorio
    assert registro["falha"] == (
        "ArquivoRecusado: inf_mensal_fii_2017.zip: nenhuma linha gravada, 36 recusadas "
        "(CNPJ_Fundo vazio)"
    )
    assert "FII_INFORME:2017" not in executor.estado
    assert conn.execute("SELECT COUNT(*) FROM cargas_arquivo").fetchone() == (0,)


def _registrar(conn, hash_):
    conn.execute(
        "INSERT INTO cargas_arquivo VALUES (?, 'FCA', 'a', 'f', 'c', 1, '{}')", (hash_,)
    )


def test_falha_no_meio_da_etapa_desfaz_o_que_ela_gravou(tmp_path, conn):
    executor, _ = _backfill(tmp_path, _Rede(tmp_path), conn, de=2024, ate=2024)

    def grava_e_falha():  # como os produtores: a primeira gravação no próprio SAVEPOINT
        conn.execute("SAVEPOINT produtor")
        _registrar(conn, "h")
        conn.execute("RELEASE produtor")
        raise RuntimeError("segunda gravação falhou")

    executor.etapa("x", grava_e_falha)
    executor.etapa("y", lambda: {"resumo": _registrar(conn, "g")})
    assert executor.relatorio[0]["falha"] == "RuntimeError: segunda gravação falhou"
    assert executor.estado == {"y": "ok"} and not conn.in_transaction
    assert conn.execute("SELECT hash_sha256 FROM cargas_arquivo").fetchall() == [("g",)]


def test_etapa_nao_atomica_desfaz_so_o_que_nao_foi_gravado(tmp_path, conn):
    executor, _ = _backfill(tmp_path, _Rede(tmp_path), conn, de=2024, ate=2024)

    def familia_gravada_e_outra_pendente():
        with conn:
            _registrar(conn, "gravada")
        _registrar(conn, "pendente")
        raise RuntimeError("falhou")

    executor.etapa("macro", familia_gravada_e_outra_pendente, atomica=False)
    assert "macro" not in executor.estado and not conn.in_transaction
    assert conn.execute("SELECT hash_sha256 FROM cargas_arquivo").fetchall() == [
        ("gravada",)
    ]


def test_espaco_soma_so_o_banco_e_o_wal(tmp_path):
    banco = tmp_path / "s.db"
    with closing(sqlite3.connect(banco)) as conexao:
        migracoes.aplicar(conexao)
        (tmp_path / "s.db-wal").write_bytes(b"x" * 7)
        (tmp_path / "s.db.bak").write_bytes(b"x" * 1000)
        executor, _ = _backfill(tmp_path, _Rede(tmp_path), conexao, de=2024, ate=2024)
        espaco = executor._espaco()
    assert espaco["banco_bytes"] == banco.stat().st_size + 7


def test_informe_republicado_so_com_repetidas_e_uma_recusa_fica_ok(tmp_path, conn):
    original = FIXTURES / "inf_mensal_fii_2023.zip"
    republicado = tmp_path / "republicado.zip"
    with zipfile.ZipFile(original) as zi, zipfile.ZipFile(republicado, "w") as zo:
        for nome in zi.namelist():
            dados = zi.read(nome)
            if "geral" in nome:
                dados += b";" * dados.split(b"\n")[0].count(b";") + b"\r\n"
            zo.writestr(nome, dados)
    arquivos = iter([original, republicado])

    class _RedeRepublica(_Rede):
        def baixar(self, url, destino):
            shutil.copy(next(arquivos), destino)
            return destino

    executor, _ = _backfill(tmp_path, _RedeRepublica(tmp_path), conn, de=2023, ate=2023)
    executor.etapa("a", lambda: executor._zip("FII_INFORME", 2023))
    executor.etapa("b", lambda: executor._zip("FII_INFORME", 2023))
    segundo = executor.relatorio[1]
    assert "falha" not in segundo and executor.estado == {"a": "ok", "b": "ok"}
    assert (
        segundo["resumo"]["inseridas"] == {}
        and segundo["resumo"]["total_recusadas"] == 1
    )


def test_releitura_carrega_o_informe_antigo_sem_novo_download(tmp_path, conn):
    informe = FIXTURES / "inf_mensal_fii_2017.zip"
    destino = tmp_path / "brutos" / "fii_informe" / "inf_mensal_fii_2017.zip"
    destino.parent.mkdir(parents=True)
    shutil.copy(informe, destino)
    conn.execute(
        "INSERT INTO cargas_arquivo VALUES (?, 'FII_INFORME', 'a', 'f', 'c', 1, '{}')",
        (bf._sha256(informe),),
    )  # registrado sem linhas, como na execução de 12/11/2026 (BUG-3-25)
    conn.commit()
    rede = _Rede(tmp_path)
    executor, _ = _backfill(tmp_path, rede, conn, de=2017, ate=2017, reler=True)
    executor.estado.update(
        {f"{f}:2017": "ok" for f in ("FCA", "DFP", "ITR", "FII_INFORME", "COTAHIST")}
    )
    executor.executar([])
    relatorio = _por_etapa(executor.relatorio)
    resumo = relatorio["releitura:FII_INFORME:2017"]["resumo"]
    assert resumo["relido"] and resumo["inseridas"] == {"fii_informe_linhas": 36}
    assert not any("inf_mensal_fii" in u for u in rede.pedidos)  # sem novo download
    assert relatorio["releitura:FCA:2017"]["falha"].startswith("FileNotFoundError")
    assert conn.execute(
        "SELECT DISTINCT coleta FROM fii_informe_linhas"
    ).fetchall() == [("c",)]  # a coleta do registro, não a hora da releitura
    assert conn.execute("SELECT COUNT(*) FROM cargas_arquivo").fetchone() == (1,)
