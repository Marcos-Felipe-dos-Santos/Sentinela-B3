"""
SENTINELA B3 — SCRIPT DE AUDITORIA INTERNA
============================================
Expõe tudo que a UI esconde: dados brutos do scraper, os resultados e motivos do contrato
de valuation, o prompt exato enviado à IA, e o conteúdo real do banco.

Ao terminar, salva DOIS arquivos na mesma pasta:
  • auditoria_YYYYMMDD_HHMMSS.txt  — relatório legível (sem cores)
  • auditoria_YYYYMMDD_HHMMSS.json — dados estruturados para análise

Uso:
    python auditoria.py                  # audita PETR4, ITUB4, WEGE3
    python auditoria.py VALE3 BBAS3      # audita tickers específicos
    python auditoria.py --db-only        # só inspeciona o banco
    python auditoria.py --selic          # só testa a Selic
"""

import sys
import os
import re
import io
import json
import math
import logging
import sqlite3
from datetime import datetime

# ─── ANSI strip ───────────────────────────────────────────────────────────────
_ANSI = re.compile(r'\x1b\[[0-9;]*m')
def strip_ansi(s: str) -> str:
    return _ANSI.sub('', s)

# ─── Tee: imprime no terminal E captura em buffer limpo para arquivo ──────────
class _Tee:
    def __init__(self, stream):
        self._orig  = stream
        self._buf   = io.StringIO()

    def write(self, s):
        self._orig.write(s)
        self._buf.write(strip_ansi(s))

    def flush(self):
        self._orig.flush()

    def getvalue(self) -> str:
        return self._buf.getvalue()

# ─── cores no terminal ────────────────────────────────────────────────────────
GRN = "\033[32m"
RED = "\033[31m"
YLW = "\033[33m"
CYN = "\033[36m"
BLD = "\033[1m"
RST = "\033[0m"
ok   = lambda s: f"{GRN}✓ {s}{RST}"
err  = lambda s: f"{RED}✗ {s}{RST}"
warn = lambda s: f"{YLW}⚠ {s}{RST}"
hdr  = lambda s: f"\n{BLD}{CYN}{'═'*60}\n  {s}\n{'═'*60}{RST}"
sub  = lambda s: f"\n{BLD}── {s} ──{RST}"

DB_PATH = "sentinela_v6.db"

# ─── Relatório JSON (populado ao longo da execução) ───────────────────────────
_rel: dict = {
    "meta": {},
    "selic": {},
    "banco": {},
    "tickers": {}
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. SELIC
# ══════════════════════════════════════════════════════════════════════════════

def auditar_selic():
    print(hdr("1. TAXA SELIC"))
    import requests

    resultado = {}

    try:
        r = requests.get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json",
            timeout=5
        )
        if r.status_code == 200:
            valor_raw = r.json()[0]['valor']
            selic_432 = float(valor_raw) / 100
            resultado['serie_432_raw']    = valor_raw
            resultado['serie_432_decimal'] = selic_432
            resultado['serie_432_status'] = 'OK'
            print(ok(f"Série 432 (meta Copom): {valor_raw}% a.a. → decimal: {selic_432:.4f}"))
        else:
            resultado['serie_432_status'] = f"HTTP {r.status_code}"
            print(err(f"Série 432: HTTP {r.status_code}"))
    except Exception as e:
        resultado['serie_432_status'] = str(e)
        print(err(f"Série 432 indisponível: {e}"))

    try:
        r2 = requests.get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados/ultimos/1?formato=json",
            timeout=5
        )
        if r2.status_code == 200:
            valor_raw2 = r2.json()[0]['valor']
            selic_11 = float(valor_raw2) / 100
            resultado['serie_11_raw']    = valor_raw2
            resultado['serie_11_decimal'] = selic_11
            print(warn(f"Série 11 (taxa diária — BUG antigo): {valor_raw2}% ao dia → "
                       f"se fosse usada: {selic_11*100:.4f}% a.a. (ERRADO)"))
    except Exception as e:
        resultado['serie_11_status'] = str(e)

    print("  Selic é contexto; esta auditoria não replica fórmulas de valuation.")

    _rel['selic'] = resultado


