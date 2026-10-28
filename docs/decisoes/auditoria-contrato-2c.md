# Auditoria pelo contrato vigente — F2C-8

`python auditoria.py TSTA3` conserva os modos de diagnóstico e os relatórios TXT/JSON. Dados reais exigem as fontes normais da cascata. Testes usam apenas dados sintéticos e não acessam carteira nem rede.

A seção de valuation chama `ValuationEngine.processar`, captura uma única avaliação dos métodos e registra seus resultados ou abstenções e motivos, além do catálogo versionado do registro. Não replica Graham, Bazin, Lynch, Gordon, sigmoide, mistura de lentes ou taxa Selic acrescida de prêmio. `--selic` continua diagnóstico da fonte, sem simular preços com fórmulas aposentadas. A validação de domínios não certifica a metodologia vigente: ela continua sujeita às fichas e à auditoria externa.

A série anual aparece como contagem de observações e metadados de cobertura, sem imprimir os exercícios completos no bloco de dados ou no prompt. O JSON mantém o resultado do contrato e o resumo da série. Não é um arquivo de evidências históricas point-in-time.

Para FII, falta de valor permanece `None`; falha do motor resulta em motivo explícito e ausência de valor/upside. Não se usa preço como valor justo nem zero como upside de uma abstenção. É o BUG-2C-29: dois testes de regressão do caminho principal, antes vermelhos, agora passam. O helper não cria score ou classificação substitutos quando o motor falha.

Invariantes independentes verificam números finitos, score em [0,100] e ausência de upside quando falta valor. Não comparam a fórmula com ela própria. A contraprova em processo isolado substituiu a validação por uma função que aceita tudo: cinco testes falharam, sem editar a produção. Os métodos puros e seus números/golden não mudam. Esta alteração é de orquestração e diagnóstico, não um item de cobertura ou módulo novo de cálculo financeiro; o gate de mutação de cálculo não é atribuído ao script inteiro de IO.
