"""BUG-4-13: a auditoria lê o banco antigo e grava as posições da carteira fora de `outputs/`.

`auditoria.py` lia `sentinela_v6.db`, aposentado pelo banco único (F3-2c), e gravava o
relatório `.txt` e o `.json` no diretório corrente, com cada posição da carteira (ticker,
quantidade, preço médio e data). Na raiz do repositório público, esses arquivos ficavam fora
de `outputs/`, que o git ignora (achado 15 do Gemini; lista do Marcos de 23/11).

Banco único temporário em `tmp_path` (fora do `/tmp`, pelo `--basetemp` do executor), com
posições fictícias; diretório corrente no `tmp_path`.
"""

import json

import pytest

import auditoria
from database import DatabaseManager
from sentinela.data.store import unico

POSICOES = {"TSTA3": (7, 12.34), "TSTB4": (3, 56.78)}


@pytest.fixture
def auditar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    banco = DatabaseManager(unico.caminho_padrao())
    for ticker, (quantidade, preco) in POSICOES.items():
        banco.adicionar_posicao(ticker, quantidade, preco)

    def rodar(*flags: str) -> tuple[str, dict]:
        monkeypatch.setattr(
            auditoria.sys, "argv", ["auditoria.py", "--db-only", *flags]
        )
        monkeypatch.setattr(
            auditoria, "_rel", {"meta": {}, "selic": {}, "banco": {}, "tickers": {}}
        )
        auditoria.main()
        assert not list(tmp_path.glob("auditoria_*")), "relatório fora de outputs/"
        (txt,) = (tmp_path / "outputs" / "auditoria").glob("auditoria_*.txt")
        (arquivo_json,) = (tmp_path / "outputs" / "auditoria").glob("auditoria_*.json")
        return txt.read_text(encoding="utf-8"), json.loads(
            arquivo_json.read_text("utf-8")
        )

    return rodar


def test_relatorio_le_o_banco_unico_e_grava_so_a_contagem_em_outputs(auditar):
    texto, dados = auditar()

    assert dados["banco"]["carteira"] == {"posicoes": 2}
    assert dados["banco"]["arquivo"].endswith(unico.BANCO_UNICO)
    for ticker in POSICOES:
        assert ticker not in texto
        assert ticker not in json.dumps(dados)
    assert "12.34" not in texto
    assert "56.78" not in texto
    assert "Total investido" not in texto
    assert "2 posições" in texto


def test_flag_explicita_grava_as_posicoes_ainda_em_outputs(auditar):
    texto, dados = auditar("--com-carteira")

    tickers = sorted(p["ticker"] for p in dados["banco"]["carteira"]["itens"])
    assert tickers == sorted(POSICOES)
    assert dados["banco"]["carteira"]["posicoes"] == 2
    for ticker in POSICOES:
        assert ticker in texto
