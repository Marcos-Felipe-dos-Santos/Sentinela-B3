"""
auditar_recomendacoes.py — Auditoria de recomendações para diagnóstico de falsos positivos.

Analisa uma lista fixa de tickers (distressed, quality, cyclical, FIIs) e gera
um log detalhado identificando recomendações potencialmente inconsistentes.

Uso:
    python auditar_recomendacoes.py
"""

import logging
import os
import sys
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional

import pandas as pd

from market_engine import MarketEngine
from valuation_engine import ValuationEngine
from fii_engine import FIIEngine
from technical_engine import TechnicalEngine
from sentinela.services.asset_classifier import AssetClassifier

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

TICKERS_AUDITORIA: List[str] = [
    "AMER3", "OIBR3", "MGLU3", "CASH3", "VIIA3",
    "PETR4", "VALE3", "ITUB4", "WEGE3", "BBAS3",
    "HGLG11", "MXRF11", "CVBI11",
]

# ── Buckets de sanidade ──────────────────────────────────────────────────────
HIGH_RISK_SHOULD_NOT_BE_STRONG_BUY = ["AMER3", "OIBR3", "CASH3", "VIIA3"]
QUALITY_CAN_BE_BUY = ["ITUB4", "BBAS3", "WEGE3"]
CYCLICAL_NEEDS_CAUTION = ["PETR4", "VALE3"]
FIIS = ["HGLG11", "MXRF11", "CVBI11"]

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "auditoria_recomendacoes.txt")

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger("Auditoria")


def _fmt(val, fmt_str: str = ".4f") -> str:
    """Formata valor numérico de forma segura."""
    if val is None:
        return "N/A"
    try:
        return f"{float(val):{fmt_str}}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_bool(val) -> str:
    """Formata booleanos como Sim/Não para o relatório."""
    return "Sim" if bool(val) else "Não"


def _historico_disponivel(dados: Optional[Dict[str, Any]]) -> bool:
    if not dados:
        return False
    hist = dados.get('historico')
    return hist is not None and not getattr(hist, 'empty', True)


def classificar_qualidade_dados(dados: Optional[Dict[str, Any]]) -> str:
    """Classifica dados para a metrica de falha da auditoria."""
    if not dados or not dados.get('preco_atual'):
        return "no_data"
    if not _historico_disponivel(dados) and not dados.get('fonte_preco'):
        return "no_data"
    if dados.get('campos_faltantes') or dados.get('dados_parciais'):
        return "partial"
    return "full"


