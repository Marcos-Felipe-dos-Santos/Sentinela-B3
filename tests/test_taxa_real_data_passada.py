"""F3-1c-a: taxa real numa data passada, com a coleta real separada do corte (DD-18, DD-37).

Ponta a ponta pelas fixtures oficiais: CSV do Tesouro (data-base 15/10/2026), Focus, agenda do
BCB, calendário do IBGE, SIDRA e ANBIMA → `MacroProvider.registro` → `get_taxa_real`.
D = 20/10/2026 16h UTC; a coleta acontece depois, em 11/11/2026.
"""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

import config
from sentinela.data import macro_por_data as mpd
from sentinela.data.providers import macro, tesouro

CONTRATOS = Path(__file__).parent / "fixtures" / "contratos"
FONTES = json.loads((CONTRATOS / "macro_2026.json").read_text(encoding="utf-8"))[
    "fontes"
]
CSV = json.loads((CONTRATOS / "tesouro_2026.json").read_text(encoding="utf-8"))[
    "membros"
]["precotaxatesourodireto.csv"]
D = datetime(2026, 10, 20, 16, tzinfo=UTC)
COLETA = datetime(2026, 11, 11, 14, tzinfo=UTC)
JANELA = (date(2025, 1, 1), date(2025, 12, 31))


def _provedor(tmp_path, monkeypatch, coleta):
    """MacroProvider com as fixtures no lugar da rede; guarda o instante de cada download."""
    provedor = macro.MacroProvider(cache_dir=tmp_path / "macro")
    instantes = []

    def baixar(url, instante):
        instantes.append(instante)
        if "fer_nacionais" in url:
            nome = "anbima2026"
        elif "calendario/9256" in url:
            nome = "ibge_calendario"
        elif "sitebcb/calendario" in url:
            nome = "bcb_calendar_focus"
        elif "ExpectativasMercadoAnuais" in url:
            assert "2026-10-16" in url  # edição devida até D, não a da coleta
            nome = "focus_pib"
        else:
            assert "/1737/" in url and "202501-202609" in url
            nome = "ipca_mensal"
        fonte = FONTES[nome]
        meta = fonte.get("metadados", {})
        return macro.SnapshotMacro(
            fonte["conteudo"], url, instante.isoformat(), meta.get("sha256", "a" * 64)
        )

    monkeypatch.setattr(provedor, "baixar", baixar)
    caminho = tmp_path / "macro" / "tesouro" / "precotaxatesourodireto.csv"
    caminho.parent.mkdir(parents=True)
    caminho.write_text(CSV, encoding="utf-8")
    os.utime(caminho, (coleta.timestamp(), coleta.timestamp()))

    def baixar_tesouro(self, instante):
        instantes.append(instante)
        return self._snapshot(caminho)

    monkeypatch.setattr(tesouro.TesouroProvider, "baixar", baixar_tesouro)
    return provedor, instantes


def test_data_passada_coleta_depois_e_corta_em_d(tmp_path, monkeypatch):
    provedor, instantes = _provedor(tmp_path, monkeypatch, COLETA)
    registro = provedor.registro(D, JANELA, coleta=COLETA)
    assert "abstencao" not in registro, registro
    assert set(instantes) == {COLETA}  # todo download com o instante real
    assert registro["data_base"] == "2026-10-15"  # anterior ao dia de D
    assert registro["ntnb"] == pytest.approx((0.0682 + 0.0673) / 2)
    assert registro["as_of"] == D.isoformat()
    assert registro["coleta"] == COLETA.isoformat()
    assert registro["avisos"] == [tesouro.AVISO_HISTORICO]
    assert registro["pib"]["valor"] is not None
    assert "abstencao" not in registro["inflacao"]


def test_sem_coleta_separada_o_arquivo_posterior_a_d_e_recusado(tmp_path, monkeypatch):
    """O caminho de hoje continua exigindo coleta até o corte (2B)."""
    provedor, _ = _provedor(tmp_path, monkeypatch, COLETA)
    registro = provedor.registro(D, JANELA)
    assert registro == {"abstencao": "coleta posterior ao as_of"}


