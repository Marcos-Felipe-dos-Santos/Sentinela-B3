"""F2C-40: representações do mesmo inteiro devem produzir a mesma saída."""

import numpy as np
import pytest

from tests.test_valuation_engine import _com_divida


@pytest.mark.parametrize("tipo", [np.int32, np.int64, np.uint64])
@pytest.mark.parametrize("valor", [1, 7])
def test_inteiro_numerico_equivale_ao_nativo(tipo, valor: int) -> None:
    # Invariância de representação, sem usar o motor como oráculo de fórmula/nota.
    assert _com_divida(tipo(valor)) == _com_divida(valor)
