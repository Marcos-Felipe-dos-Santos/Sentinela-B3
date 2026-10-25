"""Fator positivo que perde representação não pode apagar um fluxo real."""

import pytest

from sentinela.domain.units import BRL, Inflacao, fluxo_nominal


def test_fluxo_nominal_recusa_fator_zerado_por_underflow():
    with pytest.raises(ValueError, match="fator"):
        fluxo_nominal(BRL(1), Inflacao(-0.5), 10000)
