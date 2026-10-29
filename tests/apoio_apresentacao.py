"""Invariantes independentes da apresentação aprovada em28/10/2026."""

import math


def verificar_lentes(resultado):
    assert "score_final" not in resultado
    assert "recomendacao" not in resultado
    assert resultado["lentes"]
    for lente in resultado["lentes"].values():
        assert lente["regime"]
        assert isinstance(lente["janela"], dict)
        if lente["valor"] is None:
            assert lente["abstencao"]
            assert lente["distancia_ao_preco_pct"] is None
        else:
            assert math.isfinite(lente["valor"]) and lente["valor"] > 0
            assert not lente["abstencao"]
            assert math.isfinite(lente["distancia_ao_preco_pct"])
