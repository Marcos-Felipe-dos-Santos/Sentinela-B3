"""SIDRA e Focus: domínio, janela e calendário de publicação explícitos."""

from datetime import UTC, date, datetime

import pytest

from sentinela.data.providers import macro

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)


def _ipca():
    return [
        {"D1C": "1", "D2C": "63", "D3C": f"2025{m:02}", "MN": "%", "V": "0.1"}
        for m in range(1, 13)
    ] + [{"D1C": "1", "D2C": "63", "D3C": "202609", "MN": "%", "V": "-0.1"}]


def _publicacoes():
    return {f"2025{m:02}": date(2026, 1, 9) for m in range(1, 13)} | {
        "202609": date(2026, 10, 9)
    }


def test_ipca_composto_na_janela_anual_sem_arredondar():
    r = macro.ipca_da_janela(
        _ipca(),
        _publicacoes(),
        inicio=date(2025, 1, 1),
        fim=date(2025, 12, 31),
        as_of=AS_OF,
    )
    assert r["valor"] == pytest.approx(1.001**12 - 1)
    assert r["inicio"] == "2025-01-01" and r["fim"] == "2025-12-31"
    assert r["ultimo_mes_publicado"] == "202609"


@pytest.mark.parametrize("valor", ["...", "NaN", "inf", "-100", "texto"])
def test_ipca_invalido_abstem(valor):
    linhas = _ipca()
    linhas[0]["V"] = valor
    with pytest.raises(ValueError):
        macro.ipca_da_janela(
            linhas,
            _publicacoes(),
            inicio=date(2025, 1, 1),
            fim=date(2025, 12, 31),
            as_of=AS_OF,
        )


def test_pib_escolhe_base_zero_e_maior_ano_da_ultima_pesquisa():
    linhas = [
        {
            "Indicador": "PIB Total",
            "baseCalculo": b,
            "Data": "2026-10-16",
            "DataReferencia": str(a),
            "Mediana": v,
        }
        for b, a, v in [(0, 2029, 1.9), (0, 2030, 2), (1, 2031, 9)]
    ]
    r = macro.pib_focus(
        linhas,
        {date(2026, 10, 16): datetime(2026, 10, 19, 11, 30, tzinfo=UTC)},
        as_of=AS_OF,
    )
    assert r["valor"] == 0.02
    assert r["ano"] == 2030 and r["baseCalculo"] == 0
    assert r["pesquisa"] == "2026-10-16"


def test_pib_edicao_devida_indisponivel_nao_usa_anterior():
    with pytest.raises(ValueError, match="edição"):
        macro.pib_focus(
            [],
            {date(2026, 10, 16): datetime(2026, 10, 19, 11, 30, tzinfo=UTC)},
            as_of=AS_OF,
        )


def test_deflacao_e_permitida_e_publicacao_no_dia_ainda_nao_entra():
    linhas = _ipca()
    for linha in linhas:
        linha["V"] = "-0.1"
    r = macro.ipca_da_janela(
        linhas,
        _publicacoes(),
        inicio=date(2025, 1, 1),
        fim=date(2025, 12, 31),
        as_of=AS_OF,
    )
    assert r["valor"] == pytest.approx(0.999**12 - 1)
    publicacoes = _publicacoes() | {"202512": AS_OF.date()}
    with pytest.raises(ValueError, match="janela"):
        macro.ipca_da_janela(
            linhas,
            publicacoes,
            inicio=date(2025, 1, 1),
            fim=date(2025, 12, 31),
            as_of=AS_OF,
        )


@pytest.mark.parametrize(
    "inicio,fim",
    [
        (date(2025, 1, 2), date(2025, 12, 31)),
        (date(2025, 1, 1), date(2025, 12, 30)),
        (date(2025, 1, 1), date(2025, 11, 30)),
    ],
)
def test_janela_incompleta_recusada(inicio, fim):
    with pytest.raises(ValueError, match="janela"):
        macro.ipca_da_janela(
            _ipca(), _publicacoes(), inicio=inicio, fim=fim, as_of=AS_OF
        )


def test_ipca_atualidade_nao_se_confunde_com_janela_antiga():
    linhas = _ipca()[:-1]
    with pytest.raises(ValueError, match="desatualizada"):
        macro.ipca_da_janela(
            linhas,
            _publicacoes(),
            inicio=date(2025, 1, 1),
            fim=date(2025, 12, 31),
            as_of=AS_OF,
        )
    with pytest.raises(ValueError, match="publicado ausente"):
        macro.ipca_da_janela(
            linhas, {}, inicio=date(2025, 1, 1), fim=date(2025, 12, 31), as_of=AS_OF
        )


