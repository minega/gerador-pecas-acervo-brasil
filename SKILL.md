---
name: gerador-pecas-acervo-brasil
description: Organize um acervo jurídico local de peças brasileiras e gere novas minutas, pareceres e análises a partir das próprias peças do usuário. Use quando for necessário catalogar PDFs/DOCXs/TXTs/MDs, importar arquivos de uma pasta externa, extrair texto, classificar tipos de peças, reaproveitar modelos do acervo ou redigir petições e análises contratuais em português jurídico brasileiro formal.
---

# Gerador de Peças por Acervo

## Visão geral

Use esta skill para transformar o workspace do usuário em um acervo reutilizável de peças jurídicas, sem depender do seu acervo pessoal. O foco é separar método de conteúdo: a skill entrega o fluxo, os scripts e os modelos; cada advogado alimenta o próprio `acervo_pecas/`.

## Regra de execução no app do Codex

Quando esta skill for acionada dentro do app do Codex, o agente deve tentar executar o setup necessário por conta própria. Não tratar o bootstrap manual como fluxo padrão.

- Se `acervo_pecas/` não existir, criar automaticamente a estrutura inicial.
- Priorizar execução automática em vez de pedir ao usuário que rode comandos.
- Só instruir execução manual se a execução pelo próprio agente falhar ou estiver bloqueada.
- Depois do bootstrap, seguir normalmente com catalogação, organização e redação.

## Fluxo base

1. Verificar se existe `acervo_pecas/` no workspace.
2. Se não existir, criar a estrutura automaticamente, nesta ordem de preferência:

- em Windows, executar `scripts/bootstrap_acervo.ps1`;
- se necessário, usar `scripts/bootstrap_acervo.cmd`;
- se Python estiver disponível, usar `scripts/bootstrap_acervo.py`.

Referência de comandos:

```text
python <skill_dir>/scripts/bootstrap_acervo.py
```

ou, em Windows sem Python:

```text
powershell -ExecutionPolicy Bypass -File <skill_dir>/scripts/bootstrap_acervo.ps1
```

ou:

```text
<skill_dir>\scripts\bootstrap_acervo.cmd
```

3. Se o usuário informar uma pasta externa com documentos:

- com Python disponível, importar automaticamente para `acervo_pecas/entrada_novas/` com:

```text
python <skill_dir>/scripts/importar_pasta_externa.py --origem "<caminho>" --modo <pecas|processo>
```

- sem Python, orientar o usuário a copiar os arquivos manualmente para `acervo_pecas/entrada_novas/`.

4. Para catalogar peças novas, preferir o ciclo automático:

```text
python <skill_dir>/scripts/catalogar_acervo.py --acervo acervo_pecas
```

Esse fluxo deve:

- extrair texto;
- classificar o tipo principal;
- mover o original para `catalogadas/<tipo>/`;
- criar `metadados/Pxxxx.md`;
- atualizar `indices/indice_pecas.md`;
- atualizar `indices/mapa_tipos.md`;
- atualizar `tipos/<tipo>/ORIENTACOES.md`;
- gerar plano pós-decisão quando houver `processo_integral`.

5. Sem Python, o agente deve reproduzir manualmente o mesmo padrão estrutural.

6. Extrair texto dos arquivos que serão reaproveitados:

- com Python disponível:

```text
python <skill_dir>/scripts/extract_legal_text.py --input acervo_pecas/entrada_novas --output acervo_pecas/texto_extraido
```

- sem Python, trabalhar diretamente com arquivos `.md` e `.txt` quando existirem e tratar PDFs/DOCXs como material a ser lido caso a caso, sem prometer extração automática.

7. Classificar os arquivos lidos conforme `references/classificacao_tipos.md`.
8. Redigir a peça ou análise usando primeiro o acervo do mesmo tipo, depois tipos relacionados e, por fim, os templates em `assets/templates/`.
9. Antes da minuta final, verificar `references/dados_minimos_por_tipo.md` e devolver apenas:
   - `dados_confirmados`
   - `dados_faltantes`
   - `riscos_se_nao_informar`

## Intenções que devem acionar a skill

