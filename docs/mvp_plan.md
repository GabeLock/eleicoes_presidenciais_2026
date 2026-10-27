# Plano do MVP

Escopo: Presidência, 2026, dois turnos, todas as UFs + exterior, diagnóstico por município.

| # | Entrega | Critério de conclusão | Status |
|---|---|---|---|
| 1 | Inventário, documentação, decisões, esqueleto executável | Testes e lint verdes no CI; inventário real gerado pelo Actions | **Concluída** (PR #1) |
| 2 | Piloto MG com dados reais | Dois turnos presentes; esquema confirmado contra o leiame 2026; seção → município reconcilia exatamente; relatório de qualidade sem falha crítica | **Concluída** (27/10): dois turnos 2026 presentes (votacao_secao gerado 26/10 12:07:25, sha256 `c928321f63f2`; detalhe_votacao_secao 26/10 09:49:06, `8ef9ce3a85cd`); relatório liberado, sem falha crítica (execução 40441896364) |
| 3 | Nacional + exterior | Idem, com Σ municípios = Brasil e conferência contra o Relatório de Totalização BR/ZZ e a consulta oficial | **Parcial**: dois turnos nacional + exterior liberados (execução 40442163704, relatório `20261027T030648Z-130719`); falta conferência contra a totalização oficial (A-03) e explicar I-01 |
| 4 | Gold, dashboard, relatório exploratório | Cada gráfico aponta para tabela e snapshot; cartões com denominador | Pendente |
| 5 | Modelos vs. baseline | Validação por blocos geográficos; limites documentados | Pendente |
| 6 | Relatório final | Achados sustentados, hipóteses rejeitadas, incertezas, próximos passos | Pendente |

## Monitoramento do 2º turno

Tarefa agendada (08:01, 16:01 e 00:01, horário de Brasília) dispara a etapa `verificar` do
workflow Pipeline. Se o TSE republicar os arquivos, o workflow roda ingestão + piloto MG e
publica um branch `resultados/<run_id>`; a tarefa confere `NR_TURNO = 2` no manifesto e avisa.

## Sequência de execução

1. `make inventory` no Actions → confirma URLs, HTTP 200, tamanhos e `Last-Modified`.
2. `make ingest UF=MG` no Actions → SHA-256, cabeçalho real, leiame, turnos presentes.
3. Ajustar `configs/sources.yml` ao dicionário de 2026 (via PR, com o leiame citado).
4. `make transform UF=MG` → reconciliação e relatório de qualidade.
5. Só então: `UF=ALL`, reconciliação com totalização oficial e primeiras análises.

## Pendências conhecidas

- 2º turno publicado pelo TSE nos arquivos por seção (detectado em 27/10/2026 03:02 UTC). Os arquivos por
  município/zona (`detalhe_votacao_munzona`, `votacao_candidato_munzona`) seguem só com o 1º turno
  (gerados 25/10): as checagens seção → zona do 2º turno ficam pendentes até a republicação.
- ~~Conferir códigos 95/96~~ — confirmados em 27/10 (A-06). Falta reconciliar com a consulta oficial e o
  Relatório de Totalização BR/ZZ (A-03).
- `DT_RECEBIMENTO_BU_HOR_TSE` e `DT_PRIM_TOT_PARCIAL_HOR_TSE` dão horários por seção, mas não
  reconstituem sozinhos a sequência da divulgação (liderança durante a apuração segue indisponível).
- ~~Explicar os 5.246 votos nominais~~ — nulos técnicos da candidatura 28 (ADR 0005, 27/10).
- Mapear `consulta_cand_2026` (cabeçalho + leiame coletados) e confirmar a situação da candidatura 28.
- Grupo de comparecimento/abstenção inventariado (27/10); arquivo de 21/10, anterior ao 2º turno — fase v2.
- Definir a fonte da correspondência TSE–IBGE de municípios.
- Série histórica 2018/2022 (expansão inicial) e depois 1989–2014.
