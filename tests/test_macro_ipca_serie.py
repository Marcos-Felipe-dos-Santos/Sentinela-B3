"""IPCA das cinco DFP: produto mensal independente e disponibilidade oficial."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from sentinela.data.providers import macro

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)


def cenario():
    exercicios = [{"fim": f"{ano}-12-31"} for ano in range(2021, 2026)]
    linhas, eventos = [], []
    for numero in range(2021 * 12 + 11, 2025 * 12 + 12):
        ano, mes = divmod(numero, 12)
        mes += 1
        referencia = f"{ano:04}{mes:02}"
        linhas.append({"D1C": "1", "D2C": "63", "D3C": referencia, "MN": "%", "V": "1"})
        ano_pub, mes_pub = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        eventos.append(
            {
                "produto_id": 9256,
                "ano_referencia_inicio": ano,
                "mes_referencia_inicio": mes,
                "data_divulgacao": f"10/{mes_pub:02}/{ano_pub} 09:00:00",
            }
        )
    return exercicios, linhas, eventos


def provider(monkeypatch, linhas, eventos):
    p = macro.MacroProvider()
    chamadas = []

    def baixar(url, instante):
        chamadas.append((url, instante))
        conteudo = {"items": eventos} if url == macro.IBGE_CALENDARIO else linhas
        return macro.SnapshotMacro(
            json.dumps(conteudo), url, AS_OF.isoformat(), "a" * 64
        )

    monkeypatch.setattr(p, "baixar", baixar)
    return p, chamadas


def test_cinco_encerramentos_produto_mensal_sem_ipca_do_primeiro_mes(monkeypatch):
    exercicios, linhas, eventos = cenario()
    p, chamadas = provider(monkeypatch, linhas, eventos)
    resultado = p.ipca_serie(exercicios[::-1], AS_OF)
    esperado = {
        f"{ano}-12": float(Decimal("1.01") ** (12 * (ano - 2021)))
        for ano in range(2021, 2026)
    }
    assert resultado["indices"] == pytest.approx(esperado)
    assert resultado["publicacoes"]["2021-12"] == "2022-01-10"
    assert resultado["publicacoes"]["2025-12"] == "2026-01-10"
    assert resultado["fonte"] == chamadas[1][0]
    assert resultado["coleta"] == AS_OF.isoformat()
    assert resultado["proveniencia"]["hash_sha256"] == "a" * 64
    assert resultado["calendario"]["fonte"] == macro.IBGE_CALENDARIO
    assert chamadas == [
        (macro.IBGE_CALENDARIO, AS_OF),
        (
            "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/202112-202512?formato=json",
            AS_OF,
        ),
    ]


@pytest.mark.parametrize(
    "tipo",
    [
        "mes_ausente",
        "publicacao_ausente",
        "publicacao_futura",
        "outro_produto",
        "unidade",
        "conflito",
        "nao_finito",
        "fator_zero",
    ],
)
def test_serie_recusa_falta_de_cobertura_ou_formato_sem_inventar_indice(
    monkeypatch, tipo
):
    exercicios, linhas, eventos = cenario()
    if tipo == "mes_ausente":
        linhas.pop(12)
    elif tipo == "publicacao_ausente":
        eventos.pop(12)
    elif tipo == "publicacao_futura":
        eventos[12]["data_divulgacao"] = "21/10/2026 09:00:00"
    elif tipo == "outro_produto":
        eventos[12]["produto_id"] = 999
    elif tipo == "unidade":
        linhas[12]["MN"] = "índice"
    elif tipo == "conflito":
        linhas.append(linhas[12] | {"V": "2"})
    elif tipo == "nao_finito":
        linhas[12]["V"] = "inf"
    else:
        linhas[12]["V"] = "-100"
    p, _ = provider(monkeypatch, linhas, eventos)
    with pytest.raises(ValueError, match="IPCA|fator"):
        p.ipca_serie(exercicios, AS_OF)


def test_deflacao_mensal_e_duplicata_igual_sao_validas(monkeypatch):
    exercicios, linhas, eventos = cenario()
    linhas[1]["V"] = "-1"
    linhas.append(linhas[1].copy())
    linhas.append(linhas[2] | {"D2C": "999", "V": "999"})
    p, _ = provider(monkeypatch, linhas, eventos)
    esperado = float(Decimal(".99") * Decimal("1.01") ** 47)
    assert p.ipca_serie(exercicios, AS_OF)["indices"]["2025-12"] == pytest.approx(
        esperado
    )


@pytest.mark.parametrize(
    "exercicios", [[], [{"fim": "2025-12-30"}], [{"fim": "2025-12-31"}] * 5]
)
def test_cinco_encerramentos_distintos_e_no_fim_do_mes(monkeypatch, exercicios):
    _, linhas, eventos = cenario()
    p, chamadas = provider(monkeypatch, linhas, eventos)
    with pytest.raises(ValueError, match="cinco|encerramento"):
        p.ipca_serie(exercicios, AS_OF)
    assert chamadas == []


def test_as_of_sem_fuso_nao_inicia_coleta(monkeypatch):
    exercicios, linhas, eventos = cenario()
    p, chamadas = provider(monkeypatch, linhas, eventos)
    with pytest.raises(ValueError, match="fuso"):
        p.ipca_serie(exercicios, AS_OF.replace(tzinfo=None))
    assert chamadas == []


@pytest.mark.parametrize("posicao", [0, 1, 12, 48])
def test_cada_mes_da_janela_exige_indice_e_calendario(monkeypatch, posicao):
    exercicios, linhas, eventos = cenario()
    eventos[posicao]["data_divulgacao"] = "20/10/2026 09:00:00"
    p, _ = provider(monkeypatch, linhas, eventos)
    with pytest.raises(ValueError, match="IPCA ausente ou não publicado"):
        p.ipca_serie(exercicios, AS_OF)


@pytest.mark.parametrize("valor", [None, "", True, "NaN", "-inf", "-101", "abc"])
def test_percentual_invalido_nao_entra_no_produto(monkeypatch, valor):
    exercicios, linhas, eventos = cenario()
    linhas[1]["V"] = valor
    p, _ = provider(monkeypatch, linhas, eventos)
    with pytest.raises(ValueError, match="IPCA"):
        p.ipca_serie(exercicios, AS_OF)


def test_overflow_do_produto_abstem(monkeypatch):
    exercicios, linhas, eventos = cenario()
    for linha in linhas:
        linha["V"] = "1e300"
    p, _ = provider(monkeypatch, linhas, eventos)
    with pytest.raises(ValueError, match="acumulado"):
        p.ipca_serie(exercicios, AS_OF)


def test_mes_de_encerramento_nao_civil_e_fontes_identificadas(monkeypatch):
    exercicios, linhas, eventos = cenario()
    exercicios = [{"fim": f"{ano}-02-28"} for ano in range(2022, 2027)]
    exercicios[2]["fim"] = "2024-02-29"
    # A cobertura continua explícita: nove meses posteriores são acrescentados.
    for ano, mes in [(2026, m) for m in range(1, 13)] + [(2027, 1), (2027, 2)]:
        linhas.append(
            {"D1C": "1", "D2C": "63", "D3C": f"{ano}{mes:02}", "MN": "%", "V": "1"}
        )
        eventos.append(
            {
                "produto_id": 9256,
                "ano_referencia_inicio": ano,
                "mes_referencia_inicio": mes,
                "data_divulgacao": "10/03/2027 09:00:00",
            }
        )
    p, _ = provider(monkeypatch, linhas, eventos)
    r = p.ipca_serie(exercicios, datetime(2027, 4, 1, tzinfo=UTC))
    assert set(r["indices"]) == {f"{ano}-02" for ano in range(2022, 2027)}
    assert r["indices"]["2026-02"] == pytest.approx(float(Decimal("1.01") ** 48))
    assert r["variavel"] == "63"
    assert r["tabela"] == "1737"
    assert r["publicacoes"]["2026-02"] == "2027-03-10"


def test_filtra_outro_territorio_e_outra_variavel(monkeypatch):
    exercicios, linhas, eventos = cenario()
    linhas.extend(
        [linhas[1] | {"D1C": "2", "V": "200"}, linhas[1] | {"D2C": "2", "V": "200"}]
    )
    p, _ = provider(monkeypatch, linhas, eventos)
    assert p.ipca_serie(exercicios, AS_OF)["indices"]["2025-12"] == pytest.approx(
        float(Decimal("1.01") ** 48)
    )
