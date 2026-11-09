"""Rastreabilidade: conservar unidades, datas, fontes e motivos dos dados sintéticos.

Oráculo: ficha FII 1.3 e contratos de unidades/proveniência D16/D21; nenhum
número é calculado por método financeiro nestes testes de apresentação.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from sentinela.domain import units
from sentinela.reports import rastreabilidade as r


@pytest.mark.parametrize(
    ("entrada", "texto"),
    [
        (units.BRL(1234.5), "R$ 1.234,50"),
        (units.RateReal(0.075), "7,50%"),
        (units.RateNominal(0.125), "12,50%"),
        (units.Percent(12.5), "12,50%"),
        (units.Ratio(0.125), "0,1250"),
        (True, "sim"),
        (False, "não"),
        (None, "ausente"),
        (1.25, "1,2500"),
        (7, "7"),
        ("origem X", "origem X"),
    ],
)
def test_unidades_e_ausencia_sao_explicitas(entrada, texto):
    assert r._formatar(entrada) == texto


@pytest.mark.parametrize("entrada", [None, True, "12", float("nan"), float("inf")])
def test_numero_invalido_nao_inventa_valor(entrada):
    assert r._numero(entrada) == "n/d"


@pytest.mark.parametrize(
    ("campo", "dados", "texto"),
    [
        ("dy", {}, "herdada de fonte_fundamentos: desconhecida"),
        ("dy", {"fonte_fundamentos": "CVM"}, "herdada de fonte_fundamentos: CVM"),
        (
            "dy",
            {
                "field_provenance": {
                    "dy": {
                        "provenance": {"source": "B3", "warnings": ["janela", "escala"]}
                    }
                }
            },
            "B3 (avisos: janela, escala)",
        ),
        ("dy", {"field_provenance": {"dy": {"provenance": {}}}}, "unknown"),
    ],
)
def test_fonte_e_avisos_nao_se_perdem(campo, dados, texto):
    assert r._proveniencia(campo, dados) == texto


def test_rendimento_preserva_base_janela_evento_e_aviso():
    medida = {
        "dy": 0.12,
        "mes_final": "2026-09",
        "rendimento_12m": 12.0,
        "base": "preço de R$ 100",
        "tipo": "tijolo",
        "emissoes": [{"mes": "2026-03", "cotas_antes": 100, "cotas_depois": 120}],
        "avisos": ["B3 incompleta"],
    }
    assert r._texto_rendimento_fii(medida, 0.1) == (
        "DY de 12 meses 12,00% pelo Informe (até 2026-09, rendimento de R$ 12,00 por cota, "
        "sobre o preço de R$ 100) contra 10,00% da cascata; tipo tijolo; "
        "emissão em 2026-03 (100 → 120 cotas); aviso: B3 incompleta"
    )
    assert (
        r._texto_rendimento_fii({"abstencao": "VP ausente"}, None)
        == "não calculado: VP ausente"
    )
    medida.pop("tipo")
    medida.pop("emissoes")
    medida.pop("avisos")
    assert r._texto_rendimento_fii(medida, True) == (
        "DY de 12 meses 12,00% pelo Informe (até 2026-09, rendimento de R$ 12,00 por cota, "
        "sobre o preço de R$ 100) contra n/d da cascata"
    )


def test_taxa_fii_conserva_fonte_data_e_calibracao(monkeypatch):
    monkeypatch.setattr(
        r,
        "MACRO",
        SimpleNamespace(
            FII_SPREAD_TIJOLO=0.035,
            FII_SPREAD_CALIBRACAO={
                "janela": ["2025-01", "2025-12"],
                "data": "2026-01-15",
            },
        ),
    )
    dados = {"taxa_real": {"ntnb": 0.07, "data_base": "2026-10-16", "fonte": "Tesouro"}}
    assert r._texto_taxa_fii(dados) == (
        "NTN-B real 7,00% (data-base 2026-10-16, Tesouro) + spread 3,50% "
        "(mediana dos tijolos, 2025-01–2025-12, calibrado em 2026-01-15); a Selic não forma o preço justo"
    )


@pytest.mark.parametrize("ntnb", [None, True, float("nan"), float("inf"), "0.07"])
def test_taxa_fii_invalida_preserva_abstencao(monkeypatch, ntnb):
    monkeypatch.setattr(r, "MACRO", SimpleNamespace())
    assert r._texto_taxa_fii(
        {"taxa_real": {"ntnb": ntnb, "abstencao": "sem cesta"}}
    ) == (
        "NTN-B real indisponível (sem cesta) + spread indisponível; a Selic não forma o preço justo"
    )


def test_liquidez_conserva_unidades_incompletude_e_lacunas():
    dados = {
        "janelas": {
            63: {
                "incompleta": True,
                "volume_mediano": 123456.78,
                "negocios_mediana": 12.5,
                "presenca": 0.8,
            }
        },
        "data_final": "2026-10-16",
        "fonte": "B3 COTAHIST",
        "meses_ausentes": ["2026-08", "2026-09"],
    }
    assert r._texto_liquidez(dados) == (
        "63 pregões (incompleta): volume mediano R$ 123.456,78/dia, negócios 12,5/dia, "
        "presença 80,0%; até 2026-10-16 (B3 COTAHIST); meses ausentes na coleta: 2026-08, 2026-09"
    )
    assert r._texto_liquidez({"abstencao": "sem coleta"}) == "não calculada: sem coleta"


def test_tabela_taxa_real_conserva_regimes_e_proveniencia():
    registro = {
        "ntnb": 0.07,
        "custo_capital_real": 0.12,
        "premio": 0.05,
        "vertice": "2035",
        "data_base": "2026-10-16",
        "fonte": "Tesouro",
        "proveniencia": "documento sintético",
        "inflacao": {
            "valor": 0.045,
            "inicio": "2025-01",
            "fim": "2025-12",
            "proveniencia": {"fonte": "IBGE"},
        },
    }
    assert r._taxa_real({"taxa_real": registro}) == [
        ("NTN-B real", "7,00%"),
        ("Custo de capital real", "12,00%"),
        ("Prêmio das ações", "5,00%"),
        ("Vértice", "2035"),
        ("Data-base", "2026-10-16"),
        ("Fonte", "Tesouro"),
        ("Inflação da janela", "4,50%"),
        ("Janela", "2025-01 a 2025-12"),
        ("Fonte do IPCA", "IBGE"),
        ("Proveniência", "documento sintético"),
    ]
    registro["inflacao"]["abstencao"] = "sem janela"
    assert (
        dict(r._taxa_real({"taxa_real": registro}))["Inflação da janela"]
        == "sem janela"
    )
    assert r._taxa_real({}) == []
    assert r._taxa_real({"taxa_real": {"abstencao": "sem títulos"}}) == [
        ("Taxa real", "abstenção: sem títulos")
    ]


def test_contexto_fii_abstido_preserva_sintese_e_fontes_sem_numero_ficticio():
    analise = {
        "metodos_usados": "sem Informe",
        "score_final": 0,
        "confianca": "baixa",
        "riscos": ["informe ausente"],
        "aviso_liquidez": "sem coleta",
        "aviso_alavancagem": "fora do escopo",
    }
    dados = {
        "ticker": "TST11",
        "preco_atual": 100.0,
        "dy": 0.1,
        "pvp": None,
        "tipo": "Tijolo",
        "fonte_preco": "yfinance",
        "fonte_fundamentos": "CVM",
        "dados_parciais": True,
        "dados_cache": False,
        "dados_manual": True,
        "fundamentos_incompletos": True,
        "campos_faltantes": ["pvp", "vp"],
        "serie_cvm": {
            "exercicios": [{"exercicio": 2025}, {"exercicio": 2024}],
            "proventos_base": "competência",
        },
        "liquidez": {"abstencao": "sem coleta"},
        "rendimento_fii_cvm": {"abstencao": "VP ausente"},
        "ttm_cvm": {"abstencao": "sem comparabilidade"},
    }
    contexto = r.construir_contexto(
        dados,
        True,
        date(2026, 10, 19),
        None,
        SimpleNamespace(analisar=lambda _: analise),
    )
    assert contexto["ticker"] == "TST11"
    assert contexto["classe"] == "FII"
    assert contexto["data"] == "2026-10-19"
    assert contexto["sintese"] == [
        ("Abstenção da lente", "sem Informe"),
        ("Confiança", "baixa"),
        ("Riscos sinalizados pelo motor", "informe ausente"),
        ("Aviso de liquidez (fora dos riscos)", "sem coleta"),
        ("Aviso de alavancagem (fora dos riscos)", "fora do escopo"),
    ]
    fontes = dict(contexto["fontes"])
    assert fontes["Fonte do preço"] == "yfinance"
    assert fontes["Fonte dos fundamentos"] == "CVM"
    assert fontes["Dados parciais"] == "sim"
    assert fontes["Dados cache"] == "não"
    assert fontes["Dados manual"] == "sim"
    assert fontes["Fundamentos incompletos"] == "sim"
    assert fontes["Campos faltantes"] == "pvp, vp"
    assert (
        fontes["Série da CVM (F2A-7, ainda sem uso nos métodos)"]
        == "exercícios: 2025, 2024; proventos por competência"
    )
    assert fontes["Últimos doze meses da CVM"] == "não calculado: sem comparabilidade"
    assert (
        fontes["Rendimento do FII pelo Informe (F2B-2, lente de rendimento)"]
        == "não calculado: VP ausente"
    )
    assert (
        fontes[
            "Liquidez (63 pregões: presença ≥ 80%; mediana ≥ R$ 500 mil em ações/units e R$ 100 mil em FIIs)"
        ]
        == "não calculada: sem coleta"
    )
    insumos = {i["campo"]: i for i in contexto["insumos"]}
    assert insumos["preco_atual"] == {
        "campo": "preco_atual",
        "valor": "R$ 100,00",
        "unidade": "BRL",
        "proveniencia": "herdada de fonte_fundamentos: CVM",
    }
    assert insumos["pvp"]["valor"] == "ausente"
    assert insumos["pvp"]["unidade"] == "razão"
    assert "se abstém e não pontua" in insumos["pvp"]["proveniencia"]


def test_taxa_fii_nao_inventa_fonte_data_ou_calibracao(monkeypatch):
    monkeypatch.setattr(r, "MACRO", SimpleNamespace(FII_SPREAD_TIJOLO=0.035))
    assert r._texto_taxa_fii({"taxa_real": {"ntnb": 0.07}}) == (
        "NTN-B real 7,00% (data-base n/d, fonte n/d) + spread 3,50% "
        "(mediana dos tijolos, , calibrado em None); a Selic não forma o preço justo"
    )
    assert r._texto_taxa_fii({}) == (
        "NTN-B real indisponível (sem registro) + spread 3,50% "
        "(mediana dos tijolos, , calibrado em None); a Selic não forma o preço justo"
    )
