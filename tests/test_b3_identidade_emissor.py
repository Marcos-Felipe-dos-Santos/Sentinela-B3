"""Identidade do emissor na relação de proventos da B3 (F3-P01; decisões 30 e 33).

Nome de pregão do GetDetail transformado por regra fixa ("S/A" e "S.A." → "SA"); a relação
lida pelo nome só vale com a conferência da decisão 33: (a) cada espécie da relação tem
ISIN da companhia no GetDetail pelo código CVM; (b) cada provento do complemento aparece
na relação com a mesma data com e o mesmo valor (|relação − complemento arredondado a 4
casas| ≤ 0,00005); (c) complemento vazio abstém; (d) qualquer falha abstém com motivo.
Fixture oficial da Ambev (código CVM 23264), coletada em 10/11/2026, com o homônimo
"AMBEV" (2000 a 2013).
"""

import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from apoio_escopo import de_empresa

import market_engine
from market_engine import MarketEngine
from sentinela.data import proventos_b3 as pb
from sentinela.data.providers import b3_proventos
from valuation_engine import ValuationEngine

PASTA = Path(__file__).parent / "fixtures" / "contratos"
AGORA = datetime(2026, 11, 10, 15, tzinfo=UTC)
IDENTIDADE = pb.MOTIVO_IDENTIDADE


def _fixture(nome):
    return json.loads((PASTA / nome).read_text(encoding="utf-8"))


ABEV = _fixture("b3_proventos_abev_2026.json")["membros"]
LREN = _fixture("b3_proventos_lren_2026.json")


def _parametros(endereco):
    metodo, codificado = endereco.removeprefix(b3_proventos.URL_BASE + "/").split(
        "/", 1
    )
    return metodo, json.loads(base64.b64decode(codificado))


def _b3_ambev(relacoes=None, detalhe=None, complemento=None):
    """B3 a partir da fixture oficial; `relacoes` troca o nome de pregão de cada lista."""
    paginas = relacoes or {"AMBEV SA": ["GetListedCashDividends_AMBEV_SA.json"]}
    chamadas = []

    def obter(endereco):
        metodo, parametros = _parametros(endereco)
        chamadas.append((metodo, parametros))
        if metodo == "GetDetail":
            corpo = json.loads(ABEV["GetDetail.json"]) if detalhe is None else detalhe
        elif metodo == "GetListedSupplementCompany":
            corpo = (
                json.loads(ABEV["GetListedSupplementCompany.json"])
                if complemento is None
                else complemento
            )
        else:
            nomes = paginas.get(parametros["tradingName"], [])
            if len(nomes) < parametros["pageNumber"]:
                corpo = {"page": {"totalRecords": 0, "totalPages": 0}, "results": []}
            else:
                corpo = json.loads(ABEV[nomes[parametros["pageNumber"] - 1]])
        return corpo, {"url": endereco}

    obter.chamadas = chamadas
    return obter


HOMONIMO = {
    "AMBEV SA": [
        "GetListedCashDividends_AMBEV_p1.json",
        "GetListedCashDividends_AMBEV_p2.json",
    ]
}


# ── nome de pregão ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("nome", "consulta"),
    [
        ("AMBEV S/A", "AMBEV SA"),
        ("KLABIN S/A", "KLABIN SA"),
        ("TESTE S.A.", "TESTE SA"),
        ("TESTE S.A", "TESTE SA"),
        ("TESTE S/A ON", "TESTE SA ON"),
        ("LOJAS RENNER", "LOJAS RENNER"),
        ("AMBEV SA", "AMBEV SA"),
        ("CASAS/AMIGAS", "CASAS/AMIGAS"),
        ("BS/A", "BS/A"),
    ],
)
def test_nome_de_pregao_pela_regra_escrita(nome, consulta):
    assert b3_proventos.nome_de_consulta(nome) == consulta


def test_relacao_pelo_nome_transformado_e_isins_do_getdetail():
    obter = _b3_ambev()
    relacao = b3_proventos.coletar(23264, AGORA, obter)
    consultas = [
        p["tradingName"] for m, p in obter.chamadas if m == "GetListedCashDividends"
    ]
    assert consultas == ["AMBEV SA"]
    assert relacao.nome_pregao == "AMBEV SA"
    assert relacao.isins == ("BRABEVACNOR1",)
    assert relacao.total == len(relacao.registros) == 40
    assert relacao.identidade is None


