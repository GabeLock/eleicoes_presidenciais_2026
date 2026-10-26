-- Gold: votos por município × turno × votável (Presidência).
-- Granularidade: ano × turno × uf × cd_municipio_tse × nr_votavel. Exterior (uf = 'ZZ') é mantido.
CREATE OR REPLACE TABLE gold_votos_municipio AS
SELECT
    ano,
    turno,
    uf,
    cd_municipio_tse,
    any_value(nm_municipio)             AS nm_municipio,
    nr_votavel,
    any_value(nm_votavel)               AS nm_votavel,
    tipo_votavel,
    sum(qt_votos)::BIGINT               AS qt_votos,
    count(DISTINCT zona || '-' || secao) AS n_secoes
FROM silver_votos_secao
GROUP BY ano, turno, uf, cd_municipio_tse, nr_votavel, tipo_votavel;
