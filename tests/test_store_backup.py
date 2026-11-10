"""Cópia verificada e restauração dos bancos SQLite (F3-2a, D29, pacote §3)."""

import hashlib
import json
import sqlite3
from contextlib import closing

import pytest

from sentinela.data.store import backup


def _banco(caminho, wal=False):
    conn = sqlite3.connect(caminho)
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE carteira_real (ticker TEXT PRIMARY KEY, quantidade INTEGER)"
    )
    conn.execute('CREATE TABLE "tabela ""estranha""" (x INTEGER)')
    conn.execute("CREATE INDEX idx_q ON carteira_real (quantidade)")
    conn.executemany(
        "INSERT INTO carteira_real VALUES (?, ?)", [("TST3", 10), ("TST4", 20)]
    )
    conn.execute('INSERT INTO "tabela ""estranha""" VALUES (1)')
    conn.commit()
    return conn


def test_copia_consistente_com_hash_e_contagens(tmp_path):
    origem, destino = tmp_path / "a.db", tmp_path / "copia" / "a.db"
    _banco(origem).close()
    copia = backup.copiar(origem, destino)
    assert isinstance(copia, backup.Copia)
    assert copia.contagens_antes == {"carteira_real": 2, 'tabela "estranha"': 1}
    assert copia.contagens_depois == copia.contagens_antes
    assert copia.iguais
    assert copia.sha256 == hashlib.sha256(destino.read_bytes()).hexdigest()
    assert copia.origem == str(origem) and copia.destino == str(destino)


def test_copia_inclui_o_que_esta_so_no_wal(tmp_path):
    origem, destino = tmp_path / "a.db", tmp_path / "b.db"
    conn = _banco(origem, wal=True)
    conn.execute("INSERT INTO carteira_real VALUES ('TST5', 30)")
    conn.commit()  # ainda no -wal, sem checkpoint
    copia = backup.copiar(origem, destino)
    conn.close()
    assert copia.contagens_depois["carteira_real"] == 3
    assert copia.iguais


def test_banco_ausente_e_registro_sem_criar_arquivo(tmp_path):
    origem, destino = tmp_path / "nao_existe.db", tmp_path / "b.db"
    assert backup.copiar(origem, destino) == backup.Ausente(str(origem))
    assert not origem.exists()
    assert not destino.exists()


def test_nao_sobrescreve_destino(tmp_path):
    origem, destino = tmp_path / "a.db", tmp_path / "b.db"
    _banco(origem).close()
    destino.write_bytes(b"outro")
    with pytest.raises(FileExistsError):
        backup.copiar(origem, destino)
    assert destino.read_bytes() == b"outro"


def test_divergencia_de_contagem_fica_visivel():
    copia = backup.Copia("a", "b", "0" * 64, {"t": 2}, {"t": 1})
    assert not copia.iguais


def test_restauracao_reproduz_tabelas_indices_e_contagens(tmp_path):
    origem, copia, restaurado = tmp_path / "a.db", tmp_path / "b.db", tmp_path / "r.db"
    _banco(origem).close()
    backup.copiar(origem, copia)
    resultado = backup.restaurar(copia, restaurado)
    assert resultado.iguais
    assert resultado.contagens == {"carteira_real": 2, 'tabela "estranha"': 1}
    with closing(sqlite3.connect(restaurado)) as conn:
        nomes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert {"carteira_real", "idx_q", 'tabela "estranha"'} <= nomes


def test_restauracao_que_perde_tabela_nao_e_igual(tmp_path):
    origem, restaurado = tmp_path / "a.db", tmp_path / "r.db"
    _banco(origem).close()
    with closing(sqlite3.connect(restaurado)) as conn:
        conn.execute(
            "CREATE TABLE carteira_real (ticker TEXT PRIMARY KEY, quantidade INTEGER)"
        )
    assert not backup.conferir(origem, restaurado).iguais


def test_restauracao_com_linha_a_menos_nao_e_igual(tmp_path):
    origem, outro = tmp_path / "a.db", tmp_path / "o.db"
    _banco(origem).close()
    conn = _banco(outro)
    conn.execute("DELETE FROM carteira_real WHERE ticker = 'TST4'")
    conn.commit()
    conn.close()
    conferencia = backup.conferir(origem, outro)
    assert not conferencia.iguais
    assert conferencia.contagens == {"carteira_real": 1, 'tabela "estranha"': 1}


def test_restaurar_nao_sobrescreve(tmp_path):
    origem, restaurado = tmp_path / "a.db", tmp_path / "r.db"
    _banco(origem).close()
    restaurado.write_bytes(b"x")
    with pytest.raises(FileExistsError):
        backup.restaurar(origem, restaurado)


def test_linha_de_comando_grava_o_relatorio(tmp_path):
    a = tmp_path / "a.db"
    _banco(a).close()
    ausente = tmp_path / "sentinela.db"
    destino = tmp_path / "saida"
    assert backup.main([str(destino), str(a), str(ausente)]) == 0
    relatorio = json.loads((destino / "backup.json").read_text())
    assert relatorio[0]["iguais"] is True
    assert relatorio[0]["restauracao_iguais"] is True
    assert (
        relatorio[0]["sha256"]
        == hashlib.sha256((destino / "a.db").read_bytes()).hexdigest()
    )
    assert relatorio[1] == {"origem": str(ausente), "ausente": True}
    assert not ausente.exists()


def test_linha_de_comando_com_divergencia_sai_com_erro(tmp_path, monkeypatch):
    a = tmp_path / "a.db"
    _banco(a).close()
    monkeypatch.setattr(
        backup, "contagens", lambda caminho: {"t": 1 if "saida" in str(caminho) else 2}
    )
    assert backup.main([str(tmp_path / "saida"), str(a)]) == 1