# ── conferência da decisão 33 ────────────────────────────────────────────────


def test_homonimo_recusado_pela_especie_sem_isin():
    relacao = b3_proventos.coletar(23264, AGORA, _b3_ambev(HOMONIMO))
    assert relacao.total == len(relacao.registros) == 134
    assert relacao.identidade == (
        f"{IDENTIDADE}: espécie PN da relação sem ISIN da companhia no GetDetail"
    )


def test_homonimo_so_com_on_recusado_pelo_complemento():
    registros = [
        r
        for nome in HOMONIMO["AMBEV SA"]
        for r in json.loads(ABEV[nome])["results"]
        if r["typeStock"] == "ON"
    ]
    complemento = json.loads(ABEV["GetListedSupplementCompany.json"])[0][
        "cashDividends"
    ]
    motivo = pb.conferir_emissor(registros, complemento, ("BRABEVACNOR1",))
    assert motivo == (
        f"{IDENTIDADE}: provento do complemento JRS CAP PROPRIO 21/09/2026 "
        "ausente da relação"
    )


def test_complemento_vazio_abstem():
    complemento = json.loads(ABEV["GetListedSupplementCompany.json"])
    complemento[0]["cashDividends"] = []
    relacao = b3_proventos.coletar(23264, AGORA, _b3_ambev(complemento=complemento))
    assert relacao.identidade == (
        "identidade do emissor não comprovada: complemento sem proventos para conferir"
    )


@pytest.mark.parametrize(
    "detalhe",
    [
        {"tradingName": "AMBEV S/A", "issuingCompany": "ABEV"},
        {"tradingName": "AMBEV S/A", "issuingCompany": "ABEV", "otherCodes": None},
        {"tradingName": "AMBEV S/A", "issuingCompany": "ABEV", "otherCodes": []},
        {
            "tradingName": "AMBEV S/A",
            "issuingCompany": "ABEV",
            "otherCodes": [{"code": "X"}],
        },
        {
            "tradingName": "AMBEV S/A",
            "issuingCompany": "ABEV",
            "otherCodes": ["BRABEVACNOR1"],
        },
    ],
)
def test_getdetail_sem_isin_abstem(detalhe):
    relacao = b3_proventos.coletar(23264, AGORA, _b3_ambev(detalhe=detalhe))
    assert relacao.isins == ()
    assert relacao.identidade == f"{IDENTIDADE}: GetDetail sem ISIN da companhia"


def _r(data, valor, especie="ON"):
    return {"typeStock": especie, "lastDatePriorEx": data, "valueCash": valor}


def _c(data, valor):
    return {
        "lastDatePrior": data,
        "rate": valor,
        "label": "DIVIDENDO",
        "isinCode": "BRTSTEACNOR1",
    }


@pytest.mark.parametrize(
    ("relacao", "complemento", "conferida"),
    [
        ("0,240666", "0,24066600000", True),  # Lojas Renner, 22/09/2026
        ("0,2407", "0,24066600000", True),
        ("0,2406", "0,24066600000", False),
        ("0,24072", "0,24066600000", True),
        ("0,24076", "0,24066600000", False),
        ("0,0713", "0,07130000000", True),
        ("3,0064572", "3,00645720000", True),
        ("0,1235", "0,12345000000", True),  # empate arredonda para cima
        ("0,1234", "0,12345000000", False),
        ("0,5", "0,51", False),
        ("0,24065", "0,24066600000", True),  # no limite de 0,00005
        ("1.234,5600", "1234,56000000000", True),  # separador de milhar
        ("1234,56", "1.234,56000000000", True),
    ],
)
def test_valor_na_precisao_da_relacao(relacao, complemento, conferida):
    motivo = pb.conferir_emissor(
        [_r("10/12/2025", relacao)], [_c("10/12/2025", complemento)], ("BRTSTEACNOR1",)
    )
    assert (motivo is None) is conferida, motivo


