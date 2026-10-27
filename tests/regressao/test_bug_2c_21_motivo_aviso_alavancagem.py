"""F2C-40: preservar no aviso o motivo de ausência já demonstrado pela CVM."""

import pytest
from apoio_bancos import enriquecer_bancos

from sentinela.data.divida_liquida import MOTIVO_EBITDA, MOTIVO_MODELO
from tests.test_valuation_bancos import BANCO, _processar
from tests.test_valuation_escopo import DADOS
from valuation_engine import ValuationEngine


@pytest.mark.parametrize(
    "modelo,motivo", [("empresa", MOTIVO_EBITDA), ("banco", MOTIVO_MODELO)]
)
def test_aviso_mostra_motivo_cvm(modelo: str, motivo: str) -> None:
    campos = {
        "divida_liq_ebitda": None,
        "alavancagem_motivos": {"divida_liq_ebitda": motivo},
    }
    if modelo == "banco":
        r = _processar(enriquecer_bancos({**BANCO, **campos}))
    else:
        r = ValuationEngine().processar(
            {**DADOS, **campos, "classe_ativo": "STOCK", "modelo_bpp": "empresa"}
        )
    assert motivo in r["aviso_alavancagem"]


@pytest.mark.parametrize(
    "motivos",
    [
        None,
        {},
        "texto",
        {"divida_liq_ebitda": None},
        {"divida_liq_ebitda": 0},
        {"divida_liq_ebitda": ""},
        {"divida_liq_ebitda": "   "},
    ],
)
def test_motivo_ausente_ou_invalido_conserva_aviso_generico(motivos) -> None:
    r = ValuationEngine().processar(
        {
            **DADOS,
            "classe_ativo": "STOCK",
            "modelo_bpp": "empresa",
            "divida_liq_ebitda": None,
            "alavancagem_motivos": motivos,
        }
    )
    assert (
        r["aviso_alavancagem"]
        == "alavancagem não avaliada: dívida líquida/EBITDA ausente"
    )


def test_mudar_apenas_motivo_nao_muda_numeros_ou_classificacao() -> None:
    dados = {
        **DADOS,
        "classe_ativo": "STOCK",
        "modelo_bpp": "empresa",
        "divida_liq_ebitda": None,
    }
    anterior = ValuationEngine().processar(dict(dados))
    informado = ValuationEngine().processar(
        {**dados, "alavancagem_motivos": {"divida_liq_ebitda": "  EBITDA ≤ 0  "}}
    )
    assert informado.pop("aviso_alavancagem").endswith("EBITDA ≤ 0")
    anterior.pop("aviso_alavancagem")
    assert informado == anterior
