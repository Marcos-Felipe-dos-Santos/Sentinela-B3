"""BUG-2B-41: ticker ausente não prova presença zero numa janela sem cobertura conhecida."""

from sentinela.data import liquidez


def test_ticker_ausente_sem_cobertura_nao_vira_zero():
    resultado = liquidez.avaliar(
        {"abstencao": liquidez.MOTIVO_TICKER_AUSENTE},
        janela=63,
        presenca_min=0.8,
        volume_min=500000,
    )
    assert "aviso" in resultado
    assert "abstencao" not in resultado
