"""Limpeza e manutenção do banco Sentinela B3.

Remove ou sinaliza:
  1. Análises com upside absurdo (>1000%).
  2. Análises com fair_value > 10x preço atual.
  3. Units/BDRs com sufixo 11 classificadas como FII.
  4. FIIs reais classificados como ação/RENDA/VALOR.

Uso:
  python limpar_banco.py
  python limpar_banco.py --dry-run
"""

import argparse
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from config import FIIS_CONHECIDOS, UNITS_CONHECIDAS
except ImportError:
    FIIS_CONHECIDOS = {'HGLG11', 'XPML11', 'VISC11', 'MXRF11', 'KNRI11'}
    UNITS_CONHECIDAS = {
        'KLBN11', 'TAEE11', 'SAPR11', 'CMIG11', 'CPLE11', 'ELET11',
        'BBSE11', 'SANB11', 'TRPL11', 'ALUP11', 'ENGI11', 'CPFE11',
    }

logger = logging.getLogger(__name__)

DB_PATH = Path("sentinela_v6.db")
Remocao = Tuple[str, str, str]
Manter = Tuple[str, str, str, float, float, str]


def carregar_analises(db_path: Path) -> List[sqlite3.Row]:
    """Carrega as análises salvas no banco local.

    Args:
        db_path: Caminho do arquivo SQLite.

    Returns:
        Lista de linhas da tabela analises.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ticker, data_analise, score, recomendacao, dados_completos "
            "FROM analises ORDER BY data_analise DESC"
        )
        return cur.fetchall()
    finally:
        conn.close()


def analisar_linhas(rows: List[sqlite3.Row]) -> Tuple[List[Remocao], List[Manter]]:
    """Classifica análises entre remoção e preservação."""
    remover = []
    manter = []

    for row in rows:
        ticker = row['ticker']
        data = row['data_analise']

        try:
            dados: Dict[str, Any] = json.loads(row['dados_completos'])
        except (json.JSONDecodeError, TypeError):
            logger.warning("JSON corrompido para %s em %s", ticker, data)
            remover.append((ticker, data, "JSON corrompido"))
            continue

        fair_value = dados.get('fair_value', 0) or 0
        preco = dados.get('preco_atual', 0) or 0
        upside = dados.get('upside', 0) or 0
        perfil = dados.get('perfil', '') or ''

        if upside > 1000:
            motivo = f"upside={upside:.0f}% (absurdo - bug DY ou Selic pre-v13)"
            remover.append((ticker, data, motivo))
        elif fair_value > 0 and preco > 0 and fair_value > preco * 10:
            motivo = (
                f"FV=R${fair_value:.2f} vs Preco=R${preco:.2f} "
                f"({fair_value / preco:.0f}x)"
            )
            remover.append((ticker, data, motivo))
        elif ticker in UNITS_CONHECIDAS and perfil == 'FII':
            motivo = (
                f"ticker={ticker} e acao/unit (nao FII) - engine errado "
                "aplicado pre-fix quote_type"
            )
            remover.append((ticker, data, motivo))
        elif ticker in FIIS_CONHECIDOS and perfil != 'FII':
            motivo = (
                f"ticker={ticker} e FII real mas perfil={perfil} - val_engine "
                "aplicado em vez de fii_engine"
            )
            remover.append((ticker, data, motivo))
        else:
            manter.append(
                (
                    ticker,
                    data,
                    row['recomendacao'],
                    fair_value,
                    upside,
                    perfil,
                )
            )

    return remover, manter


def imprimir_relatorio(remover: List[Remocao], manter: List[Manter]) -> None:
    """Imprime o relatório de limpeza."""
    print("== REMOVER ==")
    if not remover:
        print("  Nenhuma análise problemática encontrada.")

    for ticker, data, motivo in remover:
        print(f"  - {ticker:<8} ({data})  ->  {motivo}")

    print(f"\n== MANTER ({len(manter)} análises) ==")
    for ticker, data, rec, fair_value, upside, perfil in manter:
        print(
            f"  - {ticker:<8} ({data})  FV=R${fair_value:>8.2f}  "
            f"{upside:>+7.1f}%  {rec:<14} [{perfil}]"
        )


def executar_limpeza(db_path: Path, remover: List[Remocao]) -> None:
    """Remove do banco as análises classificadas como problemáticas."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        for ticker, data, _ in remover:
            cur.execute(
                "DELETE FROM analises WHERE ticker=? AND data_analise=?",
                (ticker, data),
            )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    """Executa a limpeza do banco via linha de comando."""
    parser = argparse.ArgumentParser(description="Limpa análises corrompidas.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria removido sem alterar o banco.",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Banco {str(DB_PATH)!r} não encontrado.")
        return 1

    rows = carregar_analises(DB_PATH)
    print(f"Total de análises no banco: {len(rows)}\n")

    remover, manter = analisar_linhas(rows)
    imprimir_relatorio(remover, manter)

    if not remover:
        print("\nBanco limpo - nada a remover.")
        return 0

    if args.dry_run:
        print(f"\n[DRY-RUN] {len(remover)} análise(s) seriam removidas.")
        print("Execute sem --dry-run para confirmar.")
        return 0

    executar_limpeza(DB_PATH, remover)
    print(f"\n{len(remover)} análise(s) removidas.")
    print(f"{len(manter)} análise(s) preservadas.")

    units_removidas = [ticker for ticker, _, _ in remover if ticker in UNITS_CONHECIDAS]
    fiis_removidos = [ticker for ticker, _, _ in remover if ticker in FIIS_CONHECIDOS]

    if units_removidas:
        print(f"\nUnits removidas: {', '.join(units_removidas)}")
        print("Re-analisar no app para usar val_engine.")

    if fiis_removidos:
        print(f"\nFIIs removidos: {', '.join(fiis_removidos)}")
        print("Re-analisar no app para usar fii_engine.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
