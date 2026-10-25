"""BUG-2A-23: o motor de ações converte `divida_liq_ebitda` em texto pt-BR.

`valuation_engine.py:278-291` converte "9,5" em 9,5 e aplica a penalidade de dívida, mas
nenhuma fonte da cascata entrega texto nesse campo desde o F2A-22; os testes desse caminho só
conferem `0 <= score_final <= 100`. Comportamento decidido (F2B-45): valor que não é número
finito, texto inclusive, não recebe a penalidade e ganha o aviso "alavancagem não avaliada".
Origem: 2ª passada do Gemini (15/10/2026).
"""

from apoio_escopo import de_empresa

from tests.test_saidas_finitas import ACAO
from valuation_engine import ValuationEngine


def test_divida_em_texto_nao_e_avaliada():
    resultado = ValuationEngine().processar(
        de_empresa({**ACAO, "preco_atual": 10.0, "divida_liq_ebitda": "9,5"})
    )
    assert "Dívida elevada" not in resultado["riscos"]
    # F2B-45 (decisão do Marcos de 25/10/2026): o aviso fica num campo próprio.
    assert resultado["aviso_alavancagem"].startswith("alavancagem não avaliada")
