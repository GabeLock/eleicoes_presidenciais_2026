-- Gold: participação por município × turno (Presidência). Uma linha por unidade.
-- Votos válidos = nominais (+ legenda, se o recurso trouxer); brancos e nulos digitados ficam separados
-- dos votos anulados e apurados em separado (sub judice; QT_VOTOS_ANULADOS_APU_SEP), que
-- segundo o leiame "ainda não são votos válidos nem nulos" e NÃO são somados a nenhum dos dois.
CREATE OR REPLACE TABLE gold_participacao_municipio AS
SELECT
    ano,
    turno,
    uf,
    cd_municipio_tse,
    any_value(nm_municipio)                        AS nm_municipio,
    sum(qt_aptos)::BIGINT                          AS qt_aptos,
    sum(qt_comparecimento)::BIGINT                 AS qt_comparecimento,
    sum(qt_abstencoes)::BIGINT                     AS qt_abstencoes,
    sum(qt_votos_brancos)::BIGINT                  AS qt_votos_brancos,
    sum(qt_votos_nulos)::BIGINT                    AS qt_votos_nulos,
    sum(qt_votos_nominais + coalesce(qt_votos_legenda, 0))::BIGINT AS qt_votos_validos,
    sum(coalesce(qt_votos_anulados_apu_sep, 0))::BIGINT AS qt_votos_anulados_apu_sep,
    count(*) FILTER (WHERE st_secao_anulada = 'S') AS n_secoes_anuladas,
    count(*)                                       AS n_secoes
FROM silver_participacao_secao
GROUP BY ano, turno, uf, cd_municipio_tse;
