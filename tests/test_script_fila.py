"""Testes de `scripts/fila.py` (F3-0a): leitura da fila por trecho, sem abrir o arquivo inteiro."""

import importlib.util
import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "fila.py"

FILA = """# Fila de teste

Cabeçalho com `scripts/fila.py` citado, que não é item.

- [x] **T-1** · docs · `docs: first` — Arquivos: `docs/a.md`.
- [ ] **T-2** · feat · `feat: second` — Arquivos: `scripts/x.py`, `tests/test_x.py`.
- [!] **T-3** · feat · `feat: third` — Arquivos: `sentinela/data/pit/`, `docs/b.md`, `tests/test_y.py`.
- [ ] **T-4** · feat · `feat: fourth` — Arquivos: `sentinela/data/pit/leitor.py`.
- [ ] **T-5** · docs · `docs: fifth` — depende do T-3. Arquivos: `docs/c.md`.
- [ ] **T-6** · feat · `feat: sixth` — Arquivos: `market_engine.py`, `docs/b.md`, `tests/test_y.py`.
- [ ] **T-30** · docs · `docs: thirtieth` — Arquivos: `docs/d.md`.
- [ ] **[DECISÃO] Checkpoint de teste.** O Marcos decide o que vem depois desta linha.
- [ ] **T-7** · feat · `feat: after decision` — Arquivos: `outro.py`.
"""


