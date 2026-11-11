"""F3-1c: insumos da taxa real por data em `series_macro` e a leitura pelo banco.

Ponta a ponta: fixtures oficiais (Tesouro, ANBIMA, agenda e série do Focus, calendário do
IBGE, SIDRA, SGS) → provedor → `gravar_series` → `series_macro` → `registro_do_banco` →
`get_taxa_real(as_of)` → Gordon e FII. O resultado é o mesmo do caminho histórico do F3-1c-a.
"""

import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime

import pytest
from test_macro_por_data import _sgs_oficial
from test_taxa_real_data_passada import COLETA, JANELA, D, _Agora, _provedor

import config
from sentinela.data.providers import macro
from sentinela.data.store import migracoes

NUMEROS = (
    "ntnb",
    "custo_capital_real",
    "data_base",
    "dias_uteis",
    "quantidade",
    "as_of",
)


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


@pytest.fixture
def provedor(tmp_path, monkeypatch):
    provedor, _ = _provedor(tmp_path, monkeypatch, COLETA)
    original = provedor.baixar

    def baixar(url, instante):
        if "bcdata.sgs" in url:
            resposta = _sgs_oficial(url)
            return macro.SnapshotMacro(
                resposta.text, url, instante.isoformat(), "b" * 64
            )
        if "fer_nacionais/2025" in url:
            raise OSError("ANBIMA 2025 fora da fixture")
        return original(url, instante)

    monkeypatch.setattr(provedor, "baixar", baixar)
    return provedor


def _gravar(conn, provedor):
    return macro.gravar_series(
        conn, provedor, coleta=COLETA, datas=[D.date()], janela=JANELA
    )


def test_grava_cada_familia_com_fonte_coleta_e_hash(conn, provedor):
    resumo = _gravar(conn, provedor)
    assert resumo["tesouro"] == 4 and resumo["selic"] > 0 and resumo["focus"] > 0
    assert resumo["anbima_2025"] == {"abstencao": "ANBIMA 2025 fora da fixture"}
    familias = {
        serie.split("|")[0]
        for (serie,) in conn.execute("SELECT DISTINCT serie FROM series_macro")
    }
    assert familias == {
        "tesouro", "anbima_ano", "anbima_feriado", "focus_edicao", "focus_pib",
        "ipca_divulgacao", "ipca_sidra", "sgs_432",
    }  # fmt: skip
    vazias = conn.execute(
        "SELECT COUNT(*) FROM series_macro WHERE fonte = '' OR coleta != ? OR hash_sha256 = ''",
        (COLETA.isoformat(),),
    ).fetchone()
    assert vazias == (0,)


def test_banco_da_o_mesmo_resultado_do_caminho_historico(conn, provedor):
    _gravar(conn, provedor)
    do_banco = macro.registro_do_banco(conn, D, JANELA)
    historico = provedor.registro(D, JANELA, coleta=COLETA)
    assert "abstencao" not in do_banco, do_banco
    assert {k: do_banco[k] for k in NUMEROS} == {k: historico[k] for k in NUMEROS}
    assert do_banco["pib"]["valor"] == historico["pib"]["valor"]
    assert do_banco["pib"]["pesquisa"] == historico["pib"]["pesquisa"]
    assert do_banco["inflacao"]["valor"] == historico["inflacao"]["valor"]
    assert do_banco["coleta"] == COLETA.isoformat()
    assert do_banco["proveniencia"]["banco"] == "series_macro"


def test_banco_vazio_abstem_sem_numero(conn):
    assert macro.registro_do_banco(conn, D, JANELA) == {
        "abstencao": macro.SEM_NTNB_NO_BANCO
    }


def test_nao_usa_linha_posterior_a_d(conn, provedor):
    _gravar(conn, provedor)
    antes = datetime(
        2026, 10, 15, 16, tzinfo=UTC
    )  # a única data-base é a do próprio dia
    assert macro.registro_do_banco(conn, antes, JANELA) == {
        "abstencao": macro.SEM_NTNB_NO_BANCO
    }


