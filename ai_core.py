from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import logging
import os

import requests

from config import GEMINI_MODEL, GROQ_MODEL, OLLAMA_URL, OLLAMA_MODEL

# CORRIGIDO: removido `import html` que foi importado mas nunca usado

logger = logging.getLogger("AI")

class SentinelaAI:
    def __init__(self):
        self.clients = {}
        self._gemini_executor = ThreadPoolExecutor(max_workers=1)
        self._setup()

    def __del__(self):
        try:
            self._gemini_executor.shutdown(wait=False)
        except Exception:
            pass

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
Você é um analista financeiro. Analise o ativo {ticker} (Perfil: {perfil}).
Baseie-se ESTRITAMENTE nos dados fornecidos abaixo. Não invente ou presuma dados ausentes.

DADOS FORNECIDOS:
{dados_txt}

Forneça uma análise estruturada, direta e em Português, contendo exatamente:
1. Valuation: Comente o preço justo calculado e o upside.
2. Análise Técnica: Comente os indicadores técnicos e momentum.
3. Riscos e Confiança: Liste as bandeiras de risco e avalie o nível de confiança dos dados.
4. Recomendação Final: Sua conclusão (Compra/Neutro/Venda/Aguardar) baseada exclusivamente nos dados acima.
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
            future = self._gemini_executor.submit(
                self.clients['gemini'].models.generate_content,
                model=GEMINI_MODEL,
                contents=prompt,
            )
            try:
                resp = future.result(timeout=15)
                return {"content": resp.text, "model": "Gemini"}
            except FuturesTimeout:
                future.cancel()
                logger.warning("Gemini timeout (15s). Falling back to Ollama.")
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
