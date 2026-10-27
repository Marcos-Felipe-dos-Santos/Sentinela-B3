"""F2C-39: modelo seguradora conhecido não é modelo não demonstrado."""

from data_quality import DataQualityReport


def test_seguradora_informa_seu_escopo() -> None:
    r = DataQualityReport(
        {"classe_ativo": "STOCK", "modelo_bpp": "seguradora"}
    ).completude()
    assert r["limitacoes"] == ["modelo seguradora fora do escopo"]
    assert r["completude_do_modelo_determinada"] is False
