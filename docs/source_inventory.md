# Inventário de fontes

**Versão:** 0.1 · **Levantamento do catálogo:** 2026-10-26 (consulta às páginas dos conjuntos no
Portal de Dados Abertos do TSE) · **Snapshot de dados:** nenhum coletado ainda.

> Este inventário é **preliminar**: foi montado a partir dos metadados publicados no catálogo.
> Tamanho, SHA-256, data de geração (dentro do arquivo), turnos presentes, cabeçalho real e
> versão do dicionário só são conhecidos após o download. Esses campos serão preenchidos pela
> execução de `make inventory` + `make ingest` no GitHub Actions e consolidados por PR
> (arquivo gerado: `reports/inventory/<run_id>.consolidado.json`).

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
| Presidente — Votação por seção eleitoral | `cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip` | seção × votável | Nacional; inclusão do exterior (ZZ) **a confirmar** | MVP nacional | nao_coletado |
| {UF} — Votação por seção eleitoral (27 arquivos) | `…/votacao_secao/votacao_secao_2026_{UF}.zip` | seção × votável, todos os cargos | Por UF; **sem arquivo ZZ** listado | MVP piloto (MG) | nao_coletado |
| Detalhe da apuração por seção eleitoral | `…/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip` | seção | Todas as UFs | MVP | nao_coletado |
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
