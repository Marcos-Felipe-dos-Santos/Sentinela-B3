"""Macro por data a partir das séries completas do SGS (F3-1b)."""

import json
from datetime import UTC, date, datetime
from itertools import pairwise
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

import config
import fii_engine
from config import MacroContext
from fii_engine import FIIEngine
from sentinela.data import macro_por_data as mpd
from sentinela.data.providers import macro as provedor_macro
from sentinela.data.providers.macro import MacroProvider

SGS = Path(__file__).parent / "fixtures" / "sgs"
# Instante da coleta das fixtures (FONTE.md): 10/11/2026 00:33 em Brasília.
COLETA = datetime(2026, 11, 10, 3, 33, tzinfo=UTC)
HOJE = date(2026, 11, 10)


def _fixture(serie):
    return json.loads((SGS / f"bcdata_sgs_{serie}.json").read_text(encoding="utf-8"))


class _Resposta:
    def __init__(self, dados):
        self.text = json.dumps(dados)

    def raise_for_status(self):
        return None

    def json(self):
        return json.loads(self.text)


def _sgs_oficial(url, *args, **kwargs):
    """Responde como a API do SGS, a partir das fixtures oficiais."""
    caminho = urlparse(url)
    serie = int(caminho.path.split("bcdata.sgs.")[1].split("/")[0])
    dados = _fixture(serie)
    if "/ultimos/" in caminho.path:
        return _Resposta(dados[-int(caminho.path.rsplit("/", 1)[1]) :])
    consulta = parse_qs(caminho.query)
    if "dataInicial" in consulta:
        inicio = mpd.data_sgs(consulta["dataInicial"][0])
        fim = mpd.data_sgs(consulta["dataFinal"][0])
        if (fim - inicio).days > 3653:
            raise AssertionError("janela de mais de 10 anos")
        dados = [o for o in dados if inicio <= mpd.data_sgs(o["data"]) <= fim]
    elif serie != mpd.IPCA:
        raise AssertionError("série diária sem datas")
    return _Resposta(dados)


@pytest.fixture
def sgs(monkeypatch, tmp_path):
    chamadas = []

    def _get(url, *args, **kwargs):
        chamadas.append(url)
        return _sgs_oficial(url)

    monkeypatch.setattr(provedor_macro.requests, "get", _get)
    return MacroProvider(cache_dir=tmp_path / "macro"), chamadas


def _macro(provedor, as_of):
    return MacroContext(as_of=as_of, provedor=provedor, instante=COLETA)


# leitura do formato oficial


def test_ler_sgs_le_o_formato_oficial():
    obs = mpd.ler_sgs((SGS / "bcdata_sgs_432.json").read_text(encoding="utf-8"))
    assert obs[0] == mpd.Observacao(date(2025, 1, 1), 12.25)
    assert obs[-1] == mpd.Observacao(date(2026, 12, 9), 13.75)
    assert list(obs) == sorted(obs, key=lambda o: o.data)


@pytest.mark.parametrize(
    ("conteudo", "motivo"),
    [
        ('{"data": "01/01/2025"}', "SGS: formato inesperado, sem lista"),
        ('[{"data": "01/01/2025"}]', "SGS: observação sem data ou valor"),
        ('[{"valor": "1"}]', "SGS: observação sem data ou valor"),
        ('[{"data": "2025-01-01", "valor": "1"}]', "SGS: observação inválida"),
        ('[{"data": "01/01/2025", "valor": ""}]', "SGS: observação inválida"),
        ('[{"data": "01/01/2025", "valor": "NaN"}]', "SGS: valor não finito"),
        ('[{"data": "01/01/2025", "valor": null}]', "SGS: observação inválida"),
        ('["01/01/2025"]', "SGS: observação sem data ou valor"),
    ],
)
def test_ler_sgs_recusa_formato_invalido(conteudo, motivo):
    with pytest.raises(ValueError, match=motivo):
        mpd.ler_sgs(conteudo)


def test_data_sgs_fora_do_formato_diz_o_motivo():
    with pytest.raises(ValueError, match="SGS: data fora do formato dd/mm/aaaa"):
        mpd.data_sgs("1/1/2025")


def test_juntar_recusa_valores_diferentes_na_mesma_data():
    a = (mpd.Observacao(date(2025, 1, 1), 1.0),)
    b = (mpd.Observacao(date(2025, 1, 1), 2.0),)
    with pytest.raises(ValueError, match="mesma data"):
        mpd.juntar([a, b])
    assert mpd.juntar([a, a, ()]) == a


