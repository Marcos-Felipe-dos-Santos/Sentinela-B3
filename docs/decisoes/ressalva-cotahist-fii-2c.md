# Ressalva COTAHIST/FII — F2C-33

**Resultado em27/10/2026, base cb4ab9c:** ressalva refutada no código entregue e no recorte enviado ao auditor. Nenhuma produção/teste/golden alterado.

O fechamento da2B registrou a frase `CVMFIIProvider._preco_cotahist` sem cobertura/idade (`docs/loop/historico/fase-2b/auditoria-externa.md`, linha50). O símbolo não existe em `cvm_fii_provider.py`, nem no histórico desse arquivo: `git log --all -S _preco_cotahist -- cvm_fii_provider.py` não retorna commit. A busca global no código, excluindo mutantes, também não localiza produtor ou leitor. Não se implementa uma proteção para um caminho inexistente.

Foi conferido o pacote de entrada doGemini em `/mnt/c/Users/marcos/Downloads/gemini-fase-2b/parte-04.md`, seção `ARQUIVO: cvm_fii_provider.py` (linha3407 do contêiner,314linhas de fonte). Não contém `_preco_cotahist` ou import COTAHIST nesse arquivo. Nas demais partes, a busca literal também não encontra o símbolo. O pacote é entrada de auditoria, não o parecer completo; não se atribui ao auditor uma explicação que não está disponível. A frase é preservada como origem do levantamento, não como fato técnico confirmado.

## Caminhos efetivos

| Caminho | O que entrega | Controle ou limite |
|---|---|---|
| `CVMFIIProvider.obter_dados_fii` | VP, cotas e metadados do Informe; não cotação | patrimônio/cotas não se tornam preço negociado |
| `MarketEngine._buscar_yfinance` | preço do histórico; na falta, preço da resposta do mesmo provedor | não usa cotação COTAHIST |
| `MarketEngine._buscar_brapi` | preço somente se o primário não o entregou | não usa cotação COTAHIST |
| `MarketEngine._buscar_liquidez` | bloco de liquidez por COTAHIST | passa `meses_ausentes` ao cálculo e grava abstenção/motivo |
| `_pregoes` da cascata | datas de negociação para conferência de data ex dos proventosB3 | não fornece cotação ao motorFII |
| `referencia`/levantamentos públicos | identidade/negociação e análises documentais | não são reserva oculta de preço no motorFII |

Não há, portanto, cotação COTAHIST desse provedor alimentando valor, P/VP ou score sem conferir idade. A política geral de atualidade do preço yfinance/brapi é outro contrato; esta refutação não afirma que toda coleta esteja livre de problema de idade, nem altera tolerância temporal. Se aparecer reprodução de outro caminho, deverá ganhar BUG/regressão e ticket próprio com idade máxima aprovada.

## Reprodutibilidade

Buscar literal `_preco_cotahist` em `cvm_fii_provider.py`, `sentinela/` e histórico do arquivo; enumerar métodos do provedor; seguir preço na cascata e `coleta.meses_ausentes` na liquidez. Comparar o arquivo integral da seção do pacote com a alegação. Não é preciso inicializar motores, acessar banco, credenciais ou fonte de mercado para refutar símbolo/leitor ausentes.

Sem bug confirmado, sem xfail artificial e sem fix derivado deste item. O levantamento não determina uma idade máxima nova.

Hashes de conferência: provedor atual `d9e28c8b6c9f0a1b81640295cba75bef4c38f7a012d994b5bd4c0d595eaec85c`; contêiner parte04 `0864974e342f39d8ceecaf8daa1c0cf9a85704fc22e5ed694bb41ffe10d5e8d2`. O hash do contêiner não identifica sozinho o parecer nem o commit auditado.
