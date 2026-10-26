-- Gold: painel de margem entre os finalistas A e B por município, nos dois turnos.
-- Parâmetros: $a, $b = nr_votavel dos finalistas (A = líder do 1º turno nacional).
-- Contribuição_i = M_i2 − M_i1; a soma sobre todos os territórios (inclusive ZZ) é a variação nacional.
CREATE OR REPLACE TABLE gold_margem_municipio AS
WITH v AS (
    SELECT uf, cd_municipio_tse, turno,
           sum(qt_votos) FILTER (WHERE nr_votavel = $a) AS votos_a,
           sum(qt_votos) FILTER (WHERE nr_votavel = $b) AS votos_b,
           sum(qt_votos) FILTER (WHERE tipo_votavel = 'candidato') AS validos_votos
    FROM gold_votos_municipio
    GROUP BY uf, cd_municipio_tse, turno
),
p AS (
    SELECT uf, cd_municipio_tse, turno, nm_municipio, qt_aptos, qt_comparecimento,
           qt_abstencoes, qt_votos_brancos, qt_votos_nulos, qt_votos_validos
    FROM gold_participacao_municipio
),
j AS (
    SELECT p.*, coalesce(v.votos_a, 0) AS votos_a, coalesce(v.votos_b, 0) AS votos_b,
           coalesce(v.validos_votos, 0) AS validos_votos
    FROM p LEFT JOIN v USING (uf, cd_municipio_tse, turno)
)
SELECT
    uf,
    cd_municipio_tse,
    any_value(nm_municipio) AS nm_municipio,
    max(votos_a)           FILTER (WHERE turno = 1) AS votos_a_1,
    max(votos_b)           FILTER (WHERE turno = 1) AS votos_b_1,
    max(qt_votos_validos)  FILTER (WHERE turno = 1) AS validos_1,
    max(validos_votos)     FILTER (WHERE turno = 1) AS validos_votos_1,
    max(qt_aptos)          FILTER (WHERE turno = 1) AS aptos_1,
    max(qt_comparecimento) FILTER (WHERE turno = 1) AS comparecimento_1,
    max(qt_votos_brancos)  FILTER (WHERE turno = 1) AS brancos_1,
    max(qt_votos_nulos)    FILTER (WHERE turno = 1) AS nulos_1,
    max(votos_a)           FILTER (WHERE turno = 2) AS votos_a_2,
    max(votos_b)           FILTER (WHERE turno = 2) AS votos_b_2,
    max(qt_votos_validos)  FILTER (WHERE turno = 2) AS validos_2,
    max(validos_votos)     FILTER (WHERE turno = 2) AS validos_votos_2,
    max(qt_aptos)          FILTER (WHERE turno = 2) AS aptos_2,
    max(qt_comparecimento) FILTER (WHERE turno = 2) AS comparecimento_2,
    max(qt_votos_brancos)  FILTER (WHERE turno = 2) AS brancos_2,
    max(qt_votos_nulos)    FILTER (WHERE turno = 2) AS nulos_2,
    count(*)                                        AS n_turnos
FROM j
GROUP BY uf, cd_municipio_tse;