def test_d_hoje_da_o_mesmo_registro_que_o_historico_sem_coleta_e_aviso(
    tmp_path, monkeypatch
):
    """Com D = dia da coleta, o caminho de hoje; coletado depois, o histórico dá os mesmos
    números, mais a coleta e o aviso."""
    hoje, _ = _provedor(tmp_path / "hoje", monkeypatch, D)
    de_hoje = hoje.registro(D, JANELA)
    assert hoje.registro(D, JANELA, coleta=D) == de_hoje
    assert "coleta" not in de_hoje and "avisos" not in de_hoje
    depois, _ = _provedor(tmp_path / "depois", monkeypatch, COLETA)
    historico = depois.registro(D, JANELA, coleta=COLETA)
    extras = {"coleta", "avisos", "proveniencia", "pib", "inflacao"}
    assert {k: v for k, v in historico.items() if k not in extras} == {
        k: v for k, v in de_hoje.items() if k not in extras
    }
    assert historico["pib"]["valor"] == de_hoje["pib"]["valor"]
    assert historico["inflacao"]["valor"] == de_hoje["inflacao"]["valor"]


def test_historico_sem_data_base_anterior_a_d_abstem(tmp_path, monkeypatch):
    provedor, _ = _provedor(tmp_path, monkeypatch, COLETA)
    no_dia = datetime(
        2026, 10, 15, 16, tzinfo=UTC
    )  # a única data-base é a do próprio dia
    registro = provedor.registro(no_dia, None, coleta=COLETA)
    assert registro == {"abstencao": "cesta vazia: nenhum título elegível"}


def test_historico_com_conteudo_alterado_abstem(tmp_path, monkeypatch):
    provedor, _ = _provedor(tmp_path, monkeypatch, COLETA)
    caminho = tmp_path / "macro" / "tesouro" / "precotaxatesourodireto.csv"
    provedor.registro(D, JANELA, coleta=COLETA)  # grava a proveniência
    caminho.write_text(CSV.replace("6,82", "9,99"), encoding="utf-8")
    os.utime(caminho, (COLETA.timestamp(), COLETA.timestamp()))
    assert provedor.registro(D, JANELA, coleta=COLETA) == {
        "abstencao": "conteúdo diverge da proveniência"
    }


class _Agora(datetime):
    @classmethod
    def now(cls, tz=None):
        return COLETA.astimezone(tz) if tz else COLETA.replace(tzinfo=None)


def test_get_taxa_real_le_do_banco_so_para_dia_anterior(monkeypatch):
    """F3-1c: data de dia anterior pelo `series_macro`; o mesmo dia pelo caminho de hoje."""
    chamadas = []
    monkeypatch.setattr(config, "datetime", _Agora)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    monkeypatch.setattr(
        config,
        "_carregar_taxa_real",
        lambda instante, janela, coleta=None: (
            chamadas.append(("hoje", instante)) or {"x": 1}
        ),
    )
    monkeypatch.setattr(
        config,
        "_taxa_real_do_banco",
        lambda instante, janela: chamadas.append(("banco", instante)) or {"x": 1},
    )
    config.get_taxa_real(as_of=D)
    hoje = datetime(2026, 11, 11, 10, tzinfo=UTC)
    config.get_taxa_real(as_of=hoje)
    config._taxa_real_cache.clear()  # mesmo dia de `hoje`: sem o cache, chama de novo
    config.get_taxa_real()
    assert chamadas == [("banco", D), ("hoje", hoje), ("hoje", COLETA)]


