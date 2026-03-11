import logging
import os
import requests
from config import GEMINI_MODEL, GROQ_MODEL, OLLAMA_URL, OLLAMA_MODEL

# CORRIGIDO: removido `import html` que foi importado mas nunca usado

logger = logging.getLogger("AI")

class SentinelaAI:
    def __init__(self):
        self.clients = {}
        self._setup()

    def _setup(self):
        # Gemini
        if os.getenv("GEMINI_API_KEY"):
            try:
                from google import genai
                self.clients['gemini'] = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            except ImportError:
                logger.error("Pacote google-genai não encontrado. Execute: pip install google-genai")
            except Exception as e:
                logger.error(f"Erro init Gemini: {e}")

        # Groq
        if os.getenv("GROQ_API_KEY"):
            try:
                from groq import Groq
                self.clients['groq'] = Groq(api_key=os.getenv("GROQ_API_KEY"))
            except Exception as e:
                logger.error(f"Erro init Groq: {e}")

    def _formatar_dados(self, dados):
        if isinstance(dados, dict):
            # Exclui campos volumosos que não agregam ao prompt
            excluir = {'historico', 'analise_ia', 'tech'}
            return "\n".join(
                [f"- {k}: {v}" for k, v in dados.items()
                 if v is not None and k not in excluir]
            )
        return str(dados)

    def analisar(self, ticker, dados):
        dados_txt = self._formatar_dados(dados)
        perfil    = dados.get('perfil', 'GERAL')

        prompt = f"""
Analise a ação {ticker} (Perfil: {perfil}).

Dados Fundamentais:
{dados_txt}

Responda em Português com exatamente 3 tópicos:
1. Qualidade da empresa (Forte / Moderada / Fraca) — justifique com os dados acima.
2. Riscos principais — liste os 2-3 maiores riscos identificados.
3. Veredito final (Compra / Neutro / Venda) — justifique com base no valuation e qualidade.
"""

        # 1. Groq (primário)
        if 'groq' in self.clients:
            try:
                resp = self.clients['groq'].chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=GROQ_MODEL,
                    timeout=20
                )
                return {"content": resp.choices[0].message.content, "model": "Groq"}
            except Exception as e:
                logger.warning(f"Groq falhou: {e}")

        # 2. Gemini (fallback)
        if 'gemini' in self.clients:
            try:
                resp = self.clients['gemini'].models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
                return {"content": resp.text, "model": "Gemini"}
            except Exception as e:
                logger.warning(f"Gemini falhou: {e}")

        # 3. Ollama (fallback local)
        return self._call_ollama(prompt)

    def _call_ollama(self, prompt):
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=30
            )
            if r.status_code == 200:
                return {"content": r.json()['response'], "model": "Ollama Local"}
            logger.error(f"Ollama HTTP {r.status_code}")
        except Exception as e:
            logger.error(f"Ollama error: {e}")

        return {"content": "IA Indisponível (todos os provedores falharam).", "model": "Offline"}