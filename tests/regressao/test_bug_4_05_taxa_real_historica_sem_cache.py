"""BUG-4-05: leituras históricas da taxa real usam o banco, fora do cache corrente."""

from datetime import UTC, datetime, timedelta

import pytest

import config

D = datetime(2026, 10, 20, 15, tzinfo=UTC)


@pytest.fixture
def relogio(monkeypatch: pytest.MonkeyPatch) -> type[datetime]:
    class Relogio(datetime):
        valor = D

        @classmethod
        def now(cls, tz=None):
            return cls.valor.astimezone(tz)

    monkeypatch.setattr(config, "datetime", Relogio)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    return Relogio


def test_historico_ignora_cache_de_rede_da_epoca_do_corte(
    relogio: type[datetime], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "_carregar_taxa_real", lambda *_: {"ntnb": 0.08})
    monkeypatch.setattr(config, "_taxa_real_do_banco", lambda *_: {"ntnb": 0.07})
    assert config.get_taxa_real(as_of=D) == {"ntnb": 0.08}

    relogio.valor = D + timedelta(days=1)

    assert config.get_taxa_real(as_of=D) == {"ntnb": 0.07}


def test_banco_historico_e_relido_e_nunca_entra_no_cache_corrente(
    relogio: type[datetime], monkeypatch: pytest.MonkeyPatch
) -> None:
    relogio.valor = D + timedelta(days=1)
    registros = iter([{"ntnb": 0.07}, {"ntnb": 0.075}])
    monkeypatch.setattr(config, "_taxa_real_do_banco", lambda *_: next(registros))

    assert config.get_taxa_real(as_of=D) == {"ntnb": 0.07}
    assert config.get_taxa_real(as_of=D + timedelta(hours=1)) == {"ntnb": 0.075}
    assert config._taxa_real_cache == {}


def test_data_do_servico_define_a_leitura_sem_consultar_o_relogio(
    relogio: type[datetime], monkeypatch: pytest.MonkeyPatch
) -> None:
    def falha(*args: object) -> None:
        pytest.fail("a leitura com corte do serviço usou o relógio ou a fonte corrente")

    monkeypatch.setattr(relogio, "now", falha)
    monkeypatch.setattr(config, "_carregar_taxa_real", falha)
    monkeypatch.setattr(config, "_taxa_real_do_banco", lambda *_: {"ntnb": 0.07})

    assert config.get_taxa_real(as_of=D, hoje=D.date() + timedelta(days=1)) == {
        "ntnb": 0.07
    }
    assert config._taxa_real_cache == {}


def test_abstencao_do_banco_vazio_da_lugar_a_taxa_depois_da_carga(
    relogio: type[datetime], monkeypatch: pytest.MonkeyPatch
) -> None:
    relogio.valor = D + timedelta(days=1)
    sem_taxa = {"abstencao": "series_macro sem NTN-B até a data"}
    registros = iter([sem_taxa, {"ntnb": 0.07}])
    monkeypatch.setattr(config, "_taxa_real_do_banco", lambda *_: next(registros))

    assert config.get_taxa_real(as_of=D) == sem_taxa
    assert config.get_taxa_real(as_of=D + timedelta(hours=1)) == {"ntnb": 0.07}
