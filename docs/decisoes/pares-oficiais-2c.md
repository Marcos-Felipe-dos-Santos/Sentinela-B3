# Comparação de pares — F2C-7

O setor é `SETOR_ATIV` do cadastro CVM já incorporado pelo F2A-2 no índice. O grupo conserva classe e espécie do registro, exclui o próprio ticker e outro papel com o mesmo CNPJ. O modelo BPP dos fundamentos deve ser demonstrado e igual ao do ativo consultado. Não se infere banco pelo ticker nem se resolve aqui a divergência setor/modelo levantada no F2C-45.

Sem índice, identidade, setor, pares ou modelo demonstrado, a comparação fica indisponível com motivo. Não há retorno ao mapa manual. Um grupo com menos de dois pares utilizados ou coleta parcial declara cobertura curta, esperados e utilizados; isso é diagnóstico de cobertura, não limiar econômico de elegibilidade. A consulta pode conservar comparação de um único par explicitamente identificado.

**decisão provisória: P/L não positivo, ausente ou não finito em qualquer par utilizado → comparação P/L indisponível com motivo.** O aceite admite indisponibilidade na ausência de política aprovada. Não se substitui média por mediana nem se elimina prejuízo silenciosamente. P/VP e DY só têm média quando todos os pares utilizados entregam números finitos; não há coerção de ausente para zero. Nenhum método de valuation consome essa comparação.

Exemplo independente: dois emissores compatíveis, P/L 4 e 8, média aritmética `(4+8)/2 = 6`; substituir 8 por -2 deixa P/L indisponível, preservando os nomes e a cobertura. Classe FII, outra espécie e outro setor não entram no grupo sintético. Os contratos novos provam a substituição do mapa antes de sua aposentadoria.

A CLI de diagnóstico usa a coleção canônica `DISTRESSED_TICKERS`, sem repetir MGLU3 em listas independentes, e só percorre candidatos presentes no índice. VIIA3 sai da seleção antiga; ausência de identidade é informada, sem adivinhar uma conversão para BHIA3 nem instituir uma tabela de aliases. Identidade atual é responsabilidade do índice oficial e de sua proveniência, não de uma lista de diagnóstico.

O commit Jules C-C `bb830f5` existe nos refs locais, mas `git merge-base --is-ancestor bb830f5 HEAD` devolveu 1 no início do item. Não foi entregue neste branch: continuavam mapa fixo e média simples inclusive com prejuízo. Sua proposta de mediana não é incorporada sem política aprovada. O item executa as lacunas observadas neste checkout, sem cherry-pick.