# ══════════════════════════════════════════════════════════════════════════════
# 2. DADOS BRUTOS DO SCRAPER
# ══════════════════════════════════════════════════════════════════════════════

def auditar_dados_scraper(ticker: str):
    print(hdr(f"2. DADOS BRUTOS — {ticker}"))

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from market_engine import MarketEngine
    except ImportError as e:
        print(err(f"Não foi possível importar market_engine: {e}"))
        return None

    market = MarketEngine()
    print(f"  Buscando dados de {ticker}...")
    dados = market.buscar_dados_ticker(ticker)

    if not dados:
        print(err("Nenhum dado retornado."))
        return None

    hist = dados.pop('historico', None)

    print(sub("Dados Fundamentalistas"))
    campos_importantes = ['ticker','preco_atual','pl','pvp','dy','roe','roic',
                          'margem_liquida','margem_bruta','div_liq_patrimonio',
                          'patrimonio_liquido','receita_liquida','lucro_liquido',
                          'quote_type','pl_confiavel']

    dados_json = {}
    for campo in campos_importantes:
        val = dados.get(campo)
        dados_json[campo] = val
        if val is not None:
            if campo == 'quote_type':
                # Classificação do ativo pelo Yahoo — chave para FII vs ação
                tipo_map = {
                    'MUTUALFUND': (ok,   'FII / Fundo Imobiliário → engine FII será usado'),
                    'EQUITY':     (ok,   'Ação/Unit → engine Valuation será usado'),
                    'ETF':        (warn, 'ETF → engine FII será usado (fallback)'),
                }
                fn_cor, desc = tipo_map.get(val, (warn, f'Tipo desconhecido: {val}'))
                print(f"  {campo:<25}: {fn_cor(f'{val} — {desc}')}")
            elif campo in ['dy','roe','roic','margem_liquida','margem_bruta'] and isinstance(val, float):
                # Avisar se DY parece estar em formato percentagem (não decimal)
                if campo == 'dy' and val > 0.5:
                    msg = (
                        f"{val} — FORMATO % (>50%)! Yahoo retornou em % "
                        "em vez de decimal. Valuation engine vai normalizar."
                    )
                    print(f"  {campo:<25}: {warn(msg)}")
                elif campo == 'dy' and val > 0.04:
                    msg = "Verificar: DY>4% sendo tratado como is_growth=False"
                    print(
                        f"  {campo:<25}: {val*100:.2f}%  "
                        f"(decimal: {val:.4f})  {warn(msg)}"
                    )
                else:
                    print(f"  {campo:<25}: {val*100:.2f}%  (decimal: {val:.4f})")
            elif campo == 'preco_atual':
                # Float64 artifact indica que o preço veio do Yahoo, não do Fundamentus
                preco_str = str(val)
                fonte = warn("Yahoo Finance (Fundamentus falhou)") if len(preco_str) > 10 else ok("Fundamentus")
                print(f"  {campo:<25}: R$ {val:.2f}  ← fonte: {fonte}")
            else:
                print(f"  {campo:<25}: {val}")
        else:
            print(f"  {campo:<25}: {warn('AUSENTE')}")

    extras = {k: v for k, v in dados.items() if k not in campos_importantes and v is not None}
    if extras:
        print(sub("Campos adicionais"))
        for k, v in extras.items():
            exibido = resumo_serie(v) if k == "serie_cvm" else v
            dados_json[k] = exibido
            print(f"  {k:<25}: {exibido}")

    hist_json = {}
    if hist is not None and not hist.empty:
        print(sub("Histórico"))
        print(f"  Período: {hist.index[0].date()} → {hist.index[-1].date()}")
        print(f"  Pregões: {len(hist)}")
        print(f"  Preço mín/máx 1 ano: R${hist['Close'].min():.2f} / R${hist['Close'].max():.2f}")
        print(f"  Preço atual (último Close): R${hist['Close'].iloc[-1]:.2f}")
        vol_anual = hist['Close'].pct_change().std() * (252**0.5)
        print(f"  Volatilidade anualizada: {vol_anual*100:.1f}%")
        hist_json = {
            "pregoes": len(hist),
            "inicio": str(hist.index[0].date()),
            "fim": str(hist.index[-1].date()),
            "preco_min_1a": round(float(hist['Close'].min()), 2),
            "preco_max_1a": round(float(hist['Close'].max()), 2),
            "preco_atual_close": round(float(hist['Close'].iloc[-1]), 2),
            "volatilidade_anual_pct": round(vol_anual * 100, 1),
        }
        dados['historico'] = hist
    else:
        print(warn("  Histórico indisponível."))

    if ticker not in _rel['tickers']:
        _rel['tickers'][ticker] = {}
    _rel['tickers'][ticker]['dados_scraper'] = dados_json
    _rel['tickers'][ticker]['historico']     = hist_json

    return dados


