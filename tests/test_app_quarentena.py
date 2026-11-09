"""Quarentena da V1 (F0-9): aviso fixo em todas as telas e sem "Alocação Sugerida".

Usa o AppTest do Streamlit com banco temporário e sem rede: nenhuma tela dispara
coleta de dados sem clique.
"""

import ast
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"
MODOS = ["Terminal", "Carteira", "Config"]
PLANO_URL = (
    "https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/blob/main/docs/PLANO.md"
)


def _abrir(monkeypatch, tmp_path, modo):
    monkeypatch.chdir(tmp_path)  # o banco SQLite nasce no diretório atual
    st.cache_resource.clear()  # `load_engines` é cacheado e guardaria o banco do teste anterior
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    if modo != "Terminal":
        at.sidebar.radio[0].set_value(modo).run()
        assert not at.exception
    return at


@pytest.mark.parametrize("modo", MODOS)
def test_aviso_de_revisao_metodologica_em_todas_as_telas(monkeypatch, tmp_path, modo):
    at = _abrir(monkeypatch, tmp_path, modo)
    avisos = [w.value for w in at.warning]
    assert any("revisão metodológica" in a and PLANO_URL in a for a in avisos)
    assert any("não use para decisão" in a.lower() for a in avisos)


def test_alocacao_sugerida_nao_e_exibida():
    codigo = APP.read_text(encoding="utf-8")
    assert "Alocação Sugerida" not in codigo
    assert 'name="Alocação %"' not in codigo


def test_gestor_aposentado_nao_tem_rota_ou_produtor():
    arvore = ast.parse(APP.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom):
            assert no.module != "portfolio_engine"
        if isinstance(no, ast.Attribute):
            assert no.attr != "otimizar"
        if isinstance(no, ast.Compare):
            assert not any(
                isinstance(v, ast.Constant) and v.value == "Gestor"
                for v in no.comparators
            )


def test_menu_conserva_todas_as_telas_mantidas(monkeypatch, tmp_path):
    at = _abrir(monkeypatch, tmp_path, "Terminal")
    assert at.sidebar.radio[0].options == MODOS
