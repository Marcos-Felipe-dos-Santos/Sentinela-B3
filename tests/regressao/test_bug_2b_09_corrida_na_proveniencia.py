"""BUG-2B-09: duas gravações simultâneas da proveniência do mesmo arquivo colidem.

`proveniencia.registrar_arquivo` grava o registro num `.tmp` de nome fixo e o troca de nome;
com duas threads no mesmo arquivo, a segunda troca não acha o `.tmp` e levanta
`FileNotFoundError`. Origem: F2B-21, pergunta 8 (2ª passada do Gemini).
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from sentinela.data import proveniencia


def test_duas_gravacoes_simultaneas_do_mesmo_registro(tmp_path: Path) -> None:
    origem = tmp_path / "arquivo.zip"
    origem.write_bytes(b"conteudo sintetico")
    barreira = threading.Barrier(2)
    substituir_original = Path.replace
    temporarios: list[Path] = []

    def substituir(caminho: Path, destino: Path) -> Path:
        temporarios.append(caminho)
        # Ambos já escreveram antes da primeira troca. Timeout é falha real do teste.
        barreira.wait(timeout=5)
        return substituir_original(caminho, destino)

    def gravar(indice: int) -> proveniencia.Proveniencia:
        return proveniencia.registrar_arquivo(
            origem, f"fonte sintética {indice}", "DFP", "2025"
        )

    with patch.object(Path, "replace", substituir), ThreadPoolExecutor(2) as executor:
        futuros = [executor.submit(gravar, indice) for indice in range(2)]
        # result propaga falhas dos dois workers; nenhum erro é aceito como reprodução.
        resultados = [futuro.result(timeout=10) for futuro in futuros]
    assert len(temporarios) == 2
    assert len(set(temporarios)) == 2
    final = proveniencia.ler_registro(origem)
    assert final in resultados
    assert {registro.fonte for registro in resultados} == {
        "fonte sintética 0",
        "fonte sintética 1",
    }
    assert final.hash_sha256 == proveniencia.hash_sha256(origem)
    assert not any(caminho.suffix == ".tmp" for caminho in tmp_path.iterdir())
