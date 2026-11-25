"""BUG-4-21: a auditoria cria e migra o banco, e lista os tickers das análises salvas.

O F4-A12 fez `auditoria.auditar_banco` ler `unico.caminho_padrao()`, que cria o banco único
quando não há nenhum e aplica migrações pendentes. A inspeção deixava de ser só leitura. A
seção "Análises salvas" continuava a listar os tickers analisados, que podem revelar a carteira
(ressalva da auditoria R2 do bloco 0 e pergunta 2 do relatório, decisão do Marcos de 25/11).

Banco temporário em `tmp_path`, diretório corrente nele; tickers sintéticos.
"""

import json
import sqlite3
from contextlib import closing

import auditoria
from database import DatabaseManager
from sentinela.data.store import unico


def _rel(monkeypatch):
    monkeypatch.setattr(auditoria, "_rel", {"banco": {}})


def test_sem_banco_unico_a_auditoria_nao_cria_o_arquivo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _rel(monkeypatch)

    auditoria.auditar_banco()

    assert not (tmp_path / unico.BANCO_UNICO).exists()
    assert "ausente" in auditoria._rel["banco"]["erro"]


def test_banco_existente_nao_e_migrado(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with closing(sqlite3.connect(tmp_path / unico.BANCO_UNICO)) as conn:
        conn.execute(
            "CREATE TABLE carteira_real (ticker TEXT, quantidade INTEGER, "
            "preco_medio REAL, data_aporte TEXT)"
        )
        conn.execute(
            "CREATE TABLE analises (ticker TEXT, data_analise TEXT, score INTEGER, "
            "recomendacao TEXT, dados_completos TEXT)"
        )
        conn.commit()
        antes = conn.execute("SELECT name FROM sqlite_master ORDER BY name").fetchall()
    _rel(monkeypatch)

    auditoria.auditar_banco()

    with closing(sqlite3.connect(tmp_path / unico.BANCO_UNICO)) as conn:
        depois = conn.execute("SELECT name FROM sqlite_master ORDER BY name").fetchall()
    assert depois == antes
    assert auditoria._rel["banco"]["carteira"] == {"posicoes": 0}


def _com_analise(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    banco = DatabaseManager(unico.caminho_padrao())
    banco.salvar_analise({"ticker": "TSTA3", "apresentacao_versao": "1.0"})
    _rel(monkeypatch)


def test_tickers_das_analises_so_com_opcao_explicita(tmp_path, monkeypatch, capsys):
    _com_analise(tmp_path, monkeypatch)

    auditoria.auditar_banco()

    assert "TSTA3" not in capsys.readouterr().out

    assert auditoria._rel["banco"]["analises"] == {"quantidade": 1}
    assert "TSTA3" not in json.dumps(auditoria._rel)


def test_opcao_explicita_lista_as_analises(tmp_path, monkeypatch):
    _com_analise(tmp_path, monkeypatch)

    auditoria.auditar_banco(com_analises=True)

    itens = auditoria._rel["banco"]["analises"]["itens"]
    assert [a["ticker"] for a in itens] == ["TSTA3"]
    assert auditoria._rel["banco"]["analises"]["quantidade"] == 1


def test_banco_e_aberto_so_para_leitura(tmp_path, monkeypatch):
    _com_analise(tmp_path, monkeypatch)
    aberturas = []
    conectar = sqlite3.connect

    def anotar(*args, **kwargs):
        aberturas.append((args, kwargs))
        return conectar(*args, **kwargs)

    monkeypatch.setattr(auditoria.sqlite3, "connect", anotar)

    auditoria.auditar_banco()

    assert aberturas
    assert all(str(a[0][0]).endswith("?mode=ro") and a[1].get("uri") for a in aberturas)


def test_banco_sem_as_tabelas_vira_erro_sem_migrar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / unico.BANCO_UNICO).write_bytes(b"")
    _rel(monkeypatch)

    auditoria.auditar_banco()

    assert "sem as tabelas carteira_real, analises" in auditoria._rel["banco"]["erro"]
    assert (tmp_path / unico.BANCO_UNICO).stat().st_size == 0


def test_relatorio_registra_so_o_nome_do_banco(tmp_path, monkeypatch):
    _com_analise(tmp_path, monkeypatch)

    auditoria.auditar_banco()

    assert auditoria._rel["banco"]["arquivo"] == unico.BANCO_UNICO
