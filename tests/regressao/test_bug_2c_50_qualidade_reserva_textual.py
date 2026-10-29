"""BUG-2C-50: saneamento da fonte não pode apagar a reserva textual legítima da D20."""

import json

from sentinela.data.controladores import RESERVA_PL
from tests.test_qualidade import documentos, quadro


def test_reserva_textual_d20_permanece_na_fonte_do_pl():
    docs = documentos()
    docs[0]["pl_inicial_proveniencia"] = {
        "reserva": RESERVA_PL,
        "demonstrativo": "BPP_con PENÚLTIMO",
    }
    r = quadro(docs)
    assert r["exercicios"][0]["pl_inicial_proveniencia"]["reserva"] == RESERVA_PL
    json.dumps(r, allow_nan=False)
