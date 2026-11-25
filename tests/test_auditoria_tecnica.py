"""F4-A14: caracterização de `auditoria.auditar_tecnica`, escrita e verde antes da delegação.

Fixa o registro (`_rel`, em JSON, que preserva `NaN`) e o texto impresso (sem cores, por
SHA-256) em séries sintéticas com mais e com menos de 30 pregões (0, 1, 14, 29, 30, 31, 49,
50, 199, 200 e 260), com preços constantes (40 e 260 pregões), em queda (RSI abaixo de 30),
com média em empate decimal (16,055: o arredondamento do motor daria 16,06, e o script mostra
16,05) e com `NaN` no último fechamento. Nenhum valor é dado de mercado.
"""

import contextlib
import hashlib
import io
import json
import math

import pandas as pd
import pytest

import auditoria
from technical_engine import TechnicalEngine


def _senoide(n: int) -> list[float]:
    return [round(20 + 3 * math.sin(i / 5) + i * 0.05, 4) for i in range(n)]


def _serie(nome: str) -> list[float]:
    if nome.startswith("constante"):
        return [40.0] * int(nome.removeprefix("constante"))
    if nome == "queda60":
        return [round(60 - i * 0.5, 4) for i in range(60)]
    if nome == "empate60":
        return [16.055] * 60
    if nome == "nan_no_fim60":
        return [*_senoide(59), float("nan")]
    return _senoide(int(nome.removeprefix("n")))


ESPERADO = {
    "n0": (
        '{"disponivel": false}',
        "c921bc224037f55ed41cba0a33330f528014e9beedf3a2536177353ec906fdec",
    ),
    "n1": (
        '{"disponivel": true, "ma200": null, "ma50": null, "preco": 20.0, "pregoes": 1, "rsi": 50.0, "tendencia": "Indefinida"}',
        "61d813feb3df68676a0d6deb5127d076dedfc38579e870a3cef8ec5e94e10a97",
    ),
    "n14": (
        '{"disponivel": true, "ma200": null, "ma50": null, "preco": 22.2, "pregoes": 14, "rsi": 60.6, "tendencia": "Indefinida"}',
        "352e64de8ce9689241949e0f2581cacbd48582ee3665d8721a8e7ad7676d4713",
    ),
    "n29": (
        '{"disponivel": true, "ma200": null, "ma50": null, "preco": 19.51, "pregoes": 29, "rsi": 44.3, "tendencia": "Indefinida"}',
        "e19e6d26e3e6085ae4a5c6c7a759d88914464ef3a72fd9a5721b4917171acbfe",
    ),
    "n30": (
        '{"disponivel": true, "ma200": null, "ma50": null, "preco": 20.06, "pregoes": 30, "rsi": 51.4, "tendencia": "Indefinida"}',
        "8f52c371e0aac735547198a326d67b0a0010f98f8b9585dba967dab618009dc5",
    ),
    "n31": (
        '{"disponivel": true, "ma200": null, "ma50": null, "preco": 20.66, "pregoes": 31, "rsi": 57.8, "tendencia": "Indefinida"}',
        "c7ec221a0634b4ad5055aeb5897d0f4c58094ba7a697d02a0df90585cb8fefab",
    ),
    "n49": (
        '{"disponivel": true, "ma200": null, "ma50": null, "preco": 21.88, "pregoes": 49, "rsi": 42.3, "tendencia": "Indefinida"}',
        "54c0990a9bb1495e03bb44daa3d53155d6f9693db9e49268212b1a49b54db90a",
    ),
    "n50": (
        '{"disponivel": true, "ma200": null, "ma50": 21.79, "preco": 21.35, "pregoes": 50, "rsi": 38.3, "tendencia": "Baixa (Curto Prazo)"}',
        "0f1733e2c9dda36c51b01e597db42af7a2b341f8c492e50459329a214de134b3",
    ),
    "n199": (
        '{"disponivel": true, "ma200": null, "ma50": 28.76, "preco": 32.74, "pregoes": 199, "rsi": 79.4, "tendencia": "Alta (Curto Prazo)"}',
        "ffef4d64b9eb9db6e0089b39197d5f8b05c986bafb436bd9ac8318cd426d63d3",
    ),
    "n200": (
        '{"disponivel": true, "ma200": 25.09, "ma50": 28.92, "preco": 32.54, "pregoes": 200, "rsi": 76.1, "tendencia": "Alta (Longo Prazo)"}',
        "7737621282e55a0fea774d4948ac2a5067c51ab66f80f7446b0693299b31093d",
    ),
    "n260": (
        '{"disponivel": true, "ma200": 28.04, "ma50": 31.6, "preco": 35.95, "pregoes": 260, "rsi": 80.7, "tendencia": "Alta (Longo Prazo)"}',
        "8cf9e1e351fa879e76df57db1f9f63956a0bcaed482d39ea418509e4908ac123",
    ),
    "constante40": (
        '{"disponivel": true, "ma200": null, "ma50": null, "preco": 40.0, "pregoes": 40, "rsi": 50.0, "tendencia": "Indefinida"}',
        "b09c193b90f9b67dd76eda516579613020720e028f5c65f97a319e7139cfc4b7",
    ),
    "constante260": (
        '{"disponivel": true, "ma200": 40.0, "ma50": 40.0, "preco": 40.0, "pregoes": 260, "rsi": 50.0, "tendencia": "Baixa (Longo Prazo)"}',
        "61e21f1e90c444f015746876a25eddc036fabff2ca128897e15d97f3f75074ca",
    ),
    "queda60": (
        '{"disponivel": true, "ma200": null, "ma50": 42.75, "preco": 30.5, "pregoes": 60, "rsi": 0.0, "tendencia": "Baixa (Curto Prazo)"}',
        "ce6359b2fe7bf39402a2bcf46cdd310516239d8aada67beb8fb2e36fb7ee5267",
    ),
    "empate60": (
        '{"disponivel": true, "ma200": null, "ma50": 16.05, "preco": 16.05, "pregoes": 60, "rsi": 50.0, "tendencia": "Baixa (Curto Prazo)"}',
        "154a2e641ff65b8ccbfe78a3b1856cc29556112fc14125b42029330b36416338",
    ),
    "nan_no_fim60": (
        '{"disponivel": true, "ma200": null, "ma50": null, "preco": NaN, "pregoes": 60, "rsi": 38.8, "tendencia": "Indefinida"}',
        "c24c0b67e9eb870e607afac7cc31673e6e8994c4fe51ce4a805d28604652443a",
    ),
}


