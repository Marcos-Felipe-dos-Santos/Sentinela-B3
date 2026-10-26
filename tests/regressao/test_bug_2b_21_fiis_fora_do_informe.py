"""Lacuna de cobertura BTCI11/TRPL11, destino F2C-21 (proposta da 2C).

Fontes B3, consultadas em 20/10/2026, anteriores ao corte da auditoria:
TRPL11: https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias/Detail?agencia=18&dataNoticia=2026-01-07+14%3A20%3A39&idNoticia=3196072
BTCI11: https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias/Detail?agencia=15&dataNoticia=2026-02-09+05%3A04%3A31&idNoticia=3233160

Ambos são FII. A falta de ISIN no Informe não é evidência de outra classe.
A correção deverá enriquecer o índice com identidade oficial complementar;
não deduzir FII de todo CI ou forçar UNIT pela lista antiga. Este caso mínimo
registra o caminho que hoje perde a classe; a fixture poderá ganhar a fonte
complementar quando o item 2C implementar sua entrada, preservando a asserção.
"""

from datetime import date
from pathlib import Path

import pytest

from sentinela.data.providers.b3_cotahist import Cotacao
from sentinela.data.referencia.correcoes import ler_identidades_fii
from sentinela.data.referencia.montagem import montar_outros


@pytest.mark.parametrize(
    "ticker,isin", [("BTCI11", "BRBTCICTF005"), ("TRPL11", "BRTRPLCTF015")]
)
def test_fii_confirmado_na_b3_nao_perde_classe_fora_do_informe(ticker, isin):
    cotacao = Cotacao(
        date(2026, 10, 15), ticker, "12", "010", "CI", isin, 1.0, 100.0, 100, 1, 1
    )
    (registro,) = montar_outros(
        [cotacao],
        set(),
        {"arquivo": "COTAHIST público", "data": "2026-10-15"},
        identidades_fii=ler_identidades_fii(),
    )
    assert registro.classe == "FII"


def _cotacao(ticker: str = "BTCI11", isin: str = "BRBTCICTF005") -> Cotacao:
    return Cotacao(
        date(2026, 10, 15), ticker, "12", "010", "CI", isin, 1.0, 100.0, 100, 1, 1
    )


@pytest.mark.parametrize(
    "alteracao",
    [
        {"cnpj": ""},
        {"cnpj": None},
        {"isin": "BRXXXXCTF000"},
        {"sha256": ""},
        {"fonte": "https://fonte.invalid/"},
        {"data": "ilegível"},
    ],
)
def test_identidade_invalida_ou_incompativel_nao_promove_fii(alteracao: dict) -> None:
    identidade = {**ler_identidades_fii()[0], **alteracao}
    (registro,) = montar_outros([_cotacao()], set(), {}, identidades_fii=[identidade])
    assert registro.classe == "UNKNOWN"
    assert registro.motivo


def test_duas_identidades_do_mesmo_ticker_nao_escolhem_a_primeira() -> None:
    identidade = ler_identidades_fii()[0]
    conflitante = {**identidade, "cnpj": "00.000.000/0001-00"}
    (registro,) = montar_outros(
        [_cotacao()], set(), {}, identidades_fii=[identidade, conflitante]
    )
    assert registro.classe == "UNKNOWN"
    assert "conflitante" in registro.motivo


def test_isins_conflitantes_no_cotahist_nao_escolhem_o_primeiro() -> None:
    registros = montar_outros(
        [_cotacao(), _cotacao(isin="BRXXXXCTF000")],
        set(),
        {},
        identidades_fii=ler_identidades_fii(),
    )
    assert len(registros) == 1
    assert registros[0].classe == "UNKNOWN"


def test_ci_generico_permanece_unknown_e_nao_vence_classe_oficial() -> None:
    from sentinela.services.asset_classifier import AssetClassifier

    (registro,) = montar_outros(
        [_cotacao("TEST11", "BRTESTCTF000")],
        set(),
        {},
        identidades_fii=ler_identidades_fii(),
    )
    assert registro.classe == "UNKNOWN"
    classificador = AssetClassifier(
        fiis_conhecidos=["TEST11"], units_conhecidas=["TEST11"]
    )
    assert (
        classificador.classify("TEST11", {"classe_ativo": registro.classe}).value
        == "UNKNOWN"
    )
    assert classificador.classify("TRPL11", {"classe_ativo": "FII"}).value == "FII"
    assert (
        montar_outros(
            [_cotacao()], {"BTCI11"}, {}, identidades_fii=ler_identidades_fii()
        )
        == []
    )


def test_snapshot_oficial_e_ligado_aos_bytes_do_contrato() -> None:
    import base64
    import hashlib
    import json
    from pathlib import Path

    pasta = Path(__file__).parents[1] / "fixtures" / "contratos"
    meta = json.loads((pasta / "fnet_identidades_fii.meta.json").read_text())
    identidades = ler_identidades_fii()
    assert identidades == meta["documentos"]
    assert {i["ticker"] for i in identidades} == {"BTCI11", "TRPL11"}
    for identidade in identidades:
        bruto = (
            pasta / ("fnet_identidade_" + identidade["ticker"].lower() + ".html.base64")
        ).read_bytes()
        bruto = base64.b64decode(bruto.strip(), validate=True)
        assert hashlib.sha256(bruto).hexdigest() == identidade["sha256"]
        texto = bruto.decode()
        for campo in ("ticker", "cnpj", "isin"):
            assert identidade[campo] in texto


