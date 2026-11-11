"""BUG-3-18: cada observação da Selic gravada com a fonte e o hash da primeira janela do SGS.

Auditoria externa do Gemini sobre 284165f..419f010 (achado 1, 11/11/2026): o `serie_sgs`
baixa a série 432 em janelas de até 10 anos e devolve a proveniência de cada uma, mas o
`gravar_series` (`_selic`) grava `proveniencia[0]` em todas as observações. Observação de
outra janela fica com a URL e o hash de um conteúdo que não a contém. Corrige: F3-A-F6.
"""

import hashlib
import json
import re
import sqlite3
from contextlib import closing

import pytest
from test_macro_por_data import _sgs_oficial
from test_taxa_real_data_passada import COLETA, JANELA, D, _provedor

from sentinela.data.providers import macro
from sentinela.data.store import migracoes

_DATA = re.compile(r"dataInicial=(\d{2}/\d{2}/\d{4})&dataFinal=(\d{2}/\d{2}/\d{4})")


def _dia(texto):
    dia, mes, ano = texto.split("/")
    return f"{ano}-{mes}-{dia}"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG-3-18 · Selic gravada com o hash da primeira janela · corrige: F3-A-F6",
)
def test_cada_observacao_com_a_fonte_e_o_hash_da_sua_janela(tmp_path, monkeypatch):
    provedor, _ = _provedor(tmp_path, monkeypatch, COLETA)
    original = provedor.baixar
    janelas = {}

    def baixar(url, instante):
        if "bcdata.sgs" not in url:
            return original(url, instante)
        hash_janela = hashlib.sha256(url.encode()).hexdigest()  # distinto por janela
        de, ate = _DATA.search(url).groups()
        janelas[url] = (_dia(de), _dia(ate), hash_janela)
        observacoes = json.loads(_sgs_oficial(url).text)
        if _dia(de) <= "2015-01-02" <= _dia(ate):
            # a fixture oficial começa em 2025: uma observação na janela 2009–2019 faz a
            # Selic vir de duas janelas, e `[0]` ou `[-1]` não passam
            observacoes.insert(0, {"data": "02/01/2015", "valor": "11.75"})
        return macro.SnapshotMacro(
            json.dumps(observacoes), url, instante.isoformat(), hash_janela
        )

    monkeypatch.setattr(provedor, "baixar", baixar)
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        resumo = macro.gravar_series(
            conn, provedor, coleta=COLETA, datas=[D.date()], janela=JANELA
        )
        assert isinstance(resumo["selic"], int) and resumo["selic"] > 0
        linhas = conn.execute(
            "SELECT data, fonte, hash_sha256 FROM series_macro WHERE serie = 'sgs_432' "
            "ORDER BY data"
        ).fetchall()
    assert len({h for _, _, h in janelas.values()}) >= 2
    assert len({fonte for _, fonte, _ in linhas}) >= 2  # linhas de duas janelas
    for data, fonte, hash_linha in linhas:
        dono = [u for u, (de, ate, _) in janelas.items() if de <= data <= ate]
        assert len(dono) == 1, data
        assert (fonte, hash_linha) == (dono[0], janelas[dono[0]][2]), data
