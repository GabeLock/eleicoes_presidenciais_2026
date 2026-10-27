# ADR 0004 — Códigos canônicos e reconciliação entre versões dos arquivos

Data: 2026-10-26 · Status: aceita

**Contexto.** A coleta nacional do 1º turno de 2026 mostrou que:
1. o arquivo por zona grava `CD_MUNICIPIO` de AC, AM, AP, MA, PA, RO e RR sem o zero inicial,
   enquanto o arquivo por seção o mantém;
2. os arquivos por seção foram gerados em 05–06/10/2026 e os por zona em 25/10/2026 —
   versões diferentes da mesma totalização;
3. seções não instaladas (41, todas no exterior) mantêm aptos com comparecimento e abstenção
   zerados; o campo vem como `Sim`/`Não`, embora o leiame indique `S`/`N`.

**Decisão.**
- Na Silver, `cd_municipio_tse` é canonizado com 5 dígitos, `zona` e `secao` com 4
  (`lpad`, texto). O valor bruto fica em `<coluna>_original`.
- A identidade aptos = comparecimento + abstenção é verificada só em seções instaladas;
  as não instaladas são contadas e reportadas.
- Os arquivos por município/zona são **complementares**: reconciliam a camada por seção
  (zona e município) com checagens não críticas e alimentam `gold_dim_candidatura`.
  Divergências entre versões são reportadas e explicadas, nunca forçadas.

**Resultado (1º turno 2026, nacional + exterior).** Aptos, comparecimento, abstenção, brancos
e nulos reconciliam exatamente em 6.292 zonas e 5.757 municípios. Votos nominais diferem em
5.246 votos (mesmo total nos níveis zona, município e candidato) — **explicado em 27/10/2026**:
são os votos da candidatura 28, classificados como nulos técnicos na versão de 25/10 (ADR 0005).
