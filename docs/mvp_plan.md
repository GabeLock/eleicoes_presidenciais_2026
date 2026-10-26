# Plano do MVP

Escopo: Presidência, 2026, dois turnos, todas as UFs + exterior, diagnóstico por município.

| # | Entrega | Critério de conclusão | Status |
|---|---|---|---|
| 1 | Inventário, documentação, decisões, esqueleto executável | Testes e lint verdes no CI; inventário real gerado pelo Actions | **Concluída** (PR #1) |
| 2 | Piloto MG com dados reais | Dois turnos presentes; esquema confirmado contra o leiame 2026; seção → município reconcilia exatamente; relatório de qualidade sem falha crítica | **Parcial**: 1º turno reconcilia; aguardando publicação do 2º turno |
| 3 | Nacional + exterior | Idem, com Σ municípios = Brasil e conferência contra o Relatório de Totalização BR/ZZ e a consulta oficial | Pendente |
| 4 | Gold, dashboard, relatório exploratório | Cada gráfico aponta para tabela e snapshot; cartões com denominador | Pendente |
| 5 | Modelos vs. baseline | Validação por blocos geográficos; limites documentados | Pendente |
| 6 | Relatório final | Achados sustentados, hipóteses rejeitadas, incertezas, próximos passos | Pendente |

## Sequência de execução

1. `make inventory` no Actions → confirma URLs, HTTP 200, tamanhos e `Last-Modified`.
2. `make ingest UF=MG` no Actions → SHA-256, cabeçalho real, leiame, turnos presentes.
3. Ajustar `configs/sources.yml` ao dicionário de 2026 (via PR, com o leiame citado).
4. `make transform UF=MG` → reconciliação e relatório de qualidade.
5. Só então: `UF=ALL`, reconciliação com totalização oficial e primeiras análises.

## Pendências conhecidas

- Confirmar se o arquivo `votacao_secao_2026_BR.zip` inclui o exterior (ZZ) e voto em trânsito (VT).
- **Aguardar a publicação do 2º turno** (em 26/10/2026 os arquivos só têm o 1º turno).
- Conferir códigos 95/96 (branco/nulo) nos dados de Presidente e reconciliar com a consulta oficial.
- `DT_RECEBIMENTO_BU_HOR_TSE` e `DT_PRIM_TOT_PARCIAL_HOR_TSE` dão horários por seção, mas não
  reconstituem sozinhos a sequência da divulgação (liderança durante a apuração segue indisponível).
- Localizar o conjunto de candidaturas 2026 e o grupo de comparecimento/abstenção.
- Definir a fonte da correspondência TSE–IBGE de municípios.
- Série histórica 2018/2022 (expansão inicial) e depois 1989–2014.
