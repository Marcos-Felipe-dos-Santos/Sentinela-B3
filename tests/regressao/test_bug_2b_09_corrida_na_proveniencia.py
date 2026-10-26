"""BUG-2B-09: duas gravações simultâneas da proveniência do mesmo arquivo colidem.

`proveniencia.registrar_arquivo` grava o registro num `.tmp` de nome fixo e o troca de nome;
com duas threads no mesmo arquivo, a segunda troca não acha o `.tmp` e levanta
`FileNotFoundError`. Origem: F2B-21, pergunta 8 (2ª passada do Gemini).
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from sentinela.data import proveniencia


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-09 · gravações simultâneas da proveniência colidem no .tmp · corrige: F2C-18",
)
def test_duas_gravacoes_simultaneas_do_mesmo_registro(tmp_path):
    origem = tmp_path / "arquivo.zip"
    origem.write_bytes(b"conteudo sintetico")
    barreira = threading.Barrier(2)
    escrever_original = Path.write_text

    def escrever(caminho, *args, **kwargs):
        resultado = escrever_original(caminho, *args, **kwargs)
        if caminho.name.endswith(".tmp"):
            # Espera curta pela outra thread logo depois da escrita: sem trava, as duas
            # escrevem o mesmo .tmp antes da troca de nome; com trava, a espera expira e a
            # gravação segue sozinha.
            try:
                barreira.wait(timeout=0.5)
            except threading.BrokenBarrierError:
                pass
        return resultado

    def gravar(_):
        try:
            proveniencia.registrar_arquivo(origem, "fonte sintética", "DFP", "2025")
        except OSError as exc:
            return type(exc).__name__
        return "gravado"

    with patch.object(Path, "write_text", escrever), ThreadPoolExecutor(2) as executor:
        resultados = list(executor.map(gravar, range(2)))
    assert resultados == ["gravado", "gravado"]
