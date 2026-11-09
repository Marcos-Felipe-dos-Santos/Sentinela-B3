"""BUG-2C-42: falha da nova leitura de PL inicial não apaga a série disponível."""

from cvm_provider import CVMProvider
from tests.test_cvm_series import _ind


def test_pl_inicial_indisponivel_preserva_lucro(tmp_path, monkeypatch):
    p = CVMProvider(tmp_path / "cache")
    monkeypatch.setattr(p, "calcular_indicadores", lambda *a, **k: {2025: _ind(2025)})

    def indisponivel(ano):
        raise OSError("arquivo indisponível")

    monkeypatch.setattr(p, "baixar_dfp", indisponivel)
    r = p.indicadores_da_serie(9999, 2025)[2025]
    assert r["lucro_liquido"] == 100
    assert r["pl_inicial_controladores"] is None
    assert "indisponível" in r["pl_inicial_motivo"]
