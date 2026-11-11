"""F3-P06: origem da classe é contexto, não prova de elegibilidade."""

import sqlite3
from contextlib import closing
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from ai_core import SentinelaAI
from market_engine import RISCO_SEM_REFERENCIA, MarketEngine
from sentinela.data.store import migracoes
from sentinela.services.analyze_asset import AnalysisService, contexto_classe_ia
from sentinela.services.asset_classifier import AssetClassifier


@pytest.mark.parametrize("apresentacao", [None, "1.0"])
@pytest.mark.parametrize("classe", ["STOCK", "FII", "UNIT"])
@pytest.mark.parametrize(
    "fonte", ["FCA/B3", {"arquivo": "fca_cia_aberta_2026.zip", "data": "2026-11-01"}]
)
def test_prompt_classe_oficial_sem_aviso_falso(
    apresentacao: str | None, classe: str, fonte: str | dict
) -> None:
    dados = {
        "classe_ativo": classe,
        "referencia_oficial": {"fonte": fonte, "regra": "registro do ticker"},
    }
    if apresentacao:
        dados["apresentacao_versao"] = apresentacao
    prompt = object.__new__(SentinelaAI)._montar_prompt("TSTA3", dados)
    assert f"Classe do ativo: {classe}" in prompt
    assert "origem: oficial" in prompt
    assert (fonte if isinstance(fonte, str) else fonte["arquivo"]) in prompt
    assert "inferida" not in prompt


@pytest.mark.parametrize(
    "referencia", [None, {}, {"fonte": ""}, {"fonte": True}, "ilegível"]
)
def test_origem_ausente_nao_vira_fonte_oficial(referencia: object) -> None:
    dados = {
        "classe_ativo": "STOCK",
        "referencia_oficial": referencia,
        "riscos_dados": [RISCO_SEM_REFERENCIA],
    }
    antes = deepcopy(dados)
    prompt = object.__new__(SentinelaAI)._montar_prompt("TSTA3", dados)
    assert "origem: inferida" in prompt
    assert "motivo:" in prompt
    assert RISCO_SEM_REFERENCIA in prompt
    assert "não comprova elegibilidade" in prompt
    assert dados == antes


@pytest.mark.parametrize("classe", [None, "UNKNOWN", "inválida"])
def test_unknown_nao_inventa_tipo_ou_elegibilidade(classe: str | None) -> None:
    prompt = object.__new__(SentinelaAI)._montar_prompt(
        "TSTX11", {"classe_ativo": classe}
    )
    assert "Classe do ativo: UNKNOWN" in prompt
    assert "origem: indisponível" in prompt
    assert "não presumir tipo nem elegibilidade" in prompt


