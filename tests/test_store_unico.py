"""Banco único: migração verificada dos dois bancos atuais (F3-2c, E-14, D29)."""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from database import DatabaseManager
from sentinela.data.store import backup, migracoes, unico
from sentinela.domain.apresentacao import adaptar_leitura
from sentinela.repositories.analysis_repository import AnalysisRepository

AGORA = datetime(2026, 11, 10, 12, tzinfo=UTC)
LEGADO = {
    "ticker": "TSTA3",
    "score_final": 87,
    "recomendacao": "COMPRA",
    "fair_value": 10,
}


def _bancos(pasta: Path) -> dict[str, Path]:
    """Dois bancos sintéticos com as tabelas reais, criados pelas próprias classes."""
    v6, s = pasta / "sentinela_v6.db", pasta / "sentinela.db"
    db = DatabaseManager(str(v6))
    db.adicionar_posicao("TSTA3", 100, 10.0)
    db.adicionar_posicao("TSTB4", 7, 33.333333333333336)
    db.adicionar_posicao("TSTA3", 50, 13.0)
    db.salvar_fundamentos_cache("TSTA3", {"pl": 8.5}, "cvm")
    with closing(db._get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO analises VALUES (?, ?, ?, ?, ?)",
            ("TSTA3", "2020-01-02", 87, "COMPRA", json.dumps(LEGADO)),
        )
    repo = AnalysisRepository(str(s))
    repo.save_run({"ticker": "TSTA3", "x": 1})
    repo.save_run({"ticker": "TSTA3", "x": 2})
    ultimo = repo.save_run({"ticker": "TSTB4"})
    with closing(repo._get_conn()) as conn, conn:
        conn.execute("DELETE FROM analysis_runs WHERE id = ?", (ultimo,))
    return {"sentinela_v6.db": v6, "sentinela.db": s}


def _backup(pasta: Path, origens: dict[str, Path]) -> Path:
    assert (
        backup.main([str(pasta / "backups"), *map(str, origens.values())], agora=AGORA)
        == 0
    )
    return unico.pasta_de_backup_valida(pasta / "backups")


def _linhas(caminho, tabela):
    with closing(sqlite3.connect(caminho)) as conn:
        return conn.execute(f"SELECT * FROM {tabela} ORDER BY 1, 2").fetchall()


# ── migração ponta a ponta ───────────────────────────────────────────────────


def test_migracao_sem_perda_e_leitura_pelas_classes(tmp_path):
    origens = _bancos(tmp_path)
    destino = tmp_path / "sentinela_store.db"
    relatorio = unico.migrar(origens, destino, _backup(tmp_path, origens))
    for nome, tabelas in unico.TABELAS.items():
        for tabela in tabelas:
            assert _linhas(destino, tabela) == _linhas(origens[nome], tabela)
            assert relatorio[nome][tabela]["linhas"] == len(_linhas(destino, tabela))
            assert len(relatorio[nome][tabela]["sha256"]) == 64
    # posições da carteira linha a linha, pela própria classe
    assert (
        DatabaseManager(str(destino)).listar_carteira()
        == DatabaseManager(str(origens["sentinela_v6.db"])).listar_carteira()
    )
    # o adaptador de leitura do F2C-4 lê as análises antigas no banco novo
    assert DatabaseManager(str(destino)).buscar_analise("TSTA3") == adaptar_leitura(
        LEGADO
    )
    repo = AnalysisRepository(str(destino))
    assert [r["payload"] for r in repo.list_runs("TSTA3")] == [
        adaptar_leitura({"ticker": "TSTA3", "x": 2}),
        adaptar_leitura({"ticker": "TSTA3", "x": 1}),
    ]
    # o id apagado no banco antigo não é reaproveitado no novo
    novo = repo.save_run({"ticker": "TSTC3"})
    assert novo == 4
    # esquema do banco novo é o das migrações
    with closing(sqlite3.connect(destino)) as conn:
        assert [v for (v,) in conn.execute("SELECT versao FROM schema_version")] == [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
        ]
    # os bancos antigos ficam no disco, intactos
    assert all(p.is_file() for p in origens.values())


