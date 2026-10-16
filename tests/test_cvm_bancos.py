"""Bancos pelo modelo de instituição financeira (F2A-9; F-13, armadilha 17, P5).

DFP no modelo do ITUB4 (F2A-16): PL consolidado na 2.08, lucro na 3.09 e a parte dos
controladores na 3.09.01; a 2.03 é "Passivos Financeiros ao Custo Amortizado".
"""

from datetime import date

import pytest
import requests

import cvm_provider
from cvm_provider import CVMProvider
from sentinela.data import divida_liquida
from sentinela.data.providers import ifdata
from tests.test_contas_cvm_consumidores import _calcular_com_modelo
from tests.test_market_engine import _engine

ITUB_BPP = [
    ("2", "Passivo Total", 3_000.0),
    ("2.03", "Passivos Financeiros ao Custo Amortizado", 2_500.0),
    ("2.08", "Patrimônio Líquido Consolidado", 200.0),
    ("2.08.09", "Participação dos Acionistas Não Controladores", 10.0),
]
ITUB_DRE = [
    ("3.09", "Lucro/Prejuízo Consolidado do Período", 42.0),
    ("3.09.01", "Atribuído a Sócios da Empresa Controladora", 38.0),
    ("3.09.02", "Atribuído a Sócios Não Controladores", 4.0),
]


def test_banco_usa_contas_do_modelo_financeiro(tmp_path, monkeypatch):
    ind = _calcular_com_modelo(
        tmp_path, monkeypatch, "banco", dre=ITUB_DRE, bpp=ITUB_BPP
    )
    assert ind["patrimonio_liquido"] == pytest.approx(200.0)
    assert ind["lucro_liquido"] == pytest.approx(42.0)
    assert ind["lucro_controladores"] == pytest.approx(38.0)
    assert ind["pl_controladores"] == pytest.approx(190.0)
    assert ind["roe"] == pytest.approx(38.0 / 190.0)


def test_banco_nao_recebe_margem_nem_alavancagem(tmp_path, monkeypatch):
    ind = _calcular_com_modelo(
        tmp_path, monkeypatch, "banco", dre=ITUB_DRE, bpp=ITUB_BPP
    )
    assert ind["receita_liquida"] is None
    assert ind["margem_liquida"] is None
    assert ind["divida_liq_ebitda"] is None and ind["div_liq_patrimonio"] is None
    assert (
        ind["contas_abstidas"]["receita_liquida"]
        == cvm_provider.MOTIVO_SEM_SIGNIFICADO_BANCO
    )
    assert (
        ind["contas_abstidas"]["margem_liquida"]
        == cvm_provider.MOTIVO_SEM_SIGNIFICADO_BANCO
    )
    assert (
        ind["alavancagem_motivos"]["divida_liq_ebitda"] == divida_liquida.MOTIVO_MODELO
    )

    # Na cascata, os motivos chegam a `riscos_dados`.
    class _CVM:
        def calcular_indicadores(self, cd_cvm, anos=1, **kwargs):
            return {2025: ind}

    engine = _engine(monkeypatch, info={"currentPrice": 20.0}, cvm=_CVM())
    dados = {"setor": "Bancos", "cd_cvm": 19348, "riscos_dados": [], "preco_atual": 20.0}
    engine._buscar_cvm("ITUB4", dados)
    riscos = " | ".join(dados["riscos_dados"])
    assert f"receita_liquida: {cvm_provider.MOTIVO_SEM_SIGNIFICADO_BANCO}" in riscos
    assert f"margem_liquida: {cvm_provider.MOTIVO_SEM_SIGNIFICADO_BANCO}" in riscos
    assert "alavancagem não avaliada (divida_liq_ebitda)" in riscos
    assert "receita_liquida" not in dados and "margem_liquida" not in dados
    assert dados["roe"] == pytest.approx(38.0 / 190.0)


def test_sem_ifdata_a_limitacao_e_declarada(monkeypatch):
    engine = _engine(monkeypatch, info={"currentPrice": 20.0})
    dados = {"setor": "Bancos", "cnpj": "60.872.504/0001-23", "riscos_dados": []}
    engine._buscar_ifdata(dados)  # sem o atributo `ifdata`
    assert dados["riscos_dados"] == [
        "limitação do banco: Basileia e inadimplência sem fonte (IF.data não consultado)"
    ]
    assert "basileia" not in dados

    class _Falha:
        def capital(self, cnpj, data_referencia):
            raise OSError("sem rede")

    engine.ifdata = _Falha()
    dados = {"setor": "Bancos", "cnpj": "60.872.504/0001-23", "riscos_dados": []}
    engine._buscar_ifdata(dados)
    assert "IF.data indisponível: sem rede" in dados["riscos_dados"][0]

    # Fora do setor de banco, nada é consultado nem declarado.
    dados = {"setor": "Petróleo e Gás", "riscos_dados": []}
    engine._buscar_ifdata(dados)
    assert dados == {"setor": "Petróleo e Gás", "riscos_dados": []}


