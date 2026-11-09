"""BUG-2C-08: segunda obtenção da DFP fora da fronteira apaga exercícios já lidos.

F2C-29/31: uma falha dos proventos deve virar motivo por campo, preservando os
indicadores anuais já disponíveis. O erro de programação continua propagando.
"""

from cvm_provider import CVMProvider
from tests.test_cvm_series import _ind


def test_falha_de_download_dva_preserva_anos_e_motivos(tmp_path, monkeypatch):
    p = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(
        p,
        "calcular_indicadores",
        lambda *a, **k: {ano: _ind(ano) for ano in range(2022, 2026)},
    )

    def indisponivel(ano):
        raise OSError("arquivo indisponível na segunda leitura")

    monkeypatch.setattr(p, "baixar_dfp", indisponivel)
    anos = p.indicadores_da_serie(9999, 2025)
    assert sorted(anos) == [2022, 2023, 2024, 2025]
    for ind in anos.values():
        assert ind["lucro_liquido"] == 100
        assert ind["dividendos"] is None
        assert "indisponível" in ind["proventos_motivos"]["dividendos"]