def test_janelas_de_no_maximo_dez_anos_cobrem_o_periodo():
    janelas = mpd.janelas(date(1999, 3, 5), date(2026, 11, 10))
    assert janelas[0][0] == date(1999, 3, 5)
    assert janelas[-1][1] == date(2026, 11, 10)
    assert all(fim < inicio.replace(year=inicio.year + 10) for inicio, fim in janelas)
    assert all(
        b[0] == date.fromordinal(a[1].toordinal() + 1) for a, b in pairwise(janelas)
    )
    assert mpd.janelas(date(2000, 2, 29), date(2010, 3, 1))[0] == (
        date(2000, 2, 29),
        date(2010, 2, 28),
    )
    assert mpd.janelas(date(2026, 1, 2), date(2026, 1, 1)) == []
    assert mpd.janelas(date(2026, 1, 1), date(2026, 1, 1)) == [
        (date(2026, 1, 1), date(2026, 1, 1))
    ]
    assert mpd.janelas(date(2000, 1, 1), date(2030, 1, 1))[:2] == [
        (date(2000, 1, 1), date(2009, 12, 31)),
        (date(2010, 1, 1), date(2019, 12, 31)),
    ]


# valor vigente, sem olhar dado posterior


@pytest.mark.parametrize(
    ("as_of", "selic"),
    [
        (date(2025, 1, 29), 0.1225),
        (date(2025, 1, 30), 0.1325),
        (date(2026, 3, 18), 0.15),
        (date(2026, 3, 19), 0.1475),
        (HOJE, 0.1375),
    ],
)
def test_selic_vigente_na_data(sgs, as_of, selic):
    provedor, _ = sgs
    m = _macro(provedor, as_of)
    assert m.selic == pytest.approx(selic)
    assert m.selic_liquida == pytest.approx(selic * MacroContext.FII_FATOR_IR)
    assert m.motivo("selic") is None


def test_observacao_futura_da_serie_432_nao_entra():
    obs = mpd.ler_sgs((SGS / "bcdata_sgs_432.json").read_text(encoding="utf-8"))
    assert obs[-1].data > HOJE
    assert mpd.vigente(obs, HOJE).data == HOJE
    assert mpd.selic(obs, HOJE) == {"valor": 0.1375, "data": HOJE}


def test_cdi_vigente_anualizado_em_252_dias(sgs):
    provedor, _ = sgs
    m = _macro(provedor, date(2025, 1, 3))
    diario = next(o["valor"] for o in _fixture(12) if o["data"] == "03/01/2025")
    assert m.cdi == pytest.approx((1 + float(diario) / 100) ** 252 - 1)


def test_ipca_passado_so_conta_mes_ja_divulgado(sgs):
    provedor, _ = sgs
    # Em 15/10/2025, o IPCA de setembro/2025 ainda não tinha saído pela regra
    # conservadora (mês M só a partir do primeiro dia de M+2): a janela vai até agosto.
    m = _macro(provedor, date(2025, 10, 15))
    meses = sorted((mpd.data_sgs(o["data"]), float(o["valor"])) for o in _fixture(433))
    janela = [(d, v) for d, v in meses if d <= date(2025, 8, 1)][-12:]
    esperado = 1.0
    for _, valor in janela:
        esperado *= 1 + valor / 100
    assert janela[-1][0] == date(2025, 8, 1)
    assert m.ipca_12m == pytest.approx(esperado - 1)
    assert m.registro_por_data("ipca_12m")["data"] == date(2025, 8, 1)


def test_ipca_sem_doze_meses_disponiveis_abstem(sgs):
    provedor, _ = sgs
    m = _macro(provedor, date(2024, 6, 1))
    assert m.ipca_12m is None
    assert "12 meses" in m.motivo("ipca_12m")


def test_ipca_disponivel_nas_bordas():
    # Mês de referência no próprio as_of: só conta se a coleta já aconteceu.
    assert mpd.ipca_disponivel(
        date(2026, 9, 1), date(2026, 9, 1), coleta=date(2026, 9, 1)
    )
    assert not mpd.ipca_disponivel(
        date(2026, 9, 1), date(2026, 9, 1), coleta=date(2026, 9, 2)
    )
    # as_of igual à coleta: tudo o que está na série já saiu.
    assert mpd.ipca_disponivel(
        date(2026, 9, 1), date(2026, 10, 1), coleta=date(2026, 10, 1)
    )
    assert not mpd.ipca_disponivel(
        date(2026, 9, 1), date(2026, 10, 31), coleta=date(2026, 11, 10)
    )
    assert mpd.ipca_disponivel(
        date(2026, 9, 1), date(2026, 11, 1), coleta=date(2026, 11, 10)
    )