# Respostas no formato do OData do IF.data (F2A-16, chamada de controle do BB em 12/2025).
CADASTRO_BB = [
    {"CodInst": "00000000", "NomeInstituicao": "BANCO DO BRASIL S.A.", "Td": "I", "CnpjInstituicaoLider": "00000000"},
    {"CodInst": "C0049906", "NomeInstituicao": "BB", "Td": "C", "CnpjInstituicaoLider": "00000000"},
    {"CodInst": "C0080329", "NomeInstituicao": "BB - PRUDENCIAL", "Td": "C", "CnpjInstituicaoLider": "00000000"},
]  # fmt: skip
CAPITAL_BB = [
    {"NomeColuna": "Patrimônio de Referência para Comparação com o RWA \n(e)", "Saldo": 204528805240.77},
    {"NomeColuna": "Índice de Basileia  (n) = (e) / (j)", "Saldo": 0.151297835513664},
]  # fmt: skip


def _buscar_falso(respostas):
    pedidos = []

    def buscar(caminho):
        pedidos.append(caminho)
        for chave, resposta in respostas.items():
            if chave in caminho:
                return resposta
        return []

    return buscar, pedidos


def test_ifdata_grava_basileia_e_inadimplencia(monkeypatch):
    buscar, pedidos = _buscar_falso(
        {"@AnoMes=202606&$filter=Cnpj": CADASTRO_BB, "@AnoMes=202606&@Tipo": CAPITAL_BB}
    )
    capital = ifdata.ler_capital("00.000.000/0001-91", date(2026, 10, 13), buscar)
    assert capital.basileia == pytest.approx(0.151297835513664)
    assert capital.data_base == "202606"
    assert capital.codinst == "C0080329"  # o conglomerado prudencial, não a instituição
    assert capital.inadimplencia is None
    assert capital.motivos == {"inadimplencia": ifdata.MOTIVO_SEM_INADIMPLENCIA}
    assert "CodInst eq 'C0080329'" in pedidos[-1] and "@Relatorio='5'" in pedidos[-1]

    class _IFData:
        def capital(self, cnpj, data_referencia):
            return capital

    engine = _engine(monkeypatch, info={"currentPrice": 20.0})
    engine.ifdata = _IFData()
    dados = {"setor": "Bancos", "cnpj": "00.000.000/0001-91", "riscos_dados": []}
    engine._buscar_ifdata(dados)
    assert dados["basileia"] == pytest.approx(0.1513, abs=1e-4)
    assert dados["inadimplencia"] is None
    assert dados["ifdata"] == {
        "fonte": ifdata.FONTE,
        "data_base": "202606",
        "codinst": "C0080329",
    }
    assert dados["riscos_dados"] == [
        f"limitação do banco (inadimplencia): {ifdata.MOTIVO_SEM_INADIMPLENCIA}"
    ]


# ── bordas do IF.data ────────────────────────────────────────────────────────


def test_datas_base_sao_fins_de_trimestre_anteriores():
    assert ifdata.datas_base(date(2026, 10, 13)) == [
        "202609",
        "202606",
        "202603",
        "202512",
    ]
    assert ifdata.datas_base(date(2026, 2, 1), 2) == ["202512", "202509"]
    assert ifdata.datas_base(date(2026, 3, 31), 1) == ["202512"]
    assert ifdata.datas_base(date(2026, 4, 1), 1) == ["202603"]


def test_raiz_do_cnpj():
    assert ifdata.raiz_do_cnpj("60.872.504/0001-23") == "60872504"
    assert ifdata.raiz_do_cnpj("123") is None
    assert ifdata.raiz_do_cnpj(None) is None


def test_data_base_sem_dado_cai_para_a_anterior():
    buscar, _ = _buscar_falso(
        {"@AnoMes=202603&$filter=Cnpj": CADASTRO_BB, "@AnoMes=202603&@Tipo": CAPITAL_BB}
    )
    capital = ifdata.ler_capital("00.000.000/0001-91", date(2026, 10, 13), buscar)
    assert capital.data_base == "202603"


def test_sem_conglomerado_ou_sem_basileia_declara_o_motivo():
    so_instituicao = [CADASTRO_BB[0]]
    buscar, _ = _buscar_falso({"$filter=Cnpj": so_instituicao})
    capital = ifdata.ler_capital("00.000.000/0001-91", date(2026, 10, 13), buscar)
    assert capital.basileia is None and capital.data_base is None
    assert capital.motivos["basileia"] == ifdata.MOTIVO_SEM_CONGLOMERADO

    buscar, _ = _buscar_falso({"$filter=Cnpj": CADASTRO_BB, "@Tipo": CAPITAL_BB[:1]})
    capital = ifdata.ler_capital("00.000.000/0001-91", date(2026, 10, 13), buscar)
    assert capital.motivos["basileia"] == ifdata.MOTIVO_SEM_BASILEIA

    capital = ifdata.ler_capital("123", date(2026, 10, 13), buscar)
    assert capital.motivos["basileia"] == ifdata.MOTIVO_CNPJ_INVALIDO