def test_ipca_conflito_e_unidade_errada():
    linhas = _ipca()
    with pytest.raises(ValueError, match="conflitante"):
        macro.ipca_da_janela(
            linhas + [linhas[0] | {"V": "9"}],
            _publicacoes(),
            inicio=date(2025, 1, 1),
            fim=date(2025, 12, 31),
            as_of=AS_OF,
        )
    linhas[0]["MN"] = "razão"
    with pytest.raises(ValueError, match="unidade"):
        macro.ipca_da_janela(
            linhas,
            _publicacoes(),
            inicio=date(2025, 1, 1),
            fim=date(2025, 12, 31),
            as_of=AS_OF,
        )


@pytest.mark.parametrize("valor", [None, True, "nan", "inf", -100])
def test_mediana_invalida_nao_vira_teto(valor):
    with pytest.raises(ValueError):
        macro.pib_focus(
            [
                {
                    "Indicador": "PIB Total",
                    "baseCalculo": 0,
                    "Data": "2026-10-16",
                    "DataReferencia": "2030",
                    "Mediana": valor,
                }
            ],
            {date(2026, 10, 16): datetime(2026, 10, 19, 11, 30, tzinfo=UTC)},
            as_of=AS_OF,
        )


def test_pib_edicao_futura_e_conflito():
    linha = {
        "Indicador": "PIB Total",
        "baseCalculo": 0,
        "Data": "2026-10-16",
        "DataReferencia": "2030",
        "Mediana": 2,
    }
    edicoes = {date(2026, 10, 16): datetime(2026, 10, 19, 11, 30, tzinfo=UTC)}
    with pytest.raises(ValueError, match="conflitante"):
        macro.pib_focus([linha, linha | {"Mediana": 3}], edicoes, as_of=AS_OF)
    with pytest.raises(ValueError, match="publicada ausente"):
        macro.pib_focus([linha], edicoes, as_of=datetime(2026, 10, 18, tzinfo=UTC))
    for valor in [0, -1]:
        assert (
            macro.pib_focus([linha | {"Mediana": valor}], edicoes, as_of=AS_OF)["valor"]
            == valor / 100
        )


def test_cache_ttl_falha_de_rede_integridade_e_coleta(tmp_path, monkeypatch):
    import json
    from datetime import timedelta
    from types import SimpleNamespace

    import requests

    chamadas = []

    def obter(url, timeout):
        chamadas.append((url, timeout))
        return SimpleNamespace(text='{"value":[]}', raise_for_status=lambda: None)

    monkeypatch.setattr(macro.requests, "get", obter)
    provider = macro.MacroProvider(tmp_path)
    inicial = provider.baixar("https://exemplo.invalid/publico", AS_OF)
    assert inicial.conteudo == '{"value":[]}'
    assert inicial.coleta == AS_OF.isoformat()
    assert provider.baixar(inicial.fonte, AS_OF + timedelta(hours=1)) == inicial
    assert len(chamadas) == 1

    def fora(*args, **kw):
        raise requests.ConnectionError("fora")

    monkeypatch.setattr(macro.requests, "get", fora)
    antigo = provider.baixar(inicial.fonte, AS_OF + timedelta(days=2))
    assert antigo.coleta == inicial.coleta and antigo.hash_sha256 == inicial.hash_sha256
    assert "cache exige" in antigo.aviso
    with pytest.raises(ValueError, match="posterior"):
        provider.baixar(inicial.fonte, AS_OF - timedelta(seconds=1))
    with pytest.raises(requests.ConnectionError):
        provider.baixar("https://exemplo.invalid/sem-cache", AS_OF)
    caminho = next(tmp_path.glob("*.json"))
    dados = json.loads(caminho.read_text())
    dados["conteudo"] = "alterado"
    caminho.write_text(json.dumps(dados))
    with pytest.raises(ValueError, match="integridade"):
        provider.baixar(inicial.fonte, AS_OF)


def test_cache_renova_depois_do_ttl(tmp_path, monkeypatch):
    from datetime import timedelta
    from types import SimpleNamespace

    conteudos = iter(["primeiro", "segundo"])
    monkeypatch.setattr(
        macro.requests,
        "get",
        lambda *a, **k: SimpleNamespace(
            text=next(conteudos), raise_for_status=lambda: None
        ),
    )
    provider = macro.MacroProvider(tmp_path)
    primeiro = provider.baixar("https://exemplo.invalid/publico", AS_OF)
    segundo = provider.baixar(primeiro.fonte, AS_OF + timedelta(seconds=macro.TTL))
    assert segundo.conteudo == "segundo" and segundo.hash_sha256 != primeiro.hash_sha256
    assert segundo.aviso is None


