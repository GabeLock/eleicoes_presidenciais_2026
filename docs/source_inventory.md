# Inventário de fontes

**Versão:** 0.3 · **Levantamento do catálogo:** 2026-10-26 (API CKAN; 94 recursos nos dois conjuntos); ampliado em
2026-10-27 com `candidatos-2026` (92 recursos) e o grupo `comparecimento-e-abstencao` (3) ·
**Primeiros snapshots:** 2026-10-26 10:53–10:57 UTC (GitHub Actions; ver tabela abaixo).

> Recursos não coletados constam com os metadados do catálogo. Para os coletados, os valores vêm
> dos manifestos em `data/manifests/` (gerados por `make ingest`); o texto do dicionário oficial
> (leiame 2026) está em `reports/dicionarios/leiame.txt`.

## Snapshots coletados

| Recurso | SHA-256 | Bytes (ZIP) | Gerado na fonte (DT/HH_GERACAO) | Last-Modified (CDN) | Coletado (UTC) | Turnos | Linhas | Status |
|---|---|---|---|---|---|---|---|---|
| `votacao_secao_2026_BR.zip` (Presidente) | `2d42006d0f6c6e00bad83f5c23cd3d78cd3e3182dbc1ad6718222b6b132c23e1` | 161.616.519 | 06/10/2026 14:03:43 | Tue, 06 Oct 2026 19:22:49 GMT | 2026-10-26T10:57:26 | 1 | 3.800.511 | **parcial** |
| `detalhe_votacao_secao_2026.zip` | `11a62c3a604e8b73fc328617b7688d2c635de1c76df02ba63b8f77879512f573` | 176.923.175 | 05/10/2026 14:03:30 | Wed, 07 Oct 2026 20:54:59 GMT | 2026-10-26T10:57:41 | 1 | — | **parcial** |
| `votacao_secao_2026_BR.zip` (Presidente) — **2º turno** | `c928321f63f2d095706fca73d4607c048d2ada23bda6876455d6911aaf1bc9c1` | 241.891.087 | 26/10/2026 12:07:25 | Mon, 26 Oct 2026 17:42:32 GMT | 2026-10-27T03:05:23 | 1, 2 | 5.731.614 | **disponível** |
| `detalhe_votacao_secao_2026.zip` — **2º turno** | `8ef9ce3a85cde260471faf7a83a9b4f5ccf3993fdda942aacaa658574344789c` | 234.357.769 | 26/10/2026 09:49:06 | Mon, 26 Oct 2026 15:35:35 GMT | 2026-10-27T03:05:57 | 1, 2 | 998.496 (`_BR`) | **disponível** |
| `detalhe_votacao_munzona_2026.zip` | `7f6f40a14ba805b453b1d85c18fe12eec4225cfbf2ba21989ecd7c4e15a12043` | 2.511.067 | 25/10/2026 12:33:24 | Sun, 25 Oct 2026 15:58:00 GMT | 2026-10-27T03:06:12 | 1 | 6.292 | **parcial** (sem 2º turno) |
| `votacao_candidato_munzona_2026.zip` | `cef14bbf848da85cb1462657c9d3c95cd2d76d9b884c4ccd579e0384035be9a6` | 452.159.174 | 25/10/2026 12:31:43 | Sun, 25 Oct 2026 16:16:37 GMT | 2026-10-27T03:06:25 | 1 | 75.504 | **parcial** (sem 2º turno) |
| `votacao_secao_2026_MG.zip` | `56826e143f4fb2628a6f82f9697a3e4ad87094ed89782ad8ab51d06c7c30877a` | 255.063.843 | 06/10/2026 14:03:43 | Tue, 06 Oct 2026 19:32:09 GMT | 2026-10-26T10:53:42 | 1 | 5.923.656 | **incompatível com o MVP** (não contém Presidente) |

Achados da primeira coleta:
- **2º turno ausente**: nenhum arquivo traz `NR_TURNO = 2`. A base fica bloqueada até a
  republicação ("arquivo atualizado ao final de cada turno").
- **Presidente só nos arquivos `_BR`** (abrangência federal). Os arquivos por UF trazem os cargos
  3 (Governador), 5 (Senador), 6 (Dep. Federal) e 7 (Dep. Estadual). No detalhe por seção, o ZIP
  único contém membros `_<UF>`, `_BR` (Presidente, 176 MB), `_BRASIL` (900 MB) e `_ZZ` (606 bytes).
- **Layout conferido** com o leiame 2026: latin-1, `;`, campos entre aspas; `#NULO` ↔ `-1` e `#NE` ↔ `-3`
  em campos numéricos; `SG_UF` pode valer `BR`, `VT` (voto em trânsito) ou `ZZ` (exterior).
- **Piloto MG, 1º turno**: todas as checagens de integridade passaram (unicidade, contagens não
  negativas, aptos = comparecimento + abstenção, seção → município, válidos entre os dois
  arquivos) — `reports/quality/20261026T105750Z-a590e2.md`.

