"""Contratos externos dos transportes, complemento do gate G do F3-P06.

Ollama: https://docs.ollama.com/api/generate (POST, model/prompt, stream, response).
Groq: https://github.com/groq/groq-python (messages/role/content, choices.message).
Google: https://github.com/googleapis/python-genai (Client, generate_content, text).
Os SDKs e o HTTP são dublês estritos; não se leem credenciais nem se faz rede.
"""

import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

import ai_core
from ai_core import SentinelaAI

TEXTO = '<tag>texto externo Ω; {"numero": 123}</tag>'
PROMPT = "contexto educacional do cenário Ω"


@pytest.fixture
def ia() -> Iterator[SentinelaAI]:
    objeto = object.__new__(SentinelaAI)
    objeto.clients = {}
    objeto._gemini_executor = ThreadPoolExecutor(max_workers=1)
    yield objeto
    objeto._gemini_executor.shutdown(wait=True)


@pytest.mark.parametrize("texto", [TEXTO, "", "0", "linha1\nlinha2"])
def test_ollama_json_nao_streaming_preserva_resposta(
    ia: SentinelaAI, monkeypatch: pytest.MonkeyPatch, texto: str
) -> None:
    monkeypatch.setattr(ai_core, "OLLAMA_URL", "http://servidor.invalid:11434")
    monkeypatch.setattr(ai_core, "OLLAMA_MODEL", "modelo-do-cenario")
    chamadas = []

    def post(url: str, *, json: dict, timeout: float) -> SimpleNamespace:
        chamadas.append((url, json))
        # O servidor do cenário só oferece este modelo. stream=True daria NDJSON.
        assert url == "http://servidor.invalid:11434/api/generate"
        assert json == {"model": "modelo-do-cenario", "prompt": PROMPT, "stream": False}
        assert timeout is not None and timeout > 0
        return SimpleNamespace(status_code=200, json=lambda: {"response": texto})

    monkeypatch.setattr(ai_core.requests, "post", post)
    resultado = ia._call_ollama(PROMPT)
    assert resultado["content"] == texto
    assert resultado["model"].lower().split()[0] == "ollama"
    assert len(chamadas) == 1


@pytest.mark.parametrize("status", [201, 400, 404, 500])
def test_http_sem_resposta_de_geracao_nao_vira_texto(
    ia: SentinelaAI,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    resposta = SimpleNamespace(
        status_code=status,
        json=Mock(side_effect=AssertionError("não há geração JSON200")),
    )
    monkeypatch.setattr(ai_core.requests, "post", Mock(return_value=resposta))
    r = ia._call_ollama(PROMPT)
    assert r["content"] != TEXTO
    assert "indisponível" in r["content"].lower()
    resposta.json.assert_not_called()
    assert str(status) in caplog.text


@pytest.mark.parametrize(
    "falha",
    [
        requests.ConnectionError("sem servidor"),
        requests.Timeout("sem resposta"),
        ValueError("JSON ilegível"),
    ],
)
def test_ollama_falha_nao_cria_resposta(
    ia: SentinelaAI,
    monkeypatch: pytest.MonkeyPatch,
    falha: Exception,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(ai_core.requests, "post", Mock(side_effect=falha))
    r = ia._call_ollama(PROMPT)
    assert "indisponível" in r["content"].lower()
    assert str(falha) in caplog.text


def test_groq_mensagem_e_resposta_seguem_sdk(
    ia: SentinelaAI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ai_core, "GROQ_MODEL", "modelo-groq-do-cenario")
    montar = Mock(return_value=PROMPT)
    monkeypatch.setattr(ia, "_montar_prompt", montar)
    chamadas = []

    def create(*, messages: list, model: str, timeout: float) -> SimpleNamespace:
        chamadas.append((messages, model))
        assert messages == [{"role": "user", "content": PROMPT}]
        assert model == "modelo-groq-do-cenario"
        assert timeout is not None and timeout > 0
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=TEXTO))]
        )

    ia.clients["groq"] = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(
        ia, "_call_ollama", Mock(side_effect=AssertionError("já há resposta"))
    )
    r = ia.analisar(" tsta3 ", {})
    assert r["content"] == TEXTO
    assert r["model"].casefold() == "groq"
    montar.assert_called_once_with("TSTA3", {})
    assert len(chamadas) == 1


def test_gemini_model_contents_e_text_seguem_sdk(
    ia: SentinelaAI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ai_core, "GEMINI_MODEL", "modelo-gemini-do-cenario")
    monkeypatch.setattr(ia, "_montar_prompt", Mock(return_value=PROMPT))
    chamadas = []

    def generate_content(*, model: str, contents: str) -> SimpleNamespace:
        chamadas.append((model, contents))
        assert model == "modelo-gemini-do-cenario"
        assert contents == PROMPT
        return SimpleNamespace(text=TEXTO)

    ia.clients["gemini"] = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    monkeypatch.setattr(
        ia, "_call_ollama", Mock(side_effect=AssertionError("já há resposta"))
    )
    r = ia.analisar("TSTA3", {})
    assert r["content"] == TEXTO
    assert r["model"].casefold() == "gemini"
    assert len(chamadas) == 1