@pytest.mark.parametrize("oficial", [False, True])
def test_cascata_classificador_servico_prompt_e_texto_nao_confiavel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, oficial: bool
) -> None:
    classificador = AssetClassifier(
        fiis_conhecidos=[], units_conhecidas=[], pasta_dados=tmp_path
    )
    mercado = MarketEngine.__new__(MarketEngine)
    mercado.asset_classifier = classificador
    if oficial:
        from types import SimpleNamespace

        from tests.test_referencia import _indice

        mercado.referencia = SimpleNamespace(indice=lambda instante: _indice())
    else:
        mercado.referencia = None
    mercado._buscar_yfinance = lambda t, d: d.update(
        preco_atual=10, fonte_preco="yfinance"
    )
    for nome in (
        "_buscar_brapi",
        "_buscar_cvm",
        "_buscar_ifdata",
        "_buscar_cvm_fii",
        "_buscar_rendimento_fii",
        "_buscar_proventos_b3",
        "_buscar_liquidez",
        "_buscar_taxa_real",
        "_contexto_janelas",
        "_aplicar_cache_fundamentos",
        "_salvar_cache_se_valido",
    ):
        monkeypatch.setattr(mercado, nome, Mock())
    montar = Mock(wraps=contexto_classe_ia)
    monkeypatch.setattr("ai_core.contexto_classe_ia", montar)
    ia = object.__new__(SentinelaAI)
    ia.clients = {}
    recebido = []
    texto = "<script>texto externo</script>"

    def local(prompt: str) -> dict:
        recebido.append(prompt)
        return {"content": texto, "model": "transporte simulado"}

    monkeypatch.setattr(ia, "_call_ollama", local)
    val = Mock()
    val.processar.return_value = {
        "abstencao": "sem fundamentos demonstrados",
        "lentes": {},
    }
    tech = Mock()
    tech.calcular_indicadores.return_value = {}
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        s = AnalysisService(
            mercado,
            val,
            Mock(),
            tech,
            ai_engine=ia,
            asset_classifier=classificador,
            hoje=date(2026, 11, 10),
            conexao_resultados=conn,
        )
        resultado = s.analisar("TSTA3", datetime(2026, 11, 10, 15, tzinfo=UTC))
    assert len(recebido) == 1
    assert montar.call_count == 1
    if oficial:
        assert "origem: oficial" in recebido[0]
        assert "fca_cia_aberta_2026.zip" in recebido[0]
        assert "inferida" not in recebido[0]
    else:
        assert "origem: inferida" in recebido[0]
        assert RISCO_SEM_REFERENCIA in recebido[0]
    assert resultado.ai_analysis == texto
    assert resultado.raw["analise_ia"] == texto
    assert "contexto_classe_ia" not in resultado.raw
    assert resultado.valuation.extra["abstencao"] == "sem fundamentos demonstrados"


@pytest.mark.parametrize("campo", ["preco_atual", "dy", "pl", "pvp", "roe"])
@pytest.mark.parametrize(
    "flags",
    [
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, True),
    ],
)
def test_contexto_preserva_fonte_avisos_e_estados_por_campo(
    campo: str, flags: tuple[bool, bool, bool]
) -> None:
    """AGENTS: confiança é contexto; provenance.md §AI exige fontes e ressalvas.

    Os estados vêm do cenário, não de regras de qualidade ou valor econômico.
    """
    import re

    fonte = "fonte do cenário Ω"
    aviso = "ressalva do arquivo Ω"
    cached, manual, stale = flags
    dados = {
        "classe_ativo": "STOCK",
        "field_provenance": {
            campo: {
                "value": 10,
                "provenance": {
                    "source": fonte,
                    "confidence": 0.5,
                    "cached": cached,
                    "manual": manual,
                    "stale": stale,
                    "warnings": [aviso],
                },
            }
        },
    }
    prompt = object.__new__(SentinelaAI)._montar_prompt("TSTA3", dados)
    assert fonte in prompt and aviso in prompt
    resumo = next(l for l in prompt.splitlines() if f"- {campo}: fonte=" in l)
    numero = re.search(r"confianca=([0-9.]+)", resumo)
    assert numero and float(numero.group(1)) == 0.5
    for nome, valor in [("cache", cached), ("manual", manual), ("stale", stale)]:
        assert (f"{nome}=True" in resumo) == valor
    assert "field_provenance" not in prompt


@pytest.mark.parametrize("confidence", [0.0, 1.0, None])
def test_contexto_confidence_zero_nao_e_ausencia(confidence: float | None) -> None:
    import re

    dados = {
        "field_provenance": {
            "dy": {
                "provenance": {
                    "source": "fonte do cenário",
                    "confidence": confidence,
                    "warnings": [],
                }
            }
        }
    }
    prompt = object.__new__(SentinelaAI)._montar_prompt("TSTA3", dados)
    numero = re.search(r"confianca=([0-9.]+)", prompt)
    if confidence is None:
        assert numero is None  # ausência não produz confiança numérica
    else:
        assert numero and float(numero.group(1)) == confidence