def test_series_macro_e_so_de_insercao(conn, provedor):
    _gravar(conn, provedor)
    for sql in ("UPDATE series_macro SET valor = 1", "DELETE FROM series_macro"):
        with pytest.raises(sqlite3.IntegrityError, match="series_macro"):
            conn.execute(sql)
    with pytest.raises(sqlite3.IntegrityError, match="series_macro"):
        _gravar(conn, provedor)  # mesma coleta de novo: nada sobrescrito


def test_nova_coleta_prevalece_na_leitura(conn, provedor, tmp_path):
    _gravar(conn, provedor)
    depois = datetime(2026, 11, 12, 14, tzinfo=UTC)
    linha = conn.execute(
        "SELECT serie, data, detalhe_json, fonte, hash_sha256 FROM series_macro WHERE serie LIKE 'tesouro|Tesouro IPCA+|%'"
    ).fetchone()
    detalhe = linha[2].replace("6,73", "6,99")
    conn.execute(
        "INSERT INTO series_macro VALUES (?, ?, NULL, NULL, ?, ?, ?, ?)",
        (linha[0], linha[1], detalhe, linha[3], depois.isoformat(), "c" * 64),
    )
    registro = macro.registro_do_banco(conn, D, JANELA)
    assert registro["ntnb"] == pytest.approx((0.0682 + 0.0699) / 2)
    assert registro["coleta"] == depois.isoformat()


def test_get_taxa_real_de_data_passada_le_do_banco_ate_gordon_e_fii(
    conn, provedor, monkeypatch
):
    from unittest.mock import patch

    from apoio_bazin import enriquecer_bazin
    from apoio_escopo import de_empresa
    from apoio_fii import enriquecer_fii
    from apoio_gordon import AS_OF_GORDON, DiaGordon, enriquecer_gordon

    from fii_engine import FIIEngine
    from valuation_engine import ValuationEngine

    _gravar(conn, provedor)
    monkeypatch.setattr(config, "datetime", _Agora)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    monkeypatch.setattr(config, "_conexao_series_macro", lambda: conn)
    registro = config.get_taxa_real(as_of=AS_OF_GORDON, janela=JANELA)
    assert registro["proveniencia"]["banco"] == "series_macro"
    dados = enriquecer_bazin(
        enriquecer_gordon(
            {
                "ticker": "DIVG3",
                "preco_atual": 100.0,
                "roe": 0.15,
                "pl": 10.0,
                "pvp": 2.0,
                "dy": 0.10,
            }
        )
    )
    dados["taxa_real"] = registro
    with patch("valuation_engine.date", DiaGordon):
        acoes = ValuationEngine().processar(de_empresa(dados), as_of=AS_OF_GORDON)
    assert acoes["lentes"]["Gordon"]["valor"] is not None
    fii = enriquecer_fii(
        {"ticker": "TSTI11", "preco_atual": 100.0, "dy": 0.09, "pvp": 1.0}
    )
    resultado = FIIEngine().analisar({**fii, "taxa_real": registro}, as_of=AS_OF_GORDON)
    assert next(iter(resultado["lentes"].values()))["valor"] is not None


def test_get_taxa_real_de_data_passada_sem_banco_abstem(monkeypatch):
    monkeypatch.setattr(config, "datetime", _Agora)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    monkeypatch.setattr(config, "_conexao_series_macro", lambda: None)
    assert config.get_taxa_real(as_of=D, janela=JANELA) == {
        "abstencao": "banco único indisponível para a data passada"
    }


def test_janela_ou_selic_nao_sao_exigidas_para_registrar_a_taxa(conn, provedor):
    resumo = macro.gravar_series(conn, provedor, coleta=COLETA, datas=[D.date()])
    assert "ipca" in resumo
    assert macro.registro_do_banco(conn, D)["inflacao"] == {
        "abstencao": "janela contábil anual não demonstrada"
    }
    assert date.fromisoformat(macro.registro_do_banco(conn, D)["data_base"]) < D.date()


# --- contrato fino da gravação e da leitura (mutação do F3-1c) -------------------------


def _linhas(conn, serie_like):
    return conn.execute(
        "SELECT serie, data, valor, divulgacao, detalhe_json, fonte, hash_sha256 FROM series_macro "
        "WHERE serie LIKE ? ORDER BY serie, data",
        (serie_like,),
    ).fetchall()


