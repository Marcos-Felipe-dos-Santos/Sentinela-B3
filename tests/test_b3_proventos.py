"""Provedor da relação de proventos da B3 e a etapa da cascata (F2B-31)."""

import base64
import hashlib
import json
from datetime import UTC, date, datetime

import pandas as pd
import pytest

import market_engine
from market_engine import MarketEngine
from sentinela.data import proventos_b3
from sentinela.data.providers import b3_proventos

AGORA = datetime(2026, 10, 20, 15, tzinfo=UTC)


def _parametros(endereco):
    metodo, codificado = endereco.rsplit("/", 2)[-2:]
    return metodo, json.loads(base64.b64decode(codificado))


class _B3Falsa:
    def __init__(self, paginas, total=None, detalhe=None, complemento=None):
        self.paginas = paginas
        self.total = sum(len(p) for p in paginas) if total is None else total
        self.detalhe = (
            {"tradingName": "TESTE SA", "issuingCompany": "TSTE"}
            if detalhe is None
            else detalhe
        )
        self.complemento = (
            [
                {
                    "stockDividends": [{"label": "BONIFICACAO"}],
                    "cashDividends": [{"rate": "1"}],
                }
            ]
            if complemento is None
            else complemento
        )
        self.urls = []

    def __call__(self, endereco):
        self.urls.append(endereco)
        metodo, parametros = _parametros(endereco)
        if metodo == "GetDetail":
            return self.detalhe, {"url": endereco}
        if metodo == "GetListedSupplementCompany":
            return self.complemento, {"url": endereco}
        indice = parametros["pageNumber"] - 1
        return {
            "page": {
                "pageNumber": parametros["pageNumber"],
                "pageSize": parametros["pageSize"],
                "totalRecords": self.total,
                "totalPages": len(self.paginas),
            },
            "results": self.paginas[indice],
        }, {"url": endereco}


def test_url_codifica_os_parametros_em_base64():
    endereco = b3_proventos.url("GetDetail", {"codeCVM": "8133", "language": "pt-br"})
    assert endereco.startswith(b3_proventos.URL_BASE + "/GetDetail/")
    assert _parametros(endereco) == (
        "GetDetail",
        {"codeCVM": "8133", "language": "pt-br"},
    )


def test_coleta_todas_as_paginas_com_120_por_pagina():
    b3 = _B3Falsa([[{"n": 1}, {"n": 2}], [{"n": 3}]])
    relacao = b3_proventos.coletar(8133, AGORA, b3)
    assert [r["n"] for r in relacao.registros] == [1, 2, 3]
    assert relacao.total == 3
    assert (relacao.nome_pregao, relacao.emissor) == ("TESTE SA", "TSTE")
    assert relacao.eventos_acoes == ({"label": "BONIFICACAO"},)
    assert relacao.dinheiro_complemento == ({"rate": "1"},)
    assert relacao.coleta == AGORA.isoformat()
    assert len(relacao.fontes) == 4
    metodos = [_parametros(u) for u in b3.urls]
    assert metodos[0] == ("GetDetail", {"codeCVM": "8133", "language": "pt-br"})
    assert metodos[1] == (
        "GetListedCashDividends",
        {
            "language": "pt-br",
            "pageNumber": 1,
            "pageSize": 120,
            "tradingName": "TESTE SA",
        },
    )
    assert metodos[2][1]["pageNumber"] == 2
    assert metodos[3] == (
        "GetListedSupplementCompany",
        {"issuingCompany": "TSTE", "language": "pt-br"},
    )


def test_total_nulo_e_preservado_para_a_abstencao():
    relacao = b3_proventos.coletar(8133, AGORA, _B3Falsa([[]], total=None))
    assert relacao.total == 0
    vazio = _B3Falsa([[]])
    vazio.total = None
    assert b3_proventos.coletar(8133, AGORA, vazio).total is None


def test_paginacao_para_no_limite():
    b3 = _B3Falsa([[{"n": i}] for i in range(80)])
    relacao = b3_proventos.coletar(8133, AGORA, b3)
    assert len(relacao.registros) == b3_proventos.MAX_PAGINAS


@pytest.mark.parametrize(
    "detalhe",
    [
        [],
        {"tradingName": "X"},
        {"issuingCompany": "X"},
        {"tradingName": "", "issuingCompany": "X"},
    ],
)
def test_cadastro_sem_nome_ou_emissor_e_erro(detalhe):
    with pytest.raises(ValueError, match="cadastro"):
        b3_proventos.coletar(8133, AGORA, _B3Falsa([[]], detalhe=detalhe))


@pytest.mark.parametrize(
    "complemento",
    [
        [],
        {},
        [[]],
        [{"stockDividends": None, "cashDividends": []}],
        [{"stockDividends": [], "cashDividends": None}],
        [{"stockDividends": []}],
    ],
)
def test_complemento_fora_do_leiaute_e_erro(complemento):
    with pytest.raises(ValueError, match="complemento"):
        b3_proventos.coletar(8133, AGORA, _B3Falsa([[]], complemento=complemento))