def test_ponta_a_ponta_ate_gordon_e_fii(tmp_path, monkeypatch):
    """CSV e fixtures oficiais → provedor → get_taxa_real(as_of passado) → Gordon e FII."""
    from unittest.mock import patch

    from apoio_bazin import enriquecer_bazin
    from apoio_escopo import de_empresa
    from apoio_fii import enriquecer_fii
    from apoio_gordon import AS_OF_GORDON, DiaGordon, enriquecer_gordon

    from fii_engine import FIIEngine
    from valuation_engine import ValuationEngine

    provedor, _ = _provedor(tmp_path, monkeypatch, COLETA)
    monkeypatch.setattr(config, "datetime", _Agora)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    # o caminho histórico do provedor (F3-1c-a); a leitura pelo banco é do test_series_macro
    monkeypatch.setattr(
        config,
        "_taxa_real_do_banco",
        lambda instante, janela: provedor.registro(instante, janela, coleta=COLETA),
    )
    registro = config.get_taxa_real(as_of=AS_OF_GORDON, janela=JANELA)
    assert registro["coleta"] == COLETA.isoformat()
    assert registro["as_of"] == AS_OF_GORDON.isoformat()

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
    gordon = acoes["lentes"]["Gordon"]
    assert gordon["valor"] is not None, gordon
    # a lente usa a NTN-B histórica: outra taxa muda o valor
    outra = {
        **registro,
        "ntnb": registro["ntnb"] + 0.01,
        "custo_capital_real": registro["custo_capital_real"] + 0.01,
    }
    with patch("valuation_engine.date", DiaGordon):
        mudado = ValuationEngine().processar(
            de_empresa({**dados, "taxa_real": outra}), as_of=AS_OF_GORDON
        )
    assert mudado["lentes"]["Gordon"]["valor"] != gordon["valor"]

    fii = enriquecer_fii(
        {"ticker": "TSTI11", "preco_atual": 100.0, "dy": 0.09, "pvp": 1.0}
    )
    fii["taxa_real"] = registro
    resultado = FIIEngine().analisar(fii, as_of=AS_OF_GORDON)
    lente = next(iter(resultado["lentes"].values()))
    assert lente.get("valor") is not None, lente
    fii_outra = FIIEngine().analisar({**fii, "taxa_real": outra}, as_of=AS_OF_GORDON)
    assert next(iter(fii_outra["lentes"].values()))["valor"] != lente["valor"]


# --- contrato fino do caminho histórico (mutação do F3-1c-a) ---------------------------


def _arquivo(tmp_path, texto, coleta=COLETA, bom=False):
    caminho = tmp_path / "t" / "precotaxatesourodireto.csv"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes((b"\xef\xbb\xbf" if bom else b"") + texto.encode("utf-8"))
    os.utime(caminho, (coleta.timestamp(), coleta.timestamp()))
    return tesouro.TesouroProvider(tmp_path / "t")._snapshot(caminho)


def test_ler_historico_sem_proveniencia_recusa(tmp_path):
    arquivo = _arquivo(tmp_path, CSV)
    sem = tesouro.ArquivoTesouro(arquivo.caminho, None)
    with pytest.raises(ValueError, match="^proveniência ausente$"):
        tesouro.ler_historico(sem, as_of=D)


def test_ler_historico_le_arquivo_com_bom(tmp_path):
    titulos = tesouro.ler_historico(_arquivo(tmp_path, CSV, bom=True), as_of=D)
    assert {t.nome for t in titulos} >= {
        "Tesouro IPCA+ com Juros Semestrais",
        "Tesouro IPCA+",
    }


def test_ler_historico_preserva_linha_invalida_de_outro_titulo(tmp_path):
    """Como o download, o histórico não descarta o arquivo por uma linha fora da cesta."""
    texto = (
        CSV + "Tesouro Prefixado;01/01/2031;15/10/2026;x;12,00;700,00;700,00;700,00\n"
    )
    titulos = tesouro.ler_historico(_arquivo(tmp_path, texto), as_of=D)
    assert any(t.nome == "Tesouro IPCA+ com Juros Semestrais" for t in titulos)


def test_ipca_publicado_na_propria_data_de_referencia():
    assert mpd.ipca_publicado(
        date(2025, 6, 1), date(2025, 6, 1), date(2025, 6, 1), None
    )