def test_linha_original_gravada_com_acentos_e_chaves_ordenadas(conn, provedor):
    import json

    _gravar(conn, provedor)
    (primeira, *_) = _linhas(conn, "ipca_sidra")
    original = json.loads(primeira[4])
    assert primeira[4] == json.dumps(original, ensure_ascii=False, sort_keys=True)
    assert "Variação" in primeira[4]
    assert primeira[1] == "2025-01-01" and primeira[2] == pytest.approx(0.0016)
    assert _linhas(conn, "anbima_feriado")[0][4] == '{"ano": 2026}'


def test_contagens_e_instante_da_coleta(conn, provedor, tmp_path, monkeypatch):
    import json

    from test_taxa_real_data_passada import FONTES

    resumo = _gravar(conn, provedor)
    feriados = len(_linhas(conn, "anbima_feriado"))
    assert resumo["anbima"] == 1 + feriados  # a linha do ano mais os feriados de 2026
    edicoes = macro.edicoes_focus(FONTES["bcb_calendar_focus"]["conteudo"])
    assert len(_linhas(conn, "focus_edicao")) == len(edicoes)
    assert len(_linhas(conn, "focus_pib|%")) == len(
        json.loads(FONTES["focus_pib"]["conteudo"])["value"]
    )
    assert resumo["focus"] == len(edicoes) + len(_linhas(conn, "focus_pib|%"))
    assert _linhas(conn, "focus_edicao")[0][3].endswith("+00:00")


def test_selic_com_fonte_e_hash_da_coleta(conn, provedor):
    _gravar(conn, provedor)
    selic = _linhas(conn, "sgs_432")
    assert all("bcdata.sgs.432" in linha[5] and linha[6] == "b" * 64 for linha in selic)
    assert [linha[1] for linha in selic] == sorted(linha[1] for linha in selic)


def test_falha_de_cada_familia_traz_o_motivo(conn, provedor, monkeypatch):
    from sentinela.data.providers import tesouro

    original = provedor.baixar

    def baixar(url, instante):
        if "sitebcb/calendario" in url:
            raise OSError("agenda Focus fora")
        if "calendario/9256" in url:
            raise KeyError("items")
        if "bcdata.sgs" in url:
            raise OSError("SGS fora")
        return original(url, instante)

    monkeypatch.setattr(provedor, "baixar", baixar)
    monkeypatch.setattr(
        tesouro.TesouroProvider,
        "baixar",
        lambda self, instante: tesouro.ArquivoTesouro(self.cache_dir / "x.csv", None),
    )
    resumo = _gravar(conn, provedor)
    assert resumo["tesouro"] == {"abstencao": "proveniência ausente"}
    assert resumo["focus"] == {"abstencao": "agenda Focus fora"}
    assert resumo["ipca"]["abstencao"].startswith("erro inesperado no provedor macro")
    assert resumo["selic"] == {"abstencao": "SGS fora"}
    assert conn.execute(
        "SELECT COUNT(*) FROM series_macro WHERE serie LIKE 'tesouro|%'"
    ).fetchone() == (0,)


def test_falha_do_codigo_numa_familia_tem_motivo_proprio(conn, provedor, monkeypatch):
    def quebra(*a, **k):
        raise TypeError("quebrou")

    monkeypatch.setattr(provedor, "serie_sgs", quebra)
    motivo = _gravar(conn, provedor)["selic"]["abstencao"]
    assert (
        motivo.startswith("erro inesperado no provedor macro") and "TypeError" in motivo
    )


def _so_prefixado(conn):
    conn.execute(
        "INSERT INTO series_macro VALUES (?, ?, NULL, NULL, ?, ?, ?, ?)",
        (
            "tesouro|Tesouro Prefixado|01/01/2029",
            "2026-10-15",
            (
                '{"cabecalho": "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha", '
                '"linha": "Tesouro Prefixado;01/01/2029;15/10/2026;12,64;12,76;770,85;768,69;768,69"}'
            ),
            "tesouro",
            COLETA.isoformat(),
            "d" * 64,
        ),
    )


