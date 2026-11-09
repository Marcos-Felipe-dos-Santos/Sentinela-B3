# Fronteiras restantes de dados — F2C-32

Levantamento em 27/10/2026 sobre `79e4355`; sem alteração de produção.
As decisões de método continuam nas fichas aprovadas e no pacote de26/10.
Os novos fixes abaixo têm destino na2C-b, aguardam ativação e não integram a2C-a.
IDs48/49 já reservados no trabalho pós-2B de outro branch; novos IDs começam em50.

## Fontes e alcance

- [CPC41, texto hospedado pela CVM](https://conteudo.cvm.gov.br/cvm_institucional/export/sites/cvm/menu/regulados/normascontabeis/cpc/CPC_41_rev_12.pdf), conferido27/10: itens3A,9–10,19–20 e66 distinguem classe e denominador médio ponderado. A soma por unit e a conferência pelo capital final são as políticas da ficha por ação1.1, §§1,7.3 e7.9; a norma não escolhe a reserva do projeto.
- [OASIS OData4.01, Part2, §2.2](https://docs.oasis-open.org/odata/odata/v4.01/odata-v4.01-part2-url-conventions.html), conferido27/10: apóstrofo interno de literal deve ser duplicado antes da codificação de URL. Codificar uma única aspa como `%27` não resolve a gramática. O exemplo O'Neil é um controle de sintaxe, não instituição real nem evidência de exploração no BCB.
- Leiautes oficiais DFP/ITR e seus hashes: `contrato-insumos-cvm-2c.md`, fontes conferidas noF2C-29. Leiaute do Informe: fichaFII1.3 e contratosD18 já versionados. Esses leiautes definem campos e disponibilidades, não os textos do prompt ou o schema interno.
- Para avisos, proveniência e inferência: especificação externa ao código é o aceite explícito aprovado doF2C-32, junto de D16/D18/D19/D20. Para schema, trata-se de proposta prospectiva de compatibilidade, não regra imposta pela CVM.

## 1. Conferência do LPA da unit

`acoes_cvm.lpa_dos_metodos` já soma quantidade×LPA por classe; não refazer esse cálculo.
A divergência está em `market_engine._por_acao_cvm`: chama `_lpa_divulgado_comparado` sem classe para unit e escolhe a primeira linha da escala. `DataQualityReport._alertas_fontes_independentes` divide o recalculado pelo fator e compara essa média com a primeira classe, ignorando os pesos do divulgado.

Contrato: conferir unit contra unit, `LPA_divulgado_unit = Σ(q_classe × LPA_classe)`; recalculado e divulgado na mesma base. Exemplo independente:1ON×1 +2PN×2 =5; recalculado5 por unit não diverge. Hoje o alerta é67%, ao comparar5/3 com1. Direitos diferentes podem produzir diferenças legítimas entre recalculado e divulgado; o fix corrige a unidade da comparação, não transforma diferença em erro contábil nem altera LPA dos métodos. Sem composição ou componente válido, conferência indisponível com motivo; não usar a primeira espécie como substituta.

**Confirmado BUG-2C-11**, regressão estrita `test_bug_2c_11_unit_conferencia_ponderada.py`,1FAIL anterior. **F2C-50**: fix próprio na2C-b, produtor/consumidor do alerta e testes; preservar método/limiar vigente e controlar composição incompleta/classes inválidas.

## 2. DRE PNA com FCA sem sigla

`cvm_provider.lpa_basico_por_classe` preserva PNA; `_lpa_da_classe` não deve adivinhar que um registro PN sem sigla equivale à PNA da DRE. A regra7.9 aprovada autoriza atribuir a linha genérica PN a classes conhecidas, não a direção inversa sem identidade. `tests/test_acoes_cvm.py::test_classe_pn_sem_sigla_com_varias_classes_nao_usa_o_desvio` já demonstra o caso PN genérico; contraprova deste levantamento verifica DRE somentePNA sem recalculado: abstenção, sem atribuição silenciosa.

**Não confirmado como bug de cálculo**: falta de identidade não autoriza inventá-la. Contrato: guardar PNA literal, informar classe não conciliada, não usar sufixo do ticker como prova. Complementação oficial do FCA e proposta de reconciliação ficam no **F2C-54**, levantamento da2C-b com fonte/versão/identidade e aceite próprio antes de qualquer fix. Se não houver vínculo demonstrável, manter abstenção. Não requer schema/tempo novo, portanto não foi empurrado àFase3.

## 3. Reserva e motivo D20 em LPA/VPA

`market_engine._CAMPOS_DA_RESERVA` liga lucro aROE/LPA e PL aROE/VPA; `_buscar_cvm` copia as reservas quando existe proveniência documental e acrescenta o detalhe `lpa_cvm` com origem/notas. Contraprova com dados sintéticos declara duas reservas e verifica os motivos nos dois campos; recalculado permanece explicitamente marcado. Ausência de proveniência documental não é resolvida fabricando uma data/hash.

**Refutado o defeito genérico de ausência do transporte** no estado atual. A leitura D20 é dos provedores/controladores e os bugs deBPP ilegível já foram corrigidos no30/31. Contrato de aceite futuro: reserva efetivamente usada, seu motivo e documento precisam permanecer distinguíveis de linha controladora direta e de LPA divulgado; a conferência de sinal pode depender do lucro sem mudar a origem do LPA divulgado. Um eventual caso concreto divergente exige regressão própria, sem remover genericamente reservas por causa da palavra "divulgado". Nenhum novo fix sem reprodução.

## 4. Falha do Informe e riscos

`MarketEngine._buscar_rendimento_fii` registra `informe_fii.abstencao` e retorna na exceção, sem acrescentar `riscos_dados`. O dado não vira zero e a lente já se abstém, mas falta o aviso no canal comum.

**Confirmado BUG-2C-12**,1FAIL. **F2C-51**: na2C-b, propagar aviso do Informe ao canal de riscos preservando abstenção/motivo e independência dos demais campos; testar fonte indisponível, sucesso e ausência de interface. Nenhum valor ou regra da lente muda. Tipos de falha de fonte versus programação devem ser explícitos no fix, sem captura genérica nova.

## 5. CodInst OData

`providers/ifdata.caminho_capital` interpola `codinst` entre aspas simples; `caminho_carteira` reutiliza a mesma construção. Para entrada sintética O'Neil, os dois produzem literal inválido. Não se afirma que o cadastro atual contenha esse código; a função pública recebe string e deve tratar seu conteúdo como dado opaco.

**Confirmado BUG-2C-13**,2FAIL. **F2C-52**: na2C-b, escape do literal e codificação da query, sem mudar o identificador institucional ou selecionar homônimo; controlar apóstrofo, Unicode e caracteres reservados, além dos códigos numéricos existentes. Sem rede no teste; metadados ou hipótese de ataque não são necessários para provar o erro da gramática publicada.

## 6. Versão do schema do índice

`referencia.indice.salvar_indice/carregar_indice` e `registro.Indice` não possuem versão explícita; `gerado_em` e hashes das fontes não versionam a estrutura. Isso é inventário de formato atual, não violação de um número de versão já aprovado. **Sem bug/xfail artificial.**

Contrato proposto: envelope com versão de schema, leitor com compatibilidade explícita, rejeição motivada de versão futura, sem reinterpretar arquivo antigo como novo. Migração/restauração verificável e compatibilidade do cache pertencem a **F3-6**, com D29; motivo da fase é a evolução persistida do schema e seus leitores. Definir o número e conversor em ticket próprio antes da implantação; manter índice antigo utilizável até existir migração aprovada. Não adicionar campo solto neste levantamento.

## 7. Classe inferida no prompt

`AssetClassifier.classify` usa fonte oficial primeiro; sem registro pode inferir STOCK para ticker que não termina11 ou recorrer às listas legadas. A cascata só usa esse caminho sem `classe_ativo` oficial e já registra risco de referência ausente/fora. `SentinelaAI._formatar_dados` mantém a classe, exclui `referencia_oficial`; `_montar_prompt` não identifica explicitamente que aquela classe foi inferida. O risco de referência indisponível não diz a origem específica da classe.

**Confirmado BUG-2C-14**,1FAIL: índice ausente em diretório temporário, TSTA3 inferidoSTOCK, prompt sem identificação da inferência. Nenhum cliente/credencial/rede inicializado. **F2C-53**: na2C-b, transportar origem/motivo da classificação e identificá-la no prompt, distinguindo registro oficial, inferência e UNKNOWN; não transformar inferência em elegibilidade de método, nem adicionar a mesma funcionalidade à camada de serviços desconectada. Aceite inclui classe oficial sem falso aviso e origem indisponível sem alegar fonte oficial.

## Evidências e destinos

Regressões novas permanecem xfail estritas até seus fixes; nenhuma produção corrigida por nota. `/tmp/2c32-vermelho.txt`:4FAIL (11/12/13); `/tmp/2c32-prompt-vermelho.txt`:1FAIL (14). Contraprovas de classe e reservas em `/tmp/test_2c32_contraprovas.py` e `/tmp/2c32-contraprovas.txt`. Os arquivos temporários são apoio; os testes e contratos permanentes acima preservam a evidência essencial.

F2C-50..54 são **propostos com destino2C-b, não ativados**, sujeitos a revisãoDOCUMENTO doClaude e à ativação posterior peloMarcos. Não se executam entre os itens da2C-a nem junto dos quatro rascunhos autorizados. Não há regra econômica nova ou [!] neste levantamento.