## Achados da coleta nacional (1º turno 2026) e do teste 2022

- O arquivo `votacao_secao_2026_BR.zip` inclui o **exterior** (`ZZ`, 916.534 aptos no 1º turno);
  não há linhas com `SG_UF = VT`.
- `detalhe_votacao_munzona_2026` e `votacao_candidato_munzona_2026` foram **regerados em
  25/10/2026** (ainda só com o 1º turno); os arquivos por seção são de 05–06/10/2026.
- Códigos de município sem zero inicial no arquivo por zona (7 UFs) — ver ADR 0004.
- **2022 (teste com dois turnos reais):** layout idêntico ao de 2026; piloto MG com todas as
  checagens críticas aprovadas, decomposição territorial fechando exatamente e reconciliação
  seção → zona exata (relatório `reports/quality/20261026T122749Z-7dd437.md`).
- Relatório nacional 2026: `reports/quality/20261026T124109Z-1588ed.md` (+ pasta `_diag`).

## Legenda de status

| Status | Significado |
|---|---|
| `disponivel` | Baixado, íntegro, esquema confere e os dois turnos estão presentes |
| `parcial` | Baixado e íntegro, mas falta um turno ou parte da cobertura |
| `indisponivel` | URL não responde 200 ou recurso não publicado |
| `incompativel` | Baixado, mas cabeçalho/dicionário divergem do esperado |
| `nao_coletado` | Listado no catálogo; ainda não baixado por este pipeline |

## Conjunto: Resultados — 2026 (`resultados-2026`)

Metadados do conjunto: criado em 06/10/2026; periodicidade declarada "Diária"; extração "Data de
geração disponível por arquivo"; licença Creative Commons Attribution; organização TSE/AGEL.
61 recursos (32 CSV-em-ZIP, 29 PDF-em-ZIP).

| Recurso | URL oficial | Granularidade (declarada) | Cobertura | Prioridade | Status |
|---|---|---|---|---|---|
| Presidente — Votação por seção eleitoral | `cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip` | seção × votável | Nacional (Presidente); presença de ZZ/VT **a confirmar** | MVP (piloto e nacional) | parcial (só 1º turno) |
| {UF} — Votação por seção eleitoral (27 arquivos) | `…/votacao_secao/votacao_secao_2026_{UF}.zip` | seção × votável, cargos estaduais | Por UF; sem arquivo ZZ | Fora do MVP | MG: incompatível (sem Presidente) |
| Detalhe da apuração por seção eleitoral | `…/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip` | seção | Membro `_BR` = Presidente | MVP | parcial (só 1º turno) |
| Detalhe da apuração por município e zona | `…/detalhe_votacao_munzona/detalhe_votacao_munzona_2026.zip` | município × zona | Todas as UFs | Reconciliação | nao_coletado |
| Votação nominal por município e zona | `…/votacao_candidato_munzona/votacao_candidato_munzona_2026.zip` | município × zona × candidatura | Todas as UFs | Reconciliação | nao_coletado |
| Votação em partido por município e zona | `…/votacao_partido_munzona/votacao_partido_munzona_2026.zip` | município × zona × partido | Todas as UFs | Fora do MVP | nao_coletado |
| Relatório de Totalização (PDF) — BR, ZZ e 27 UFs | `…/relatorio_resultado_totalizacao/Relatorio_Resultado_Totalizacao_2026_{UF}.zip` | documento | BR, ZZ, UFs | Reconciliação manual | nao_coletado |

Observações do catálogo:
- Os arquivos de votação por seção trazem a nota "Arquivo atualizado ao final de cada turno".
  O nome **não muda** entre atualizações — por isso o pipeline detecta mudança por SHA-256.
- Recursos individuais mostram data de criação dos metadados (ex.: 07–08/10/2026), mas a
  "data dos dados" consta apenas **dentro do arquivo** (DT_GERACAO/HH_GERACAO, a confirmar).
- O 2º turno ocorreu em 25/10/2026. Em 26/10/2026 não é possível afirmar, pelo catálogo, que os
  arquivos já contêm o 2º turno; isso será verificado pelo campo de turno dentro de cada arquivo.

## Conjunto: Eleitorado — 2026 (`eleitorado-2026`)

Metadados: criado em 20/07/2026; atualização "Sob demanda/necessidade". Uso previsto na v2
(contexto demográfico do **cadastro** — não descreve voto).