def test_cesta_sem_ntnb_no_banco_abstem(conn):
    _so_prefixado(conn)
    conn.execute(
        "INSERT INTO series_macro VALUES ('anbima_ano', '2026-01-01', NULL, NULL, "
        "'{\"proveniencia\": {}}', 'anbima', ?, 'f')",
        (COLETA.isoformat(),),
    )
    assert macro.registro_do_banco(conn, D) == {
        "abstencao": "cesta vazia: nenhum título elegível"
    }


def test_ipca_ausente_no_banco_e_inflacao_fora_da_janela(conn, provedor):
    macro.gravar_series(
        conn, provedor, coleta=COLETA, datas=[D.date()]
    )  # sem janela: sem SIDRA
    assert macro.registro_do_banco(conn, D, JANELA)["inflacao"] == {
        "abstencao": "IPCA ausente no banco"
    }
    conn2 = sqlite3.connect(":memory:")
    migracoes.aplicar(conn2)
    _gravar(conn2, provedor)
    fora = macro.registro_do_banco(conn2, D, (date(2023, 1, 1), date(2023, 12, 31)))[
        "inflacao"
    ]
    assert fora["abstencao"].startswith("IPCA")
    conn2.close()


def test_pib_do_banco_igual_ao_historico_com_a_proxima_publicacao(conn, provedor):
    _gravar(conn, provedor)
    historico = provedor.registro(D, JANELA, coleta=COLETA)["pib"]
    do_banco = macro.registro_do_banco(conn, D, JANELA)["pib"]
    assert do_banco["proxima_publicacao"] == historico["proxima_publicacao"] is not None
    assert {k: do_banco[k] for k in ("valor", "ano", "pesquisa", "publicacao")} == {
        k: historico[k] for k in ("valor", "ano", "pesquisa", "publicacao")
    }


def test_pib_sem_edicao_ou_sem_linhas_abstem_com_motivo(conn, provedor):
    _gravar(conn, provedor)
    cedo = datetime(2026, 1, 2, 12, tzinfo=UTC)  # nenhuma edição de 2026 publicada
    assert macro._pib_do_banco(conn, cedo) == {
        "abstencao": "edição Focus devida ausente no banco"
    }
    tarde = datetime(2026, 11, 10, 12, tzinfo=UTC)  # edição devida sem linhas gravadas
    assert macro._pib_do_banco(conn, tarde) == {
        "abstencao": "edição Focus devida indisponível"
    }


def test_linha_invalida_de_outro_titulo_no_banco_nao_derruba(conn, provedor):
    _gravar(conn, provedor)
    conn.execute(
        "INSERT INTO series_macro VALUES (?, ?, NULL, NULL, ?, ?, ?, ?)",
        (
            "tesouro|Tesouro Prefixado|01/01/2031",
            "2026-10-15",
            '{"cabecalho": "x", "linha": "Tesouro Prefixado;01/01/2031;15/10/2026;x;12,00;700,00;700,00;700,00"}',
            "tesouro",
            COLETA.isoformat(),
            "e" * 64,
        ),
    )
    assert "ntnb" in macro.registro_do_banco(conn, D, JANELA)


def test_hash_da_proveniencia_e_o_da_coleta_mais_recente(conn, provedor):
    _gravar(conn, provedor)
    depois = datetime(2026, 11, 12, 14, tzinfo=UTC)
    linha = conn.execute(
        "SELECT serie, data, detalhe_json, fonte FROM series_macro WHERE serie LIKE 'tesouro|Tesouro IPCA+|%'"
    ).fetchone()
    conn.execute(
        "INSERT INTO series_macro VALUES (?, ?, NULL, NULL, ?, ?, ?, ?)",
        (*linha, depois.isoformat(), "c" * 64),
    )
    assert (
        macro.registro_do_banco(conn, D, JANELA)["proveniencia"]["hash_sha256"]
        == "c" * 64
    )


