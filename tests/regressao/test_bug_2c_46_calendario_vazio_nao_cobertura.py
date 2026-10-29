"""BUG-2C-46: calendário vazio não comprova ano sem distribuição B3."""

from sentinela.data.qualidade_inputs import entradas
from tests.test_qualidade import AS_OF
from tests.test_qualidade_inputs import dados


def test_calendario_vazio_nao_certifica_ano_zero():
    d = dados()
    d["calendario_proventos_b3"]["pregoes"] = []
    d["proventos_b3"]["registros"] = d["proventos_b3"]["registros"][:1]
    d["proventos_b3"]["total"] = 1
    r = entradas(d, AS_OF)
    assert all(e["proventos_b3"]["valor"] is None for e in r)
    assert all(e["proventos_b3"]["cobertura_integral"] is False for e in r)


def test_so_bordas_fora_do_ano_nao_comprovam_calendario_anual():
    d = dados()
    d["calendario_proventos_b3"]["pregoes"] = ["2019-12-02", "2026-01-15"]
    d["proventos_b3"]["registros"] = d["proventos_b3"]["registros"][:1]
    d["proventos_b3"]["total"] = 1
    assert entradas(d, AS_OF)[0]["proventos_b3"]["valor"] is None
