"""BUG-4-25: a referência comprovada no recuo deve acompanhar a versão até a leitura."""

from io import BytesIO

import pytest

import market_engine
from cvm_provider import CVMProvider
from tests.regressao.test_bug_4_23_dfp_ano_anterior_fora_do_corte import AS_OF, D, _dfp
from tests.test_cvm_series import CD_CVM, CNPJ
from tests.test_market_engine import _engine

SETEMBRO = ("2025-09-30", "1", "2024-10-01", 100)
DEZEMBRO = ("2025-12-31", "1", "2025-01-01", 900)


@pytest.fixture
def analisar(tmp_path, monkeypatch):
    def zip_dfp(nome, ano, linhas, indice):
        memoria = _dfp(BytesIO(), ano, linhas, indice)
        caminho = tmp_path / nome
        caminho.write_bytes(memoria.getvalue())
        return caminho

    indice = (
        f"{CNPJ};2025-09-30;1;{CD_CVM};DFP;2026-06-15\n"
        f"{CNPJ};2025-12-31;1;{CD_CVM};DFP;2026-06-16\n"
    )
    anterior = zip_dfp("anterior.zip", 2025, [SETEMBRO, DEZEMBRO], indice)
    incompleto = zip_dfp("incompleto.zip", 2025, [DEZEMBRO], indice)
    corrente = zip_dfp("corrente.zip", 2026, [], "")

    def executar(*, retirar_setembro=False):
        provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
        arquivos_2025 = iter([anterior])

        def baixar_dfp(ano):
            if ano == 2026:
                return corrente
            if ano == 2025:
                return next(arquivos_2025, incompleto if retirar_setembro else anterior)
            raise FileNotFoundError(ano)

        def sem_itr(ano):
            raise FileNotFoundError(ano)

        monkeypatch.setattr(provedor, "baixar_dfp", baixar_dfp)
        monkeypatch.setattr(provedor, "baixar_itr", sem_itr)
        monkeypatch.setattr(market_engine, "_hoje_sp", lambda: D)
        engine = _engine(monkeypatch, info={}, cvm=provedor)
        dados = {"cd_cvm": CD_CVM, "preco_atual": 10.0}
        engine._buscar_cvm("TSTA3", dados, as_of=AS_OF)
        return dados

    return executar


def test_snapshot_le_setembro_e_exclui_dezembro_entregue_em_d(analisar):
    dados = analisar()

    assert dados["lucro_liquido"] == 100_000
    assert dados["modelo_bpp_proveniencia"]["periodo_referencia"] == SETEMBRO[0]
    assert dados["modelo_bpp_proveniencia"]["versao"] == "1"
    assert "_documento_dfp_final" not in dados


def test_serie_le_setembro_e_exclui_dezembro_entregue_em_d(analisar):
    dados = analisar()

    (ultimo,) = dados["serie_cvm"]["exercicios"]
    assert ultimo["lucro_liquido"] == 100_000
    assert ultimo["dt_refer"] == SETEMBRO[0]
    assert ultimo["versao"] == "1"


def test_snapshot_abstem_quando_setembro_some_do_demonstrativo(analisar):
    dados = analisar(retirar_setembro=True)

    assert dados["cvm_disponivel"] is False
    assert "lucro_liquido" not in dados


def test_serie_abstem_quando_setembro_some_do_demonstrativo(analisar):
    dados = analisar(retirar_setembro=True)

    assert dados["serie_cvm"]["exercicios"] == []
    assert SETEMBRO[0] in dados["serie_cvm"]["abstencao"]
