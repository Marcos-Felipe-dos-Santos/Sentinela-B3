"""BUG-3-20: IPCA ainda não divulgado no SIDRA derruba a família; o registro do banco omite chaves.

Auditoria externa do Gemini sobre 284165f..419f010, achado 3 (11/11/2026): o `_ipca` do
`gravar_series` converte o valor de todas as linhas do SIDRA antes de olhar se o mês foi
publicado; o SIDRA traz o mês ainda não divulgado com `V = "..."`, e a família inteira abstém,
sem gravar nem a agenda do IBGE. E o `registro_do_banco` devolve `inflacao` e `pib` sem a
`proveniencia` e o `calendario` que o caminho histórico (`MacroProvider.registro`) traz.
Corrige: F3-A-F8.
"""

import json
import sqlite3
from contextlib import closing

import pytest
from test_series_macro import _gravar, provedor  # noqa: F401  (fixture)
from test_taxa_real_data_passada import COLETA, JANELA, D

from sentinela.data.providers import macro
from sentinela.data.store import migracoes


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def test_mes_nao_divulgado_no_sidra_nao_derruba_a_familia(conn, provedor, monkeypatch):  # noqa: F811
    original = provedor.baixar

    def baixar(url, instante):
        resposta = original(url, instante)
        if "/1737/" not in url:
            return resposta
        linhas = json.loads(resposta.conteudo)
        ultima = linhas[-1]
        linhas.append({**ultima, "D3C": "209912", "D3N": "dezembro 2099", "V": "..."})
        return macro.SnapshotMacro(
            json.dumps(linhas), resposta.fonte, resposta.coleta, resposta.hash_sha256
        )

    monkeypatch.setattr(provedor, "baixar", baixar)
    resumo = _gravar(conn, provedor)
    assert isinstance(resumo["ipca"], int), resumo["ipca"]


def test_registro_do_banco_tem_as_chaves_do_caminho_historico(conn, provedor):  # noqa: F811
    _gravar(conn, provedor)
    do_banco = macro.registro_do_banco(conn, D, JANELA)
    historico = provedor.registro(D, JANELA, coleta=COLETA)
    for bloco in ("inflacao", "pib"):
        assert set(historico[bloco]) <= set(do_banco[bloco]), (
            bloco,
            set(historico[bloco]) - set(do_banco[bloco]),
        )
