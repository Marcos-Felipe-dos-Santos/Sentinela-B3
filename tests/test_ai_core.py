import pytest
from ai_core import SentinelaAI
from unittest.mock import MagicMock, patch

@pytest.fixture
def ai():
    # Patch config keys to avoid real requests
    with patch.dict('os.environ', {'GROQ_API_KEY': '', 'GEMINI_API_KEY': ''}):
        return SentinelaAI()

def test_ai_fallback_ollama(ai):
    # Test that when groq/gemini are not available, it calls local ollama
    with patch.object(ai, '_call_ollama', return_value={"content": "Ollama response", "model": "Ollama"}) as mock_ollama:
        result = ai.analisar("Contexto fake", {
            "classificacao_heuristica": "SINAL POSITIVO",
            "recomendacao": "SINAL POSITIVO",
        })
        
        assert mock_ollama.called
        assert result['model'] == "Ollama"
        assert result['content'] == "Ollama response"

def test_ai_fallback_gemini(ai):
    # If groq not available, but gemini is, test gemini is called
    ai.clients['gemini'] = MagicMock() # Fake presence and attributes
    
    with patch.object(ai._gemini_executor, 'submit') as mock_submit:
        # Mocking the future
        class FakeFuture:
            def result(self, timeout):
                class FakeResponse:
                    text = "Gemini response"
                return FakeResponse()
                
        mock_submit.return_value = FakeFuture()
        
        result = ai.analisar("Contexto fake", {
            "classificacao_heuristica": "SINAL POSITIVO",
            "recomendacao": "SINAL POSITIVO",
        })
        assert result['model'] == "Gemini"
        assert result['content'] == "Gemini response"


def test_ai_prompt_includes_field_provenance_summary(ai):
    prompt = ai._montar_prompt(
        "PETR4",
        {
            "classificacao_heuristica": "SINAL POSITIVO",
            "recomendacao": "SINAL POSITIVO",
            "field_provenance": {
                "preco_atual": {
                    "value": 35.0,
                    "unit": "BRL",
                    "provenance": {
                        "source": "yfinance",
                        "confidence": 1.0,
                        "warnings": [],
                    },
                },
                "dy": {
                    "value": 0.08,
                    "unit": "ratio",
                    "provenance": {
                        "source": "brapi",
                        "confidence": 0.9,
                        "warnings": ["source_inferred_from_aggregate_flag"],
                    },
                },
            },
        },
    )

    assert "Proveniência" in prompt
    assert "preco_atual" in prompt
    assert "dy" in prompt
    assert "yfinance" in prompt
    assert "brapi" in prompt
    assert "field_provenance" not in prompt


def test_ai_prompt_handles_missing_field_provenance(ai):
    prompt = ai._montar_prompt("PETR4", {
        "classificacao_heuristica": "SINAL POSITIVO",
        "recomendacao": "SINAL POSITIVO",
        "fair_value": 36.0,
    })

    assert "Proveniência por campo indisponível" in prompt
    assert "- fair_value: 36.0" in prompt


@pytest.mark.parametrize("field_provenance", [None, "malformed", {"dy": "bad"}])
def test_ai_prompt_handles_malformed_field_provenance(ai, field_provenance):
    prompt = ai._montar_prompt(
        "PETR4",
        {"classificacao_heuristica": "NEUTRO", "field_provenance": field_provenance},
    )

    assert "DADOS FORNECIDOS" in prompt
    assert "Proveniência" in prompt


def test_ai_prompt_instructs_not_to_override_system_calculations(ai):
    prompt = ai._montar_prompt(
        "PETR4",
        {
            "classificacao_heuristica": "SINAL POSITIVO",
            "recomendacao": "SINAL POSITIVO",
            "fair_value": 36.0,
            "upside": 0.15,
            "score_final": 75,
            "confianca": 80,
        },
    )

    assert "Não altere nem substitua" in prompt
    assert "classificação heurística" in prompt.lower()
    assert "fair_value" in prompt
    assert "upside" in prompt
    assert "score" in prompt
    assert "confiança" in prompt


def test_ai_prompt_does_not_contain_unsafe_language(ai):
    prompt = ai._montar_prompt(
        "PETR4",
        {
            "classificacao_heuristica": "SINAL POSITIVO",
            "fair_value": 36.0,
        },
    )

    # Must NOT contain unsafe buy/sell language
    assert "Compra/Neutro/Venda/Aguardar" not in prompt
    assert "Recomendação Final" not in prompt

    # MUST contain safe educational language
    assert "Classificação Heurística" in prompt


def test_ai_prompt_uses_educational_role(ai):
    prompt = ai._montar_prompt("PETR4", {"classificacao_heuristica": "NEUTRO"})

    assert "analista educacional" in prompt
    assert "linguagem educacional" in prompt