def test_bancos_padrao_sao_os_dois_atuais():
    assert backup.BANCOS == ("sentinela_v6.db", "sentinela.db")


def test_ausente_antes_nao_interrompe_os_seguintes(tmp_path):
    a = tmp_path / "a.db"
    _banco(a).close()
    destino = tmp_path / "x" / "y"
    assert backup.main([str(destino), str(tmp_path / "falta.db"), str(a)]) == 0
    relatorio = json.loads((destino / "backup.json").read_text())
    assert [item.get("ausente", False) for item in relatorio] == [True, False]


def test_copia_cria_diretorios_intermediarios(tmp_path):
    origem = tmp_path / "a.db"
    _banco(origem).close()
    assert backup.copiar(origem, tmp_path / "x" / "y" / "a.db").iguais


def test_destino_existente_cita_o_caminho(tmp_path):
    origem, destino = tmp_path / "a.db", tmp_path / "b.db"
    _banco(origem).close()
    destino.write_bytes(b"x")
    with pytest.raises(FileExistsError, match="b.db"):
        backup.copiar(origem, destino)


def test_sem_argumentos_mostra_o_uso(capsys):
    assert backup.main([]) == 2
    assert "uso: python -m sentinela.data.store.backup" in capsys.readouterr().out


def test_le_os_argumentos_da_linha_de_comando(tmp_path, monkeypatch):
    a = tmp_path / "a.db"
    _banco(a).close()
    destino = tmp_path / "saida"
    monkeypatch.setattr("sys.argv", ["backup", str(destino), str(a)])
    assert backup.main() == 0
    assert (destino / "a.db").is_file()


def test_sem_bancos_le_os_dois_atuais_do_diretorio_corrente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _banco(tmp_path / "sentinela_v6.db").close()
    assert backup.main(["saida"]) == 0
    relatorio = json.loads((tmp_path / "saida" / "backup.json").read_text())
    assert relatorio[0]["origem"] == "sentinela_v6.db"
    assert relatorio[1] == {"origem": "sentinela.db", "ausente": True}
    assert not (tmp_path / "sentinela.db").exists()


def test_so_ausentes_ainda_grava_o_relatorio(tmp_path):
    destino = tmp_path / "x" / "y"
    assert backup.main([str(destino), str(tmp_path / "falta.db")]) == 0
    assert json.loads((destino / "backup.json").read_text()) == [
        {"origem": str(tmp_path / "falta.db"), "ausente": True}
    ]


def test_rodar_de_novo_no_mesmo_diretorio_registra_o_erro(tmp_path):
    a = tmp_path / "a.db"
    _banco(a).close()
    destino = tmp_path / "saida"
    assert backup.main([str(destino), str(a)]) == 0
    copia = (destino / "a.db").read_bytes()
    assert backup.main([str(destino), str(a)]) == 1
    relatorio = json.loads((destino / "backup.json").read_text())
    esperado = f"destino já existe: {destino / 'a.db'}"
    assert relatorio == [{"origem": str(a), "erro": esperado}]
    assert (destino / "a.db").read_bytes() == copia


def test_falha_no_meio_nao_deixa_copia_parcial(tmp_path):
    origem, destino = tmp_path / "a.db", tmp_path / "b.db"
    origem.write_bytes(b"nao e sqlite" * 100)
    with pytest.raises(sqlite3.DatabaseError):
        backup.copiar(origem, destino)
    assert not destino.exists()


def test_contagem_antes_e_da_mesma_leitura_da_copia(tmp_path, monkeypatch):
    origem, destino = tmp_path / "a.db", tmp_path / "b.db"
    escritor = _banco(origem, wal=True)
    original = backup._contar
    chamadas = []

    def contar_e_escrever(conn):
        resultado = original(conn)
        chamadas.append(1)
        if len(chamadas) == 1:  # escrita concorrente logo depois da contagem da origem
            escritor.execute("INSERT INTO carteira_real VALUES ('TST9', 9)")
            escritor.commit()
        return resultado

    monkeypatch.setattr(backup, "_contar", contar_e_escrever)
    copia = backup.copiar(origem, destino)
    monkeypatch.setattr(backup, "_contar", original)
    escritor.close()
    assert copia.contagens_antes["carteira_real"] == 2
    assert backup.contagens(destino)["carteira_real"] == 2


def test_erro_num_banco_nao_interrompe_os_seguintes(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    _banco(a).close()
    _banco(b).close()
    destino = tmp_path / "saida"
    destino.mkdir()
    (destino / "a.db").write_bytes(b"x")
    assert backup.main([str(destino), str(a), str(b)]) == 1
    relatorio = json.loads((destino / "backup.json").read_text())
    assert "erro" in relatorio[0]
    assert relatorio[1]["iguais"] is True


def test_banco_corrompido_no_meio_entra_no_relatorio(tmp_path):
    ruim, b = tmp_path / "ruim.db", tmp_path / "b.db"
    ruim.write_bytes(b"nao e sqlite" * 100)
    _banco(b).close()
    destino = tmp_path / "saida"
    assert backup.main([str(destino), str(ruim), str(b)]) == 1
    relatorio = json.loads((destino / "backup.json").read_text())
    assert relatorio[0]["origem"] == str(ruim) and "erro" in relatorio[0]
    assert relatorio[1]["iguais"] is True


def test_restauracao_de_teste_nao_fica_no_diretorio(tmp_path):
    a = tmp_path / "a.db"
    _banco(a).close()
    destino = tmp_path / "saida"
    assert backup.main([str(destino), str(a)]) == 0
    assert sorted(p.name for p in destino.iterdir()) == ["a.db", "backup.json"]
