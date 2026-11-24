"""BUG-4-02: o DY da cascata impede ou altera a saída da lente do FII."""

import pytest
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

from config import MACRO
from fii_engine import FIIEngine

DY_INFORME = 0.09
PRECO = 100.0
VALOR = DY_INFORME * PRECO / (0.07 + MACRO.FII_SPREAD_TIJOLO)


@pytest.mark.parametrize(
    "dy_cascata",
    [
        pytest.param({}, id="ausente"),
        pytest.param({"dy": 0.0}, id="zero"),
        pytest.param({"dy": 0.50}, id="invalido"),
        pytest.param({"dy": DY_INFORME}, id="igual"),
        pytest.param({"dy": 0.06}, id="divergente"),
    ],
)
def test_valor_e_dy_do_fii_vem_do_informe(dy_cascata):
    dados = enriquecer_fii({"ticker": "TSTF11", "preco_atual": PRECO, "dy": DY_INFORME})
    dados.pop("dy")
    dados.update(dy_cascata)

    resultado = FIIEngine().analisar(dados, as_of=AS_OF_GORDON)

    lente = resultado["lentes"]["Rendimento do FII"]
    assert lente["abstencao"] is None
    assert lente["valor"] == pytest.approx(VALOR)
    assert resultado["dy"] == pytest.approx(DY_INFORME)
    assert resultado["dy_efetivo"] == pytest.approx(DY_INFORME)


@pytest.mark.parametrize("dy_historico", [0.0, 0.06])
def test_fii_por_publicacao_preserva_o_dy_do_motor_historico(dy_historico):
    dados = enriquecer_fii({"ticker": "TSTF11", "preco_atual": PRECO, "dy": DY_INFORME})
    dados["disponibilidade_por_publicacao"] = True
    dados["dy"] = dy_historico

    resultado = FIIEngine().analisar(dados, as_of=AS_OF_GORDON)

    lente = resultado["lentes"]["Rendimento do FII"]
    if dy_historico == 0.0:
        assert lente["valor"] is None
        assert lente["abstencao"] == "Dados insuficientes (DY ausente ou inválido)"
    else:
        assert lente["valor"] == pytest.approx(VALOR)
        assert resultado["dy"] == resultado["dy_efetivo"] == dy_historico