def test_calendario_com_datas_iguais_nao_e_crescente():
    assert not mpd.calendario_crescente(
        {"202501": date(2025, 2, 11), "202502": date(2025, 2, 11)}
    )
    assert mpd.calendario_crescente(
        {"202501": date(2025, 2, 11), "202502": date(2025, 3, 12)}
    )


def test_publicacoes_ipca_falha_da_fonte_traz_o_motivo(tmp_path, monkeypatch):
    provedor = macro.MacroProvider(cache_dir=tmp_path)

    def fora(url, instante):
        raise OSError("IBGE fora do ar")

    monkeypatch.setattr(provedor, "baixar", fora)
    assert provedor.publicacoes_ipca(COLETA) == {"abstencao": "IBGE fora do ar"}

    def quebrado(url, instante):
        raise KeyError("items")

    monkeypatch.setattr(provedor, "baixar", quebrado)
    motivo = provedor.publicacoes_ipca(COLETA)["abstencao"]
    assert (
        motivo.startswith("erro inesperado no provedor macro") and "KeyError" in motivo
    )


def test_macro_context_sem_calendario_abstem_e_com_calendario_registra_a_agenda():
    from types import SimpleNamespace

    from config import MacroContext

    obs = tuple(mpd.Observacao(date(2025, mes, 1), 0.4) for mes in range(1, 13))
    serie = lambda *a: {"observacoes": obs, "coleta": date(2026, 11, 10)}
    sem = SimpleNamespace(
        serie_sgs=serie,
        publicacoes_ipca=lambda instante: {"abstencao": "calendário fora"},
    )
    contexto = MacroContext(as_of=date(2026, 3, 1), provedor=sem, instante=COLETA)
    assert contexto.registro_por_data("ipca_12m") == {"abstencao": "calendário fora"}
    agenda = {
        "publicacoes": {"202512": date(2026, 1, 9)},
        "proveniencia": {"fonte": "IBGE"},
    }
    com = SimpleNamespace(serie_sgs=serie, publicacoes_ipca=lambda instante: agenda)
    contexto = MacroContext(as_of=date(2026, 3, 1), provedor=com, instante=COLETA)
    registro = contexto.registro_por_data("ipca_12m")
    assert registro["calendario"] == {"fonte": "IBGE"}
    assert registro["data"] == date(2025, 12, 1)


def test_get_taxa_real_leva_a_janela_nos_dois_caminhos(monkeypatch):
    janelas = []
    monkeypatch.setattr(config, "datetime", _Agora)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    monkeypatch.setattr(
        config,
        "_carregar_taxa_real",
        lambda instante, janela, coleta=None: janelas.append(janela) or {"x": 1},
    )
    monkeypatch.setattr(
        config,
        "_taxa_real_do_banco",
        lambda instante, janela: janelas.append(janela) or {"x": 1},
    )
    config.get_taxa_real(as_of=D, janela=JANELA)
    config.get_taxa_real(as_of=datetime(2026, 11, 11, 10, tzinfo=UTC), janela=JANELA)
    assert janelas == [JANELA, JANELA]


def test_ipca_12m_de_hoje_nao_depende_do_calendario():
    """Revisão do F3-1c-a: na data da coleta, a falha do IBGE não derruba o IPCA de hoje."""
    from types import SimpleNamespace

    from config import MacroContext

    obs = tuple(mpd.Observacao(date(2025, mes, 1), 0.4) for mes in range(1, 13))
    provedor = SimpleNamespace(
        serie_sgs=lambda *a: {"observacoes": obs, "coleta": date(2026, 3, 1)},
        publicacoes_ipca=lambda instante: pytest.fail(
            "calendário não é preciso na coleta"
        ),
    )
    contexto = MacroContext(as_of=date(2026, 3, 1), provedor=provedor, instante=COLETA)
    assert contexto.registro_por_data("ipca_12m")["data"] == date(2025, 12, 1)