def calcular_metricas_dados(amostras: List[Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    """Calcula taxa de falha sem penalizar erro_scraper quando dados estao completos."""
    total = len(amostras)
    full_data_count = 0
    partial_data_count = 0
    no_data_count = 0

    for dados in amostras:
        status = classificar_qualidade_dados(dados)
        if status == "full":
            full_data_count += 1
        elif status == "partial":
            partial_data_count += 1
        else:
            no_data_count += 1

    failure_rate_percent = (
        round(((partial_data_count + no_data_count) / total) * 100, 1)
        if total else 0.0
    )
    return {
        "total_tickers_analyzed": total,
        "full_data_count": full_data_count,
        "partial_data_count": partial_data_count,
        "no_data_count": no_data_count,
        "failure_rate_percent": failure_rate_percent,
    }


def _excluir_da_taxa_operacional(registro: Dict[str, Any]) -> bool:
    dados = registro.get("dados")
    analise = registro.get("analise") or {}

    if classificar_qualidade_dados(dados) == "no_data":
        return True
    if analise.get("perfil") == "DISTRESSED":
        return True
    if analise.get("recomendacao") == "ALTO RISCO — EVITAR":
        return True
    return False


def calcular_metricas_operacionais(registros: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula falha apenas no universo operacionalmente analisavel."""
    operacionais = [
        registro for registro in registros
        if not _excluir_da_taxa_operacional(registro)
    ]
    metricas = calcular_metricas_dados([
        registro.get("dados") for registro in operacionais
    ])
    metricas["excluded_count"] = len(registros) - len(operacionais)
    return metricas


# ══════════════════════════════════════════════════════════════════════════════
# AUDITORIA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def auditar() -> str:
    """Executa a auditoria completa e retorna o log como string."""

    output = StringIO()

    def log(msg: str = "") -> None:
        """Escreve tanto no stdout quanto no buffer."""
        print(msg)
        output.write(msg + "\n")

    # ── Engines ──────────────────────────────────────────────────────────────
    market = MarketEngine()
    val_engine = ValuationEngine()
    fii_engine = FIIEngine()
    tech_engine = TechnicalEngine()
    asset_classifier = AssetClassifier()

    log("=" * 80)
    log(f"  AUDITORIA DE RECOMENDAÇÕES — Sentinela B3")
    log(f"  Executado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 80)

    alertas_totais: List[str] = []
    amostras_dados: List[Optional[Dict[str, Any]]] = []
    registros_operacionais: List[Dict[str, Any]] = []

    for ticker in TICKERS_AUDITORIA:
        log("")
        log("─" * 80)
        log(f"  TICKER: {ticker}")
        log("─" * 80)

        registrou_metrica = False
        try:
            # ── 1. Buscar dados ──────────────────────────────────────────────
            dados = market.buscar_dados_ticker(ticker)
            if not dados or not dados.get('preco_atual'):
                amostras_dados.append(dados)
                registros_operacionais.append({
                    "ticker": ticker,
                    "dados": dados,
                    "analise": None,
                })
                registrou_metrica = True
                log(f"  [ERRO] {ticker}: Sem dados de mercado disponíveis.")
                alertas_totais.append(f"{ticker}: SEM DADOS")
                continue
            amostras_dados.append(dados)
            registrou_metrica = True

            erro_scraper = bool(dados.get("erro_scraper", False))
            preco = float(dados.get('preco_atual', 0) or 0)

            # ── 2. Análise (FII ou Ação) ─────────────────────────────────────
            is_fii = asset_classifier.is_fii(ticker, dados)

            if is_fii:
                analise = fii_engine.analisar(dados)
            else:
                analise = val_engine.processar(dados)

            if analise is None:
                registros_operacionais.append({
                    "ticker": ticker,
                    "dados": dados,
                    "analise": None,
                })
                log(f"  [ERRO] {ticker}: Engine retornou None (dados insuficientes).")
                alertas_totais.append(f"{ticker}: ANÁLISE NULA")
                continue
            registros_operacionais.append({
                "ticker": ticker,
                "dados": dados,
                "analise": analise,
            })

            # ── 3. Técnica ───────────────────────────────────────────────────
            hist = dados.get('historico', pd.DataFrame())
            tech = tech_engine.calcular_indicadores(hist)

            # ── 4. Extrair campos ────────────────────────────────────────────
            rec = analise.get('recomendacao', 'N/A')
            fair_value = analise.get('fair_value', 0)
            upside = analise.get('upside', 0)
            score = analise.get('score_final', 0)
            confianca = analise.get('confianca', 100)
            riscos = analise.get('riscos', [])
            perfil = analise.get('perfil', 'N/A')
            metodos = analise.get('metodos_usados', 'N/A')

            dy = float(dados.get('dy', 0) or 0)
            pl = float(dados.get('pl', 0) or 0)
            pvp = float(dados.get('pvp', 0) or 0)
            roe = float(dados.get('roe', 0) or 0)
            divida = dados.get('divida_liq_ebitda', 'N/A')

            tendencia = tech.get('tendencia', 'N/A')
            rsi = tech.get('rsi', 'N/A')
            macd_rec = tech.get('macd_rec', 'N/A')
            hist_audit = dados.get('historico', pd.DataFrame())
            dados_yfinance = hist_audit is not None and not hist_audit.empty

            # ── 5. Imprimir debug completo ───────────────────────────────────
            log(f"  Tipo:            {'FII' if is_fii else 'AÇÃO'}")
            log(f"  Preço:           R$ {_fmt(preco, '.2f')}")
            log(f"  Recomendação:    {rec}")
            log(f"  Fair Value:      R$ {_fmt(fair_value, '.2f')}")
            log(f"  Upside:          {_fmt(upside, '.1f')}%")
            log(f"  Score:           {score}/100")
            log(f"  Confiança:       {confianca}")
            log(f"  Riscos:          {riscos if riscos else '(nenhum)'}")
            log(f"  Perfil:          {perfil}")
            log(f"  Métodos:         {metodos}")
            log(f"  ──────────────── Fundamentalista ────────────────")
            log(f"  DY:              {_fmt(dy)}")
            log(f"  P/L:             {_fmt(pl, '.2f')}")
            log(f"  P/VP:            {_fmt(pvp, '.2f')}")
            log(f"  ROE:             {_fmt(roe)}")
            log(f"  Dív.Líq/EBITDA:  {divida}")
            log(f"  ──────────────── Técnica ────────────────────────")
            log(f"  Tendência:       {tendencia}")
            log(f"  RSI:             {rsi}")
            log(f"  MACD Rec:        {macd_rec}")
            log(f"  ──────────────── Dados ──────────────────────────")
            log(f"  Fonte Preço:     {dados.get('fonte_preco', 'N/A')}")
            log(f"  Fonte Fund.:     {dados.get('fonte_fundamentos', 'N/A')}")
            log(f"  Erro Scraper:    {_fmt_bool(erro_scraper)}")
            log(f"  Dados Parciais:  {_fmt_bool(dados.get('dados_parciais', False))}")
            log(f"  Dados Cache:     {_fmt_bool(dados.get('dados_cache', False))}")
            log(f"  Dados Manual:    {_fmt_bool(dados.get('dados_manual', False))}")
            log(f"  Campos Falt.:    {dados.get('campos_faltantes', [])}")
            log(f"  Riscos Dados:    {dados.get('riscos_dados', [])}")
            log(f"  Dados yfinance:  {_fmt_bool(dados_yfinance)}")

            # ── 6. Validação de sanidade ─────────────────────────────────────
            alertas_ticker: List[str] = []

            # Regra 1: High-risk não deve ser COMPRA/COMPRA FORTE
            if ticker in HIGH_RISK_SHOULD_NOT_BE_STRONG_BUY and rec in ("COMPRA", "COMPRA FORTE"):
                alertas_ticker.append(
                    f"⚠ FALSO POSITIVO: {ticker} é high-risk mas recebeu '{rec}'"
                )

            # Regra 2: Confiança baixa + COMPRA FORTE
            if confianca < 60 and rec == "COMPRA FORTE":
                alertas_ticker.append(
                    f"⚠ CONFIANÇA BAIXA ({confianca}) com COMPRA FORTE"
                )

            # Regra 3: Riscos presentes + COMPRA FORTE
            if riscos and rec == "COMPRA FORTE":
                alertas_ticker.append(
                    f"⚠ RISCOS PRESENTES ({len(riscos)}) com COMPRA FORTE: {riscos}"
                )

            # Regra 4: Erro de scraper + recomendação positiva
            if erro_scraper and rec in ("COMPRA", "COMPRA FORTE"):
                alertas_ticker.append(
                    f"⚠ SCRAPER FALHOU mas recomendação é '{rec}'"
                )

            # Regra 5: PL <= 0 + recomendação positiva (empresa com prejuízo)
            if pl <= 0 and rec in ("COMPRA", "COMPRA FORTE"):
                alertas_ticker.append(
                    f"⚠ PL ≤ 0 (prejuízo/sem lucro) mas recomendação é '{rec}'"
                )

            # Regra 6: DY = 0 + COMPRA FORTE
            if dy == 0 and rec == "COMPRA FORTE":
                alertas_ticker.append(
                    f"⚠ DY = 0 (sem dividendos) com COMPRA FORTE"
                )

            # Regra 7: FII com vacância alta + COMPRA FORTE
            if is_fii and rec == "COMPRA FORTE":
                vacancia = dados.get('vacancia')
                if vacancia is not None and float(vacancia) > 0.15:
                    alertas_ticker.append(
                        f"⚠ FII com vacância alta ({float(vacancia)*100:.0f}%) e COMPRA FORTE"
                    )

            # ── 7. Imprimir alertas ──────────────────────────────────────────
            if alertas_ticker:
                log(f"  ╔══════════════════════════════════════════════════╗")
                log(f"  ║  🚨 ALERTAS DE SANIDADE                        ║")
                log(f"  ╚══════════════════════════════════════════════════╝")
                for alerta in alertas_ticker:
                    log(f"  {alerta}")
                alertas_totais.extend(
                    f"{ticker}: {a}" for a in alertas_ticker
                )
            else:
                log(f"  ✅ Nenhum alerta de sanidade.")

        except Exception as e:
            if not registrou_metrica:
                amostras_dados.append(None)
                registros_operacionais.append({
                    "ticker": ticker,
                    "dados": None,
                    "analise": None,
                })
            log(f"  [ERRO] {ticker}: {e}")
            alertas_totais.append(f"{ticker}: EXCEÇÃO — {e}")

    # ── Resumo final ─────────────────────────────────────────────────────────
    metricas_dados = calcular_metricas_dados(amostras_dados)
    metricas_operacionais = calcular_metricas_operacionais(registros_operacionais)
    log("")
    log("=" * 80)
    log(f"  RESUMO DA AUDITORIA")
    log("=" * 80)
    log(f"  Tickers analisados: {metricas_dados['total_tickers_analyzed']}")
    log(f"  full_data_count:    {metricas_dados['full_data_count']}")
    log(f"  partial_data_count: {metricas_dados['partial_data_count']}")
    log(f"  no_data_count:      {metricas_dados['no_data_count']}")
    log(f"  Taxa geral de falha: {metricas_dados['failure_rate_percent']:.1f}%")
    log("")
    log(f"  Tickers operacionais: {metricas_operacionais['total_tickers_analyzed']}")
    log(f"  operational_full_data_count:    {metricas_operacionais['full_data_count']}")
    log(f"  operational_partial_data_count: {metricas_operacionais['partial_data_count']}")
    log(f"  operational_no_data_count:      {metricas_operacionais['no_data_count']}")
    log(f"  Excluídos da taxa operacional:  {metricas_operacionais['excluded_count']}")
    log(f"  Taxa operacional de falha: {metricas_operacionais['failure_rate_percent']:.1f}%")
    log(f"  Alertas totais:     {len(alertas_totais)}")
    log("")

    if alertas_totais:
        log("  Alertas:")
        for i, alerta in enumerate(alertas_totais, 1):
            log(f"    {i}. {alerta}")
    else:
        log("  ✅ Nenhum alerta detectado.")

    log("")
    log(f"  Log salvo em: {os.path.abspath(LOG_FILE)}")
    log("=" * 80)

    return output.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Windows: forçar UTF-8 no stdout para evitar UnicodeEncodeError com cp1252
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    os.makedirs(LOG_DIR, exist_ok=True)

    resultado = auditar()

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(resultado)

    print(f"\nAuditoria concluida. Log: {os.path.abspath(LOG_FILE)}")