- "Organize minhas peças."
- "Configure meu acervo para mim."
- "Prepare o ambiente para começar a usar meu acervo."
- "Catalogue minhas peças novas."
- "Organize o que está em entrada_novas."
- "Vou te passar uma pasta com petições."
- "Criei uma contestação e quero guardar no acervo."
- "Gere uma petição com base nas minhas peças."
- "Analise este contrato para o cliente."
- "Quero reaproveitar meu acervo para outra minuta."

## Regras de redação e segurança

- Redigir sempre em português brasileiro formal.
- Não inventar fatos, datas, provas, valores, precedentes ou dispositivos.
- Em petições judiciais, usar tópicos principais em numeração romana.
- Não numerar todos os parágrafos; numerar apenas subtópicos autônomos e os pedidos.
- Em fatos, fundamentos e tutela de urgência, preferir texto corrido.
- Encerrar cada tópico de fundamentação com pedido expresso, preferencialmente iniciado por `Requer-se, portanto, ...`.
- O último tópico da petição deve ser `Dos Pedidos`.
- Remover artefatos de formatação importada antes da entrega final.
- Quando a resposta depender de lei vigente, precedente atual ou entendimento jurisprudencial atual, confirmar em fonte oficial no momento da redação.

## Como usar os recursos

### `references/`

Ler apenas o necessário:

- `references/estrutura_acervo.md`: usar quando for preciso montar o acervo do zero ou explicar a estrutura a terceiros.
- `references/classificacao_tipos.md`: usar para classificar peças e escolher o tipo principal.
- `references/dados_minimos_por_tipo.md`: usar antes de redigir a minuta final.
- `references/legislacao_ritos_base_brasil.md`: usar para enquadramento processual mínimo e links oficiais.
- `references/guia_estilos_redacao.md`: usar para ajustar `estilo=<expositivo|objetivo|equilibrado>`.

### `scripts/`

- `scripts/bootstrap_acervo.py`: cria a estrutura padrão de `acervo_pecas/`.
- `scripts/bootstrap_acervo.ps1`: cria a estrutura padrão em Windows sem depender de Python.
- `scripts/bootstrap_acervo.cmd`: atalho para executar o bootstrap em Windows com duplo clique.
- `scripts/importar_pasta_externa.py`: traz apenas arquivos novos/editados de uma pasta externa.
- `scripts/catalogar_acervo.py`: executa a catalogação ponta a ponta das peças novas.
- `scripts/extract_legal_text.py`: extrai texto de PDF, DOCX, TXT e MD para `.md`.
- `scripts/gerar_plano_pos_decisao.py`: gera plano de providências para arquivos `processo_*.md`.

### `assets/`

- `assets/templates/`: modelos base neutros para quando o acervo ainda estiver pequeno.
- `assets/checklists/`: checklists para revisão final, análise de caso e análise contratual.

## Saídas mínimas esperadas

### Catalogação

- arquivos organizados em `acervo_pecas/catalogadas/<tipo>/`
- texto extraído em `acervo_pecas/texto_extraido/`
- metadados em `acervo_pecas/metadados/`
- índices atualizados em `acervo_pecas/indices/`
- orientações por tipo atualizadas em `acervo_pecas/tipos/<tipo>/ORIENTACOES.md`

### Redação

- minuta em `casos/<id>/saida/` quando houver um caso definido
- ou minuta estruturada no chat, com pendências, quando o caso ainda não estiver montado
- para análise contratual, saída em `analises/`

## Observação de portabilidade

Esta skill foi feita para ser compartilhada sem levar peças reais do autor. Ao instalá-la em outro computador, o destinatário deve preencher o próprio `acervo_pecas/` com seus documentos.

## Modo sem Python

Se o computador do usuário não tiver Python:

- usar `bootstrap_acervo.ps1` ou `bootstrap_acervo.cmd`, preferencialmente executados pelo próprio Codex;
- copiar manualmente as peças para `acervo_pecas/entrada_novas/`;
- usar a skill principalmente como método de organização, classificação e redação, mesmo quando a catalogação precisar ser reproduzida manualmente;
- tratar os scripts em Python como opcionais, úteis apenas para automação adicional.