def test_relacao_fora_do_leiaute_e_erro():
    b3 = _B3Falsa([[]])
    original = b3.__call__

    def obter(endereco):
        corpo, fonte = original(endereco)
        if _parametros(endereco)[0] == "GetListedCashDividends":
            return {"page": {}, "results": None}, fonte
        return corpo, fonte

    with pytest.raises(TypeError, match="leiaute"):
        b3_proventos.coletar(8133, AGORA, obter)


def test_obter_json_devolve_corpo_e_hash(monkeypatch):
    class _Resposta:
        content = b'{"a": 1}'

        def raise_for_status(self):
            pass

    monkeypatch.setattr(b3_proventos.requests, "get", lambda url, timeout: _Resposta())
    corpo, fonte = b3_proventos.obter_json("https://x")
    assert corpo == {"a": 1}
    assert fonte["bytes"] == 8
    assert fonte["sha256"] == hashlib.sha256(b'{"a": 1}').hexdigest()


# ── cascata ──────────────────────────────────────────────────────────────────


class _Provedor:
    def __init__(self, relacao=None, erro=None):
        self.relacao, self.erro, self.chamadas = relacao, erro, []

    def coletar(self, cd_cvm, agora):
        self.chamadas.append(cd_cvm)
        if self.erro:
            raise self.erro
        return self.relacao


RELACAO = b3_proventos.Relacao(
    nome_pregao="TESTE SA",
    emissor="TSTE",
    registros=({"lastDatePriorEx": "10/12/2025"},),
    total=1,
    eventos_acoes=(),
    dinheiro_complemento=({"rate": "1"},),
    fontes=({"url": "u"},),
    coleta="2026-10-20T15:00:00+00:00",
)


def _historico(datas, dividendos=None):
    indice = pd.DatetimeIndex(pd.to_datetime(datas)).tz_localize("America/Sao_Paulo")
    tabela = {"Close": [10.0 + i for i in range(len(datas))]}
    if dividendos is not None:
        tabela["Dividends"] = dividendos
    return pd.DataFrame(tabela, index=indice)


def _cascata(dados, provedor=None, monkeypatch=None):
    engine = MarketEngine.__new__(MarketEngine)
    engine.b3_proventos = provedor if provedor is not None else _Provedor(RELACAO)
    base = {
        "classe_ativo": "STOCK",
        "modelo_bpp": "empresa",
        "cd_cvm": 8133,
        "fonte_preco": "yfinance",
        "historico": _historico(["2026-10-16", "2026-10-19"], [0.0, 0.3]),
    }
    base.update(dados)
    engine._buscar_proventos_b3("TSTE3", base)
    return base


class _Relogio(datetime):
    @classmethod
    def now(cls, tz=None):
        return AGORA if tz is None else AGORA.astimezone(tz)


@pytest.fixture(autouse=True)
def _agora(monkeypatch):
    monkeypatch.setattr(market_engine, "datetime", _Relogio)


def test_cascata_grava_a_relacao_e_os_fechamentos():
    provedor = _Provedor(RELACAO)
    dados = _cascata({}, provedor)
    relacao = dados["proventos_b3"]
    assert provedor.chamadas == [8133]
    assert relacao["registros"] == [{"lastDatePriorEx": "10/12/2025"}]
    assert relacao["total"] == 1
    assert relacao["eventos_acoes"] == []
    assert relacao["dinheiro_complemento"] == [{"rate": "1"}]
    assert relacao["fechamentos"] == {"2026-10-16": 10.0, "2026-10-19": 11.0}
    assert relacao["conferencia_yfinance"] == {"2026-10-19": 0.3}
    assert relacao["pregoes"] is None
    assert relacao["coleta"] == RELACAO.coleta
    assert relacao["proveniencia"]["nome_pregao"] == "TESTE SA"
    assert relacao["proveniencia"]["arquivos"] == [{"url": "u"}]


def test_cascata_sem_dividendos_no_historico_nao_tem_conferencia():
    dados = _cascata({"historico": _historico(["2026-10-19"])})
    assert dados["proventos_b3"]["conferencia_yfinance"] is None


@pytest.mark.parametrize(
    ("dados", "motivo"),
    [
        ({"modelo_bpp": "banco"}, "fora do escopo do Bazin: modelo banco"),
        ({"modelo_bpp": None}, "modelo empresa não demonstrado no BPP consolidado"),
        ({"fonte_preco": "brapi"}, proventos_b3.MOTIVO_PRECO),
        ({"historico": None}, proventos_b3.MOTIVO_PRECO),
        ({"historico": pd.DataFrame()}, proventos_b3.MOTIVO_PRECO),
        (
            {"historico": _historico(["2026-10-20"])},
            proventos_b3.MOTIVO_PRECO_NAO_ENCERRADO,
        ),
    ],
)
def test_cascata_abstem_sem_escopo_ou_preco(dados, motivo):
    provedor = _Provedor(RELACAO)
    assert _cascata(dados, provedor)["proventos_b3"] == {"abstencao": motivo}
    assert provedor.chamadas == []


def test_cascata_com_falha_da_b3_abstem():
    dados = _cascata({}, _Provedor(erro=OSError("sem rede")))
    assert dados["proventos_b3"] == {
        "abstencao": "relação de proventos da B3 indisponível: sem rede"
    }


