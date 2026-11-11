"""F3-A-F4: a Selic do FII pelo caminho de produção, com `as_of` = hoje.

Ressalva da auditoria cruzada da 3-a (Claude, sobre o F3-6c): a fixture `autouse` do
`conftest` troca a fábrica `fii_engine.MacroContext` em toda a suíte, e o caminho real (série
completa do SGS 432 pelo `MacroProvider`) não era exercitado com `as_of` = hoje. Aqui a fábrica
volta a ser a classe `config.MacroContext`, sem provedor nem Selic injetados; só a rede (as
fixtures oficiais do SGS) e o relógio (o instante da coleta das fixtures) são dublês.
"""

from datetime import datetime

import pytest
from apoio_fii import enriquecer_fii

import config
import fii_engine
from config import SELIC_FALLBACK, MacroContext
from fii_engine import FIIEngine
from sentinela.data.providers import macro as provedor_macro
from tests.test_macro_por_data import COLETA, HOJE, _sgs_oficial


class _Relogio(datetime):
    """`datetime.now` parado no instante da coleta das fixtures (10/11/2026, 00:33 em Brasília)."""

    @classmethod
    def now(cls, tz=None):
        return COLETA.astimezone(tz) if tz is not None else COLETA.replace(tzinfo=None)


@pytest.fixture
def producao(monkeypatch, tmp_path):
    """Fábrica real do motor do FII, com o cache padrão do provedor dentro de `tmp_path`."""
    monkeypatch.chdir(tmp_path)  # MacroProvider() grava em data/macro, relativo
    monkeypatch.setattr(
        fii_engine, "MacroContext", MacroContext
    )  # desfaz a semente autouse
    monkeypatch.setattr(config, "datetime", _Relogio)
    monkeypatch.setattr(
        fii_engine,
        "get_selic_atual",
        lambda: pytest.fail("o motor do FII lê a Selic pelo MacroContext(as_of)"),
    )


def _fii():
    dados = enriquecer_fii(
        {"ticker": "TSTI11", "preco_atual": 100.0, "dy": 0.09, "pvp": 1.0}, ntnb=0.07
    )
    # o registro da taxa real precisa ser do mesmo dia da análise (F2B-58)
    dados["taxa_real"] = {
        **dados["taxa_real"],
        "as_of": COLETA.isoformat(),
        "data_base": "2026-11-06",
    }
    return dados


def test_as_of_hoje_pelo_caminho_de_producao_igual_ao_ultimos_1(
    producao, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        provedor_macro.requests, "get", lambda url, *a, **k: _sgs_oficial(url)
    )
    monkeypatch.setattr(config, "_selic_cache_value", None)
    monkeypatch.setattr(config, "_selic_cache_time", 0.0)
    atual = config.get_selic_atual()  # caminho antigo: `ultimos/1` do SGS 432
    assert atual != SELIC_FALLBACK

    resultado = FIIEngine().analisar(_fii(), as_of=COLETA)

    assert resultado["selic_liquida"] == pytest.approx(
        atual * MacroContext.FII_FATOR_IR
    )
    contexto = MacroContext(as_of=HOJE)
    assert contexto.selic == pytest.approx(atual)
    assert "proveniencia" in contexto.registro_por_data("selic")
    # o provedor padrão (sem injeção) gravou o cache da coleta, aqui dentro de tmp_path
    assert list((tmp_path / "data" / "macro").glob("*.json"))


def test_falha_da_fonte_cai_no_fallback_com_motivo(producao, monkeypatch):
    def fora_do_ar(url, *a, **k):
        raise OSError("SGS fora do ar")

    monkeypatch.setattr(provedor_macro.requests, "get", fora_do_ar)

    resultado = FIIEngine().analisar(_fii(), as_of=COLETA)

    assert resultado["selic_liquida"] == pytest.approx(
        SELIC_FALLBACK * MacroContext.FII_FATOR_IR
    )
    registro = MacroContext(as_of=HOJE).registro_por_data("selic")
    assert "valor" not in registro
    assert (
        registro["abstencao"] == "SGS fora do ar"
    )  # falha da fonte, não erro do código
    assert MacroContext(as_of=HOJE).selic == SELIC_FALLBACK
