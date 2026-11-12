# Atribuição ON/PN quando os direitos são distintos (F3-P09, F2C-38)

Levantamento feito em 12/11/2026 sobre os dados oficiais já guardados no banco único (DFP de 2025, só leitura) e sobre o FRE aberto de 2025 da CVM. O FRE foi baixado em `data/fontes/l1/cvm/fre/fre_cia_aberta_2025.zip`, com 8.498.082 bytes e SHA-256 `cf20738928f94ad0a4da61cfc53452aa38ca9af7046cb9e45f4f307e5cecbf4e`.

O estudo não muda nada no código: a regra atual continua valendo até o Marcos decidir a ficha.

## 1. A regra atual, por componente

| Componente | De onde vem por classe | Respeita direitos distintos? |
|---|---|---|
| LPA (Graham e Lynch) | LPA básico divulgado da classe, da DRE (D19 e ficha por ação 1.1). O recalculado é só conferência | Sim. Pelo CPC 41, a companhia reparte o lucro entre as classes conforme os direitos de cada uma |
| Proventos (Bazin e perfil) | Relação da B3 por espécie (`b3_proventos`, decisão 33) | Sim. É o valor pago a cada espécie |
| VPA (Graham e lente de bancos) | PL dos controladores ÷ ações em circulação de todas as classes (`acoes_cvm.derivar_por_acao`) | Não. Supõe direitos iguais sobre o PL |
| D0 e payout do Gordon | DVA dos controladores ÷ ações (`gordon_cvm`) | Não. Divide o total por ações, como se os direitos fossem iguais |
| D0 da lente de bancos | Igual ao do Gordon (`gordon_cvm.entradas(..., modelo="banco")`) | Não. É a limitação citada na tabela F3-P09 |
| ON de companhia com mais de uma classe preferencial | A lente de bancos abstém a ON e as PNs (BRSR3; `MOTIVO_CLASSES_PREFERENCIAIS`) | A abstenção evita o erro. Avaliar a ON em separado está nesta proposta |

## 2. Quanto os direitos distintos aparecem nos dados

O levantamento usou a DFP de 2025 (referência 31/12/2025), as linhas 3.99.01.xx da DRE consolidada (ou da individual, sem a consolidada), com valor diferente de zero:
- **121 companhias** divulgam LPA de ON e de pelo menos uma classe preferencial.
- **54 delas** divulgam LPA diferente entre ON e PN. Nas 46 com LPA da ON positivo, a mediana da razão PN/ON é **1,10**, os 10% a mais da Lei 6.404, art. 17, §1º, II.
- Três razões passam de 10 vezes (CNPJs 87.762.563/0001-03, 92.715.812/0001-31 e 59.418.806/0001-47) e uma é 0. Não as conferi uma a uma. Podem ser erros de escala ou de classe na DRE, e ficam como amostra para a ficha.

A consulta: `SELECT cnpj, demonstracao, descricao, valor FROM demonstracoes WHERE documento = 'DFP' AND dt_refer = '2025-12-31' AND demonstracao IN ('DRE_con', 'DRE_ind') AND ordem_exerc = 'ÚLTIMO' AND conta LIKE '3.99.01.%'`, com a descrição normalizada (maiúsculas, sem espaços) e só as classes `ON` e `PN`, `PNA`, `PNB`…; por CNPJ, a consolidada quando existe.

Nessas 54 companhias, o LPA dos métodos já reflete a diferença, mas o VPA e o D0 não.

## 3. A fonte oficial dos direitos

O FRE aberto da CVM não traz os direitos de cada classe:
- `fre_cia_aberta_capital_social_classe_acao` (292 linhas em 2025) dá só o tipo da classe e a quantidade;
- `fre_cia_aberta_distribuicao_capital_classe_acao` e `fre_cia_aberta_posicao_acionaria_classe_acao` dão a posição acionária.

Os direitos (prioridade no reembolso, dividendo mínimo ou fixo, 10% a mais, tag along, voto restrito) ficam no item 18.1 do formulário de referência e no estatuto. Os dois são documentos em PDF no sistema da CVM, sem campo estruturado. A ligação não pode ser feita de forma automática nem pelo ticker.

## 4. Ficha proposta, para decisão do Marcos no checkpoint da 3-b

1. **Manter a regra atual** para o LPA (divulgado por classe) e para os proventos (B3 por espécie).
2. **VPA e D0 com direitos distintos** passariam a ler uma tabela de referência curada à mão, versionada e com fonte, no molde da tabela de correções do índice. Cada linha teria:
   - CNPJ e classe;
   - o direito: prioridade no reembolso do capital, dividendo mínimo ou fixo, ou 10% a mais;
   - a fonte: FRE com `ID_Documento`, versão e item 18.1, ou estatuto com a data de aprovação;
   - a vigência.

   Sem linha na tabela, vale a regra atual, com um aviso de contexto: "direitos iguais entre classes assumidos no VPA e no D0". Com linha, a divisão por classe segue o direito documentado, e direito que não se converte em número leva à abstenção daquela lente, com o motivo.
3. **ON de companhia com várias preferenciais:** avaliar a ON em separado só quando a tabela documentar os direitos de todas as classes. Sem isso, a abstenção atual continua.
4. **Alternativa rejeitada como regra automática:** usar a razão entre os LPAs divulgados para repartir o D0 ou o PL. Ela capta o efeito dos 10% a mais no lucro do ano, mas não prova o direito sobre o PL nem a política de distribuição.

Nenhuma dessas mudanças entra sem a ficha aprovada. A mudança de método é caso do §3 da política.