def test_basileia_invalida_e_none():
    assert (
        ifdata.basileia([{"NomeColuna": "Índice de Basileia", "Saldo": "abc"}]) is None
    )
    assert (
        ifdata.basileia([{"NomeColuna": "Índice de Basileia", "Saldo": float("nan")}])
        is None
    )
    assert (
        ifdata.basileia([{"NomeColuna": "Índice de Imobilização", "Saldo": 0.2}])
        is None
    )


class _Resposta:
    def __init__(self, valor):
        self.valor = valor

    def raise_for_status(self):
        return None

    def json(self):
        return {"value": self.valor}


def test_provedor_usa_o_cache_e_o_cache_antigo_sem_rede(tmp_path, monkeypatch):
    chamadas = []

    def get(url, timeout):
        chamadas.append(url)
        return _Resposta(CAPITAL_BB)

    monkeypatch.setattr("sentinela.data.providers.ifdata.requests.get", get)
    provedor = ifdata.IFDataProvider(cache_dir=str(tmp_path), ttl_segundos=3600)
    assert provedor._buscar("x") == CAPITAL_BB
    assert provedor._buscar("x") == CAPITAL_BB
    assert len(chamadas) == 1
    assert chamadas[0] == f"{ifdata.URL_BASE}/x"

    def sem_rede(url, timeout):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr("sentinela.data.providers.ifdata.requests.get", sem_rede)
    vencido = ifdata.IFDataProvider(cache_dir=str(tmp_path), ttl_segundos=0)
    assert vencido._buscar("x") == CAPITAL_BB  # cache antigo, com aviso
    with pytest.raises(requests.ConnectionError):
        vencido._buscar("y")  # sem cache, a falha sobe para a cascata


def test_ttm_do_banco_usa_o_modelo_financeiro(tmp_path):
    from tests.test_cvm_series import _zip

    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    dre = [
        ("2025-03-31", "1", "ÚLTIMO", "2025-01-01", "2025-03-31", "3.09", "Lucro/Prejuízo Consolidado do Período", 10),
        ("2025-03-31", "1", "ÚLTIMO", "2025-01-01", "2025-03-31", "3.09.01", "Atribuído a Sócios da Empresa Controladora", 9),
    ]  # fmt: skip
    caminho = _zip(tmp_path / "itr.zip", "itr", 2025, dre, [])
    (acumulado,) = provider._acumulados_do_arquivo(caminho, "ITR", 9999, "banco")
    assert acumulado.valores["lucro_liquido"] == 10_000.0
    assert acumulado.valores["lucro_controladores"] == 9_000.0


def test_caminhos_odata_seguem_o_servico():
    assert ifdata.raiz_do_cnpj("12345678") == "12345678"
    assert ifdata.caminho_cadastro("202606", "00000000") == (
        "IfDataCadastro(AnoMes=@AnoMes)?@AnoMes=202606"
        "&$filter=CnpjInstituicaoLider eq '00000000'&$format=json"
    )
    assert ifdata.caminho_capital("202606", "C0080329") == (
        "IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)"
        "?@AnoMes=202606&@TipoInstituicao=1&@Relatorio='5'"
        "&$filter=CodInst eq 'C0080329'&$format=json"
    )
    buscar, pedidos = _buscar_falso({})
    ifdata.ler_capital("00.000.000/0001-91", date(2026, 10, 13), buscar)
    assert pedidos[0] == ifdata.caminho_cadastro("202609", "00000000")
    assert (
        ifdata.codinst_prudencial(
            [{"CodInst": "X", "Td": "C", "CnpjInstituicaoLider": "1"}], "1"
        )
        is None
    )


def test_resposta_sem_value_vira_lista_vazia(tmp_path, monkeypatch):
    class _SemValue(_Resposta):
        def json(self):
            return {}

    monkeypatch.setattr(
        "sentinela.data.providers.ifdata.requests.get",
        lambda url, timeout: _SemValue(None),
    )
    assert ifdata.IFDataProvider(cache_dir=str(tmp_path))._buscar("z") == []


def test_provedor_le_o_capital_pelo_cnpj_e_pela_data(tmp_path, monkeypatch):
    buscar, pedidos = _buscar_falso(
        {"@AnoMes=202606&$filter=Cnpj": CADASTRO_BB, "@AnoMes=202606&@Tipo": CAPITAL_BB}
    )
    provedor = ifdata.IFDataProvider(cache_dir=str(tmp_path))
    monkeypatch.setattr(provedor, "_buscar", buscar)
    capital = provedor.capital("00.000.000/0001-91", date(2026, 10, 13))
    assert (capital.basileia, capital.data_base) == (
        pytest.approx(0.151297835513664),
        "202606",
    )
    assert "CnpjInstituicaoLider eq '00000000'" in pedidos[0]
