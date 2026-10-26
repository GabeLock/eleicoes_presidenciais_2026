# Dicionário de dados (Silver e Gold)

Nomes de origem (MAIÚSCULAS) seguem o layout de 2022 e estão **a confirmar** contra o leiame de
2026, extraído automaticamente para `reports/dicionarios/` em cada `make ingest`. A validação de
esquema bloqueia o pipeline se um campo obrigatório não existir.

## Silver

### `silver_votos_secao` — fato_votos
Granularidade: ano × turno × UF × município TSE × zona × seção × votável (Presidência).
Chave única verificada: (turno, uf, cd_municipio_tse, zona, secao, nr_votavel).

| Coluna | Tipo | Origem | Regra |
|---|---|---|---|
| ano, turno | INTEGER | ANO_ELEICAO, NR_TURNO | CAST estrito |
| uf | VARCHAR | SG_UF | ZZ = exterior (confirmado no arquivo _BR de 2026) |
| cd_municipio_tse | VARCHAR | CD_MUNICIPIO | texto canônico de 5 dígitos (`lpad`); bruto em `cd_municipio_tse_original`; **não** é código IBGE |
| nm_municipio | VARCHAR | NM_MUNICIPIO | trim |
| zona, secao | VARCHAR | NR_ZONA, NR_SECAO | texto canônico de 4 dígitos; brutos em `*_original` |
| cd_cargo / ds_cargo | VARCHAR | CD_CARGO / DS_CARGO | filtro `upper(trim(DS_CARGO)) = 'PRESIDENTE'` |
| nr_votavel / nm_votavel | VARCHAR | NR_VOTAVEL / NM_VOTAVEL | texto |
| tipo_votavel | VARCHAR | derivado | 95 → branco, 96 → nulo, demais → candidato (códigos a confirmar) |
| qt_votos | BIGINT | QT_VOTOS | CAST estrito |
| fonte_sha256 | VARCHAR | manifesto | rastreia o snapshot de origem |

### `silver_participacao_secao` — fato_participacao
Granularidade: ano × turno × UF × município × zona × seção (Presidência). Uma linha por seção.

| Coluna | Origem | Observação |
|---|---|---|
| qt_aptos, qt_comparecimento, qt_abstencoes | QT_APTOS, QT_COMPARECIMENTO, QT_ABSTENCOES | identidade aptos = comp. + abst. checada só em seções instaladas |
| st_secao_instalada, st_secao_anulada, ds_origem_voto | ST_SECAO_INSTALADA, ST_SECAO_ANULADA, DS_ORIGEM_VOTO | valores `Sim`/`Não` nos dados de 2026 (leiame diz S/N) |
| qt_votos_nominais | QT_VOTOS_NOMINAIS | base dos válidos |
| qt_votos_brancos, qt_votos_nulos | QT_VOTOS_BRANCOS, QT_VOTOS_NULOS | nulos **digitados** |
| qt_votos_legenda | QT_VOTOS_LEGENDA (opcional) | nulo se ausente |
| qt_votos_anulados_apu_sep | QT_VOTOS_ANULADOS_APU_SEP (opcional) | sub judice: nem válidos nem nulos (leiame); nunca somado |

## Gold

| Tabela | Granularidade | Uso |
|---|---|---|
| `gold_votos_municipio` | turno × UF × município × votável | votos por candidato, brancos, nulos |
| `gold_participacao_municipio` | turno × UF × município | aptos, comparecimento, abstenção, inválidos, válidos |
| `gold_margem_municipio` | UF × município (largo, turnos 1 e 2) | painel A × B |
| `gold_decomposicao_municipio` | UF × município | margem_1, margem_2, contribuição, participação no saldo, mudou_vencedor |
| `gold_dim_candidatura` | ano × turno × candidatura | nome de urna, partido, situação da candidatura, julgamento, destinação dos votos, situação de totalização, votos nominais e válidos (do arquivo por zona) |
| `resumo_virada.json` | nacional (ou escopo) | A, B, M1, M2, inversão |

### Silver complementar
- `silver_detalhe_munzona` — turno × município × zona (× voto em trânsito); reconciliação.
- `silver_candidato_munzona` — turno × município × zona × candidatura; situação jurídica.

Todas as camadas derivadas ficam em `data/<camada>/<ano>/` (2018, 2022 e 2026 configurados).

## Planejado (v2)

- `fato_perfil` — fotografia cadastral × seção × combinação de categorias; agregada à
  granularidade de destino **antes** de qualquer join com votos.
- `dim_eleicao`, `dim_territorio` e correspondência TSE–IBGE versionada
  (com auditoria de não encontrados e cardinalidade).
