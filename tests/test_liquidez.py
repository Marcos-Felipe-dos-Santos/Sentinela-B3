"""Liquidez pelo COTAHIST (F2A-26; insumo da [LIQUIDEZ], que é da 2B).

Linhas sintéticas montadas pelo layout oficial das Séries Históricas da B3 (registro 01),
como no F2A-18. Volume financeiro e negócios por dia, somados por código; dia sem negócio
conta zero; presença = pregões com negócio no ticker ÷ pregões do arquivo na janela.
"""

from datetime import date, timedelta

import pytest

from sentinela.data.providers import b3_cotahist as cot
from tests.test_cotahist import _linha


def _cotacoes(
    dias, ticker="ABCD3", volume_centavos=100_000, negocios=10, sem_negocio=()
):
    """Um pregão por dia útil sintético; outro papel negocia todo dia (define os pregões)."""
    linhas = []
    for i in range(dias):
        dia = (date(2026, 1, 1) + timedelta(days=i)).strftime("%Y%m%d")
        linhas.append(
            _linha(DATA=dia, CODNEG="OUTR3", VOLTOT=f"{1:018d}", TOTNEG="00001")
        )
        if i not in sem_negocio:
            linhas.append(
                _linha(
                    DATA=dia,
                    CODNEG=ticker,
                    VOLTOT=f"{volume_centavos * (i + 1):018d}",
                    TOTNEG=f"{negocios:05d}",
                )
            )
    return list(cot.parsear_linhas(linhas))


def test_mediana_do_volume():
    from sentinela.data import liquidez

    # 21 pregões, volume do dia i = 1.000 × (i + 1) reais: mediana do 11º = 11.000; média idem.
    resultado = liquidez.metricas(_cotacoes(21), "ABCD3")
    janela = resultado["janelas"]["21"]
    assert janela["volume_mediano"] == pytest.approx(11_000.0)
    assert janela["volume_medio"] == pytest.approx(11_000.0)
    assert janela["negocios_mediana"] == 10
    assert janela["pregoes"] == 21
    assert resultado["data_final"] == "2026-01-21"
    assert resultado["fonte"] == liquidez.FONTE


def test_presenca_conta_pregoes_sem_negocio():
    from sentinela.data import liquidez

    # Sem negócio em 5 dos 21 pregões: presença 16/21, e os dias vazios contam zero.
    sem = {0, 1, 2, 3, 4}
    resultado = liquidez.metricas(_cotacoes(21, sem_negocio=sem), "ABCD3")
    janela = resultado["janelas"]["21"]
    assert janela["presenca"] == pytest.approx(16 / 21)
    volumes = [0.0] * 5 + [1_000.0 * (i + 1) for i in range(5, 21)]
    assert janela["volume_medio"] == pytest.approx(sum(volumes) / 21)
    assert janela["volume_mediano"] == pytest.approx(sorted(volumes)[10])
    assert janela["negocios_mediana"] == 10


def test_janela_de_63_pregoes():
    from sentinela.data import liquidez

    resultado = liquidez.metricas(_cotacoes(70), "ABCD3")
    janela = resultado["janelas"]["63"]
    # Os 63 últimos pregões: dias 8 a 70 (volume 8.000 a 70.000); mediana = 39.000.
    assert janela["pregoes"] == 63
    assert janela["volume_mediano"] == pytest.approx(39_000.0)
    assert janela["presenca"] == 1.0
    assert resultado["janelas"]["21"]["volume_mediano"] == pytest.approx(60_000.0)
    # Com menos pregões que a janela, ela vem marcada como incompleta.
    curto = liquidez.metricas(_cotacoes(30), "ABCD3")["janelas"]["63"]
    assert curto["pregoes"] == 30 and curto["incompleta"] is True


# ── leitor dos meses recentes, cascata, prompt e relatório ───────────────────


def test_meses_ate_vira_o_ano():
    assert cot.meses_ate(2026, 10, 4) == [(2026, 7), (2026, 8), (2026, 9), (2026, 10)]
    assert cot.meses_ate(2026, 2, 3) == [(2025, 12), (2026, 1), (2026, 2)]


def _zip(caminho, linhas):
    import zipfile

    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("COTAHIST.TXT", "\n".join(linhas).encode("latin-1"))
    return caminho