def test_ipca_com_mes_faltando_abstem():
    obs = tuple(
        mpd.Observacao(date(2024, mes, 1), 0.5) for mes in range(1, 13) if mes != 6
    ) + (mpd.Observacao(date(2025, 1, 1), 0.5),)
    registro = mpd.ipca_12m(obs, date(2025, 12, 1), coleta=date(2025, 12, 1))
    assert "abstencao" in registro


# abstenção e fallback


@pytest.mark.parametrize("nome", ["selic", "cdi", "ipca_12m"])
def test_as_of_passado_sem_observacao_abstem_sem_fallback(sgs, nome):
    provedor, _ = sgs
    m = _macro(provedor, date(2020, 1, 2))
    assert getattr(m, nome) is None
    assert (
        m.motivo(nome)
        == {
            "selic": "série SGS 432 sem observação até 2020-01-02",
            "cdi": "série SGS 12 sem observação até 2020-01-02",
            "ipca_12m": "série SGS 433 sem 12 meses consecutivos disponíveis até 2020-01-02",
        }[nome]
    )


def test_cdi_traz_a_data_da_observacao(sgs):
    provedor, _ = sgs
    assert _macro(provedor, date(2025, 1, 5)).registro_por_data("cdi")["data"] == date(
        2025, 1, 3
    )


def test_as_of_passado_com_fonte_fora_do_ar_abstem_sem_fallback(monkeypatch, tmp_path):
    def _fora(url, *args, **kwargs):
        raise provedor_macro.requests.ConnectionError("SGS fora do ar")

    monkeypatch.setattr(provedor_macro.requests, "get", _fora)
    m = _macro(MacroProvider(cache_dir=tmp_path), date(2025, 6, 2))
    assert m.selic is None
    assert m.selic_liquida is None
    assert m.cdi is None
    assert m.ipca_12m is None
    assert m.motivo("selic") == "SGS fora do ar"


def test_as_of_hoje_com_fonte_fora_do_ar_usa_o_fallback_existente(
    monkeypatch, tmp_path
):
    def _fora(url, *args, **kwargs):
        raise provedor_macro.requests.ConnectionError("SGS fora do ar")

    monkeypatch.setattr(provedor_macro.requests, "get", _fora)
    monkeypatch.setattr(MacroContext, "_hoje_no_relogio", staticmethod(lambda: HOJE))
    m = _macro(MacroProvider(cache_dir=tmp_path), HOJE)
    assert m.selic == config.SELIC_FALLBACK
    assert m.cdi == config.CDI_FALLBACK
    assert m.ipca_12m == config.IPCA_12M_FALLBACK
    assert m.motivo("selic") == "SGS fora do ar"


def test_coleta_injetada_no_passado_nao_libera_o_fallback(monkeypatch, tmp_path):
    def _fora(url, *args, **kwargs):
        raise provedor_macro.requests.ConnectionError("SGS fora do ar")

    monkeypatch.setattr(provedor_macro.requests, "get", _fora)
    monkeypatch.setattr(MacroContext, "_hoje_no_relogio", staticmethod(lambda: HOJE))
    instante = datetime(2025, 7, 1, 15, tzinfo=UTC)
    m = MacroContext(
        as_of=date(2025, 7, 1),
        provedor=MacroProvider(cache_dir=tmp_path),
        instante=instante,
    )
    assert m.selic is None
    assert m.cdi is None
    assert m.ipca_12m is None


def test_hoje_no_relogio_e_o_dia_de_brasilia():
    assert MacroContext._hoje_no_relogio() == datetime.now(provedor_macro.FUSO).date()


def test_as_of_datetime_e_recusado():
    with pytest.raises(TypeError, match="as_of do MacroContext é date"):
        MacroContext(as_of=COLETA)


def test_instante_sem_fuso_e_recusado():
    with pytest.raises(ValueError, match="instante da coleta exige fuso horário"):
        MacroContext(as_of=HOJE, instante=datetime(2026, 11, 10, 12))  # noqa: DTZ001


def test_as_of_posterior_a_coleta_abstem(sgs):
    provedor, chamadas = sgs
    m = _macro(provedor, date(2026, 11, 11))
    assert m.selic is None
    assert m.motivo("selic") == "as_of posterior à data da coleta"
    assert chamadas == []


