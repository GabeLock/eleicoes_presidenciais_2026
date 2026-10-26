# Eleições Presidenciais 2026 — 1º × 2º turno

Projeto público e reprodutível para investigar **onde e como** o resultado da eleição presidencial
brasileira de 2026 mudou entre o primeiro e o segundo turnos, a partir dos dados abertos do TSE.

> **Status:** esqueleto executável + inventário de fontes (etapa 1 de 6). Nenhuma conclusão
> sobre a eleição foi publicada ainda. Ver [plano do MVP](docs/mvp_plan.md).

## O que este projeto faz — e o que não faz

- Trata a "virada" como **hipótese**, com definição operacional em
  [docs/methodology.md](docs/methodology.md#definição-operacional-de-virada).
- Quantifica a contribuição de cada território para a mudança da margem nacional por
  **decomposição contábil exata** (a soma fecha com a variação nacional).
- Investiga **associações territoriais** com participação e perfil demográfico.
- **Não** infere voto individual, transferência de eleitores, causa ou irregularidade a partir
  de dados agregados. Ver [docs/limitations.md](docs/limitations.md).

## Arquitetura

```
descoberta (CKAN) → download (hash, retry, atômico) → validação bruta (ZIP, HTML, encoding, esquema)
  → Bronze (ZIP original imutável, endereçado por SHA-256)
  → Silver (DuckDB/Parquet tipado; códigos como texto)
  → Gold (painéis município × turno, decomposição)  → análises → dashboard → relatório
```

Cada execução grava `reports/runs/<run_id>.json` com commit, hash da configuração, insumos,
volumes, duração e status; os manifestos de insumos (URL, SHA-256, geração na fonte, coleta)
ficam versionados em `data/manifests/`.

## Reproduzir o piloto MG

Pré-requisitos: Python ≥ 3.12, [uv](https://docs.astral.sh/uv/), `make`, ~10 GB livres, acesso a
`cdn.tse.jus.br`.

```bash
git clone https://github.com/GabeLock/eleicoes_presidenciais_2026.git
cd eleicoes_presidenciais_2026
make setup                 # ambiente idêntico ao uv.lock
make inventory             # o que o TSE publicou hoje
make ingest YEAR=2026 UF=MG
make validate              # bloqueia se o esquema divergir do dicionário
make transform UF=MG       # Silver + Gold + reports/quality/<run_id>.md
make analyze
make dashboard
make test
```

Universo nacional + exterior: `make national` (ou `UF=ALL`). O piloto MG serve **apenas** para
testar o pipeline; não sustenta conclusões nacionais.

### Execução no GitHub Actions

O workflow **Pipeline** (`.github/workflows/pipeline.yml`) é manual (`workflow_dispatch`): escolha
etapa e UF. Os manifestos e relatórios de qualidade voltam como artefato; artefatos do Actions são
temporários e **não** são o arquivo durável dos snapshots (ver
[ADR 0002](docs/decisions/0002-execucao-e-armazenamento.md)).

## Documentação

| Documento | Conteúdo |
|---|---|
| [source_inventory.md](docs/source_inventory.md) | Recursos oficiais, URLs, status, limitações |
| [data_dictionary.md](docs/data_dictionary.md) | Tabelas Silver/Gold, granularidade, chaves |
| [methodology.md](docs/methodology.md) | Definição de virada, indicadores, decomposições |
| [hypotheses.md](docs/hypotheses.md) | H1–H5 registradas antes dos modelos |
| [limitations.md](docs/limitations.md) | Limites de interpretação |
| [mvp_plan.md](docs/mvp_plan.md) | Etapas, critérios de aceite, pendências |
| [decisions/](docs/decisions/) | Decisões técnicas (ADRs) |

## Licenças

Código: [MIT](LICENSE). Dados: condições das fontes (TSE — Creative Commons Attribution conforme o
portal; IBGE — termos próprios). Cite a fonte e a versão do snapshot ao reutilizar números.