def test_leitura_em_cache_e_invalidada_por_arquivo_novo(tmp_path):
    import os

    caminho = _zip(tmp_path / "c.zip", [_linha(CODNEG="ABCD3")])
    primeira = cot.ler_zip_em_cache(caminho)
    assert cot.ler_zip_em_cache(caminho) is primeira
    _zip(caminho, [_linha(CODNEG="ABCD3"), _linha(CODNEG="EFGH3")])
    os.utime(caminho, ns=(1, 1))  # outro mtime e outro tamanho: entrada nova
    assert len(cot.ler_zip_em_cache(caminho)) == 2


def test_historico_recente_junta_os_meses_e_pula_o_que_falta(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    arquivos = {
        (2026, 9): _zip(
            tmp_path / "set.zip", [_linha(DATA="20260930", CODNEG="ABCD3")]
        ),
        (2026, 10): _zip(
            tmp_path / "out.zip", [_linha(DATA="20261001", CODNEG="ABCD3")]
        ),
    }
    pedidos = []

    def baixar(ano, mes, agora, cache_dir, *, permitir_cache_antigo=True):
        pedidos.append((ano, mes))
        if (ano, mes) not in arquivos:
            raise OSError("sem arquivo")
        return arquivos[(ano, mes)]

    monkeypatch.setattr(cot, "baixar_mes", baixar)
    agora = datetime(2026, 10, 13, 15, tzinfo=UTC)
    coleta = cot.HistoricoRecente(cache_dir=tmp_path, meses=3).coletar(agora)
    assert pedidos == [(2026, 8), (2026, 9), (2026, 10)]
    assert [c.data for c in coleta.cotacoes] == [date(2026, 9, 30), date(2026, 10, 1)]
    assert coleta.meses_ausentes == ("08/2026",)


def test_cascata_grava_a_liquidez_fora_do_prompt(monkeypatch):
    from ai_core import SentinelaAI
    from sentinela.data import liquidez
    from tests.test_market_engine import _engine, _historico

    class _Historico:
        def coletar(self, agora):
            return cot.Coleta(_cotacoes(21, ticker="PETR4"), ())

    engine = _engine(
        monkeypatch, info={"currentPrice": 20.0}, historico=_historico(20.0)
    )
    engine.cotahist = _Historico()
    dados = engine.buscar_dados_ticker("PETR4")
    assert dados["liquidez"]["janelas"]["21"]["volume_mediano"] == pytest.approx(
        11_000.0
    )
    assert dados["liquidez"]["fonte"] == liquidez.FONTE

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GROQ_API_KEY", "")
        mp.setenv("GEMINI_API_KEY", "")
        assert "liquidez" not in SentinelaAI()._formatar_dados(dados)

    class _Vazio:
        def coletar(self, agora):
            return cot.Coleta([], ("09/2026", "10/2026"))

    engine.cotahist = _Vazio()
    assert engine.buscar_dados_ticker("PETR4")["liquidez"] == {
        "abstencao": liquidez.MOTIVO_SEM_PREGOES,
        "meses_ausentes": ["09/2026", "10/2026"],
    }


def test_relatorio_mostra_a_liquidez():
    from fii_engine import FIIEngine
    from sentinela.data import liquidez
    from sentinela.reports import rastreabilidade
    from valuation_engine import ValuationEngine

    medida = liquidez.metricas(_cotacoes(30), "ABCD3")
    dados = {
        "ticker": "ABCD3",
        "preco_atual": 100.0,
        "pl": 10.0,
        "pvp": 1.5,
        "dy": 0.08,
        "liquidez": medida,
    }
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("valuation_engine.get_selic_atual", lambda: 0.145)
        contexto = rastreabilidade.construir_contexto(
            dados, False, date(2026, 10, 13), ValuationEngine(), FIIEngine()
        )
    texto = dict(contexto["fontes"])["Liquidez (63 pregões: presença ≥ 80%; mediana ≥ R$ 500 mil em ações/units e R$ 100 mil em FIIs)"]
    assert "21 pregões: volume mediano R$ 20.000,00/dia" in texto
    assert "63 pregões (incompleta)" in texto
    assert "presença 100,0%" in texto
    assert texto.endswith(f"até 2026-01-30 ({liquidez.FONTE})")


def test_ticker_ausente_do_arquivo_se_abstem():
    from sentinela.data import liquidez

    # "Não encontrado" não é "não negocia": sem nenhuma cotação, abstenção, não volume zero.
    resultado = liquidez.metricas(_cotacoes(21), "WXYZ3")
    assert resultado == liquidez.Abstencao(liquidez.MOTIVO_TICKER_AUSENTE)


def test_meses_ausentes_chegam_ao_resultado_e_ao_relatorio():
    from sentinela.data import liquidez
    from sentinela.reports.rastreabilidade import _texto_liquidez

    medida = liquidez.metricas(_cotacoes(21), "ABCD3", meses_ausentes=("08/2026",))
    assert medida["meses_ausentes"] == ["08/2026"]
    assert _texto_liquidez(medida).endswith("; meses ausentes na coleta: 08/2026")
    assert "meses ausentes" not in _texto_liquidez(
        liquidez.metricas(_cotacoes(21), "ABCD3")
    )
    texto = _texto_liquidez({"abstencao": "x", "meses_ausentes": ["09/2026"]})
    assert texto == "não calculada: x; meses ausentes na coleta: 09/2026"


def test_mes_que_falhou_nao_e_tentado_de_novo_por_uma_hora(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    arquivo = _zip(tmp_path / "out.zip", [_linha(DATA="20261001", CODNEG="ABCD3")])
    pedidos = []

    def baixar(ano, mes, agora, cache_dir, *, permitir_cache_antigo=True):
        pedidos.append((ano, mes))
        if mes == 9:
            raise OSError("fora do ar")
        return arquivo

    monkeypatch.setattr(cot, "baixar_mes", baixar)
    historico = cot.HistoricoRecente(cache_dir=tmp_path, meses=2)
    agora = datetime(2026, 10, 13, 15, tzinfo=UTC)
    assert historico.coletar(agora).meses_ausentes == ("09/2026",)
    assert historico.coletar(agora + timedelta(minutes=59)).meses_ausentes == (
        "09/2026",
    )
    assert pedidos == [
        (2026, 9),
        (2026, 10),
        (2026, 10),
    ]  # setembro não foi tentado de novo
    historico.coletar(agora + timedelta(seconds=cot.ESPERA_APOS_FALHA_S))
    assert pedidos[-2:] == [(2026, 9), (2026, 10)]


def test_trava_por_mes_nao_deixa_duas_threads_no_mesmo_arquivo(tmp_path, monkeypatch):
    import threading
    import time
    from datetime import UTC, datetime

    arquivo = _zip(tmp_path / "out.zip", [_linha(DATA="20261001", CODNEG="ABCD3")])
    ativos, maximo, trava = [0], [0], threading.Lock()

    def baixar(ano, mes, agora, cache_dir, *, permitir_cache_antigo=True):
        with trava:
            ativos[0] += 1
            maximo[0] = max(maximo[0], ativos[0])
        time.sleep(0.01)
        with trava:
            ativos[0] -= 1
        return arquivo

    monkeypatch.setattr(cot, "baixar_mes", baixar)
    historico = cot.HistoricoRecente(cache_dir=tmp_path, meses=1)
    agora = datetime(2026, 10, 13, 15, tzinfo=UTC)
    threads = [
        threading.Thread(target=historico.coletar, args=(agora,)) for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert maximo[0] == 1


def test_memoria_de_leitura_despeja_acima_do_limite(tmp_path, monkeypatch):
    monkeypatch.setattr(cot, "_cache_leitura", {})
    caminhos = [
        _zip(tmp_path / f"{i}.zip", [_linha(CODNEG="ABCD3")])
        for i in range(cot._CACHE_LEITURA_MAX + 1)
    ]
    primeira = cot.ler_zip_em_cache(caminhos[0])
    for caminho in caminhos[1:]:
        cot.ler_zip_em_cache(caminho)
    assert len(cot._cache_leitura) == cot._CACHE_LEITURA_MAX
    assert cot.ler_zip_em_cache(caminhos[0]) is not primeira  # o mais antigo saiu


def test_threads_na_fila_nao_repetem_o_download_que_falhou(tmp_path, monkeypatch):
    import threading
    import time
    from datetime import UTC, datetime

    pedidos, trava = [], threading.Lock()

    def baixar(ano, mes, agora, cache_dir, *, permitir_cache_antigo=True):
        with trava:
            pedidos.append((ano, mes))
        time.sleep(0.01)
        raise OSError("B3 fora do ar")

    monkeypatch.setattr(cot, "baixar_mes", baixar)
    historico = cot.HistoricoRecente(cache_dir=tmp_path, meses=1)
    agora = datetime(2026, 10, 13, 15, tzinfo=UTC)
    resultados = []
    threads = [
        threading.Thread(target=lambda: resultados.append(historico.coletar(agora)))
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert pedidos == [(2026, 10)]
    assert (
        all(r.meses_ausentes == ("10/2026",) for r in resultados)
        and len(resultados) == 8
    )