@pytest.mark.parametrize("nome", list(ESPERADO))
def test_saida_da_tecnica_fica_igual(monkeypatch, nome):
    registro, sha_texto = ESPERADO[nome]
    monkeypatch.setattr(auditoria, "_rel", {"tickers": {"TSTA3": {}}})
    impresso = io.StringIO()
    with contextlib.redirect_stdout(impresso):
        auditoria.auditar_tecnica(
            "TSTA3", {"historico": pd.DataFrame({"Close": _serie(nome)})}
        )

    tecnica = auditoria._rel["tickers"]["TSTA3"]["tecnica"]
    assert json.dumps(tecnica, sort_keys=True) == registro
    texto = auditoria.strip_ansi(impresso.getvalue())
    assert hashlib.sha256(texto.encode()).hexdigest() == sha_texto, texto


def test_historico_ausente_fica_indisponivel(monkeypatch):
    monkeypatch.setattr(auditoria, "_rel", {"tickers": {"TSTA3": {}}})
    with contextlib.redirect_stdout(io.StringIO()):
        auditoria.auditar_tecnica("TSTA3", {})

    assert auditoria._rel["tickers"]["TSTA3"]["tecnica"] == {"disponivel": False}


def test_limiar_do_script_e_o_do_motor_tecnico():
    """Abaixo do limiar o motor devolve a tendência neutra; a partir dele, a calculada."""
    queda = [round(60 - i * 0.5, 4) for i in range(60)]
    motor = TechnicalEngine()
    limiar = getattr(auditoria, "PREGOES_MOTOR_TECNICO", 30)

    curta = motor.calcular_indicadores(pd.DataFrame({"Close": queda[: limiar - 1]}))
    longa = motor.calcular_indicadores(pd.DataFrame({"Close": queda[:limiar]}))

    assert curta["momento"] == "Neutro" and curta["rsi"] == 50
    assert longa["momento"] != "Neutro"
