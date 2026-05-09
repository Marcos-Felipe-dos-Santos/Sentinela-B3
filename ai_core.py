from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import logging
import os
from typing import Any

import requests

from config import GEMINI_MODEL, GROQ_MODEL, OLLAMA_URL, OLLAMA_MODEL

# CORRIGIDO: removido `import html` que foi importado mas nunca usado

logger = logging.getLogger("AI")

AI_FIELD_PROVENANCE_ORDER = ("preco_atual", "dy", "pl", "pvp", "roe")


def _safe_text(value: Any, default: str = "-") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _formatar_alertas(warnings: Any) -> str:
    if not warnings:
        return ""
    if isinstance(warnings, list):
        alertas = ", ".join(str(warning) for warning in warnings if warning)
    else:
        alertas = str(warnings)
    return f", alertas={alertas}" if alertas else ""

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
            excluir = {'historico', 'analise_ia', 'tech', 'field_provenance'}
            return "\n".join(
                [f"- {k}: {v}" for k, v in dados.items()
                 if v is not None and k not in excluir]
            )
        return str(dados)

    def _formatar_proveniencia_campos(self, field_provenance):
        if not isinstance(field_provenance, dict):
            return "Proveni\u00eancia por campo indispon\u00edvel."

        linhas = []
        for field_name in AI_FIELD_PROVENANCE_ORDER:
            field_data = field_provenance.get(field_name)
            if not isinstance(field_data, dict):
                continue

            provenance = field_data.get("provenance")
            if not isinstance(provenance, dict):
                provenance = {}

            source = _safe_text(provenance.get("source"))
            confidence = provenance.get("confidence")
            try:
                confidence_text = f"{float(confidence):.2f}"
            except (TypeError, ValueError):
                confidence_text = _safe_text(confidence)

            flags = []
            if provenance.get("cached"):
                flags.append("cache=True")
            if provenance.get("manual"):
                flags.append("manual=True")
            if provenance.get("stale"):
                flags.append("stale=True")

            flag_text = f", {', '.join(flags)}" if flags else ""
            alertas = _formatar_alertas(provenance.get("warnings"))
            linhas.append(
                f"- {field_name}: fonte={source}, confianca={confidence_text}"
                f"{flag_text}{alertas}"
            )

        if not linhas:
            return "Proveni\u00eancia por campo indispon\u00edvel."
        return "Proveni\u00eancia dos dados:\n" + "\n".join(linhas)

    def _montar_prompt(self, ticker, dados):
        dados_txt = self._formatar_dados(dados)
        perfil = dados.get('perfil', 'GERAL') if isinstance(dados, dict) else 'GERAL'
        proveniencia_txt = self._formatar_proveniencia_campos(
            dados.get("field_provenance") if isinstance(dados, dict) else None
        )

        return f"""
Você é um analista educacional. Analise o ativo {ticker} (Perfil: {perfil}).
Baseie-se ESTRITAMENTE nos dados fornecidos abaixo. Não invente ou presuma dados ausentes.

DADOS FORNECIDOS:
{dados_txt}

CONTEXTO DE QUALIDADE DOS DADOS / PROVENIÊNCIA:
{proveniencia_txt}

A proveniência por campo serve apenas para explicar limitações dos dados.
Não altere nem substitua a classificação heurística, o preço justo/fair_value, o upside, o score ou a confiança calculados pelo sistema.
Se houver dados manuais, em cache, ausentes ou de baixa confiança, destaque isso como limitação.

Forneça uma análise estruturada, direta e em Português, contendo exatamente:
1. Valuation: Comente o preço justo calculado e o upside, sem tratar isso como recomendação de investimento.
2. Análise Técnica: Comente os indicadores técnicos e momentum como sinais auxiliares, não como decisão final.
3. Riscos e Confiança: Liste as bandeiras de risco e avalie o nível de confiança dos dados.
4. Classificação Heurística: Explique o sinal calculado pelo sistema usando linguagem educacional. Não use orientação direta de compra ou venda. Prefira termos como sinal positivo, neutro, sinal de atenção, dados insuficientes ou necessita análise adicional.
"""

    def analisar(self, ticker, dados):
        prompt = self._montar_prompt(ticker, dados)

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
