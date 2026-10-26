
CREATE OR REPLACE TABLE silver_votos_secao AS
WITH base AS (
    SELECT CAST("ANO_ELEICAO" AS INTEGER) AS ano, CAST("NR_TURNO" AS INTEGER) AS turno, trim("SG_UF") AS uf, trim("CD_MUNICIPIO") AS cd_municipio_tse, trim("NM_MUNICIPIO") AS nm_municipio, trim("NR_ZONA") AS zona, trim("NR_SECAO") AS secao, trim("CD_CARGO") AS cd_cargo, upper(trim("DS_CARGO")) AS ds_cargo, trim("NR_VOTAVEL") AS nr_votavel, trim("NM_VOTAVEL") AS nm_votavel, CAST("QT_VOTOS" AS BIGINT) AS qt_votos, trim("DT_GERACAO") AS dt_geracao, trim("HH_GERACAO") AS hh_geracao, trim("SQ_CANDIDATO") AS sq_candidato, trim("NR_LOCAL_VOTACAO") AS nr_local_votacao, '9353993de5cf03778aef44e01d4925e7ee105f5262491d344a2f0dbc956b0139' AS fonte_sha256
    FROM read_csv('/home/runner/work/eleicoes_presidenciais_2026/eleicoes_presidenciais_2026/data/bronze/_extraido/9353993de5cf/votacao_secao_2022_BR.csv', delim=';', header=true, quote='"', all_varchar=true, encoding='latin-1')
    WHERE upper(trim("DS_CARGO")) = 'PRESIDENTE'
)
SELECT *, CASE WHEN nr_votavel = '95' THEN 'branco' WHEN nr_votavel = '96' THEN 'nulo' ELSE 'candidato' END AS tipo_votavel FROM base;


CREATE OR REPLACE TABLE silver_participacao_secao AS
SELECT CAST("ANO_ELEICAO" AS INTEGER) AS ano, CAST("NR_TURNO" AS INTEGER) AS turno, trim("SG_UF") AS uf, trim("CD_MUNICIPIO") AS cd_municipio_tse, trim("NM_MUNICIPIO") AS nm_municipio, trim("NR_ZONA") AS zona, trim("NR_SECAO") AS secao, trim("CD_CARGO") AS cd_cargo, upper(trim("DS_CARGO")) AS ds_cargo, CAST("QT_APTOS" AS BIGINT) AS qt_aptos, CAST("QT_COMPARECIMENTO" AS BIGINT) AS qt_comparecimento, CAST("QT_ABSTENCOES" AS BIGINT) AS qt_abstencoes, CAST("QT_VOTOS_NOMINAIS" AS BIGINT) AS qt_votos_nominais, CAST("QT_VOTOS_BRANCOS" AS BIGINT) AS qt_votos_brancos, CAST("QT_VOTOS_NULOS" AS BIGINT) AS qt_votos_nulos, trim("DT_GERACAO") AS dt_geracao, trim("HH_GERACAO") AS hh_geracao, CAST("QT_VOTOS_LEGENDA" AS BIGINT) AS qt_votos_legenda, CAST("QT_VOTOS_ANULADOS_APU_SEP" AS BIGINT) AS qt_votos_anulados_apu_sep, trim("DS_ORIGEM_VOTO") AS ds_origem_voto, trim("ST_SECAO_INSTALADA") AS st_secao_instalada, trim("ST_SECAO_ANULADA") AS st_secao_anulada, 'ad22c50b9e6d9dfb096a2170680a190f1734895ba89d8977b95fd63ca02c03da' AS fonte_sha256
FROM read_csv('/home/runner/work/eleicoes_presidenciais_2026/eleicoes_presidenciais_2026/data/bronze/_extraido/ad22c50b9e6d/detalhe_votacao_secao_2022_BR.csv', delim=';', header=true, quote='"', all_varchar=true, encoding='latin-1')
WHERE upper(trim("DS_CARGO")) = 'PRESIDENTE';
