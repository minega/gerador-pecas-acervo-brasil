# Taxonomia de tipos (base inicial)

## Contratos
- contrato_compra_e_venda
- contrato_locacao
- contrato_prestacao_servicos

## Peticoes civeis
- peticao_inicial
- contestacao
- replica
- impugnacao_documentos
- peticao_de_custas
- peticao_juntada
- peticao_citacao_negativa

## Recursos
- agravo_instrumento
- apelacao
- contrarrazoes_apelacao

## Notificacoes extrajudiciais
- notificacao_extrajudicial_cobranca

# Heuristicas rapidas
- Documento com clausulas de objeto, preco, prazo e obrigacoes entre partes: contrato.
- Documento com enderecamento ao juizo e requerimentos processuais: peticao.
- Documento com ataque a decisao/sentenca e pedido de reforma: recurso.
- Documento com foco em guia, preparo, recolhimento, complementacao de custas: peticao_de_custas.
- Documento dirigido a pessoa fisica/juridica para constituicao em mora e cobranca antes da via judicial: notificacao_extrajudicial_cobranca.

# Confianca
- alta: conteudo textual confirma tipo com clareza.
- media: tipo inferido por nome + trechos parciais.
- baixa: sem texto extraido; classificar provisoriamente e marcar pendencia.
