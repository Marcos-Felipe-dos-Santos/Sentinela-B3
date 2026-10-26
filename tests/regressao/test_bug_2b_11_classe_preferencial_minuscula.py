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


def test_especie_da_classe_minuscula():
    assert acoes_cvm.especie_da_classe("pna") == "PN"


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


@pytest.mark.parametrize("sigla", ["pna", "PNA", " pNa "])
def test_classe_avulsa_e_lista_compartilham_sigla_normalizada(sigla: str) -> None:
    fca = _fca(
        {"Codigo_Negociacao": "TSTB5", "Valor_Mobiliario": "Ações Preferenciais"}
    )
    fca["Sigla_Classe_Acao_Preferencial"] = [sigla]
    registro = _indice_oficial(fca=fca).registros["TSTB5"]
    assert registro.classe_preferencial == "PNA"
    assert registro.classes_preferenciais == ["PNA"]
    assert registro.ticker == "TSTB5"
    assert registro.especie == "PN"


def test_unit_e_classes_preferenciais_preservam_pna_e_pnb_distintas() -> None:
    fca = _fca(
        {"Codigo_Negociacao": "TSTB5", "Valor_Mobiliario": "Ações Preferenciais"},
        {"Codigo_Negociacao": "TSTB6", "Valor_Mobiliario": "Ações Preferenciais"},
        {
            "Codigo_Negociacao": "TSTB11",
            "Valor_Mobiliario": "Units",
            "Composicao_BDR_Unit": "1 on / 2 pna / 1 pnb",
        },
    )
    fca["Sigla_Classe_Acao_Preferencial"] = ["pna", "pnb", None]
    registros = _indice_oficial(fca=fca).registros
    assert registros["TSTB5"].classe_preferencial == "PNA"
    assert registros["TSTB6"].classe_preferencial == "PNB"
    unit = registros["TSTB11"]
    assert unit.acoes_por_unit == {"ON": 1, "PNA": 2, "PNB": 1}
    assert unit.classes_preferenciais == ["PNA", "PNB"]
    assert unit.classe_preferencial is None
    assert unit.especie is None
    assert unit.classe == "UNIT"


def test_sigla_nao_supre_composicao_ausente_da_unit() -> None:
    fca = _fca({"Codigo_Negociacao": "TSTB11", "Valor_Mobiliario": "Units"})
    fca["Sigla_Classe_Acao_Preferencial"] = ["pna"]
    unit = _indice_oficial(fca=fca).registros["TSTB11"]
    assert unit.acoes_por_unit is None
    assert unit.classe_preferencial is None


@pytest.mark.parametrize("sigla", ["pna", "PNA", "pnb", "PNB", " pNa "])
def test_especie_preferencial_normaliza_so_caixa_e_espacos(sigla: str) -> None:
    assert acoes_cvm.especie_da_classe(sigla) == "PN"