def _carregar():
    spec = importlib.util.spec_from_file_location("fila_script", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def fila_mod():
    return _carregar()


@pytest.fixture
def arquivos(tmp_path):
    fila = tmp_path / "fila.md"
    fila.write_text(FILA, encoding="utf-8")
    return {
        "fila": fila,
        "diario": tmp_path / "diario.md",
        "pendencias": tmp_path / "pendencias.md",
    }


def _rodar(fila_mod, arquivos, capsys, *args):
    base = [
        "--fila",
        str(arquivos["fila"]),
        "--diario",
        str(arquivos["diario"]),
        "--pendencias",
        str(arquivos["pendencias"]),
    ]
    codigo = fila_mod.main([*base, *args])
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


# status


def test_status_conta_ate_o_primeiro_decisao_aberto(
    fila_mod, arquivos, capsys, monkeypatch
):
    monkeypatch.setattr(fila_mod, "_branch", lambda: "v2/fase-teste")
    codigo, saida, _ = _rodar(fila_mod, arquivos, capsys, "status")
    linhas = saida.splitlines()
    assert codigo == 0
    assert len(linhas) <= 12
    assert "branch: v2/fase-teste" in linhas
    assert "[x]: 1" in linhas
    assert "[ ]: 5" in linhas
    assert "[!]: 1" in linhas
    assert "próximo: T-2" in linhas
    decisao = next(linha for linha in linhas if linha.startswith("[DECISÃO]: "))
    texto = decisao.removeprefix("[DECISÃO]: ")
    assert texto.startswith("- [ ] **[DECISÃO] Checkpoint de teste.**")
    assert len(texto) <= 120


def test_status_corta_a_decisao_em_120_caracteres(
    fila_mod, arquivos, capsys, monkeypatch
):
    monkeypatch.setattr(fila_mod, "_branch", lambda: "b")
    arquivos["fila"].write_text(
        "- [ ] **A-1** · docs · x\n- [ ] **[DECISÃO] " + "y" * 300 + "**\n",
        encoding="utf-8",
    )
    _, saida, _ = _rodar(fila_mod, arquivos, capsys, "status")
    decisao = next(
        linha for linha in saida.splitlines() if linha.startswith("[DECISÃO]: ")
    )
    assert len(decisao.removeprefix("[DECISÃO]: ")) == 120


def test_status_sem_decisao_aberta_conta_a_fila_inteira(
    fila_mod, arquivos, capsys, monkeypatch
):
    monkeypatch.setattr(fila_mod, "_branch", lambda: "b")
    arquivos["fila"].write_text(
        "- [x] **A-1** · x\n- [ ] **A-2** · y\n", encoding="utf-8"
    )
    _, saida, _ = _rodar(fila_mod, arquivos, capsys, "status")
    linhas = saida.splitlines()
    assert "[x]: 1" in linhas
    assert "[ ]: 1" in linhas
    assert "próximo: A-2" in linhas
    assert "[DECISÃO]: nenhum" in linhas


def test_branch_dentro_de_repositorio_le_o_nome(fila_mod, tmp_path, monkeypatch):
    git = [
        "git",
        "-c",
        "user.name=teste",
        "-c",
        "user.email=teste@example.invalid",
        "-c",
        "commit.gpgsign=false",
    ]
    for variavel in [v for v in os.environ if v.startswith("GIT_")]:
        monkeypatch.delenv(variavel)
    subprocess.run(
        [*git, "init", "-q", "-b", "v2/fase-teste", str(tmp_path)], check=True
    )
    subprocess.run(
        [*git, "-C", str(tmp_path), "commit", "-q", "--allow-empty", "-m", "x"],
        check=True,
    )
    monkeypatch.chdir(tmp_path)
    assert fila_mod._branch() == "v2/fase-teste"


def test_branch_fora_de_repositorio_nao_quebra(fila_mod, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert fila_mod._branch() == "desconhecido"


# proximo


def test_proximo_imprime_so_a_linha_do_item(fila_mod, arquivos, capsys):
    codigo, saida, _ = _rodar(fila_mod, arquivos, capsys, "proximo")
    assert codigo == 0
    assert (
        saida
        == "- [ ] **T-2** · feat · `feat: second` — Arquivos: `scripts/x.py`, `tests/test_x.py`.\n"
    )


def test_proximo_com_decisao_a_frente_sai_com_3(fila_mod, arquivos, capsys):
    texto = arquivos["fila"].read_text(encoding="utf-8")
    for item in ("T-2", "T-4", "T-5", "T-6", "T-30"):
        texto = texto.replace(f"- [ ] **{item}**", f"- [x] **{item}**")
    arquivos["fila"].write_text(texto, encoding="utf-8")
    codigo, saida, _ = _rodar(fila_mod, arquivos, capsys, "proximo")
    assert codigo == 3
    assert saida.startswith("- [ ] **[DECISÃO] Checkpoint de teste.**")
    assert saida.count("\n") == 1


def test_proximo_sem_item_aberto_falha(fila_mod, arquivos, capsys):
    arquivos["fila"].write_text("- [x] **A-1** · x\n", encoding="utf-8")
    codigo, saida, erro = _rodar(fila_mod, arquivos, capsys, "proximo")
    assert codigo == 1
    assert saida == ""
    assert erro


# item


def test_item_imprime_so_a_linha(fila_mod, arquivos, capsys):
    codigo, saida, _ = _rodar(fila_mod, arquivos, capsys, "item", "T-3")
    assert codigo == 0
    assert saida.startswith("- [!] **T-3**")
    assert saida.count("\n") == 1


def test_item_nao_confunde_prefixo(fila_mod, arquivos, capsys):
    _, saida, _ = _rodar(fila_mod, arquivos, capsys, "item", "T-3")
    assert "T-30" not in saida


def test_item_inexistente_falha(fila_mod, arquivos, capsys):
    codigo, saida, erro = _rodar(fila_mod, arquivos, capsys, "item", "T-99")
    assert codigo == 2
    assert saida == ""
    assert "T-99" in erro


def test_item_duplicado_falha(fila_mod, arquivos, capsys):
    arquivos["fila"].write_text(FILA + "- [ ] **T-2** · repetido\n", encoding="utf-8")
    codigo, saida, erro = _rodar(fila_mod, arquivos, capsys, "item", "T-2")
    assert codigo == 2
    assert saida == ""
    assert "T-2" in erro


# marcar


def test_marcar_altera_exatamente_uma_linha(fila_mod, arquivos, capsys):
    antes = arquivos["fila"].read_text(encoding="utf-8").splitlines()
    codigo, _, _ = _rodar(fila_mod, arquivos, capsys, "marcar", "T-2", "x")
    depois = arquivos["fila"].read_text(encoding="utf-8").splitlines()
    assert codigo == 0
    diferentes = [
        i for i, (a, b) in enumerate(zip(antes, depois, strict=True)) if a != b
    ]
    assert len(diferentes) == 1
    assert depois[diferentes[0]] == antes[diferentes[0]].replace(
        "- [ ] **T-2**", "- [x] **T-2**"
    )


def test_marcar_bloqueado(fila_mod, arquivos, capsys):
    codigo, _, _ = _rodar(fila_mod, arquivos, capsys, "marcar", "T-4", "!")
    assert codigo == 0
    assert "- [!] **T-4** · feat" in arquivos["fila"].read_text(encoding="utf-8")


def test_marcar_preserva_fim_de_linha_final(fila_mod, arquivos, capsys):
    _rodar(fila_mod, arquivos, capsys, "marcar", "T-2", "x")
    assert arquivos["fila"].read_text(encoding="utf-8").endswith("\n")


@pytest.mark.parametrize("ident", ["T-99", "T-2"])
def test_marcar_falha_sem_tocar_o_arquivo(fila_mod, arquivos, capsys, ident):
    if ident == "T-2":
        arquivos["fila"].write_text(
            FILA + "- [ ] **T-2** · repetido\n", encoding="utf-8"
        )
    antes = arquivos["fila"].read_bytes()
    codigo, _, erro = _rodar(fila_mod, arquivos, capsys, "marcar", ident, "x")
    assert codigo == 2
    assert ident in erro
    assert arquivos["fila"].read_bytes() == antes


def test_marcar_recusa_estado_invalido(fila_mod, arquivos, capsys):
    antes = arquivos["fila"].read_bytes()
    with pytest.raises(SystemExit):
        _rodar(fila_mod, arquivos, capsys, "marcar", "T-2", "?")
    assert arquivos["fila"].read_bytes() == antes


# independentes


def test_independentes_exclui_citacao_e_caminho_compartilhado(
    fila_mod, arquivos, capsys
):
    codigo, saida, _ = _rodar(fila_mod, arquivos, capsys, "independentes", "T-3")
    assert codigo == 0
    # T-4 compartilha `sentinela/data/pit/` (prefixo); T-5 cita T-3; T-6 só compartilha
    # caminhos de tests/ e docs/, que não contam; T-7 está depois do [DECISÃO].
    assert saida.splitlines() == ["T-2", "T-6", "T-30"]


def test_independentes_de_item_inexistente_falha(fila_mod, arquivos, capsys):
    codigo, saida, _ = _rodar(fila_mod, arquivos, capsys, "independentes", "T-99")
    assert codigo == 2
    assert saida == ""


def test_independentes_caminho_igual_conta(fila_mod, arquivos, capsys):
    arquivos["fila"].write_text(
        "- [!] **A-1** · x — `market_engine.py`.\n"
        "- [ ] **A-2** · y — `market_engine.py`.\n"
        "- [ ] **A-3** · z — `fii_engine.py`.\n",
        encoding="utf-8",
    )
    _, saida, _ = _rodar(fila_mod, arquivos, capsys, "independentes", "A-1")
    assert saida.splitlines() == ["A-3"]


def test_caminhos_ignoram_mensagem_de_commit_e_comando(fila_mod):
    linha = "- [ ] **A-1** · feat · `feat: add x` — rode `python scripts/fila.py status`; `docs/x.md`."
    assert fila_mod._caminhos(linha) == {"scripts/fila.py"}


# diario


def test_diario_anexa_sem_imprimir(fila_mod, arquivos, capsys, tmp_path):
    arquivos["diario"].write_text("# Diário\n\n### A-1\n- antigo\n", encoding="utf-8")
    entrada = tmp_path / "entrada.md"
    entrada.write_text(
        "### T-2 — feat: second\n- **Status:** sucesso\n", encoding="utf-8"
    )
    codigo, saida, _ = _rodar(fila_mod, arquivos, capsys, "diario", str(entrada))
    assert codigo == 0
    assert saida == ""
    assert arquivos["diario"].read_text(encoding="utf-8") == (
        "# Diário\n\n### A-1\n- antigo\n\n### T-2 — feat: second\n- **Status:** sucesso\n"
    )


def test_diario_completa_quebra_de_linha_que_falta(
    fila_mod, arquivos, capsys, tmp_path
):
    arquivos["diario"].write_text("# Diário", encoding="utf-8")
    entrada = tmp_path / "entrada.md"
    entrada.write_text("### T-2", encoding="utf-8")
    _rodar(fila_mod, arquivos, capsys, "diario", str(entrada))
    assert arquivos["diario"].read_text(encoding="utf-8") == "# Diário\n\n### T-2\n"


def test_diario_com_entrada_inexistente_falha_sem_tocar(
    fila_mod, arquivos, capsys, tmp_path
):
    arquivos["diario"].write_text("# Diário\n", encoding="utf-8")
    codigo, _, erro = _rodar(
        fila_mod, arquivos, capsys, "diario", str(tmp_path / "nada.md")
    )
    assert codigo == 2
    assert erro
    assert arquivos["diario"].read_text(encoding="utf-8") == "# Diário\n"


# pendencia


def test_pendencia_cria_arquivo_e_acrescenta_linha_datada(
    fila_mod, arquivos, capsys, monkeypatch
):
    monkeypatch.setattr(fila_mod, "_hoje", lambda: date(2026, 11, 9))
    codigo, saida, _ = _rodar(
        fila_mod, arquivos, capsys, "pendencia", "T-3", "fonte fora do ar"
    )
    assert codigo == 0
    assert saida == ""
    texto = arquivos["pendencias"].read_text(encoding="utf-8")
    assert texto.startswith("# Pendências do loop\n")
    assert texto.endswith("- 2026-11-09 · T-3 · fonte fora do ar\n")

    monkeypatch.setattr(fila_mod, "_hoje", lambda: date(2026, 11, 10))
    _rodar(
        fila_mod,
        arquivos,
        capsys,
        "pendencia",
        "T-4",
        "decisão provisória: x → abstenção",
    )
    linhas = arquivos["pendencias"].read_text(encoding="utf-8").splitlines()
    assert linhas[-2:] == [
        "- 2026-11-09 · T-3 · fonte fora do ar",
        "- 2026-11-10 · T-4 · decisão provisória: x → abstenção",
    ]


def test_pendencia_preserva_arquivo_existente(fila_mod, arquivos, capsys, monkeypatch):
    monkeypatch.setattr(fila_mod, "_hoje", lambda: date(2026, 11, 9))
    arquivos["pendencias"].write_text("# Minhas\n\n- antiga", encoding="utf-8")
    _rodar(fila_mod, arquivos, capsys, "pendencia", "T-2", "nova")
    assert arquivos["pendencias"].read_text(encoding="utf-8") == (
        "# Minhas\n\n- antiga\n- 2026-11-09 · T-2 · nova\n"
    )


def test_pendencia_texto_em_uma_linha(fila_mod, arquivos, capsys, monkeypatch):
    monkeypatch.setattr(fila_mod, "_hoje", lambda: date(2026, 11, 9))
    _rodar(fila_mod, arquivos, capsys, "pendencia", "T-2", "linha 1\nlinha 2")
    assert (
        arquivos["pendencias"]
        .read_text(encoding="utf-8")
        .endswith("- 2026-11-09 · T-2 · linha 1 linha 2\n")
    )


def test_caminhos_padrao_apontam_para_docs_loop(fila_mod):
    assert fila_mod.FILA_PADRAO == Path("docs/loop/fila.md")
    assert fila_mod.DIARIO_PADRAO == Path("docs/loop/diario.md")
    assert fila_mod.PENDENCIAS_PADRAO == Path("docs/loop/pendencias.md")


def test_marcar_preserva_crlf(fila_mod, arquivos, capsys):
    arquivos["fila"].write_bytes(
        b"- [ ] **A-1** \xc2\xb7 x\r\n- [ ] **A-2** \xc2\xb7 y\r\n"
    )
    _rodar(fila_mod, arquivos, capsys, "marcar", "A-1", "x")
    assert arquivos["fila"].read_bytes() == (
        b"- [x] **A-1** \xc2\xb7 x\r\n- [ ] **A-2** \xc2\xb7 y\r\n"
    )


def test_independentes_de_item_duplicado_falha(fila_mod, arquivos, capsys):
    arquivos["fila"].write_text(FILA + "- [ ] **T-3** · repetido\n", encoding="utf-8")
    codigo, saida, erro = _rodar(fila_mod, arquivos, capsys, "independentes", "T-3")
    assert codigo == 2
    assert saida == ""
    assert "T-3" in erro


def test_diario_cria_destino_ausente(fila_mod, arquivos, capsys, tmp_path):
    entrada = tmp_path / "entrada.md"
    entrada.write_text("### T-2\n", encoding="utf-8")
    _rodar(fila_mod, arquivos, capsys, "diario", str(entrada))
    assert arquivos["diario"].read_text(encoding="utf-8") == "### T-2\n"


@pytest.mark.parametrize(
    "comando", [["status"], ["proximo"], ["item", "T-2"], ["marcar", "T-2", "x"]]
)
def test_fila_ausente_sai_com_erro_e_nao_com_vazio(fila_mod, arquivos, capsys, comando):
    arquivos["fila"].unlink()
    codigo, saida, erro = _rodar(fila_mod, arquivos, capsys, *comando)
    assert codigo == 2
    assert saida == ""
    assert "não encontrado" in erro


def test_diario_preserva_crlf(fila_mod, arquivos, capsys, tmp_path):
    arquivos["diario"].write_bytes(b"# D\r\n\r\n### A-1\r\n")
    entrada = tmp_path / "entrada.md"
    entrada.write_bytes(b"### T-2\n- ok\n")
    _rodar(fila_mod, arquivos, capsys, "diario", str(entrada))
    assert (
        arquivos["diario"].read_bytes()
        == b"# D\r\n\r\n### A-1\r\n\r\n### T-2\r\n- ok\r\n"
    )


def test_pendencia_preserva_crlf(fila_mod, arquivos, capsys, monkeypatch):
    monkeypatch.setattr(fila_mod, "_hoje", lambda: date(2026, 11, 9))
    arquivos["pendencias"].write_bytes(b"# P\r\n\r\n- antiga\r\n")
    _rodar(fila_mod, arquivos, capsys, "pendencia", "T-2", "nova")
    assert arquivos["pendencias"].read_bytes() == (
        "# P\r\n\r\n- antiga\r\n- 2026-11-09 · T-2 · nova\r\n".encode()
    )