@pytest.mark.parametrize("versao", [None, "1.0"])
def test_campos_simples_chegam_sem_perder_zero_e_perfil(versao: str | None) -> None:
    dados = {
        "preco_atual": 13.25,
        "dy": 0,
        "nome": "Companhia Ω",
        "perfil": "CENARIO Ω",
        "pl": None,
        "apresentacao_versao": versao,
    }
    prompt = object.__new__(SentinelaAI)._montar_prompt("TSTA3", dados)
    assert "13.25" in prompt
    assert "Companhia Ω" in prompt
    assert "- dy: 0" in prompt
    assert "Perfil: CENARIO Ω" in prompt
    assert "- pl: None" not in prompt
    if versao == "1.0":
        # Ficha Apresentação1.0/AGENTS: lentes independentes, sem síntese econômica.
        assert "não combine lentes" in prompt.lower()
        assert "6%" in prompt


# Texto exato do contexto (F3-P06; controles do gate de mutação, claude-code 11/11/2026).


INFERIDA = (
    "Classe do ativo: STOCK; origem: inferida a partir da classe fornecida, "
    "sem fonte oficial comprovada; motivo: {}. "
    "A inferência não comprova elegibilidade para métodos."
)


@pytest.mark.parametrize("classe", [None, "", "XYZ", "unknown", " Unknown "])
def test_contexto_unknown_exato(classe):
    assert contexto_classe_ia({"classe_ativo": classe}) == (
        "Classe do ativo: UNKNOWN; origem: indisponível; motivo: classe não demonstrada; "
        "não presumir tipo nem elegibilidade."
    )


@pytest.mark.parametrize("fonte", [" docs/ref.csv ", {"arquivo": " docs/ref.csv "}])
def test_contexto_oficial_exato(fonte):
    dados = {"classe_ativo": " fii ", "referencia_oficial": {"fonte": fonte}}
    assert contexto_classe_ia(dados) == (
        "Classe do ativo: FII; origem: oficial (docs/ref.csv); "
        "motivo: registro da referência oficial fornecido com a classe."
    )


def test_contexto_inferido_cita_so_os_riscos_de_referencia_na_ordem():
    riscos = [
        "liquidez não medida",
        RISCO_SEM_REFERENCIA,
        7,
        "ticker fora da referência oficial (sem registro)",
        "Índice oficial desatualizado",
        "ROE descartado (brapi): fora do domínio",
    ]
    assert contexto_classe_ia({"classe_ativo": "STOCK", "riscos_dados": riscos}) == (
        INFERIDA.format(
            f"{RISCO_SEM_REFERENCIA}; ticker fora da referência oficial (sem registro); "
            "Índice oficial desatualizado"
        )
    )


@pytest.mark.parametrize(
    "riscos",
    [None, [], ["liquidez não medida"], RISCO_SEM_REFERENCIA, (RISCO_SEM_REFERENCIA,)],
)
def test_contexto_inferido_sem_risco_de_referencia_usa_o_motivo_padrao(riscos):
    assert contexto_classe_ia({"classe_ativo": "STOCK", "riscos_dados": riscos}) == (
        INFERIDA.format("referência oficial não demonstrada para a classe fornecida")
    )


@pytest.mark.parametrize("fonte", [None, "", "  ", 3, {"arquivo": ""}, {"outro": "x"}])
def test_contexto_sem_fonte_textual_e_inferido(fonte):
    dados = {"classe_ativo": "STOCK", "referencia_oficial": {"fonte": fonte}}
    assert contexto_classe_ia(dados) == INFERIDA.format(
        "referência oficial não demonstrada para a classe fornecida"
    )


@pytest.mark.parametrize("dados", [None, [], "texto"])
def test_prompt_com_dados_fora_de_dicionario_tem_classe_unknown_e_perfil_geral(dados):
    ia = object.__new__(SentinelaAI)
    prompt = ia._montar_prompt("TSTA3", dados)
    assert "(Perfil: GERAL)" in prompt
    assert contexto_classe_ia({}) in prompt


def test_prompt_sem_perfil_usa_geral():
    ia = object.__new__(SentinelaAI)
    prompt = ia._montar_prompt(
        "TSTA3", {"classe_ativo": "STOCK", "apresentacao_versao": "1.0"}
    )
    assert "Analise o ativo TSTA3 (Perfil: GERAL)." in prompt
