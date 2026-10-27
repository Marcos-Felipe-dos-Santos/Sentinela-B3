# Publicação da inadimplência IF.data — F2C-37

**27/10/2026; contrato implementado na fronteira de dados, sem mudar a lente.**
O aceite autoriza abstenção quando não houver calendário oficial utilizável.

## Fonte conferida e o que ela demonstra

| Recurso BCB | Coleta UTC27/10 | Bytes | SHA256 |
|---|---|---:|---|
| [Página IF.data](https://www3.bcb.gov.br/ifdata/index.html) |11:51:35|92483|234fcb9158bd25b222625418f2d775d438a8db8df1585e65ef1b40c7a7fb0153|
| [Índice de relatórios indicado pela página](https://www3.bcb.gov.br/ifdata/rest/relatorios2025a2030) |11:51:36|1649748|b8977d383e4ea51f56ed391571aca7af1c109b83b9c17ceef8b926841d658206|

AmbosHTTP200; cópias integrais/metadados/script em `outputs/validacao-fase2c/f2c37-*`, ignorados. Nova coleta, mesmos hashes da exploração anterior; não se depende dos antigos arquivos/tmp.

A página informa **até60dias** para março/junho/setembro e **até90dias** para dezembro, além de reprocessamento anual em abril. Não fornece, nos recursos conferidos, calendário efetivo por observação. No índice, `dt` é data-base. O JavaScript usa `trel.ge−2` para o texto sobre documentos entregues: esse campo não é identificado como publicação efetiva. Nem prazo geral, nem entrega/processamento são renomeados como publicação. A pesquisa não demonstra inexistência de calendário em qualquer outro recurso; demonstra que nenhum produtor de calendário efetivo foi verificado para este item.

## Contrato e consequência operacional

`CalendarioPublicacoes` recebe mapa data-base→dia de publicação efetiva e `Proveniencia`D16 do arquivo que comprova essas datas (fonte/hash/coleta, não o arquivo do relatório16). É **entrada já conferida pelo chamador**, não descoberta automática ou prova obtida só por o domínio ser doBCB. O produtor futuro deve conferir corpo, hash e semântica antes de fornecer essa entrada; não se interpreta `dt/ge` automaticamente. O registro tipado valida os metadadosD16; o consumidor conserva e verifica elegibilidade da fonte/coleta. Não foi adicionado produtor hipotético ou feed fictício.

- Sem calendário, ou sem data da observação nele: inadimplênciaNone e motivo; não consulta relatório16.
- Fonte nãoBCB/documento diferente, coleta ilegível/sem fuso/futura, publicação inválida ou não observada: abstenção motivada. A lista de datas não pode ser um cronograma futuro apresentado como divulgação efetiva.
- Data publicada depois do corte fica de fora. Sem hora oficial, o próprio dia da publicação também fica de fora; só entra no dia local seguinte. O corte efetivo respeita `as_of` emBrasília, mesmo que `data_referencia` fornecida seja posterior. Coleta posterior ao instante não se torna elegível por ter a mesma data.
- Calendário coletado antes do dia de publicação declarado não demonstra publicação efetiva; não antecipar evento previsto.
- Com evidência admissível, a razão148834/24454 mantém o mesmo conglomerado/data-base, sem nova fórmula. Falha da carteira preserva Basileia já lida. Registro do calendário acompanha a proveniência dos relatórios, inclusive se recusado com motivo.

**No fluxo normal atual, o calendário ficaNone:** portanto a inadimplência se abstém, enquanto a Basileia continua independente e os números das lentes não mudam. Não se afirma que a simples configuração atual passou a reconstruir publicações históricas. Produtor/calendário oficial verificável e versões observadas têm destinoF3-1, que já cobre ponto-no-tempo; não se simula esse trabalho com uma data-base.

## Provas e fixtures

BUG-2C-16: dois casos sem calendário, cortes01/07 e27/10/2026, retornavam indevidamente razão≈0,0586; teste exigeNone/motivo e não consulta16, com Basileia0,151297835513664 preservada. DoisFAIL antes, doisXPASSestritos depois; marcas retiradas, registro corrigido. Logs persistentes f2c37-vermelho.txt e -xpass.txt.

`tests/apoio_ifdata_calendario.py` é **cenário sintético**, com URL que diz calendário sintético não coletado, hash fictício explícito e datas declaradas. Não é recorte de calendárioBCB, nem evidência de uma publicação real. Serve para testar a fronteira positiva/negativa sem rede. Não entra na aplicação. Os testes exercitam futuro, mesmo dia, fonte/coleta inadequadas, dataUTC que cai no dia anterior local e conservação da evidência junto a três relatórios.

Fixtures antigas de razão/ausência de carteira/falha de rede/TTL recebem premissa sintética de elegibilidade para continuar chegando ao caminho que verificavam; não se reduz a contagem de consultas esperadas nem se troca motivo de falha por calendário ausente para ocultar cobertura. No contrato de proveniência, os três registros dos relatórios continuam submetidos a **todas** as verificações anteriores (hash do arquivo, fonte, período, coleta etc.); acrescenta-se o quarto registro do calendário e sua igualdade explícita. No teste da cascata, proveniência vazia esperada passa a exigir o registro específico do calendário fornecido: cobertura mais exigente, sem alterar número financeiro.

## Limites de responsabilidade

O calendário é um insumo de dados com proveniência; domínio oficial e hash de formato válido não verificam sozinhos o conteúdo. A ligação corpo/mapa é obrigação do produtor, que não foi inventado nesta fase. Sem ele, permanece abstenção. Não usa relógio, banco ou rede em cálculo puro, não muda schemaSQLite, método, taxa, escopo ou golden. Não tenta resolver a publicação do capital/Basileia de passagem: este item trata a inadimplência conforme o aceite.