def test_d_na_manha_da_edicao_focus_tem_a_edicao_anterior_gravada(
    conn, provedor, monkeypatch
):
    """Revisão do F3-1c: antes do horário da edição de D, vale a da semana anterior."""
    import json

    from test_taxa_real_data_passada import FONTES

    original = provedor.baixar
    linhas = json.loads(FONTES["focus_pib"]["conteudo"])["value"]
    anterior = [{**linha, "Data": "2026-10-09", "Mediana": 1.7} for linha in linhas]

    def baixar(url, instante):
        if "ExpectativasMercadoAnuais" in url and "2026-10-09" in url:
            return macro.SnapshotMacro(
                json.dumps({"value": anterior}), url, instante.isoformat(), "9" * 64
            )
        if "ExpectativasMercadoAnuais" in url and "2026-10-16" not in url:
            return macro.SnapshotMacro(
                '{"value": []}', url, instante.isoformat(), "8" * 64
            )
        return original(url, instante)

    monkeypatch.setattr(provedor, "baixar", baixar)
    manha = datetime(
        2026, 10, 19, 10, tzinfo=UTC
    )  # a edição de 16/10 sai às 11h30 UTC de 19/10
    macro.gravar_series(conn, provedor, coleta=COLETA, datas=[manha.date()])
    do_banco = macro._pib_do_banco(conn, manha)
    assert do_banco["pesquisa"] == "2026-10-09" and do_banco["valor"] == pytest.approx(
        0.017
    )
    assert macro._pib_do_banco(conn, D)["pesquisa"] == "2026-10-16"


def test_banco_que_recusa_a_migracao_abstem(monkeypatch):
    """Revisão do F3-1c: `ValueError` do `caminho_padrao` vira abstenção, não exceção."""
    from conftest import CONEXAO_SERIES_MACRO_REAL

    from sentinela.data.store import unico

    assert (
        CONEXAO_SERIES_MACRO_REAL.__name__ == "_conexao_series_macro"
    )  # a real, não a semente

    def recusa():
        raise ValueError("migração já aplicada foi alterada")

    monkeypatch.setattr(unico, "caminho_padrao", recusa)
    assert CONEXAO_SERIES_MACRO_REAL() is None
    monkeypatch.setattr(config, "_conexao_series_macro", CONEXAO_SERIES_MACRO_REAL)
    monkeypatch.setattr(config, "datetime", _Agora)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    assert config.get_taxa_real(as_of=D, janela=JANELA) == {
        "abstencao": "banco único indisponível para a data passada"
    }


def test_gravacao_do_tesouro_com_hash_divergente_nao_grava(
    conn, provedor, tmp_path, monkeypatch
):
    from dataclasses import replace

    from sentinela.data.providers import tesouro

    original = tesouro.TesouroProvider.baixar

    def adulterado(self, instante):
        arquivo = original(self, instante)
        return replace(
            arquivo, proveniencia=replace(arquivo.proveniencia, hash_sha256="0" * 64)
        )

    monkeypatch.setattr(tesouro.TesouroProvider, "baixar", adulterado)
    resumo = _gravar(conn, provedor)
    assert resumo["tesouro"] == {"abstencao": "conteúdo diverge da proveniência"}
    assert conn.execute(
        "SELECT COUNT(*) FROM series_macro WHERE serie LIKE 'tesouro|%'"
    ).fetchone() == (0,)


def test_banco_sem_a_tabela_abstem(monkeypatch):
    sem_tabela = sqlite3.connect(":memory:")
    monkeypatch.setattr(config, "_conexao_series_macro", lambda: sem_tabela)
    motivo = config._taxa_real_do_banco(D, JANELA)["abstencao"]
    assert motivo.startswith("series_macro indisponível: no such table")


# --- F3-A-F6 (BUG-3-18): proveniência da Selic por janela ----------------------------------

_JANELA_A = "https://sgs?formato=json&dataInicial=01/01/2015&dataFinal=31/12/2015"
_JANELA_B = "https://sgs?formato=json&dataInicial=01/01/2016&dataFinal=31/12/2016"


