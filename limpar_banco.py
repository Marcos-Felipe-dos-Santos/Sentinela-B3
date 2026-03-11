"""
limpar_banco.py — Limpeza e manutenção do banco Sentinela B3

Remove ou sinaliza:
  1. Análises com upside absurdo (>1000%) — bug DY ou Selic pré-v13
  2. Análises com fair_value > 10× preço atual — bug DY
  3. Units/BDRs com sufixo 11 classificadas como FII (pré-fix quote_type)
  4. FIIs reais classificados como ação/RENDA/VALOR (pré-fix whitelist)

Uso:
  python limpar_banco.py              # executa limpeza
  python limpar_banco.py --dry-run    # apenas mostra o que seria removido
"""
import sys
import sqlite3
import json
import os

# Importar as listas do config.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config import FIIS_CONHECIDOS, UNITS_CONHECIDAS
except ImportError:
    # Fallback se config.py não estiver disponível
    FIIS_CONHECIDOS = {'HGLG11','XPML11','VISC11','MXRF11','KNRI11'}
    UNITS_CONHECIDAS = {'KLBN11','TAEE11','SAPR11','CMIG11','CPLE11','ELET11'}

DB_PATH = "sentinela_v6.db"
DRY_RUN = "--dry-run" in sys.argv

if not os.path.exists(DB_PATH):
    print(f"Banco {DB_PATH!r} não encontrado.")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur  = conn.cursor()

cur.execute("SELECT ticker, data_analise, score, recomendacao, dados_completos FROM analises ORDER BY data_analise DESC")
rows = cur.fetchall()

print(f"Total de análises no banco: {len(rows)}\n")

remover = []
manter  = []

for r in rows:
    ticker = r['ticker']
    data   = r['data_analise']

    try:
        d = json.loads(r['dados_completos'])
    except Exception:
        remover.append((ticker, data, "JSON corrompido"))
        continue

    fv     = d.get('fair_value',  0) or 0
    preco  = d.get('preco_atual', 0) or 0
    upside = d.get('upside',      0) or 0
    perfil = d.get('perfil',      '') or ''

    # ── Critério 1: upside absurdo (bug DY ou Selic pré-v13) ──────────────
    if upside > 1000:
        motivo = f"upside={upside:.0f}% (absurdo — bug DY ou Selic pré-v13)"
        remover.append((ticker, data, motivo))

    # ── Critério 2: FV > 10× preço (bug DY) ──────────────────────────────
    elif fv > 0 and preco > 0 and fv > preco * 10:
        motivo = f"FV=R${fv:.2f} vs Preço=R${preco:.2f} ({fv/preco:.0f}×)"
        remover.append((ticker, data, motivo))

    # ── Critério 3: Unit classificada como FII (pré-fix quote_type) ───────
    elif ticker in UNITS_CONHECIDAS and perfil == 'FII':
        motivo = f"ticker={ticker} é ação/unit (não FII) — engine errado aplicado pré-fix quote_type"
        remover.append((ticker, data, motivo))

    # ── Critério 4: FII real classificado como ação (pré-fix whitelist) ────
    elif ticker in FIIS_CONHECIDOS and perfil != 'FII':
        motivo = f"ticker={ticker} é FII real mas perfil={perfil} — val_engine aplicado em vez de fii_engine"
        remover.append((ticker, data, motivo))

    else:
        manter.append((ticker, data, r['recomendacao'], fv, upside, perfil))

# ── Relatório ────────────────────────────────────────────────────────────────
print("══ REMOVER ══")
if not remover:
    print("  ✓ Nenhuma análise problemática encontrada!")
for ticker, data, motivo in remover:
    print(f"  ✗ {ticker:<8} ({data})  →  {motivo}")

print(f"\n══ MANTER ({len(manter)} análises) ══")
for ticker, data, rec, fv, upside, perfil in manter:
    print(f"  ✓ {ticker:<8} ({data})  FV=R${fv:>8.2f}  {upside:>+7.1f}%  {rec:<14} [{perfil}]")

# ── Execução ─────────────────────────────────────────────────────────────────
if remover:
    if DRY_RUN:
        print(f"\n[DRY-RUN] {len(remover)} análise(s) seriam removidas.")
        print("  Execute sem --dry-run para confirmar.")
        if any(t in UNITS_CONHECIDAS for t, _, _ in remover):
            print("\n  Obs: análises de units removidas devem ser re-analisadas no app")
            print("  para aplicar o engine correto (Valuation em vez de FII).")
    else:
        for ticker, data, _ in remover:
            cur.execute(
                "DELETE FROM analises WHERE ticker=? AND data_analise=?",
                (ticker, data)
            )
        conn.commit()
        print(f"\n✓ {len(remover)} análise(s) removidas.")
        print(f"✓ {len(manter)} análise(s) preservadas.")

        # Avisar sobre re-análise de units e FIIs
        units_removidas = [t for t, _, _ in remover if t in UNITS_CONHECIDAS]
        fiis_removidos  = [t for t, _, _ in remover if t in FIIS_CONHECIDOS]
        
        if units_removidas:
            print(f"\n  Units removidas: {', '.join(units_removidas)}")
            print("  → Re-analisar no app (usarão val_engine correto)")
        
        if fiis_removidos:
            print(f"\n  FIIs removidos: {', '.join(fiis_removidos)}")
            print("  → Re-analisar no app (usarão fii_engine correto)")
else:
    print("\n✓ Banco limpo — nada a remover.")

conn.close()