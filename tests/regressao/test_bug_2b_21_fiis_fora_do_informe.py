"""Lacuna de cobertura BTCI11/TRPL11, destino F2C-21 (proposta da 2C).

Fontes B3, consultadas em 20/10/2026, anteriores ao corte da auditoria:
TRPL11: https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias/Detail?agencia=18&dataNoticia=2026-01-07+14%3A20%3A39&idNoticia=3196072
BTCI11: https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias/Detail?agencia=15&dataNoticia=2026-02-09+05%3A04%3A31&idNoticia=3233160

Ambos são FII. A falta de ISIN no Informe não é evidência de outra classe.
A correção deverá enriquecer o índice com identidade oficial complementar;
não deduzir FII de todo CI ou forçar UNIT pela lista antiga. Este caso mínimo
registra o caminho que hoje perde a classe; a fixture poderá ganhar a fonte
complementar quando o item 2C implementar sua entrada, preservando a asserção.
"""

from datetime import date

import pytest

from sentinela.data.providers.b3_cotahist import Cotacao
from sentinela.data.referencia.montagem import montar_outros


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-21 · FII da B3 fora do Informe vira UNKNOWN · corrige: F2C-21",
)
@pytest.mark.parametrize(
    "ticker,isin", [("BTCI11", "BRBTCICTF005"), ("TRPL11", "BRTRPLCTF015")]
)
def test_fii_confirmado_na_b3_nao_perde_classe_fora_do_informe(ticker, isin):
    cotacao = Cotacao(
        date(2026, 10, 15), ticker, "12", "010", "CI", isin, 1.0, 100.0, 100, 1, 1
    )
    (registro,) = montar_outros(
        [cotacao], set(), {"arquivo": "COTAHIST público", "data": "2026-10-15"}
    )
    assert registro.classe == "FII"
