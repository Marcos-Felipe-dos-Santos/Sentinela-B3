"""BUG-4-08: P/VP e Selic líquida continuam disponíveis quando a lente do FII se abstém."""

import pytest
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

import fii_engine
from sentinela.data.rendimento_fii import MOTIVO_SEM_INFORME


@pytest.mark.parametrize(
    ("cenario", "motivo"),
    [
        ("papel", "tipo de FII fora do escopo na 2B: papel"),
        ("fof", "tipo de FII fora do escopo na 2B: fundo de fundos"),
        ("sem_informe", MOTIVO_SEM_INFORME),
        ("sem_dy", "Dados insuficientes (DY ausente ou inválido)"),
    ],
)
def test_contexto_permanece_na_abstencao(
    monkeypatch: pytest.MonkeyPatch, cenario: str, motivo: str
) -> None:
    monkeypatch.setattr(fii_engine, "get_selic_atual", lambda: 0.10)
    dados = enriquecer_fii(
        {"ticker": "TSTF11", "preco_atual": 100.0, "pvp": 0.9, "dy": 0.09}
    )
    if cenario in ("papel", "fof"):
        campo = "CRI" if cenario == "papel" else "FII"
        dados["informe_fii"]["composicoes"][0].update(
            {"Imoveis_Renda_Acabados": "50", campo: "900"}
        )
    else:
        dados.pop("informe_fii")
        if cenario == "sem_dy":
            dados.pop("dy")

    resultado = fii_engine.FIIEngine().analisar(dados, as_of=AS_OF_GORDON)

    lente = resultado["lentes"]["Rendimento do FII"]
    assert lente["abstencao"] == motivo
    assert lente["valor"] is None
    assert lente["distancia_ao_preco_pct"] is None
    assert resultado["pvp"] == pytest.approx(0.9)
    assert resultado["selic_liquida"] == pytest.approx(0.085)


def test_abstencao_historica_preserva_pvp_sem_consultar_selic_corrente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def macro_corrente(**_: object) -> None:
        pytest.fail("o caminho histórico de abstenção tentou abrir a fonte corrente")

    monkeypatch.setattr(fii_engine, "MacroContext", macro_corrente)
    dados = {
        "ticker": "TSTF11",
        "preco_atual": 100.0,
        "pvp": 0.9,
        "disponibilidade_por_publicacao": True,
    }

    resultado = fii_engine.FIIEngine().analisar(dados, as_of=AS_OF_GORDON)

    assert resultado["pvp"] == pytest.approx(0.9)
    assert resultado["selic_liquida"] is None
    lente = resultado["lentes"]["Rendimento do FII"]
    assert lente["valor"] is None
    assert lente["abstencao"] == "Dados insuficientes (DY ausente ou inválido)"