def test_banco_antigo_ausente_fica_registrado(tmp_path):
    origens = _bancos(tmp_path)
    origens["sentinela.db"].unlink()
    destino = tmp_path / "unico.db"
    relatorio = unico.migrar(origens, destino, _backup(tmp_path, origens))
    assert relatorio["sentinela.db"] == {"ausente": True}
    assert not origens["sentinela.db"].exists()
    assert _linhas(destino, "analysis_runs") == []
    assert relatorio["sentinela_v6.db"]["carteira_real"]["linhas"] == 2


# ── backup obrigatório ───────────────────────────────────────────────────────


def test_sem_backup_valido_nao_abre_o_banco_antigo(tmp_path):
    _bancos(tmp_path)
    (tmp_path / "backups").mkdir()
    with pytest.raises(unico.BackupNaoVerificado, match="nenhuma execução"):
        unico.pasta_de_backup_valida(tmp_path / "backups")


def test_pasta_com_erros_nao_vale(tmp_path):
    origens = _bancos(tmp_path)
    pasta = _backup(tmp_path, origens)
    (pasta / "erros.json").write_text("[]")
    with pytest.raises(unico.BackupNaoVerificado):
        unico.pasta_de_backup_valida(tmp_path / "backups")


def test_pasta_mais_recente_pelo_numero_do_sufixo(tmp_path):
    origens = _bancos(tmp_path)
    for _ in range(11):
        backup.main(
            [str(tmp_path / "backups"), *map(str, origens.values())], agora=AGORA
        )
    assert unico.pasta_de_backup_valida(tmp_path / "backups").name.endswith("Z-11")


def test_backup_de_outro_estado_e_recusado(tmp_path):
    origens = _bancos(tmp_path)
    pasta = _backup(tmp_path, origens)
    DatabaseManager(str(origens["sentinela_v6.db"])).adicionar_posicao("TSTC3", 1, 1.0)
    destino = tmp_path / "unico.db"
    with pytest.raises(unico.BackupNaoVerificado, match="contagens"):
        unico.migrar(origens, destino, pasta)
    assert not destino.exists()


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("iguais", False, "não verificada"),
        ("restauracao_iguais", False, "não verificada"),
        ("sha256", "0" * 64, "hash"),
    ],
)
def test_backup_com_registro_invalido_e_recusado(tmp_path, campo, valor, motivo):
    origens = _bancos(tmp_path)
    pasta = _backup(tmp_path, origens)
    relatorio = json.loads((pasta / "backup.json").read_text())
    relatorio[0][campo] = valor
    (pasta / "backup.json").write_text(json.dumps(relatorio))
    with pytest.raises(unico.BackupNaoVerificado, match=motivo):
        unico.migrar(origens, tmp_path / "unico.db", pasta)
    assert not (tmp_path / "unico.db").exists()


def test_banco_presente_sem_registro_no_backup_e_recusado(tmp_path):
    origens = _bancos(tmp_path)
    pasta = _backup(tmp_path, {"sentinela_v6.db": origens["sentinela_v6.db"]})
    with pytest.raises(unico.BackupNaoVerificado, match="sentinela.db"):
        unico.migrar(origens, tmp_path / "unico.db", pasta)


def test_banco_ausente_exige_ausencia_no_backup(tmp_path):
    origens = _bancos(tmp_path)
    pasta = _backup(tmp_path, origens)
    origens["sentinela.db"].unlink()
    with pytest.raises(unico.BackupNaoVerificado, match="sentinela.db"):
        unico.migrar(origens, tmp_path / "unico.db", pasta)


# ── nunca sobrescreve; falha não deixa banco parcial ─────────────────────────


def test_destino_existente_nao_e_sobrescrito(tmp_path):
    origens = _bancos(tmp_path)
    destino = tmp_path / "unico.db"
    destino.write_bytes(b"x")
    with pytest.raises(FileExistsError):
        unico.migrar(origens, destino, _backup(tmp_path, origens))
    assert destino.read_bytes() == b"x"


def test_divergencia_apaga_o_destino_criado(tmp_path, monkeypatch):
    origens = _bancos(tmp_path)
    pasta = _backup(tmp_path, origens)
    original = unico._linhas

    def _diverge(conn, esquema, tabela, colunas):
        linhas = original(conn, esquema, tabela, colunas)
        return linhas[1:] if esquema == "main" and tabela == "carteira_real" else linhas

    monkeypatch.setattr(unico, "_linhas", _diverge)
    destino = tmp_path / "unico.db"
    with pytest.raises(unico.MigracaoDivergente, match="carteira_real"):
        unico.migrar(origens, destino, pasta)
    assert not destino.exists()
    assert all(p.is_file() for p in origens.values())


