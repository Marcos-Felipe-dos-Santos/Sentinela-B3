"""Contrato do `ai_core` fora do prompt (F3-A-F2): textos de retorno, logs, timeouts e filtros.

Sem rede e sem credencial: os clientes Groq, Gemini e o `requests.post` do Ollama são dublês.
"""

import logging
import sys
from concurrent.futures import TimeoutError as FuturesTimeout
from types import SimpleNamespace

import pytest

import ai_core
from ai_core import SentinelaAI, _formatar_alertas, _safe_text

EXCLUIDOS = (
    "historico", "analise_ia", "tech", "field_provenance", "acoes_por_unit",
    "referencia_oficial", "acoes_cvm", "divergencia_acoes", "valores_coletados",
    "valores_por_fonte", "proveniencia", "lpa_cvm", "classe_preferencial",
    "classes_preferenciais", "serie_cvm", "ttm_cvm", "alavancagem_cvm", "ifdata",
    "liquidez", "rendimento_fii_cvm", "taxa_real", "janela_contabil_cvm", "gordon_cvm",
    "gordon_diagnostico", "base_acionaria_gordon", "proventos_b3", "bazin_proventos",
    "bazin_diagnostico", "modelo_bpp", "perfil_fonte", "fechamentos_brutos", "informe_fii",
    "b3_fundo", "escala_pelo_consolidado", "especies_da_companhia", "modelo_bpp_proveniencia",
    "bancos_diagnostico",
)  # fmt: skip
INDISPONIVEL = "Proveniência por campo indisponível."
OFFLINE = {
    "content": "IA Indisponível (todos os provedores falharam).",
    "model": "Offline",
}


@pytest.fixture
def ia(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    return SentinelaAI()


# --- funções de texto -------------------------------------------------------------------


def test_safe_text():
    assert _safe_text(None) == "-"
    assert _safe_text("") == "-"
    assert _safe_text("", default="?") == "?"
    assert _safe_text("XXXX") == "XXXX"
    assert _safe_text(0) == "0"


def test_formatar_alertas():
    assert _formatar_alertas(None) == ""
    assert _formatar_alertas([]) == ""
    assert _formatar_alertas(["a", "", None, "b"]) == ", alertas=a, b"
    assert _formatar_alertas(["", None]) == ""
    assert _formatar_alertas("um aviso") == ", alertas=um aviso"
    assert _formatar_alertas(7) == ", alertas=7"


# --- formatação dos dados ---------------------------------------------------------------


def test_formatar_dados_exclui_campos_volumosos_e_nulos(ia):
    dados = dict.fromkeys(EXCLUIDOS, "volumoso")
    dados.update(pl=8, roe=0.2, vazio=None)
    assert ia._formatar_dados(dados) == "- pl: 8\n- roe: 0.2"


def test_formatar_dados_fora_de_dict(ia):
    assert ia._formatar_dados(["a"]) == "['a']"


def test_proveniencia_completa_com_flags_e_alertas(ia):
    campos = {
        "preco_atual": {
            "provenance": {
                "source": "yfinance",
                "confidence": 0.9,
                "cached": True,
                "manual": True,
                "stale": True,
                "warnings": ["w1", "w2"],
            }
        },
        "dy": {"provenance": {"source": "B3", "confidence": "alta"}},
        "pl": {"provenance": "não é dict"},
        "pvp": "não é dict",
        "roe": {"provenance": {"confidence": None}},
    }
    assert ia._formatar_proveniencia_campos(campos) == (
        "Proveniência dos dados:\n"
        "- preco_atual: fonte=yfinance, confianca=0.90, cache=True, manual=True, "
        "stale=True, alertas=w1, w2\n"
        "- dy: fonte=B3, confianca=alta\n"
        "- pl: fonte=-, confianca=-\n"
        "- roe: fonte=-, confianca=-"
    )


def test_proveniencia_indisponivel(ia):
    assert ia._formatar_proveniencia_campos(None) == INDISPONIVEL
    assert ia._formatar_proveniencia_campos({"outro": {}}) == INDISPONIVEL
    assert ia._formatar_proveniencia_campos({"dy": "x"}) == INDISPONIVEL


# --- ciclo de vida ----------------------------------------------------------------------


def test_um_unico_trabalhador_para_o_gemini(ia):
    assert ia.clients == {}
    assert ia._gemini_executor._max_workers == 1


def test_del_desliga_o_executor_sem_esperar(ia):
    chamadas = []
    executor = ia._gemini_executor
    ia._gemini_executor = SimpleNamespace(shutdown=lambda **kw: chamadas.append(kw))
    ia.__del__()
    assert chamadas == [{"wait": False}]
    assert chamadas[0]["wait"] is False
    executor.shutdown(wait=False)


def test_setup_sem_pacote_do_gemini_registra_o_erro(monkeypatch, caplog):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-falsa")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setitem(
        sys.modules, "google", None
    )  # `from google import genai` → ImportError
    with caplog.at_level(logging.ERROR, logger="AI"):
        ia = SentinelaAI()
    assert "gemini" not in ia.clients
    assert caplog.messages == [
        "Pacote google-genai não encontrado. Execute: pip install google-genai"
    ]


