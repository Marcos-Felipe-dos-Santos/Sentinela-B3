"""BUG-2C-52: a guarda bancária não encobre inaplicabilidade das lentes empresariais."""

from apoio_bancos import enriquecer_bancos
from test_valuation_bancos import BANCO, _processar


def test_banco_abstido_conserva_cada_motivo_por_lente():
    r = _processar(enriquecer_bancos(BANCO, vpa=None))
    for nome in ("Graham", "Lynch", "Gordon", "Bazin"):
        assert r["lentes"][nome]["valor"] is None
        assert r["lentes"][nome]["abstencao"] == "modelo banco fora do escopo do método"
    assert r["lentes"]["Bancos"]["abstencao"]
    assert r["lentes"]["Bancos"]["valor"] is None
