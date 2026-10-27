"""BUG-2C-24: taxa posterior ao corte não é taxa usada na lente do FII."""

from sentinela.data.rendimento_fii import MOTIVO_TAXA_POSTERIOR
from tests.test_rastreabilidade import _contexto, _fii


def test_taxa_recusada_aparece_com_motivo_na_fonte_da_lente():
    dados = _fii()
    dados["taxa_real"]["as_of"] = "2026-10-21T12:00:00+00:00"
    contexto = _contexto(dados, eh_fii=True)
    fonte = dict(contexto["fontes"])["Taxa da lente do FII (F2B-2)"]
    assert MOTIVO_TAXA_POSTERIOR in fonte
    assert "NTN-B real 7,00%" not in fonte


def test_tabela_nao_apresenta_taxa_recusada_como_insumo():
    dados = _fii()
    dados["taxa_real"]["as_of"] = "2026-10-21T12:00:00+00:00"
    contexto = _contexto(dados, eh_fii=True)
    assert contexto["taxa_real"] == [
        ("Taxa não utilizada pela lente do FII", MOTIVO_TAXA_POSTERIOR)
    ]
