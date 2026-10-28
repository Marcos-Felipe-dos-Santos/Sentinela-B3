"""BUG-2C-34: abstenção não apaga fontes/janela/aviso já conhecidos, F2C-1."""

from tests.test_janelas_fundamentais import AS_OF, dados_exemplo
from sentinela.data.janelas_fundamentais import entradas


def test_abstencao_ipca_preserva_janela_documental_e_aviso():
    d = dados_exemplo()
    d["ipca_serie"] = {"abstencao": "IPCA não publicado"}
    r = entradas(d, AS_OF)["graham"]
    assert r["abstencao"] == "IPCA não publicado"
    assert r["inicio"] == "2021-01-01"
    assert r["fim"] == "2025-12-31"
    assert r["fontes_documentais"] == [
        e["proveniencia"] for e in d["serie_cvm"]["exercicios"]
    ]
    assert r["regime"] == "nominal na moeda final"
    assert "reorganização societária no período não é detectada" in r["avisos"]
    assert "lpa" not in r and "vpa" not in r


def test_base_ausente_preserva_os_documentos_ja_lidos():
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"][0]["acoes"] = None
    r = entradas(d, AS_OF)
    for lente in ("graham", "lynch"):
        janela = r[lente]
        assert janela["inicio"] == "2021-01-01"
        assert janela["fim"] == "2025-12-31"
        assert janela["exercicios"] == [2021, 2022, 2023, 2024, 2025]
        assert janela["fontes_documentais"] == [
            e["proveniencia"] for e in d["serie_cvm"]["exercicios"]
        ]
        assert janela["regime"] == (
            "nominal" if lente == "lynch" else "nominal na moeda final"
        )
        assert janela["abstencao"].startswith("ações do exercício 2021:")
        assert "lpa" not in janela and "vpa" not in janela


def test_quatro_documentos_preservam_cobertura_e_janela_parcial():
    d = dados_exemplo()
    d["serie_cvm"]["exercicios"].pop(0)
    r = entradas(d, AS_OF)
    assert r["cobertura"] == {"esperados": 5, "disponiveis": 4}
    for lente in ("graham", "lynch"):
        assert r[lente]["abstencao"] == "exige cinco exercícios completos contínuos"
        assert r[lente]["inicio"] == "2022-01-01"
        assert r[lente]["fim"] == "2025-12-31"
        assert r[lente]["exercicios"] == [2022, 2023, 2024, 2025]
        assert len(r[lente]["fontes_documentais"]) == 4
        assert "lpa" not in r[lente] and "vpa" not in r[lente]
