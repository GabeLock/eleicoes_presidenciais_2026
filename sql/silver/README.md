# Silver

As tabelas Silver (`silver_votos_secao`, `silver_participacao_secao`) são geradas por
`src/eleicoes/transformation/silver.py` a partir do mapeamento de colunas em `configs/sources.yml`.

O SQL é montado em código (e não em arquivo estático) porque os nomes de coluna vêm do
cabeçalho real e do dicionário de cada ano; o SQL gerado em cada execução é salvo em
`reports/runs/<run_id>_silver.sql` para auditoria.

Regras:
- códigos (município TSE, zona, seção, votável, cargo) permanecem **texto**, com zeros à esquerda;
- contagens são convertidas com `CAST` estrito — falha de conversão interrompe a execução;
- o filtro de cargo usa `DS_CARGO` normalizado (`upper(trim(...)) = 'PRESIDENTE'`) e registra os
  `CD_CARGO` encontrados para conferência com o dicionário;
- linhas duplicadas na granularidade declarada **não** são descartadas em silêncio: são contadas e
  bloqueiam a publicação.
