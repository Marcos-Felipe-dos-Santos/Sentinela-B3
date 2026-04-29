import pytest
from ai_core import SentinelaAI
from unittest.mock import patch

@pytest.fixture
def ai():
    # Patch config keys to avoid real requests
    with patch.dict('os.environ', {'GROQ_API_KEY': '', 'GEMINI_API_KEY': ''}):
        return SentinelaAI()

def test_ai_fallback_ollama(ai):
    # Test that when groq/gemini are not available, it calls local ollama
    with patch.object(ai, '_call_ollama', return_value={"content": "Ollama response", "model": "Ollama"}) as mock_ollama:
        result = ai.analisar("Contexto fake", {"recomendacao": "COMPRA"})
        
        assert mock_ollama.called
        assert result['model'] == "Ollama"
        assert result['content'] == "Ollama response"

from unittest.mock import MagicMock

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
        
        result = ai.analisar("Contexto fake", {"recomendacao": "COMPRA"})
        assert result['model'] == "Gemini"
        assert result['content'] == "Gemini response"
