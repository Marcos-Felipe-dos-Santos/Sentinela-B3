# Confirmação da composição recente — F2C-34

**Conclusão documental,27/10/2026:** a regra Gordon1.1 já aprovada usa comparação documental recente/DFP em intervalo aberto(0,9;1,1) e yfinance somente como conferência/aviso. Não exige transformar essa conferência em veto. Isso está explícito em `docs/metodologia/gordon.md`, §3, desde a2B. A §7.7 da ficha por ação trata outro ramo: escala pelo lucro consolidado quando o lucro dos controladores está abstido, para VPA/capitalização, com confirmação externa. As guardas não são matematicamente equivalentes e não devem ser descritas como se fossem.

## Código e alcance

- `CVMProvider._escala_da_composicao` usa lucro dos controladores do mesmo documento/LPA divulgado; pode usar reservaD20 apenas com BPP lido e minoritários ausentes/zero. **Não** usa o lucro consolidado quando controladores estão abstidos por minoritários, ao contrário da opção especial da§7.7. KLBN11 permanece sem escala neste caminho.
- `gordon_cvm.compatibilidade_base` converte os dois totais líquidos pela respectiva escala documental, calcula Qrecente/QDFP e exige estritamente0,9<razão<1,1. Sem escala/documento/composição válida, abstém. yfinance só compara espécie/unit quando disponível; não muda númeroCVM, razão ou elegibilidade.
- `acoes_cvm.derivar_por_acao` contém o ramo especial da§7.7, distinto do caminho acima. Não removido nem relaxado neste levantamento.

Assim, o controle documental cumpre **o papel aprovado na ficha Gordon**. Não se afirma que duas escalas erradas pelo mesmo fator possam ser distinguidas somente por sua razão: esse é um limite real, e o contrato mantém a determinação independente por documento. Alterar a confiança dessa inferência exigiria revisãoD21, não um ajuste silencioso ao código.

## Medição pública de conteúdo

`amostra-composicao-recente-2c.json` contém dados/limites/hashes e todos os casos. Fontes já disponíveis localmente:

- [DFP2025 oficial](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2025.zip), SHA256`d7aec54e7c67998e4cd3ef94c463ab247f09a6baaa2254878d1e431f28130e2a`;
- [ITR2026 oficial](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_2026.zip), SHA256`0e1ef74291d2143e7bb55247b01c8bbd94995d995536f70f0d19de1d79d7e38c`.

Extração literal dos nomes de ticker da primeira coluna de **todas** as tabelas do documento `universo-inicial.md`, incluindo sucessores e seçãoBTG:90nomes únicos;55STOCK/UNIT com registro no índice público local. Isso não redefine o denominadorD32, não identifica todos como atuais e não substitui a contagem inicial das tabelas principais. Deduplicação é por ticker, portanto BRSR3/5/6 podem repetir um emissor.

Nos55,44têm ambas as escalas determináveis pelo caminho vigente;38desses44estão dentro e6fora do intervalo aberto. Onze ficam sem razão determinável, incluindo composição ausente/escala indeterminada. Seleção de maiorDT_REFER e maiorVERSAO por emissor **dentro dos dois arquivos disponíveis**, sem afirmar que são todos os documentos entregues até uma data de corte.

| Controle público | QDFP em unidades | QITR em unidades | QITR/QDFP | Leitura documental |
|---|---:|---:|---:|---|
| ABEV3 |15.616.526.000|15.452.795.000|0,98951553|dentro|
| BBAS3 |5.708.463.641|5.708.971.478|1,00008896|dentro|
| BRSR3 |408.974.000|408.974.000|1,00000000|dentro; não demonstra igualdade dos direitos ON/PN|
| MGLU3 |774.601.561|775.658.438|1,00136441|dentro|
| USIM5 |1.230.942.660|1.230.942.660|1,00000000|dentro; agregado do emissor, não quantidadePNA|
| SBSP3 |700.219.438|3.506.830.477|5,00818784|fora; não ajustar evento automaticamente|
| KLBN11 |6.135.427.665literal|6.152.895.333literal|indisponível|escala indeterminada, sem usar§7.7como permissão implícita|

Fora:AZUL3,BMEB4,CYRE3,HYPE3,NATU3,SBSP3. Sem razão:ASAI3,BRML3,COGN3,KLBN11,NTCO3,PINE4,QUAL3,RECV3,SANB11,TIMS3,VIVT3. Não inferir a causa econômica de cada variação só dessas quantidades.

**Limites:** fotografia do conteúdo, não avaliação de métodos, elegibilidade setorial, cobertura histórica, auditoria de entrega/coleta ou prova de todos os eventos. Nenhum yfinance atual foi coletado para inventar comparação histórica. Não se chama `composicao_mais_recente` simulando downloads ausentes; lê-se explicitamente somente os dois ZIPs. As datas da amostra sãoDFP2025-12-31 eITR2026-06-30 nos controles acima, versões noJSON. Divergências/modelo/tempo seguem suas guardas antes de qualquer aplicação real.

Reprodução local: `/tmp/2c34-medida.py` e `/tmp/2c34-medida-log.txt`; selecionarCNPJ no índice público, ler `composicao_capital` por `_read_raw`, escolher referência/versão, chamar `composicao_do_documento` e `_escala_da_composicao`, multiplicar total pelo fator deEscala; só dividir quando ambas quantidades são positivas/determinadas. O JSON permanente conserva os insumos resumidos e os resultados para auditoria mesmo sem os temporários.

## Destino

Clarificação textual da fichaGordon§3, sem fórmula/regra/versão econômica nova. Nenhum bug reproduzido contra o contratoGordon vigente, portanto nenhum xfail ou fix artificial. A confirmação§7.7 continua obrigatória em seu ramo próprio. Mudança dessa política exige ficha auditada/aprovada; não é executada neste item.