@pytest.mark.parametrize("provedor", ["groq", "gemini"])
def test_cliente_recebe_apenas_identificador_injetado(
    ia: SentinelaAI, monkeypatch: pytest.MonkeyPatch, provedor: str
) -> None:
    # Substitui o objeto os local: nenhum getenv real é chamado.
    identificador = "identificador-publico-de-teste"
    nome = "GROQ_API_KEY" if provedor == "groq" else "GEMINI_API_KEY"
    monkeypatch.setattr(
        ai_core,
        "os",
        SimpleNamespace(getenv=lambda chave: identificador if chave == nome else None),
    )
    cliente = object()
    criar = Mock(return_value=cliente)
    if provedor == "groq":
        modulo = ModuleType("groq")
        modulo.Groq = criar
        monkeypatch.setitem(sys.modules, "groq", modulo)
    else:
        modulo = ModuleType("google")
        modulo.genai = SimpleNamespace(Client=criar)
        monkeypatch.setitem(sys.modules, "google", modulo)
    ia._setup()
    criar.assert_called_once_with(api_key=identificador)
    assert ia.clients == {provedor: cliente}


@pytest.mark.parametrize("ticker", ["", "TSTA3;select", "A/B3", " "])
def test_ticker_invalido_nao_chega_a_api(
    ia: SentinelaAI, monkeypatch: pytest.MonkeyPatch, ticker: str
) -> None:
    montar = Mock(side_effect=AssertionError("ticker recusado antes do prompt"))
    enviar = Mock(side_effect=AssertionError("ticker recusado antes do HTTP"))
    monkeypatch.setattr(ia, "_montar_prompt", montar)
    monkeypatch.setattr(ai_core.requests, "post", enviar)
    r = ia.analisar(ticker, {})
    assert "inválido" in r["content"]
    montar.assert_not_called()
    enviar.assert_not_called()


def test_future_sem_resposta_tem_prazo_e_cancelamento(
    ia: SentinelaAI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Future.result(timeout)/cancel: docs.python.org/3/library/concurrent.futures.html."""
    from concurrent.futures import TimeoutError as FuturesTimeout

    futuro = SimpleNamespace(result=Mock(side_effect=FuturesTimeout()), cancel=Mock())
    monkeypatch.setattr(ia._gemini_executor, "submit", Mock(return_value=futuro))
    ia.clients["gemini"] = SimpleNamespace(
        models=SimpleNamespace(generate_content=Mock())
    )
    monkeypatch.setattr(
        ia,
        "_call_ollama",
        Mock(return_value={"content": TEXTO, "model": "transporte simulado"}),
    )
    assert ia.analisar("TSTA3", {})["content"] == TEXTO
    prazo = futuro.result.call_args.kwargs["timeout"]
    assert prazo is not None and prazo > 0
    futuro.cancel.assert_called_once_with()


@pytest.mark.parametrize("provedor", ["groq", "gemini"])
def test_falha_do_sdk_conserva_causa_no_diagnostico(
    ia: SentinelaAI,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    provedor: str,
) -> None:
    nome = "GROQ_API_KEY" if provedor == "groq" else "GEMINI_API_KEY"
    monkeypatch.setattr(
        ai_core,
        "os",
        SimpleNamespace(
            getenv=lambda chave: (
                "identificador-publico-de-teste" if chave == nome else None
            )
        ),
    )
    criar = Mock(side_effect=ValueError("identificador recusado Ω"))
    if provedor == "groq":
        modulo = ModuleType("groq")
        modulo.Groq = criar
    else:
        modulo = ModuleType("google")
        modulo.genai = SimpleNamespace(Client=criar)
    monkeypatch.setitem(sys.modules, "groq" if provedor == "groq" else "google", modulo)
    ia._setup()
    assert not ia.clients
    assert "identificador recusado Ω" in caplog.text


def test_sdk_ausente_nao_declara_cliente_disponivel(
    ia: SentinelaAI, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        ai_core,
        "os",
        SimpleNamespace(
            getenv=lambda chave: (
                "identificador-publico-de-teste" if chave == "GEMINI_API_KEY" else None
            )
        ),
    )
    monkeypatch.setitem(sys.modules, "google", ModuleType("google"))
    monkeypatch.delitem(sys.modules, "google.genai", raising=False)
    ia._setup()
    assert not ia.clients
    assert "google-genai" in caplog.text.lower()