def _sgs_falso(monkeypatch, provedor, observacoes, proveniencia):
    from sentinela.data.macro_por_data import Observacao

    def serie_sgs(serie, fim, instante):
        return {
            "observacoes": tuple(
                Observacao(date.fromisoformat(d), v) for d, v in observacoes
            ),
            "coleta": instante.date(),
            "proveniencia": proveniencia,
        }

    monkeypatch.setattr(provedor, "serie_sgs", serie_sgs)


def test_selic_de_cada_janela_com_a_sua_proveniencia(conn, provedor, monkeypatch):
    _sgs_falso(
        monkeypatch,
        provedor,
        [("2015-12-31", 14.25), ("2016-01-01", 14.25)],
        [
            {"fonte": _JANELA_A, "hash_sha256": "a" * 64},
            {"fonte": _JANELA_B, "hash_sha256": "b" * 64},
        ],
    )
    assert _gravar(conn, provedor)["selic"] == 2
    assert [(l[1], l[5], l[6]) for l in _linhas(conn, "sgs_432")] == [
        ("2015-12-31", _JANELA_A, "a" * 64),
        ("2016-01-01", _JANELA_B, "b" * 64),
    ]


def test_serie_sem_janela_na_url_usa_a_unica_coleta(conn, provedor, monkeypatch):
    url = "https://sgs?formato=json"
    _sgs_falso(
        monkeypatch,
        provedor,
        [("2016-01-04", 14.25)],
        [{"fonte": url, "hash_sha256": "c" * 64}],
    )
    assert _gravar(conn, provedor)["selic"] == 1
    assert [(l[5], l[6]) for l in _linhas(conn, "sgs_432")] == [(url, "c" * 64)]


@pytest.mark.parametrize(
    ("observacoes", "proveniencia", "motivo"),
    [
        (
            [("2017-01-02", 13.75)],
            [
                {"fonte": _JANELA_A, "hash_sha256": "a" * 64},
                {"fonte": _JANELA_B, "hash_sha256": "b" * 64},
            ],
            "Selic: observação de 2017-01-02 sem janela única da coleta",
        ),
        (
            [("2015-06-01", 13.75)],
            [
                {"fonte": _JANELA_A, "hash_sha256": "a" * 64},
                {"fonte": _JANELA_A, "hash_sha256": "d" * 64},
            ],
            "Selic: observação de 2015-06-01 sem janela única da coleta",
        ),
        ([("2015-06-01", 13.75)], [], "Selic sem proveniência da coleta"),
    ],
)
def test_selic_sem_janela_unica_abstem_a_familia(
    conn, provedor, monkeypatch, observacoes, proveniencia, motivo
):
    _sgs_falso(monkeypatch, provedor, observacoes, proveniencia)
    resumo = _gravar(conn, provedor)
    assert resumo["selic"] == {"abstencao": motivo}
    assert _linhas(conn, "sgs_432") == []
    assert isinstance(resumo["tesouro"], int)  # as outras famílias seguem


@pytest.mark.parametrize(
    "proveniencia", [{"fonte": _JANELA_A}, {"hash_sha256": "a" * 64}]
)
def test_selic_com_proveniencia_incompleta_e_erro_do_codigo(
    conn, provedor, monkeypatch, proveniencia
):
    _sgs_falso(monkeypatch, provedor, [("2015-06-01", 13.75)], [proveniencia])
    motivo = _gravar(conn, provedor)["selic"]["abstencao"]
    assert motivo == "erro inesperado no provedor macro: KeyError"
    assert _linhas(conn, "sgs_432") == []


@pytest.mark.parametrize(
    "url",
    [
        "https://sgs?formato=json&dataInicial=01/01/2015",
        "https://sgs?formato=json&dataFinal=31/12/2015",
        "https://sgs?formato=json&dataFinal=31/12/2015&dataInicial=01/01/2015",
    ],
)
def test_selic_com_janela_ilegivel_na_url_abstem(conn, provedor, monkeypatch, url):
    _sgs_falso(
        monkeypatch,
        provedor,
        [("2015-06-01", 13.75)],
        [{"fonte": url, "hash_sha256": "a" * 64}],
    )
    assert _gravar(conn, provedor)["selic"] == {
        "abstencao": f"Selic: janela ilegível na fonte {url}"
    }
    assert _linhas(conn, "sgs_432") == []
