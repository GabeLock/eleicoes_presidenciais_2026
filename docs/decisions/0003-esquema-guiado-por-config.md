# ADR 0003 — Esquema guiado por configuração e validado contra o arquivo real

Data: 2026-10-26 · Status: aceita

**Contexto.** A especificação proíbe inventar nomes de campos. O dicionário de 2026 só é obtido
dentro dos ZIPs, que ainda não foram baixados.

**Decisão.** Os nomes de coluna ficam em `configs/sources.yml` com `status_layout: a_confirmar`
(ponto de partida: layout de 2022). Em cada ingestão o pipeline:
1. detecta encoding, separador e cabeçalho a partir do próprio arquivo;
2. extrai o leiame para `reports/dicionarios/`;
3. compara o cabeçalho real com as colunas obrigatórias e marca o recurso como `incompativel`
   se faltar alguma, bloqueando Silver/Gold.

O SQL da Silver é gerado a partir do mapeamento (identificadores validados por regex) e salvo por
execução para auditoria.

**Consequências.** Nenhuma tabela é construída sobre nomes não confirmados. Ajustes ao layout de
2026 entram por PR citando o leiame.