# ══════════════════════════════════════════════════════════════════════════════
# 3. VALUATION — CÁLCULO PASSO A PASSO
# ══════════════════════════════════════════════════════════════════════════════

def resumo_serie(serie: object) -> object:
    """Resume a cobertura sem despejar documentos ou listas de observações."""
    from dataclasses import asdict, is_dataclass

    if is_dataclass(serie):
        serie = asdict(serie)
    if isinstance(serie, dict):
        return {chave: resumo_serie(valor) for chave, valor in serie.items()}
    if isinstance(serie, (list, tuple)):
        return {"observacoes": len(serie)}
    return serie if isinstance(serie, (str, int, float, bool, type(None))) else type(serie).__name__


def invariantes_resultado(analise: dict) -> list[str]:
    """Domínios externos: finitude, score [0,100] e ausência sem número fabricado."""
    problemas = []
    for campo in ("fair_value", "upside", "score_final"):
        valor = analise.get(campo)
        if valor is not None and (
            isinstance(valor, bool) or not isinstance(valor, (int, float))
            or not math.isfinite(valor)
        ):
            problemas.append(f"{campo}: número não finito ou inválido")
    score = analise.get("score_final")
    if isinstance(score, (int, float)) and not 0 <= score <= 100:
        problemas.append("score_final: fora de [0,100]")
    if analise.get("fair_value") is None and analise.get("upside") is not None:
        problemas.append("upside presente sem valor da lente")
    return problemas


def auditar_valuation(ticker: str, dados: dict) -> tuple[float | None, float | None, dict]:
    """Usa a orquestração vigente e captura o contrato, sem repetir suas contas."""
    from dataclasses import asdict

    from sentinela.methods.registry import entradas
    from valuation_engine import ValuationEngine

    print(hdr(f"3. VALUATION PELO CONTRATO — {ticker}"))
    engine = ValuationEngine()
    avaliar = engine._avaliar_metodos
    resultados = {}

    def capturar(*args, **kwargs):
        resposta = avaliar(*args, **kwargs)
        resultados.update({nome: asdict(valor) for nome, valor in resposta.items()})
        return resposta

    engine._avaliar_metodos = capturar
    analise = engine.processar(dados)
    problemas = invariantes_resultado(analise)
    registro = [{"nome": e.nome, "version": e.version, "regime": str(e.regime)} for e in entradas()]
    resumo = resumo_serie(dados.get("serie_cvm"))
    print(f"  Série: {resumo}")
    for nome, resultado in resultados.items():
        print(f"  {nome}: {resultado}")
    print(f"  Invariantes: {problemas or 'domínios conferidos'}")
    _rel['tickers'].setdefault(ticker, {})['valuation'] = {
        "registro": registro, "metodos": resultados, "resultado": analise,
        "invariantes": problemas, "serie": resumo,
    }
    return analise.get("fair_value"), analise.get("upside"), analise