def test_tabela_faltando_no_banco_antigo_falha_sem_destino(tmp_path):
    origens = _bancos(tmp_path)
    with closing(sqlite3.connect(origens["sentinela_v6.db"])) as conn:
        conn.execute("DROP TABLE fundamentals_cache")
    destino = tmp_path / "unico.db"
    with pytest.raises(unico.MigracaoDivergente, match="tabelas"):
        unico.migrar(origens, destino, _backup(tmp_path, origens))
    assert not destino.exists()
    assert not (tmp_path / "unico.db.migrando").exists()


# ── caminho padrão das classes ───────────────────────────────────────────────


def test_caminho_padrao_recusa_banco_vazio_ao_lado_dos_antigos(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    DatabaseManager("sentinela_v6.db")
    with pytest.raises(RuntimeError, match="sentinela_v6.db"):
        DatabaseManager()
    with pytest.raises(RuntimeError, match="python -m sentinela.data.store.unico"):
        AnalysisRepository()
    assert not (tmp_path / unico.BANCO_UNICO).exists()


def test_caminho_padrao_sem_banco_nenhum_cria_pelo_esquema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = DatabaseManager()
    assert db.db_path == unico.BANCO_UNICO
    assert AnalysisRepository().db_path == unico.BANCO_UNICO
    with closing(sqlite3.connect(tmp_path / unico.BANCO_UNICO)) as conn:
        assert [v for (v,) in conn.execute("SELECT versao FROM schema_version")] == [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
        ]


def test_caminho_padrao_aplica_pendentes_no_banco_unico(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    origens = _bancos(tmp_path)
    unico.migrar(origens, tmp_path / unico.BANCO_UNICO, _backup(tmp_path, origens))
    chamadas = []
    original = migracoes.aplicar
    monkeypatch.setattr(
        migracoes, "aplicar", lambda conn, *a: chamadas.append(1) or original(conn, *a)
    )
    assert (
        DatabaseManager().listar_carteira()
        == DatabaseManager("sentinela_v6.db").listar_carteira()
    )
    assert chamadas


def test_caminho_explicito_nao_muda(tmp_path):
    db = DatabaseManager(str(tmp_path / "x.db"))
    assert db.db_path == str(tmp_path / "x.db")
    with closing(sqlite3.connect(tmp_path / "x.db")) as conn:
        nomes = {n for (n,) in conn.execute("SELECT name FROM sqlite_master")}
    assert "schema_version" not in nomes


# ── linha de comando ─────────────────────────────────────────────────────────


def test_linha_de_comando_migra_e_grava_o_relatorio(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _bancos(tmp_path)
    backup.main(["backups"], agora=AGORA)
    assert unico.main(["backups", "migracao.json"]) == 0
    relatorio = json.loads((tmp_path / "migracao.json").read_text(encoding="utf-8"))
    assert relatorio["destino"] == unico.BANCO_UNICO
    assert relatorio["sem_perda"] is True
    assert relatorio["bancos"]["sentinela_v6.db"]["carteira_real"]["linhas"] == 2
    assert (tmp_path / unico.BANCO_UNICO).is_file()
    # de novo: destino existente, nada sobrescrito
    antes = (tmp_path / "migracao.json").read_bytes()
    assert unico.main(["backups", "migracao.json"]) == 1
    assert (tmp_path / "migracao.json").read_bytes() == antes
    assert "já existe" in capsys.readouterr().out


def test_linha_de_comando_sem_argumentos_mostra_o_uso(capsys):
    assert unico.main([]) == 2
    assert "uso: python -m sentinela.data.store.unico" in capsys.readouterr().out


# ── migrações: banco mais novo que o código (DD-02) ──────────────────────────


def test_aplicar_recusa_versao_que_o_diretorio_nao_tem(tmp_path):
    with closing(sqlite3.connect(tmp_path / "x.db")) as conn:
        migracoes.aplicar(conn)
        conn.execute("INSERT INTO schema_version VALUES (99, '099_futura.sql', 'x')")
        conn.commit()
        with pytest.raises(
            ValueError, match="versão do banco ausente do diretório: 99"
        ):
            migracoes.aplicar(conn)


# ── casos que a mutação pediu ────────────────────────────────────────────────


def test_contador_preservado_com_a_tabela_antiga_vazia(tmp_path):
    origens = _bancos(tmp_path)
    with closing(sqlite3.connect(origens["sentinela.db"])) as conn, conn:
        conn.execute("DELETE FROM analysis_runs")
    destino = tmp_path / "unico.db"
    unico.migrar(origens, destino, _backup(tmp_path, origens))
    assert AnalysisRepository(str(destino)).save_run({"ticker": "TSTC3"}) == 4


def test_hash_do_relatorio_e_das_linhas_da_origem(tmp_path):
    import hashlib

    origens = _bancos(tmp_path)
    DatabaseManager(str(origens["sentinela_v6.db"])).salvar_fundamentos_cache(
        "TSTB4", {"nota": "ação"}, "cvm"
    )
    destino = tmp_path / "unico.db"
    relatorio = unico.migrar(origens, destino, _backup(tmp_path, origens))
    with closing(sqlite3.connect(destino)) as conn:
        colunas = unico._colunas(conn, "fundamentals_cache")
        linhas = unico._linhas(conn, "main", "fundamentals_cache", colunas)
    texto = json.dumps([list(linha) for linha in linhas], ensure_ascii=False)
    assert relatorio["sentinela_v6.db"]["fundamentals_cache"]["sha256"] == (
        hashlib.sha256(texto.encode("utf-8")).hexdigest()
    )


def test_primeiro_banco_ausente_nao_pula_o_segundo(tmp_path):
    origens = _bancos(tmp_path)
    origens["sentinela_v6.db"].unlink()
    pasta = _backup(tmp_path, origens)
    destino = tmp_path / "unico.db"
    relatorio = unico.migrar(origens, destino, pasta)
    assert relatorio["sentinela_v6.db"] == {"ausente": True}
    assert relatorio["sentinela.db"]["analysis_runs"]["linhas"] == 2
    destino.unlink()
    # e a conferência do segundo também acontece depois de um ausente
    registros = json.loads((pasta / "backup.json").read_text())
    registros[1]["sha256"] = "0" * 64
    (pasta / "backup.json").write_text(json.dumps(registros))
    with pytest.raises(unico.BackupNaoVerificado, match="sentinela.db: hash"):
        unico.migrar(origens, destino, pasta)


def test_banco_que_apareceu_depois_do_backup_e_recusado(tmp_path):
    origens = _bancos(tmp_path)
    origens["sentinela.db"].rename(tmp_path / "guardado.db")
    pasta = _backup(tmp_path, origens)
    (tmp_path / "guardado.db").rename(origens["sentinela.db"])
    with pytest.raises(unico.BackupNaoVerificado, match="sentinela.db: sem cópia"):
        unico.migrar(origens, tmp_path / "unico.db", pasta)


def test_destino_existente_cita_o_caminho(tmp_path):
    destino = tmp_path / "unico.db"
    destino.write_bytes(b"")
    with pytest.raises(FileExistsError, match="unico.db"):
        unico.migrar({}, destino, tmp_path)


def test_arquivo_com_nome_de_execucao_nao_e_pasta(tmp_path):
    (tmp_path / "20261110T120000000000Z").write_text("x")
    with pytest.raises(unico.BackupNaoVerificado):
        unico.pasta_de_backup_valida(tmp_path)


def test_caminho_padrao_lista_os_dois_antigos(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    DatabaseManager("sentinela_v6.db")
    AnalysisRepository("sentinela.db")
    with pytest.raises(
        RuntimeError,
        match=r"\(sentinela_v6.db, sentinela.db\): faça o backup e rode python -m sentinela.data.store.unico antes$",
    ):
        DatabaseManager()


def test_linha_de_comando_relatorio_e_mensagens(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _bancos(tmp_path)
    backup.main(["backups"], agora=AGORA)
    capsys.readouterr()
    monkeypatch.setattr("sys.argv", ["unico", "backups", "migracao.json"])
    assert unico.main() == 0
    relatorio = json.loads((tmp_path / "migracao.json").read_text(encoding="utf-8"))
    assert relatorio["backup"] == str(unico.pasta_de_backup_valida("backups"))
    assert capsys.readouterr().out.strip() == (
        f"banco único {unico.BANCO_UNICO} criado; relatório em migracao.json"
    )


def test_linha_de_comando_sem_backup_sai_com_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "backups").mkdir()
    assert unico.main(["backups", "migracao.json"]) == 1
    assert capsys.readouterr().out.startswith("migração não feita: nenhuma execução")
    assert not (tmp_path / "migracao.json").exists()
    assert unico.main(["so_um"]) == 2


# ── rodada 2 da revisão ──────────────────────────────────────────────────────


def test_backup_com_mesma_contagem_e_outro_conteudo_e_recusado(tmp_path):
    origens = _bancos(tmp_path)
    pasta = _backup(tmp_path, origens)
    # compra adicional: UPDATE na carteira, a contagem não muda
    DatabaseManager(str(origens["sentinela_v6.db"])).adicionar_posicao(
        "TSTA3", 10, 20.0
    )
    with pytest.raises(unico.BackupNaoVerificado, match="conteúdo atual diferente"):
        unico.migrar(origens, tmp_path / "unico.db", pasta)


def test_execucao_mais_recente_com_erro_nao_cai_para_a_anterior(tmp_path):
    origens = _bancos(tmp_path)
    _backup(tmp_path, origens)
    backup.main(
        [str(tmp_path / "backups"), str(tmp_path / "nao_sqlite.db")],
        agora=datetime(2026, 11, 10, 13, tzinfo=UTC),
    )
    (tmp_path / "nao_sqlite.db").write_bytes(b"x" * 200)
    backup.main(
        [str(tmp_path / "backups"), str(tmp_path / "nao_sqlite.db")],
        agora=datetime(2026, 11, 10, 14, tzinfo=UTC),
    )
    with pytest.raises(unico.BackupNaoVerificado, match="mais recente com erro"):
        unico.pasta_de_backup_valida(tmp_path / "backups")


def test_coluna_a_mais_na_origem_nao_some(tmp_path):
    origens = _bancos(tmp_path)
    with closing(sqlite3.connect(origens["sentinela_v6.db"])) as conn:
        conn.execute("ALTER TABLE carteira_real ADD COLUMN nota TEXT")
    destino = tmp_path / "unico.db"
    with pytest.raises(unico.MigracaoDivergente, match="colunas de carteira_real"):
        unico.migrar(origens, destino, _backup(tmp_path, origens))
    assert not destino.exists()


def test_tabela_a_mais_na_origem_nao_some(tmp_path):
    origens = _bancos(tmp_path)
    with closing(sqlite3.connect(origens["sentinela_v6.db"])) as conn:
        conn.execute("CREATE TABLE resto (x INTEGER)")
    with pytest.raises(unico.MigracaoDivergente, match="resto"):
        unico.migrar(origens, tmp_path / "unico.db", _backup(tmp_path, origens))


def test_migracao_interrompida_antes_nao_e_retomada_em_silencio(tmp_path):
    origens = _bancos(tmp_path)
    (tmp_path / "unico.db.migrando").write_bytes(b"")
    with pytest.raises(FileExistsError, match="migrando"):
        unico.migrar(origens, tmp_path / "unico.db", _backup(tmp_path, origens))
    assert not (tmp_path / "unico.db").exists()


def test_banco_novo_so_aparece_conferido(tmp_path, monkeypatch):
    origens = _bancos(tmp_path)
    pasta = _backup(tmp_path, origens)
    vistos = []
    original = unico._copiar

    def _espia(conn, caminho, tabelas):
        vistos.append((tmp_path / "unico.db").exists())
        return original(conn, caminho, tabelas)

    monkeypatch.setattr(unico, "_copiar", _espia)
    unico.migrar(origens, tmp_path / "unico.db", pasta)
    assert vistos == [False, False]
    assert (tmp_path / "unico.db").is_file()
    assert not (tmp_path / "unico.db.migrando").exists()


def test_backup_padrao_inclui_o_banco_unico(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert backup.PADRAO == ("sentinela_v6.db", "sentinela.db", unico.BANCO_UNICO)
    DatabaseManager()  # cria o banco único vazio
    assert backup.main(["saida"], agora=AGORA) == 0
    (pasta,) = (tmp_path / "saida").iterdir()
    relatorio = json.loads((pasta / "backup.json").read_text())
    assert [Path(r["origem"]).name for r in relatorio] == list(backup.PADRAO)
    assert relatorio[2]["iguais"] is True