# --- provedores -------------------------------------------------------------------------


def test_ticker_invalido_nao_chama_provedor(ia):
    assert ia.analisar("../x", {}) == {
        "content": "Análise indisponível: ticker inválido.",
        "model": "nenhum",
    }


def _groq(chamadas, erro=None):
    def create(**kw):
        chamadas.append(kw)
        if erro:
            raise erro
        mensagem = SimpleNamespace(content="resposta groq")
        return SimpleNamespace(choices=[SimpleNamespace(message=mensagem)])

    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )


def test_groq_recebe_prompt_modelo_e_timeout(ia):
    chamadas = []
    ia.clients["groq"] = _groq(chamadas)
    assert ia.analisar("TSTA3", {}) == {"content": "resposta groq", "model": "Groq"}
    (kw,) = chamadas
    assert kw["model"] == ai_core.GROQ_MODEL
    assert kw["timeout"] == 20
    assert kw["messages"] == [
        {"role": "user", "content": ia._montar_prompt("TSTA3", {})}
    ]


class _Futuro:
    def __init__(self, erro=None, texto="resposta gemini"):
        self.erro, self.texto, self.timeouts, self.cancelado = erro, texto, [], False

    def result(self, timeout=None):
        self.timeouts.append(timeout)
        if self.erro:
            raise self.erro
        return SimpleNamespace(text=self.texto)

    def cancel(self):
        self.cancelado = True


def _com_gemini(ia, futuro):
    ia._gemini_executor.shutdown(wait=False)
    ia._gemini_executor = SimpleNamespace(submit=lambda *a, **kw: futuro)
    ia.clients["gemini"] = SimpleNamespace(
        models=SimpleNamespace(generate_content=None)
    )


def test_groq_falha_registra_e_cai_no_gemini(ia, caplog):
    ia.clients["groq"] = _groq([], erro=RuntimeError("cota"))
    futuro = _Futuro()
    _com_gemini(ia, futuro)
    with caplog.at_level(logging.WARNING, logger="AI"):
        assert ia.analisar("TSTA3", {}) == {
            "content": "resposta gemini",
            "model": "Gemini",
        }
    assert caplog.messages == ["Groq falhou: cota"]
    assert futuro.timeouts == [15]


def test_gemini_timeout_cancela_e_cai_no_ollama(ia, monkeypatch, caplog):
    futuro = _Futuro(erro=FuturesTimeout())
    _com_gemini(ia, futuro)
    monkeypatch.setattr(ia, "_call_ollama", lambda prompt: {"model": "ollama"})
    with caplog.at_level(logging.WARNING, logger="AI"):
        assert ia.analisar("TSTA3", {}) == {"model": "ollama"}
    assert futuro.cancelado
    assert caplog.messages == ["Gemini timeout (15s). Falling back to Ollama."]


def test_gemini_erro_registra_e_cai_no_ollama(ia, monkeypatch, caplog):
    _com_gemini(ia, _Futuro(erro=ValueError("quebrou")))
    monkeypatch.setattr(ia, "_call_ollama", lambda prompt: {"model": "ollama"})
    with caplog.at_level(logging.WARNING, logger="AI"):
        assert ia.analisar("TSTA3", {}) == {"model": "ollama"}
    assert caplog.messages == ["Gemini falhou: quebrou"]


def _post(chamadas, status=200, erro=None):
    def post(url, json=None, timeout=None):
        chamadas.append((url, json, timeout))
        if erro:
            raise erro
        return SimpleNamespace(status_code=status, json=lambda: {"response": "local"})

    return post


def test_ollama_200(ia, monkeypatch):
    chamadas = []
    monkeypatch.setattr(ai_core.requests, "post", _post(chamadas))
    assert ia._call_ollama("P") == {"content": "local", "model": "Ollama Local"}
    assert chamadas == [
        (
            f"{ai_core.OLLAMA_URL}/api/generate",
            {"model": ai_core.OLLAMA_MODEL, "prompt": "P", "stream": False},
            30,
        )
    ]


def test_ollama_http_erro_fica_offline(ia, monkeypatch, caplog):
    monkeypatch.setattr(ai_core.requests, "post", _post([], status=503))
    with caplog.at_level(logging.ERROR, logger="AI"):
        assert ia._call_ollama("P") == OFFLINE
    assert caplog.messages == ["Ollama HTTP 503"]


def test_ollama_excecao_fica_offline(ia, monkeypatch, caplog):
    monkeypatch.setattr(ai_core.requests, "post", _post([], erro=OSError("recusado")))
    with caplog.at_level(logging.ERROR, logger="AI"):
        assert ia._call_ollama("P") == OFFLINE
    assert caplog.messages == ["Ollama error: recusado"]