def test_fluxo_de_construcao_carrega_complemento_oficial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import UTC, datetime

    from sentinela.data.referencia import fontes
    from tests.test_referencia import FONTES, _cadastro, _fca, _sem_fii

    fontes_lidas = fontes.Fontes(
        [(2026, _fca())],
        _cadastro(),
        _sem_fii(),
        [_cotacao(), _cotacao("TRPL11", "BRTRPLCTF015")],
        FONTES,
        "2026-10-26",
        [],
    )
    monkeypatch.setattr(fontes, "carregar_fontes", lambda *args: fontes_lidas)
    indice = fontes.construir_indice(datetime(2026, 10, 26, tzinfo=UTC), tmp_path)
    assert indice.registros["BTCI11"].classe == "FII"
    assert indice.registros["TRPL11"].classe == "FII"
    assert indice.registros["BTCI11"].cnpj == "09.552.812/0001-14"
    assert indice.registros["TRPL11"].cnpj == "63.320.393/0001-30"


@pytest.mark.parametrize("alteracao", ["bytes", "cnpj", "isin", "nome"])
def test_snapshot_adulterado_nao_autoriza_identidade(
    tmp_path: Path, alteracao: str
) -> None:
    import csv
    import shutil

    from sentinela.data.referencia import correcoes

    identidade = dict(ler_identidades_fii()[0])
    pasta = tmp_path / "evidencias_fii"
    pasta.mkdir()
    documento = pasta / "btci11.html.base64"
    shutil.copyfile(
        correcoes.IDENTIDADES_FII.parent / "evidencias_fii" / "btci11.html.base64",
        documento,
    )
    if alteracao == "bytes":
        documento.write_bytes(documento.read_bytes() + b"alterado")
    else:
        identidade[alteracao] = {
            "cnpj": "00.000.000/0001-00",
            "isin": "BRXXXXCTF000",
            "nome": "OUTRO FUNDO",
        }[alteracao]
    caminho = tmp_path / "identidades.csv"
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(identidade), delimiter=";")
        escritor.writeheader()
        escritor.writerow(identidade)
    assert ler_identidades_fii(caminho) == []


@pytest.mark.parametrize(
    "alteracao",
    [
        {
            "fonte": "http://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id=1280320"
        },
        {
            "fonte": "https://fnet.bmfbovespa.com.br.invalid/fnet/publico/exibirDocumento?id=1280320"
        },
        {"fonte": "https://fnet.bmfbovespa.com.br/outro?id=1280320"},
        {
            "fonte": "https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id=outro"
        },
        {"data": "20261026"},
        {"data": "2026-02-30"},
        {"nome": ""},
        {"isin": "BRBTCI"},
        {"sha256": "g" * 64},
    ],
)
def test_evidencia_sem_contrato_oficial_nao_classifica_fii(alteracao: dict) -> None:
    identidade = {**ler_identidades_fii()[0], **alteracao}
    (registro,) = montar_outros([_cotacao()], set(), {}, identidades_fii=[identidade])
    assert registro.classe == "UNKNOWN"


@pytest.mark.parametrize("falha", ["ausente", "futura"])
def test_complemento_indisponivel_na_data_nao_inventa_classe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, falha: str
) -> None:
    from datetime import UTC, datetime

    from sentinela.data.referencia import fontes
    from tests.test_referencia import FONTES, _cadastro, _fca, _sem_fii

    fontes_lidas = fontes.Fontes(
        [(2026, _fca())],
        _cadastro(),
        _sem_fii(),
        [_cotacao()],
        FONTES,
        "2026-10-26",
        [],
    )
    monkeypatch.setattr(fontes, "carregar_fontes", lambda *args: fontes_lidas)

    def indisponivel() -> list[dict[str, str]]:
        if falha == "ausente":
            raise FileNotFoundError("snapshot ausente")
        return [{**i, "data": "2027-01-01"} for i in ler_identidades_fii()]

    monkeypatch.setattr(fontes, "ler_identidades_fii", indisponivel)
    indice = fontes.construir_indice(datetime(2026, 10, 26, tzinfo=UTC), tmp_path)
    assert indice.registros["BTCI11"].classe == "UNKNOWN"
    assert indice.registros["BTCI11"].motivo


def test_fundo_de_outra_natureza_no_fnet_nao_vira_fii(tmp_path: Path) -> None:
    import base64
    import csv
    import hashlib

    identidade = dict(ler_identidades_fii()[0])
    identidade["nome"] = "FUNDO DE INVESTIMENTO EM PARTICIPAÇÕES EXEMPLO"
    campos = {
        "Nome do Fundo:": identidade["nome"],
        "CNPJ do Fundo:": identidade["cnpj"],
        "Código ISIN:": identidade["isin"],
        "Código de negociação:": identidade["ticker"],
    }
    bruto = (
        "<table>"
        + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in campos.items())
        + "</table>"
    ).encode()
    identidade["sha256"] = hashlib.sha256(bruto).hexdigest()
    pasta = tmp_path / "evidencias_fii"
    pasta.mkdir()
    (pasta / "btci11.html.base64").write_bytes(base64.b64encode(bruto))
    caminho = tmp_path / "identidades.csv"
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(identidade), delimiter=";")
        escritor.writeheader()
        escritor.writerow(identidade)
    assert ler_identidades_fii(caminho) == []