def test_as_of_sem_fuso_recusado():
    with pytest.raises(ValueError, match="fuso"):
        macro.ipca_da_janela(
            [],
            {},
            inicio=date(2025, 1, 1),
            fim=date(2025, 12, 31),
            as_of=datetime(2026, 10, 20, tzinfo=UTC).replace(tzinfo=None),
        )


def _registro_preparado(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from sentinela.data import taxas
    from sentinela.data.providers import tesouro
    from sentinela.domain.units import RateReal

    provider = macro.MacroProvider(tmp_path)
    titulo = tesouro.TituloTesouro(
        "Tesouro IPCA+",
        "NTN-B Principal",
        date(2035, 1, 1),
        date(2026, 10, 15),
        RateReal(0.07),
        RateReal(0.071),
        100,
        100,
    )
    arquivo = SimpleNamespace(
        proveniencia=SimpleNamespace(para_dict=lambda: {"fonte": tesouro.URL})
    )
    monkeypatch.setattr(tesouro.TesouroProvider, "baixar", lambda self, t: arquivo)
    monkeypatch.setattr(tesouro, "ler_snapshot", lambda a, as_of: (titulo,))
    monkeypatch.setattr(
        provider,
        "calendario",
        lambda ano, t: taxas.Calendario(
            date(ano, 1, 1), date(ano, 12, 31), frozenset(), {"ano": ano}
        ),
    )
    monkeypatch.setattr(
        provider,
        "inflacao",
        lambda inicio, fim, t: {
            "valor": 0.0426,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
        },
    )
    monkeypatch.setattr(provider, "pib", lambda t: {"valor": 0.02, "ano": 2030})
    return provider


def test_orquestracao_disponibiliza_moeda_janela_e_fontes(tmp_path, monkeypatch):
    provider = _registro_preparado(tmp_path, monkeypatch)
    r = provider.registro(AS_OF, (date(2025, 1, 1), date(2025, 12, 31)))
    assert r["ntnb"] == 0.07 and r["custo_capital_real"] == pytest.approx(0.12)
    assert r["inflacao"] == {
        "valor": 0.0426,
        "inicio": "2025-01-01",
        "fim": "2025-12-31",
    }
    assert r["pib"] == {"valor": 0.02, "ano": 2030}
    assert r["proveniencia"]["calendario"]["anos"] == [{"ano": 2026}]
    r = provider.registro(AS_OF)
    assert r["inflacao"] == {"abstencao": "janela contábil anual não demonstrada"}


def test_orquestracao_nao_inventa_fontes_ausentes(tmp_path, monkeypatch):
    provider = _registro_preparado(tmp_path, monkeypatch)

    def falha(*a, **kw):
        raise ValueError("fonte inválida")

    monkeypatch.setattr(provider, "inflacao", falha)
    monkeypatch.setattr(provider, "pib", falha)
    r = provider.registro(AS_OF, (date(2025, 1, 1), date(2025, 12, 31)))
    assert r["inflacao"] == {"abstencao": "fonte inválida"}
    assert r["pib"] == {"abstencao": "fonte inválida"}
    monkeypatch.setattr(provider, "calendario", falha)
    assert provider.registro(AS_OF) == {"abstencao": "fonte inválida"}


def test_orquestracao_nao_contorna_abstencao_da_cesta(tmp_path, monkeypatch):
    from sentinela.data import taxas

    provider = _registro_preparado(tmp_path, monkeypatch)
    monkeypatch.setattr(
        taxas, "calcular", lambda *a, **kw: taxas.Abstencao("desatualizada")
    )
    assert provider.registro(AS_OF) == {"abstencao": "desatualizada"}


@pytest.mark.parametrize("conteudo", ["sem datas", ">1/1/25<"])
def test_calendario_invalido_nao_vira_lista_vazia(conteudo, tmp_path, monkeypatch):
    provider = macro.MacroProvider(tmp_path)
    monkeypatch.setattr(
        provider,
        "baixar",
        lambda *a: macro.SnapshotMacro(conteudo, "fonte", AS_OF.isoformat(), "a" * 64),
    )
    with pytest.raises(ValueError, match="calendário"):
        provider.calendario(2026, AS_OF)
