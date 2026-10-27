# ADR 0005 — Nulos técnicos: votos de candidatura inapta no dia da eleição

Data: 2026-10-27 · Status: aceita (proposta por Claude; revisão do responsável no PR)

**Contexto (pendência I-01 / ação A-04).** No 1º turno de 2026 os votos nominais do arquivo por
seção (`votacao_secao_2026_BR`, gerado 06/10; `detalhe_votacao_secao`, 05/10 e 26/10) superavam
em **5.246** os do arquivo por município/zona (gerados 25/10). O diagnóstico
`reports/diagnosticos/20261027T134148Z-645d93/` (execução 40514006404) mostra que:

1. a diferença inteira é de **uma candidatura**: `NR_VOTAVEL = 28` tem 5.246 votos em 5.145
   linhas do arquivo por seção e **não aparece** em `votacao_candidato_munzona` (todas as demais
   13 candidaturas do 1º turno batem voto a voto, em todas as UFs);
2. `detalhe_votacao_munzona` traz `QT_VOTOS_NULOS_TECNICOS` = **5.246** no 1º turno, e
   `QT_TOTAL_VOTOS_NULOS` = 3.674.249 = 3.669.003 nulos digitados + 5.246;
3. nas **2.148 zonas** com diferença, ela é igual a `QT_VOTOS_NULOS_TECNICOS` da zona
   (0 exceções); aptos, comparecimento, abstenção, brancos e nulos digitados reconciliam exatamente;
4. o leiame 2026 (`detalhe_votacao_munzona`) define nulos técnicos como votos dados a candidatura
   ou legenda **inapta no dia da eleição** que constava na urna por não ter sido possível retirá-la
   a tempo.

Conclusão: as versões por seção (05–06/10) contam como nominais votos que a totalização posterior
(25/10) classifica como nulos técnicos. Não é erro de soma do pipeline; é diferença de
classificação entre versões. A situação jurídica da candidatura deve ser confirmada no
`consulta_cand_2026` (inventariado em 27/10; mapeamento de colunas pendente) e na consulta oficial
(A-03) — esta ADR não afirma o motivo jurídico da inaptidão.

**Decisão.**
- `configs/sources.yml` → `votacao_secao.nulos_tecnicos` declara, por ano e turno, os
  `NR_VOTAVEL` reclassificados (2026: turno 1 → `28`). Na Silver eles recebem
  `tipo_votavel = 'nulo_tecnico'`: **não** são candidatos, **não** são somados aos nulos digitados
  (96) e ficam fora dos válidos.
- `silver_participacao_secao` ganha `qt_votos_nulos_tecnicos` e
  `qt_votos_validos = nominais + legenda − nulos técnicos` (junção 1:1 por seção);
  `gold_participacao_municipio` preserva o bruto em `qt_votos_nominais_detalhe`.
- A reconciliação seção → zona passa a comparar válidos harmonizados com
  `QT_VOTOS_NOMINAIS_VALIDOS` e, quando o arquivo por zona trouxer a coluna, nulos técnicos com
  `QT_VOTOS_NULOS_TECNICOS` — uma nova reclassificação do TSE aparece como divergência.

**Consequências.** Válidos do 1º turno nacional passam de 119.306.034 para 119.300.788, igual ao
arquivo por zona. Percentuais sobre válidos mudam na 5ª casa; votos e margem dos finalistas não
mudam (a candidatura 28 não é finalista). A regra é declarativa e auditável; se o TSE republicar
os arquivos por seção já com a reclassificação, a entrada deixa de ter efeito (não haverá linhas
com o código) e deve ser revista.
