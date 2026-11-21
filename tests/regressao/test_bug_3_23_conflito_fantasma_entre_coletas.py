"""BUG-3-23: conflito do Tesouro de uma coleta antiga continua lido depois da correção do arquivo.

Revisão do F3-A-F7 (11/11/2026): `_ultimas` escolhe a coleta mais recente por (série, data).
Uma coleta com duas linhas conflitantes grava `tesouro|NTN-B|venc` e `tesouro|NTN-B|venc|2`;
a coleta seguinte, com o arquivo já corrigido, grava só a série sem sufixo, e a `|2` antiga
continua sendo a mais recente da série dela. O `registro_do_banco` junta as duas e marca o
conflito para sempre naquela data-base, enquanto o caminho histórico, que lê o arquivo
corrigido, dá número. O desvio vai para a abstenção. Corrige: F3-A-F7b.
"""

import os
import sqlite3
from contextlib import closing
from datetime import timedelta

from test_series_macro import _alterar_tesouro, _ultima_ntnb, provedor  # noqa: F401
from test_taxa_real_data_passada import COLETA, JANELA, D

from sentinela.data.providers import macro
from sentinela.data.store import migracoes


def test_coleta_corrigida_apaga_o_conflito_da_anterior(provedor, tmp_path):  # noqa: F811
    caminho = tmp_path / "macro" / "tesouro" / "precotaxatesourodireto.csv"
    original = caminho.read_text(encoding="utf-8")

    def conflitante(texto):
        campos = _ultima_ntnb(texto).split(";")
        campos[3] = "9,99"
        return texto.rstrip("\n") + "\n" + ";".join(campos) + "\n"

    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        _alterar_tesouro(tmp_path, conflitante)
        macro.gravar_series(
            conn, provedor, coleta=COLETA, datas=[D.date()], janela=JANELA
        )
        segunda = COLETA + timedelta(days=1)
        caminho.write_text(original, encoding="utf-8")
        os.utime(caminho, (segunda.timestamp(), segunda.timestamp()))
        macro.gravar_series(
            conn, provedor, coleta=segunda, datas=[D.date()], janela=JANELA
        )
        do_banco = macro.registro_do_banco(conn, D, JANELA)
    historico = provedor.registro(D, JANELA, coleta=segunda)
    assert "abstencao" not in historico, historico
    assert "abstencao" not in do_banco, do_banco