@pytest.mark.parametrize("classe", ["FII", "ETF", None])
def test_cascata_so_para_acao_e_unit(classe):
    assert "proventos_b3" not in _cascata({"classe_ativo": classe})


def test_cascata_sem_provedor_nao_grava():
    engine = MarketEngine.__new__(MarketEngine)
    dados = {"classe_ativo": "STOCK"}
    engine._buscar_proventos_b3("TSTE3", dados)
    assert "proventos_b3" not in dados


def test_fechamento_invalido_fica_de_fora():
    historico = _historico(["2026-10-15", "2026-10-16", "2026-10-19"])
    historico.loc[historico.index[2], "Close"] = float("nan")
    historico.loc[historico.index[1], "Close"] = 0.0
    dados = _cascata({"historico": historico})
    assert dados["proventos_b3"]["fechamentos"] == {"2026-10-15": 10.0}


def test_calendario_so_quando_a_data_ex_depende_dele(monkeypatch):
    lidos = []

    class _Cotacao:
        def __init__(self, dia):
            self.data = dia

    def baixar(ano, mes, agora):
        lidos.append((ano, mes))
        return f"{ano}-{mes}"

    monkeypatch.setattr(market_engine.b3_cotahist, "baixar_mes", baixar)
    monkeypatch.setattr(
        market_engine.b3_cotahist,
        "ler_zip_em_cache",
        lambda caminho: [_Cotacao(date(2025, 10, 17)), _Cotacao(date(2025, 10, 20))],
    )
    referencia = date(2026, 10, 19)  # início 19/10/2025
    assert (
        MarketEngine._pregoes_da_data_ex(
            [{"lastDatePriorEx": "10/12/2025"}, {"lastDatePriorEx": "12/10/2025"}, "x"],
            referencia,
            AGORA,
        )
        is None
    )
    assert lidos == []
    assert MarketEngine._pregoes_da_data_ex(
        [{"lastDatePriorEx": "17/10/2025"}], referencia, AGORA
    ) == ["2025-10-17", "2025-10-20"]
    assert lidos == [(2025, 10)]
    lidos.clear()
    assert MarketEngine._pregoes_da_data_ex(
        [{"lastDatePriorEx": "01/03/2025"}], date(2026, 3, 3), AGORA
    ) == ["2025-10-17", "2025-10-20"]
    assert lidos == [(2025, 2), (2025, 3)]


def test_calendario_indisponivel_fica_nulo(monkeypatch):
    def falha(ano, mes, agora):
        raise OSError("sem rede")

    monkeypatch.setattr(market_engine.b3_cotahist, "baixar_mes", falha)
    assert (
        MarketEngine._pregoes_da_data_ex(
            [{"lastDatePriorEx": "17/10/2025"}], date(2026, 10, 19), AGORA
        )
        is None
    )


# ── modelo pelo BPP ──────────────────────────────────────────────────────────


def test_modelo_do_documento_pelo_bpp(tmp_path, monkeypatch):
    import zipfile

    from cvm_provider import CVMProvider

    def bpp(linhas):
        cab = "CNPJ_CIA;DT_REFER;VERSAO;CD_CVM;ORDEM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA\n"
        corpo = "".join(
            f"00.000.000/0001-00;2025-12-31;{versao};{cd};{ordem};{conta};{ds};100\n"
            for cd, versao, ordem, conta, ds in linhas
        )
        caminho = tmp_path / "dfp.zip"
        with zipfile.ZipFile(caminho, "w") as zf:
            zf.writestr(
                "dfp_cia_aberta_BPP_con_2025.csv", (cab + corpo).encode("latin-1")
            )
        return caminho

    provedor = CVMProvider.__new__(CVMProvider)
    ind = {"cvm_dt_refer": "2025-12-31", "cvm_versao": "2"}
    empresa = (9, 2, "ÚLTIMO", "2.03", "Patrimônio Líquido Consolidado")
    banco = (9, 2, "ÚLTIMO", "2.08", "Patrimônio Líquido Consolidado")
    casos = [
        ([empresa], "empresa"),
        ([banco], "banco"),
        ([(9, 1, "ÚLTIMO", "2.03", "Patrimônio Líquido Consolidado")], None),
        ([(9, 2, "PENÚLTIMO", "2.03", "Patrimônio Líquido Consolidado")], None),
        ([(8, 2, "ÚLTIMO", "2.03", "Patrimônio Líquido Consolidado")], None),
        ([(9, 2, "ÚLTIMO", "2.01", "Passivo Circulante")], None),
    ]
    for linhas, esperado in casos:
        caminho = bpp(linhas)
        monkeypatch.setattr(provedor, "baixar_dfp", lambda ano, c=caminho: c)
        assert provedor.modelo_do_documento(9, ind) == esperado, linhas
    assert provedor.modelo_do_documento(9, {}) is None
    monkeypatch.setattr(provedor, "baixar_dfp", lambda ano: tmp_path / "nao-existe.zip")
    assert provedor.modelo_do_documento(9, ind) is None