def auditar_fii(dados: dict) -> dict:
    """Mantém ausência e motivo inclusive se a fonte falhar."""
    from fii_engine import FIIEngine

    try:
        return FIIEngine().analisar(dados)
    except Exception as erro:
        logging.exception("Falha na auditoria do FII")
        return {"fair_value": None, "upside": None, "perfil": "FII",
                "motivo": f"FIIEngine indisponível no audit: {erro}"}


# ══════════════════════════════════════════════════════════════════════════════
# 4. ANÁLISE TÉCNICA
# ══════════════════════════════════════════════════════════════════════════════

def auditar_tecnica(ticker: str, dados: dict):
    print(hdr(f"4. ANÁLISE TÉCNICA — {ticker}"))
    hist = dados.get('historico')
    if hist is None or hist.empty:
        print(warn("  Histórico indisponível."))
        _rel['tickers'][ticker]['tecnica'] = {"disponivel": False}
        return

    close = hist['Close']
    n     = len(close)
    print(f"  Pregões: {n}")

    delta = close.diff()
    gain  = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss  = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs    = gain / loss.replace(0, float('nan'))
    rsi   = (100 - (100 / (1 + rs))).fillna(50).iloc[-1]

    ma50  = close.rolling(50).mean().iloc[-1]
    ma200 = close.rolling(200).mean().iloc[-1]
    preco = close.iloc[-1]

    ma50_ok  = not (ma50  != ma50)   # not NaN
    ma200_ok = not (ma200 != ma200)

    print(f"\n  RSI (14) : {rsi:.1f}  → {'Sobrecomprado' if rsi>70 else ('Sobrevendido' if rsi<30 else 'Neutro')}")
    print(f"  MA50     : {'R$ '+f'{ma50:.2f}'  if ma50_ok  else warn('NaN (< 50 pregões)')}")
    print(f"  MA200    : {'R$ '+f'{ma200:.2f}' if ma200_ok else warn('NaN (< 200 pregões)')}")
    print(f"  Preço    : R$ {preco:.2f}")

    if ma200_ok:
        tend = "Alta (Longo Prazo)" if preco > ma200 else "Baixa (Longo Prazo)"
    elif ma50_ok:
        tend = "Alta (Curto Prazo)" if preco > ma50  else "Baixa (Curto Prazo)"
    else:
        tend = "Indefinida"
    print(f"  Tendência: {tend}")

    _rel['tickers'][ticker]['tecnica'] = {
        "disponivel": True,
        "pregoes":    n,
        "rsi":        round(float(rsi), 1),
        "ma50":       round(float(ma50),  2) if ma50_ok  else None,
        "ma200":      round(float(ma200), 2) if ma200_ok else None,
        "preco":      round(float(preco), 2),
        "tendencia":  tend,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. PROMPT EXATO PARA A IA
# ══════════════════════════════════════════════════════════════════════════════

def auditar_prompt(ticker: str, dados: dict, fv: float = 0, upside: float = 0, analise_dict: dict = None):
    print(hdr(f"5. PROMPT ENVIADO À IA — {ticker}"))

    # Em produção: app.py faz dados.update(analise) ANTES de chamar ai_engine.analisar()
    # Simulamos aqui mesclando o dict de valuation no dados
    dados_simulados = dict(dados)
    if analise_dict:
        dados_simulados.update(analise_dict)

    excluir  = {'historico', 'analise_ia', 'tech', 'serie_cvm'}
    linhas   = [f"- {k}: {v}" for k, v in dados_simulados.items()
                if v is not None and k not in excluir]
    dados_txt = "\n".join(linhas)
    perfil    = dados_simulados.get('perfil', 'GERAL')

    prompt = f"""Analise a ação {ticker} (Perfil: {perfil}).

Dados Fundamentais:
{dados_txt}

Responda em Português com exatamente 3 tópicos:
1. Qualidade da empresa (Forte / Moderada / Fraca) — justifique com os dados acima.
2. Riscos principais — liste os 2-3 maiores riscos identificados.
3. Veredito final (Compra / Neutro / Venda) — justifique com base no valuation e qualidade."""

    print(f"\n  Tamanho: {len(prompt)} chars, {len(linhas)} campos enviados")
    print("\n  Campos enviados:")
    for l in linhas:
        print(f"    {l}")
    print(f"\n  ┌── PROMPT COMPLETO {'─'*40}")
    for l in prompt.split('\n'):
        print(f"  │ {l}")
    print(f"  └{'─'*59}")

    print(sub("Checklist de qualidade"))
    checks = [
        ('historico' not in '\n'.join(linhas), "Histórico excluído do prompt"),
        ('analise_ia' not in '\n'.join(linhas), "analise_ia anterior excluída"),
        (perfil != 'GERAL',                     f"Perfil definido: {perfil}"),
        (any('fair_value'   in l for l in linhas), "fair_value incluído"),
        (any('upside'       in l for l in linhas), "upside incluído"),
        (any('recomendacao' in l for l in linhas), "recomendacao incluída"),
    ]
    check_results = []
    for passou, desc in checks:
        print(f"  {'✓' if passou else '⚠'} {desc}")
        check_results.append({"ok": passou, "desc": desc})

    _rel['tickers'][ticker]['prompt'] = {
        "tamanho_chars":  len(prompt),
        "num_campos":     len(linhas),
        "perfil":         perfil,
        "campos_enviados": [l.lstrip('- ') for l in linhas],
        "prompt_completo": prompt,
        "checklist":      check_results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 6. BANCO DE DADOS
# ══════════════════════════════════════════════════════════════════════════════

def auditar_banco():
    print(hdr("6. BANCO DE DADOS"))

    if not os.path.exists(DB_PATH):
        print(warn(f"  Banco {DB_PATH!r} não encontrado no diretório atual."))
        _rel['banco'] = {"erro": "arquivo não encontrado"}
        return

    tamanho_mb = os.path.getsize(DB_PATH) / 1024 / 1024
    print(f"  Arquivo: {DB_PATH}  ({tamanho_mb:.2f} MB)")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indices = [r[0] for r in cur.fetchall()]
    print(f"  Tabelas : {tabelas}")
    print(f"  Índices : {indices}")
    if 'idx_data' in indices:
        print(f"  {ok('idx_data presente')}")
    else:
        print(f"  {warn('idx_data ausente — full scan em queries por data')}")

    # Carteira
    print(sub("Carteira"))
    cur.execute("SELECT * FROM carteira_real")
    cart = cur.fetchall()
    cart_json = []
    if cart:
        total_inv = sum(r['quantidade'] * r['preco_medio'] for r in cart)
        print(f"  {len(cart)} posições — Total investido: R$ {total_inv:,.2f}")
        for r in cart:
            linha = dict(r)
            cart_json.append(linha)
            print(
                f"    {r['ticker']:<8} {r['quantidade']:>6} × "
                f"R${r['preco_medio']:>9.2f}  (desde {r['data_aporte']})"
            )
    else:
        print("  Carteira vazia.")

    # Análises
    print(sub("Análises salvas"))
    cur.execute("SELECT ticker, data_analise, score, recomendacao, dados_completos "
                "FROM analises ORDER BY data_analise DESC")
    analises = cur.fetchall()
    analises_json = []
    if analises:
        print(f"  {len(analises)} análise(s):\n")
        for a in analises:
            entrada = {
                "ticker":       a['ticker'],
                "data_analise": a['data_analise'],
                "score":        a['score'],
                "recomendacao": a['recomendacao'],
            }
            print(f"  {'─'*50}")
            print(f"  Ticker     : {a['ticker']}")
            print(f"  Data       : {a['data_analise']}")
            print(f"  Score      : {a['score']}/100")
            print(f"  Recomend.  : {a['recomendacao']}")
            try:
                d = json.loads(a['dados_completos'])
                tam = len(a['dados_completos'])
                print(f"  JSON size  : {tam:,} bytes ({tam/1024:.1f} KB)")
                if 'historico' in d:
                    print(f"  {err('ATENÇÃO: historico presente no banco!')}")
                    entrada['historico_no_banco'] = True
                else:
                    print(f"  {ok('historico excluído do banco')}")
                    entrada['historico_no_banco'] = False
                entrada['json_bytes'] = tam
                for campo in ['fair_value','upside','perfil','metodos_usados']:
                    if campo in d:
                        entrada[campo] = d[campo]
                        print(f"  {campo:<15}: {d[campo]}")
                if 'analise_ia' in d:
                    preview = d['analise_ia'][:300].replace('\n',' ')
                    entrada['analise_ia_preview'] = preview
                    print(f"  analise_ia : \"{preview}...\"")
            except Exception as e:
                entrada['erro_json'] = str(e)
                print(f"  {err(f'JSON corrompido: {e}')}")
            analises_json.append(entrada)
    else:
        print("  Nenhuma análise ainda.")

    conn.close()

    _rel['banco'] = {
        "arquivo":    DB_PATH,
        "tamanho_mb": round(tamanho_mb, 3),
        "tabelas":    tabelas,
        "indices":    indices,
        "idx_data":   'idx_data' in indices,
        "carteira":   cart_json,
        "analises":   analises_json,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7. VERIFICAÇÃO MANUAL (link Fundamentus)
# ══════════════════════════════════════════════════════════════════════════════

def auditar_referencia(ticker: str, dados: dict):
    print(hdr(f"7. VERIFICAÇÃO MANUAL — {ticker}"))
    print(f"""
  Compare com: https://www.fundamentus.com.br/detalhes.php?papel={ticker}

  Campo               Valor capturado
  ──────────────────────────────────────────────────""")

    campos_ref = [
        ('preco_atual',         'Cotação atual'),
        ('pl',                  'P/L'),
        ('pvp',                 'P/VP'),
        ('dy',                  'Div. Yield'),
        ('roe',                 'ROE'),
        ('roic',                'ROIC'),
        ('margem_liquida',      'Marg. Líquida'),
        ('patrimonio_liquido',  'Patrim. Líq'),
        ('lucro_liquido',       'Lucro Líquido'),
    ]
    ref_json = {}
    for campo, label in campos_ref:
        val = dados.get(campo)
        ref_json[campo] = val
        if val is None:
            print(f"  {label:<22}: {warn('AUSENTE')}")
        elif campo in ['dy','roe','roic','margem_liquida']:
            print(f"  {label:<22}: {val*100:.2f}%")
        elif campo == 'preco_atual':
            print(f"  {label:<22}: R$ {val:.2f}")
        else:
            print(f"  {label:<22}: {val}")

    print("\n  → Se algum valor divergir do Fundamentus, o bug está em")
    print("    fundamentus_scraper.py → _limpar_valor() ou buscar_dados()\n")

    _rel['tickers'][ticker]['referencia_manual'] = {
        "url":    f"https://www.fundamentus.com.br/detalhes.php?papel={ticker}",
        "campos": ref_json,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # Iniciar captura do output
    _tee = _Tee(sys.stdout)
    sys.stdout = _tee

    ts    = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"auditoria_{ts}"

    args = [a for a in sys.argv[1:] if a]

    print(f"{BLD}{CYN}")
    print("╔══════════════════════════════════════════════════════╗")
    print("║       SENTINELA B3 — AUDITORIA INTERNA               ║")
    print(f"║       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                         ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(RST)

    from config import APP_VERSION

    _rel['meta'] = {
        "timestamp":  datetime.now().isoformat(),
        "versao":     f"Sentinela B3 {APP_VERSION}",
        "db_path":    DB_PATH,
        "tickers":    [],
        "modo":       "full",
    }

    if '--db-only' in args:
        _rel['meta']['modo'] = 'db-only'
        auditar_banco()
    elif '--selic' in args:
        _rel['meta']['modo'] = 'selic-only'
        auditar_selic()
    else:
        tickers = [a.upper() for a in args if not a.startswith('--')]
        if not tickers:
            tickers = ['PETR4', 'ITUB4', 'WEGE3']
            print(f"  {warn('Nenhum ticker informado — usando padrão: PETR4, ITUB4, WEGE3')}")
            print("  Uso: python auditoria.py VALE3 BBAS3\n")

        _rel['meta']['tickers'] = tickers

        auditar_selic()
        auditar_banco()

        for ticker in tickers:
            print(f"\n\n{'█'*60}")
            print(f"  TICKER: {ticker}")
            print(f"{'█'*60}")

            dados = auditar_dados_scraper(ticker)
            if dados is None:
                _rel['tickers'][ticker] = {"erro": "dados não obtidos"}
                continue

            # Roteamento FII vs Ação — idêntico ao app.py
            from config import FIIS_CONHECIDOS, UNITS_CONHECIDAS
            qt = dados.get('quote_type', '')
            is_fii = (
                ticker in FIIS_CONHECIDOS
                or (
                    qt == 'MUTUALFUND'
                    or (
                        '11' in ticker
                        and 'SA' not in ticker
                        and ticker not in UNITS_CONHECIDAS
                    )
                )
            )

            if is_fii:
                print(hdr(f"3. VALUATION — {ticker}"))
                print(f"\n  {warn('Perfil FII detectado (quoteType='+repr(qt)+')')}")
                print("  Em produção: fii_engine.analisar() é chamado em vez de val_engine.processar()")
                analise = auditar_fii(dados)
                fv = analise.get('fair_value')
                upside_val = analise.get('upside')
                print(f"  FII: {analise}")
                _rel['tickers'][ticker]['valuation'] = {
                    "perfil": "FII", "resultado": analise,
                    "invariantes": invariantes_resultado(analise),
                }
            else:
                fv, upside_val, analise = auditar_valuation(ticker, dados)
            # CORRIGIDO: mergear resultado do valuation em dados antes do prompt
            # (mesmo que app.py faz com dados.update(analise))
            dados.update(analise)
            auditar_tecnica(ticker, dados)
            auditar_prompt(ticker, dados, fv, upside_val)
            auditar_referencia(ticker, dados)

        print(hdr("AUDITORIA CONCLUÍDA"))
        print(f"  Tickers: {', '.join(tickers)}")

    # ── Salvar TXT ────────────────────────────────────────────────────────────
    txt_path = f"{fname}.txt"
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(_tee.getvalue())
        # Restaurar stdout antes de imprimir o aviso
        sys.stdout = _tee._orig
        print(f"\n  {ok(f'Relatório TXT salvo: {txt_path}')}")
    except Exception as e:
        sys.stdout = _tee._orig
        print(f"\n  {err(f'Erro ao salvar TXT: {e}')}")

    # ── Salvar JSON ───────────────────────────────────────────────────────────
    json_path = f"{fname}.json"
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(_rel, f, ensure_ascii=False, indent=2, default=str)
        print(f"  {ok(f'Dados JSON salvos:   {json_path}')}")
    except Exception as e:
        print(f"  {err(f'Erro ao salvar JSON: {e}')}")

    print("\n  Envie os dois arquivos para análise:")
    print(f"    📄 {txt_path}")
    print(f"    📊 {json_path}\n")


if __name__ == "__main__":
    main()