@pytest.mark.parametrize(
    ("registros", "complemento", "motivo"),
    [
        (
            [_r("11/12/2025", "0,5")],
            [_c("10/12/2025", "0,5")],
            "provento do complemento DIVIDENDO 10/12/2025 ausente da relação",
        ),
        (
            [],
            [_c("10/12/2025", "0,5")],
            "provento do complemento DIVIDENDO 10/12/2025 ausente da relação",
        ),
        (
            [_r("10/12/2025", "x")],
            [_c("10/12/2025", "0,5")],
            "provento do complemento DIVIDENDO 10/12/2025 ausente da relação",
        ),
        (
            [_r("10/12/2025", "0,5")],
            [_c(None, "0,5")],
            "provento do complemento ilegível",
        ),
        (
            [_r("10/12/2025", "0,5")],
            [_c("10/12/2025", "x")],
            "provento do complemento ilegível",
        ),
        (
            [_r("10/12/2025", "0,5")],
            [_c("10/12/2025", "NaN")],
            "provento do complemento ilegível",
        ),
        ([_r("10/12/2025", "0,5")], ["x"], "provento do complemento ilegível"),
        (
            [_r("10/12/2025", "0,5", None)],
            [_c("10/12/2025", "0,5")],
            "espécie None da relação sem ISIN da companhia no GetDetail",
        ),
        (
            [_r("10/12/2025", "0,5", "PNA")],
            [_c("10/12/2025", "0,5")],
            "espécie PNA da relação sem ISIN da companhia no GetDetail",
        ),
        (["x"], [_c("10/12/2025", "0,5")], "registro da relação ilegível"),
    ],
)
def test_falha_da_conferencia_abstem_com_motivo(registros, complemento, motivo):
    assert pb.conferir_emissor(registros, complemento, ("BRTSTEACNOR1",)) == (
        f"{IDENTIDADE}: {motivo}"
    )


# Taesa (código CVM 20257), B3 real em 10/11/2026 (`outputs/f3-p01-units.txt`): ISINs
# TAEE3, TAEE4 e TAEE11; a relação traz ON e PN; o complemento traz cada provento por
# ISIN da ON, da PN e da unit (CDAM, valor por unit = ON + 2 PN).
TAESA = ("BRTAEEACNOR9", "BRTAEEACNPR6", "BRTAEECDAM10")


def _taesa(isin, valor):
    return {
        "lastDatePrior": "14/08/2026",
        "rate": valor,
        "label": "DIVIDENDO",
        "isinCode": isin,
    }


def test_unit_confere_as_especies_dos_componentes():
    registros = [
        _r("14/08/2026", "0,08025458488"),
        _r("14/08/2026", "0,08025458488", "PN"),
    ]
    complemento = [
        _taesa("BRTAEEACNOR9", "0,08025458488"),
        _taesa("BRTAEEACNPR6", "0,08025458488"),
    ]
    assert pb.conferir_emissor(registros, complemento, TAESA) is None


def test_unit_com_provento_da_unit_no_complemento_abstem():
    # Leitura literal da decisão 33 (b) (DD-06): o provento por unit não está na relação.
    registros = [
        _r("14/08/2026", "0,08025458488"),
        _r("14/08/2026", "0,08025458488", "PN"),
    ]
    complemento = [
        _taesa("BRTAEEACNOR9", "0,08025458488"),
        _taesa("BRTAEEACNPR6", "0,08025458488"),
        _taesa("BRTAEECDAM10", "0,24076375464"),
    ]
    assert pb.conferir_emissor(registros, complemento, TAESA) == (
        f"{IDENTIDADE}: provento do complemento DIVIDENDO 14/08/2026 ausente da relação"
    )


def test_anuncio_que_a_relacao_ainda_nao_traz_abstem():
    # Sem o corte de janela do `_cruzamento` (DD-06): data com futura também é conferida.
    registros = [_r("10/12/2025", "0,5")]
    complemento = [_c("10/12/2025", "0,5"), _c("10/12/2027", "0,3")]
    assert pb.conferir_emissor(registros, complemento, ("BRTSTEACNOR1",)) == (
        f"{IDENTIDADE}: provento do complemento DIVIDENDO 10/12/2027 ausente da relação"
    )


