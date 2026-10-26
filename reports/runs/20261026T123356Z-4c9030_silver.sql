
CREATE OR REPLACE TABLE silver_votos_secao AS
WITH base AS (
    SELECT CAST("ANO_ELEICAO" AS INTEGER) AS ano, CAST("NR_TURNO" AS INTEGER) AS turno, trim("SG_UF") AS uf, trim("CD_MUNICIPIO") AS cd_municipio_tse, trim("NM_MUNICIPIO") AS nm_municipio, trim("NR_ZONA") AS zona, trim("NR_SECAO") AS secao, trim("CD_CARGO") AS cd_cargo, upper(trim("DS_CARGO")) AS ds_cargo, trim("NR_VOTAVEL") AS nr_votavel, trim("NM_VOTAVEL") AS nm_votavel, CAST("QT_VOTOS" AS BIGINT) AS qt_votos, trim("DT_GERACAO") AS dt_geracao, trim("HH_GERACAO") AS hh_geracao, trim("SQ_CANDIDATO") AS sq_candidato, trim("NR_LOCAL_VOTACAO") AS nr_local_votacao, '2d42006d0f6c6e00bad83f5c23cd3d78cd3e3182dbc1ad6718222b6b132c23e1' AS fonte_sha256
    FROM read_csv('/home/runner/work/eleicoes_presidenciais_2026/eleicoes_presidenciais_2026/data/bronze/_extraido/2d42006d0f6c/votacao_secao_2026_BR.csv', delim=';', header=true, quote='"', all_varchar=true, encoding='latin-1')
    WHERE upper(trim("DS_CARGO")) = 'PRESIDENTE'
)
SELECT *, CASE WHEN nr_votavel = '95' THEN 'branco' WHEN nr_votavel = '96' THEN 'nulo' ELSE 'candidato' END AS tipo_votavel FROM base;


CREATE OR REPLACE TABLE silver_participacao_secao AS
SELECT CAST("ANO_ELEICAO" AS INTEGER) AS ano, CAST("NR_TURNO" AS INTEGER) AS turno, trim("SG_UF") AS uf, trim("CD_MUNICIPIO") AS cd_municipio_tse, trim("NM_MUNICIPIO") AS nm_municipio, trim("NR_ZONA") AS zona, trim("NR_SECAO") AS secao, trim("CD_CARGO") AS cd_cargo, upper(trim("DS_CARGO")) AS ds_cargo, CAST("QT_APTOS" AS BIGINT) AS qt_aptos, CAST("QT_COMPARECIMENTO" AS BIGINT) AS qt_comparecimento, CAST("QT_ABSTENCOES" AS BIGINT) AS qt_abstencoes, CAST("QT_VOTOS_NOMINAIS" AS BIGINT) AS qt_votos_nominais, CAST("QT_VOTOS_BRANCOS" AS BIGINT) AS qt_votos_brancos, CAST("QT_VOTOS_NULOS" AS BIGINT) AS qt_votos_nulos, trim("DT_GERACAO") AS dt_geracao, trim("HH_GERACAO") AS hh_geracao, CAST("QT_VOTOS_LEGENDA" AS BIGINT) AS qt_votos_legenda, CAST("QT_VOTOS_ANULADOS_APU_SEP" AS BIGINT) AS qt_votos_anulados_apu_sep, trim("DS_ORIGEM_VOTO") AS ds_origem_voto, trim("ST_SECAO_INSTALADA") AS st_secao_instalada, trim("ST_SECAO_ANULADA") AS st_secao_anulada, '11a62c3a604e8b73fc328617b7688d2c635de1c76df02ba63b8f77879512f573' AS fonte_sha256
FROM read_csv('/home/runner/work/eleicoes_presidenciais_2026/eleicoes_presidenciais_2026/data/bronze/_extraido/11a62c3a604e/detalhe_votacao_secao_2026_BR.csv', delim=';', header=true, quote='"', all_varchar=true, encoding='latin-1')
WHERE upper(trim("DS_CARGO")) = 'PRESIDENTE';
