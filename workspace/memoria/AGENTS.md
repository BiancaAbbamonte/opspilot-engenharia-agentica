# Memória longa do OpsPilot (AGENTS.md)

> Este arquivo é carregado no system prompt do Deep Agent a CADA execução
> (parâmetro `memory=["/memoria/AGENTS.md"]`). O próprio agente pode editá-lo
> para registrar aprendizados. Revise as mudanças no `git diff` como faria com
> um PR de um colega.

## Padrões da MercadoNimbus
- Fuso horário oficial dos relatórios: UTC (os logs já estão em UTC).
- Severidades: SEV1 = clientes sem conseguir comprar; SEV2 = degradação relevante; SEV3 = risco sem impacto.
- Toda afirmação em relatório precisa de evidência (métrica ou linha de log).

## Formato padrão de post-mortem (obrigatório)
```
# Post-mortem <ID> — <título>
## Resumo executivo (3 linhas, para diretoria)
## Linha do tempo (UTC)
## Causa raiz
## Evidências
## Sintomas e efeitos colaterais (o que NÃO era a causa)
## Mitigação aplicada / recomendada
## Ações de prevenção (com dono sugerido)
## Lições aprendidas
```

## Lições aprendidas (o agente acrescenta abaixo, 1 linha por lição)
- Fila de notificações crescendo costuma ser efeito colateral de retries da API produtora.
- Reduções bruscas de pool de conexões em banco/config podem se manifestar primeiro como latência e 503 na API dependente, antes de qualquer erro explícito no banco.
- Alerta de certificado TLS pode coexistir com incidentes de performance, mas não deve ser tratado como causa de latência sem evidência adicional.