| Recurso | URL oficial | Cobertura | Status |
|---|---|---|---|
| Eleitorado — 2026 (perfil) | `…/perfil_eleitorado/perfil_eleitorado_2026.zip` | Todas as UFs | nao_coletado |
| Perfil do eleitorado com deficiência | `…/perfil_eleitor_deficiente/perfil_eleitor_deficiencia_2026.zip` | Todas as UFs | nao_coletado |
| Eleitorado por local de votação | `…/eleitorado_locais_votacao/eleitorado_local_votacao_2026.zip` | Todas as UFs | nao_coletado |
| Transferência temporária do eleitorado | `…/perfil_eleitor_tte/transferencia_temporaria_2026.zip` | Todas as UFs | nao_coletado |
| Transferência temporária por seção | `…/perfil_eleitor_tte/transf_temporaria_secao_2026.zip` | Todas as UFs | nao_coletado |
| Perfil do eleitorado por seção — {UF} e ZZ (28 arquivos) | `…/perfil_eleitor_secao/perfil_eleitor_secao_2026_{UF}.zip` | Por UF + exterior | nao_coletado |

## Achados de 27/10/2026 (2º turno)

- O TSE publicou o 2º turno nos dois arquivos por seção (detectado às 03:02 UTC). Nacional +
  exterior liberado, sem falha crítica: `reports/quality/20261027T030648Z-130719.md`
  (branch `resultados/40442163704`). Os arquivos por município/zona seguem só com o 1º turno.
- **95/96 confirmados** (A-06): `VOTO BRANCO` e `VOTO NULO`; nos dois turnos, a soma por seção é
  igual a brancos e nulos do detalhe em todas as 499.248 seções, e a soma dos candidatos é igual a
  `QT_VOTOS_NOMINAIS` em todas. 42 (1º) e 43 (2º turno) seções do detalhe não têm linha de votação.
- **I-01 explicado**: os 5.246 votos são da candidatura 28, nulos técnicos na versão por zona
  (ADR 0005). Diagnóstico: `reports/diagnosticos/20261027T134148Z-645d93/` (branch
  `resultados/40514006404`).

## Conjunto: Candidatos — 2026 (`candidatos-2026`)

Inventário de 27/10/2026 (`reports/inventory/20261027T133953Z-44e95a.json`): 92 recursos, todos HTTP 200.

| Recurso | URL oficial | Bytes (HEAD) | Last-Modified (CDN) | Uso | Status |
|---|---|---|---|---|---|
| Candidatos | `…/consulta_cand/consulta_cand_2026.zip` | 3.240.701 | Sun, 25 Oct 2026 15:37:01 GMT | `dim_candidatura`, `DS_SIT_TOT_TURNO` | **perfilado** 27/10 (sha256 `c017f3200d33…`): 29 membros (UFs, `_BR`, `_BRASIL`), 50 colunas; leiame: `CD/DS_SITUACAO_CANDIDATURA` só valem até 2022 |
| Candidatos — informações complementares | `…/consulta_cand_complementar/consulta_cand_complementar_2026.zip` | 1.359.797 | Sun, 25 Oct 2026 15:37:01 GMT | candidata a fonte da situação jurídica em 2026 | nao_coletado |
| Histórico de candidaturas | `…/historico_candidatura/historico_candidatura_2026.zip` | 4.413.409 | Sun, 25 Oct 2026 15:37:08 GMT | identidade histórica (série) | nao_coletado |
| Coligações · Vagas · Motivo da cassação · Bens · Redes sociais | `…/consulta_coligacao/…`, `…/consulta_vagas/…`, `…/motivo_cassacao/…`, `…/bem_candidato/…`, `…/consulta_cand/rede_social_candidato_2026.zip` | 0,1–3,8 MB | 25/10/2026 | fora do MVP | nao_coletado |
| Fotos, propostas de governo e certidões criminais (por UF e BR) | `…/eleicoes2026/fotos/…`, `…/proposta_governo/…`, `…/certidao_criminal/…` | até 2,4 GB | 24–27/10/2026 | fora do escopo (dados pessoais, sem uso analítico) | não coletar |

## Conjunto: Comparecimento e abstenção — 2026 (`comparecimento-e-abstencao-2026`)

Descoberto no grupo CKAN `comparecimento-e-abstencao` em 27/10/2026.

| Recurso | URL oficial | Bytes (HEAD) | Last-Modified (CDN) | Status |
|---|---|---|---|---|
| Comparecimento e Abstenção | `…/perfil_comparecimento_abstencao/perfil_comparecimento_abstencao_2026.zip` | 229.213.668 | Wed, 21 Oct 2026 16:40:26 GMT | **perfilado** 27/10 (sha256 `abd1af8ff28a…`): 29 membros (UFs, ZZ, `_BRASIL`), granularidade município × zona × categorias, sem seção; arquivo de 21/10, anterior ao 2º turno |
| Pessoas com deficiência | `…/perfil_comparecimento_abstencao_eleitor_deficiente/…_2026.zip` | 80.189.391 | Wed, 21 Oct 2026 16:19:45 GMT | nao_coletado |
| Transferência temporária de eleitor | `…/perfil_comparecimento_abstencao_eleitor_tte/…_2026.zip` | 10.647.875 | Wed, 21 Oct 2026 16:18:31 GMT | nao_coletado |

Perfil de comparecimento descreve participação, nunca voto (instruções §13).