def test_selic_explicita_vale_sobre_o_as_of(sgs):
    provedor, chamadas = sgs
    m = MacroContext(selic=0.10, as_of=date(2020, 1, 2), provedor=provedor)
    assert m.selic == 0.10
    assert chamadas == []


class _ProvedorEspiao:
    def __init__(self):
        self.chamadas = []

    def serie_sgs(self, serie, fim, instante):
        self.chamadas.append((serie, fim, instante))
        return {"abstencao": "espião"}


def test_instante_explicito_define_o_dia_da_coleta_em_brasilia():
    espiao = _ProvedorEspiao()
    # 02:00 UTC de 10/11 ainda é 09/11 em Brasília.
    instante = datetime(2026, 11, 10, 2, 0, tzinfo=UTC)
    m = MacroContext(as_of=date(2025, 7, 1), provedor=espiao, instante=instante)
    assert m.selic is None
    assert espiao.chamadas == [(mpd.SELIC_META, date(2026, 11, 9), instante)]


def test_sem_instante_a_coleta_e_agora_com_fuso():
    espiao = _ProvedorEspiao()
    antes = datetime.now(UTC)
    m = MacroContext(as_of=date(2025, 7, 1), provedor=espiao)
    assert m.cdi is None
    _, _, instante = espiao.chamadas[0]
    assert instante.tzinfo is not None
    assert antes <= instante <= datetime.now(UTC)
    assert m.motivo("cdi") == "espião"
    assert len(espiao.chamadas) == 1


def test_sem_provedor_usa_o_provedor_macro(monkeypatch):
    espiao = _ProvedorEspiao()
    monkeypatch.setattr(provedor_macro, "MacroProvider", lambda: espiao)
    m = MacroContext(as_of=date(2025, 7, 1), instante=COLETA)
    assert m.ipca_12m is None
    assert espiao.chamadas == [(mpd.IPCA, HOJE, COLETA)]


def test_sem_as_of_motivo_e_none():
    assert MacroContext(selic=0.10).motivo("selic") is None


def test_serie_completa_em_janelas_e_lida_uma_vez(sgs):
    provedor, chamadas = sgs
    m = _macro(provedor, date(2026, 1, 5))
    assert m.selic == pytest.approx(0.15)
    assert m.selic == pytest.approx(0.15)
    selic = [u for u in chamadas if "sgs.432" in u]
    assert len(selic) == len(mpd.janelas(date(1999, 3, 5), HOJE)) == 3
    assert "dataInicial=05/03/1999" in selic[0]
    assert "dataFinal=10/11/2026" in selic[-1]
    _ = m.ipca_12m
    assert [u for u in chamadas if "sgs.433" in u] == [
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json"
    ]


def test_registro_traz_proveniencia_das_janelas(sgs):
    provedor, _ = sgs
    registro = provedor.serie_sgs(mpd.SELIC_META, HOJE, COLETA)
    assert len(registro["proveniencia"]) == 3
    assert registro["coleta"] == HOJE
    assert all(p["hash_sha256"] for p in registro["proveniencia"])


def test_provedor_com_erro_do_codigo_tem_motivo_proprio(monkeypatch, sgs):
    provedor, _ = sgs

    def _quebra(conteudo):
        raise KeyError("data")

    monkeypatch.setattr(mpd, "ler_sgs", _quebra)
    registro = provedor.serie_sgs(mpd.IPCA, HOJE, COLETA)
    assert registro == {"abstencao": "erro inesperado no provedor macro: KeyError"}


def test_provedor_sem_janela_ate_o_fim_abstem(sgs):
    provedor, chamadas = sgs
    registro = provedor.serie_sgs(mpd.SELIC_META, date(1990, 1, 1), COLETA)
    assert registro == {"abstencao": "série SGS 432 sem janela até 1990-01-01"}
    assert chamadas == []


def test_provedor_com_formato_invalido_abstem(monkeypatch, tmp_path):
    monkeypatch.setattr(
        provedor_macro.requests,
        "get",
        lambda url, *a, **k: _Resposta([{"data": "x", "valor": "1"}]),
    )
    registro = MacroProvider(cache_dir=tmp_path).serie_sgs(mpd.IPCA, HOJE, COLETA)
    assert "abstencao" in registro


# equivalência com as_of = hoje


