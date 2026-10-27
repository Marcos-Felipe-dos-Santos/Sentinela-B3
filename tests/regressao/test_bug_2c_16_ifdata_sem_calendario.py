"""F2C-37: data-base não demonstra publicação até o corte; sem calendário abstém."""

from datetime import date

import pytest

from sentinela.data.providers import ifdata
from tests.test_cvm_bancos import CADASTRO_BB, CAPITAL_BB, _buscar_falso
from tests.test_ifdata_inadimplencia import CARTEIRA_BB


@pytest.mark.parametrize("corte", [date(2026, 7, 1), date(2026, 10, 27)])
def test_sem_calendario_nao_presume_publicacao(corte: date) -> None:
    buscar, pedidos = _buscar_falso(
        {
            "@AnoMes=202606&$filter=Cnpj": CADASTRO_BB,
            "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='5'": CAPITAL_BB,
            "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='16'": CARTEIRA_BB,
        }
    )
    resultado = ifdata.ler_capital("00.000.000/0001-91", corte, buscar)
    assert resultado.basileia == pytest.approx(0.151297835513664)
    assert resultado.inadimplencia is None
    assert "calendário" in resultado.motivos["inadimplencia"]
    assert not any("@Relatorio='16'" in pedido for pedido in pedidos)
