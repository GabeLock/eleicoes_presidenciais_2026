# Inventário de fontes

**Versão:** 0.2 · **Levantamento do catálogo:** 2026-10-26 (API CKAN; 94 recursos nos dois conjuntos) ·
**Primeiros snapshots:** 2026-10-26 10:53–10:57 UTC (GitHub Actions; ver tabela abaixo).

> Recursos não coletados constam com os metadados do catálogo. Para os coletados, os valores vêm
> dos manifestos em `data/manifests/` (gerados por `make ingest`); o texto do dicionário oficial
> (leiame 2026) está em `reports/dicionarios/leiame.txt`.

## Snapshots coletados

| Recurso | SHA-256 | Bytes (ZIP) | Gerado na fonte (DT/HH_GERACAO) | Last-Modified (CDN) | Coletado (UTC) | Turnos | Linhas | Status |
|---|---|---|---|---|---|---|---|---|
| `votacao_secao_2026_BR.zip` (Presidente) | `2d42006d0f6c6e00bad83f5c23cd3d78cd3e3182dbc1ad6718222b6b132c23e1` | 161.616.519 | 06/10/2026 14:03:43 | Tue, 06 Oct 2026 19:22:49 GMT | 2026-10-26T10:57:26 | 1 | 3.800.511 | **parcial** |
| `detalhe_votacao_secao_2026.zip` | `11a62c3a604e8b73fc328617b7688d2c635de1c76df02ba63b8f77879512f573` | 176.923.175 | 05/10/2026 14:03:30 | Wed, 07 Oct 2026 20:54:59 GMT | 2026-10-26T10:57:41 | 1 | — | **parcial** |
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

## Fontes ainda não inventariadas

| Fonte | Motivo | Ação |
|---|---|---|
| Candidaturas 2026 (`consulta_cand`) | Página do conjunto não localizada no levantamento | Localizar no catálogo; necessário para `dim_candidatura` e situação jurídica |
| Grupo "Comparecimento e abstenção" | Não foi possível confirmar recursos de 2026 | Verificar via API CKAN no próximo `make inventory` |
| Consulta oficial de resultados (`resultados.tse.jus.br`) | Aplicação web, não arquivo | Usar para reconciliação pontual (BR, MG, ZZ) com registro de data/hora da consulta |
| Série histórica (2018, 2022; depois 1989–2014) | Expansão posterior | Inventariar quando o MVP 2026 estiver reconciliado |
| IBGE (população, Censo 2022, PIB municipal) | Complemento v2 | Registrar ano de referência e defasagem |

## Condições de reutilização

- TSE: licença declarada no portal = Creative Commons Attribution. Citar "Tribunal Superior
  Eleitoral — Portal de Dados Abertos", o recurso e a data de geração/coleta do snapshot.
- IBGE: termos próprios, a registrar quando incorporado.
- Código deste repositório: MIT (independente das fontes).
