"""BUG-3-37: a identidade do emissor abstém sem tentar o ISIN do ticker no COTAHIST.

Decisão 43 do Marcos (15/11/2026, DD-74), sobre a decisão 33: antes de qualquer
afrouxamento, o ISIN do ticker é provado pelo CODISI do COTAHIST do pregão (fonte
oficial e datada) e soma aos ISINs da companhia se o código do emissor bater; as
partes (a) a (d) da decisão 33 são conferidas por inteiro na leitura.

Fixture pública: as respostas oficiais da B3 da Lojas Renner (contrato D18). A relação
traz 6 registros PN e o GetDetail só o ISIN ON: a coleta grava "espécie PN da relação
sem ISIN da companhia no GetDetail". Um pregão de LREN4 com CODISI BRLRENACNPR8 prova o
ISIN PN da mesma raiz; com ele, a parte (b) (complemento contra a relação) passa.
"""

import sqlite3
import zipfile
from contextlib import closing
from datetime import date

from test_cotahist import _linha
from test_eventos_societarios import COLETA, _obter

from sentinela.data.providers import b3_cotahist, b3_proventos
from sentinela.data.store import migracoes


def test_isin_pn_do_pregao_completa_a_conferencia_da_decisao_33(tmp_path):
    relacao = b3_proventos.coletar(8133, COLETA, _obter())
    assert relacao.identidade.endswith(
        "espécie PN da relação sem ISIN da companhia no GetDetail"
    )
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        b3_proventos.gravar_proventos(conn, relacao, 8133)
        caminho = tmp_path / "COTAHIST_D20261030.ZIP"
        with zipfile.ZipFile(caminho, "w") as zf:
            linha = _linha(DATA="20261030", CODNEG="LREN4", ESPECI="PN",
                           CODISI="BRLRENACNPR8")  # fmt: skip
            zf.writestr("COTAHIST.TXT", linha.encode("latin-1"))
        b3_cotahist.carregar(conn, caminho, fonte="b3", coleta=COLETA.isoformat())
        lidos = b3_proventos.proventos_ate(
            conn, "LREN", date(2026, 11, 2), por_publicacao=True, ticker="LREN4"
        )
    assert "abstencao" not in lidos
    # sem pregões em volta das datas com, a data ex fica sem prova; a relação inteira chega
    lidas = lidos["proventos"] + lidos["sem_prova"]
    assert len(lidas) == 99 and {p["especie"] for p in lidas} == {"ON", "PN"}