def test_as_of_hoje_reproduz_o_valor_atual(sgs, monkeypatch):
    provedor, _ = sgs
    monkeypatch.setattr(config.requests, "get", _sgs_oficial)
    monkeypatch.setattr(config, "_selic_cache_value", None)
    monkeypatch.setattr(config, "_selic_cache_time", 0.0)
    atual = MacroContext()
    por_data = _macro(provedor, HOJE)
    assert por_data.selic == pytest.approx(atual.selic)
    assert por_data.cdi == pytest.approx(atual.cdi)
    assert por_data.ipca_12m == pytest.approx(atual.ipca_12m)


# ponta a ponta: SGS oficial → provedor → MacroContext(as_of) → motor do FII


def test_sgs_oficial_ate_o_motor_do_fii(sgs, monkeypatch):
    provedor, _ = sgs
    macro = _macro(provedor, date(2025, 7, 1))
    # Até o F3-6c o motor lê a Selic por `get_selic_atual`; o elo é esse ponto.
    monkeypatch.setattr(fii_engine, "get_selic_atual", lambda: macro.selic)
    dados = enriquecer_fii(
        {"ticker": "TSTI11", "preco_atual": 100.0, "dy": 0.09, "pvp": 1.0}, ntnb=0.07
    )
    resultado = FIIEngine().analisar(dados, as_of=AS_OF_GORDON)
    assert resultado["selic_liquida"] == pytest.approx(0.15 * 0.85)


# proveniência e resultado não representável (F3-1d; BUG-3-06, BUG-3-07, BUG-3-08)


@pytest.mark.parametrize("nome", ["selic", "cdi", "ipca_12m"])
def test_registro_por_data_leva_a_proveniencia_da_coleta(sgs, nome):
    provedor, _ = sgs
    registro = _macro(provedor, date(2025, 10, 15)).registro_por_data(nome)
    assert "valor" in registro
    assert registro["proveniencia"]
    for janela in registro["proveniencia"]:
        assert janela["fonte"].startswith("https://api.bcb.gov.br/")
        assert len(janela["hash_sha256"]) == 64
        assert set(janela) == {"fonte", "data_coleta", "hash_sha256", "aviso"}


def test_abstencao_calculada_leva_a_proveniencia(sgs):
    provedor, _ = sgs
    registro = _macro(provedor, date(2000, 1, 3)).registro_por_data("ipca_12m")
    assert "abstencao" in registro and "valor" not in registro
    assert registro["proveniencia"]


def test_falha_do_provedor_fica_sem_proveniencia(monkeypatch, sgs):
    provedor, _ = sgs

    def _fora(url, *args, **kwargs):
        raise provedor_macro.requests.ConnectionError("SGS fora do ar")

    monkeypatch.setattr(provedor_macro.requests, "get", _fora)
    registro = _macro(provedor, date(2025, 10, 15)).registro_por_data("selic")
    assert set(registro) == {"abstencao"}


@pytest.mark.parametrize("valor", [1e10, 1e300, -100.0, -150.0])
def test_cdi_nao_representavel_abstem(valor):
    registro = mpd.cdi([mpd.Observacao(date(2026, 1, 2), valor)], date(2026, 1, 5))
    assert registro == {
        "abstencao": "série SGS 12: resultado não representável com a observação de 2026-01-02"
    }


def test_cdi_no_limite_finito_continua_valor():
    registro = mpd.cdi([mpd.Observacao(date(2026, 1, 2), -99.0)], date(2026, 1, 5))
    assert registro["valor"] == pytest.approx(0.01**252 - 1)


@pytest.mark.parametrize(
    ("valor", "data"), [(-100.0, "2025-03-01"), (-120.0, "2025-03-01")]
)
def test_ipca_com_fator_nao_positivo_abstem(valor, data):
    observacoes = [
        mpd.Observacao(date(2025, mes, 1), valor if mes == 3 else 0.5)
        for mes in range(1, 13)
    ]
    registro = mpd.ipca_12m(observacoes, date(2026, 6, 1), date(2026, 6, 1))
    assert registro == {
        "abstencao": f"série SGS 433: resultado não representável com a observação de {data}"
    }


def test_ipca_infinito_abstem_pela_ultima_observacao():
    observacoes = [mpd.Observacao(date(2025, mes, 1), 1e300) for mes in range(1, 13)]
    registro = mpd.ipca_12m(observacoes, date(2026, 6, 1), date(2026, 6, 1))
    assert registro == {
        "abstencao": "série SGS 433: resultado não representável com a observação de 2025-12-01"
    }


def test_booleano_recusado_com_a_observacao():
    with pytest.raises(ValueError, match=r"SGS: observação inválida: .*True"):
        mpd.ler_sgs('[{"data": "02/01/2026", "valor": true}]')