@pytest.mark.parametrize("valor", ["1_000", "0,5_0"])
def test_valor_com_sublinhado_nao_confere(valor):
    assert not pb.mesmo_valor(valor, "1000")
    assert not pb.mesmo_valor("1000", valor)


def test_lojas_renner_com_pn_historica_abstem_pela_regra_a():
    # A relação da Lojas Renner traz registros PN antigos, e o GetDetail de hoje só o ISIN
    # ON: pela decisão 33 (a), literal, a relação não comprova a identidade.
    from tests.test_contratos_provedores import _b3_obter

    relacao = b3_proventos.coletar(
        8133, datetime(2026, 10, 20, 20, 40, tzinfo=UTC), _b3_obter(LREN)
    )
    assert relacao.isins == ("BRLRENACNOR1",)
    assert {r["typeStock"] for r in relacao.registros} == {"ON", "PN"}
    assert relacao.identidade == (
        f"{IDENTIDADE}: espécie PN da relação sem ISIN da companhia no GetDetail"
    )
    so_on = [r for r in relacao.registros if r["typeStock"] == "ON"]
    assert (
        pb.conferir_emissor(so_on, relacao.dinheiro_complemento, relacao.isins) is None
    )


# ── ponta a ponta: fixture oficial → provedor → cascata → motor ──────────────


class _Relogio(datetime):
    @classmethod
    def now(cls, tz=None):
        return AGORA if tz is None else AGORA.astimezone(tz)


def _cascata(monkeypatch, relacoes=None):
    obter = _b3_ambev(relacoes)
    monkeypatch.setattr(market_engine, "datetime", _Relogio)
    engine = MarketEngine.__new__(MarketEngine)
    # O provedor real, com a B3 respondendo pela fixture oficial.
    engine.b3_proventos = SimpleNamespace(
        coletar=lambda cd_cvm, agora: b3_proventos.coletar(cd_cvm, agora, obter)
    )
    indice = pd.DatetimeIndex(pd.to_datetime(["2026-11-06", "2026-11-09"])).tz_localize(
        "America/Sao_Paulo"
    )
    dados = {
        "ticker": "ABEV3",
        "classe_ativo": "STOCK",
        "especie": "ON",
        "modelo_bpp": "empresa",
        "cd_cvm": 23264,
        "fonte_preco": "yfinance",
        "historico": pd.DataFrame(
            {"Close": [14.0, 15.0], "Dividends": [0.0, 0.0]}, index=indice
        ),
        "fechamentos_brutos": {"2026-11-06": 14.0, "2026-11-09": 15.0},
        "preco_atual": 15.0,
        "roe": 0.15,
        "pl": 15.0,
        "pvp": 2.0,
        "dy": 0.05,
    }
    engine._buscar_proventos_b3("ABEV3", dados)
    return dados


def _bazin(resultado):
    for parte in str(resultado["metodos_usados"]).split(", "):
        if parte.startswith("Bazin: R$"):
            return float(parte.removeprefix("Bazin: R$"))
    return None


def test_ponta_a_ponta_ambev_chega_ao_bazin(monkeypatch):
    dados = _cascata(monkeypatch)
    assert dados["proventos_b3"]["proveniencia"]["nome_pregao"] == "AMBEV SA"
    resultado = ValuationEngine().processar(de_empresa(dados), as_of=AGORA)
    # 21/09/2026 0,0713 + 22/06/2026 0,0449 + 18/12/2025 0,269 e 0,4612 = 0,8464
    assert dados["bazin_proventos"]["d_bruto_12m"] == pytest.approx(0.8464)
    assert _bazin(resultado) == pytest.approx(0.8464 / 0.06, abs=0.01)


def test_ponta_a_ponta_homonimo_abstem_com_motivo(monkeypatch):
    dados = _cascata(monkeypatch, HOMONIMO)
    assert dados["proventos_b3"] == {
        "abstencao": f"{IDENTIDADE}: espécie PN da relação sem ISIN da companhia no GetDetail"
    }
    resultado = ValuationEngine().processar(de_empresa(dados), as_of=AGORA)
    assert _bazin(resultado) is None
    assert dados["bazin_diagnostico"] == dados["proventos_b3"]["abstencao"]
