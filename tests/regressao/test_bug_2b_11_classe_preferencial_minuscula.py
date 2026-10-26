"""BUG-2B-11: a sigla da classe preferencial não é posta em caixa alta.

A montagem do índice guarda a `Sigla_Classe_Acao_Preferencial` da ação avulsa como veio
(só a lista `classes_preferenciais` vai para caixa alta), e `acoes_cvm.especie_da_classe`
devolve `"pna"` para `"pna"`. Nenhuma sigla minúscula no índice atual. Origem: F2B-21,
pergunta 8 (2ª passada do Gemini).
"""

import pytest

from sentinela.data import acoes_cvm
from tests.test_referencia import _fca
from tests.test_referencia import _indice as _indice_oficial

BUG = pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-11 · sigla da classe preferencial sem caixa alta · corrige: F2C-20",
)


@BUG
def test_especie_da_classe_minuscula():
    assert acoes_cvm.especie_da_classe("pna") == "PN"


@BUG
def test_indice_guarda_a_sigla_em_caixa_alta():
    fca = _fca(
        {
            "Codigo_Negociacao": "TSTB5",
            "Valor_Mobiliario": "Ações Preferenciais",
        }
    )
    fca["Sigla_Classe_Acao_Preferencial"] = ["pna"]
    registro = _indice_oficial(fca=fca).registros["TSTB5"]
    assert registro.classe_preferencial == "PNA"
