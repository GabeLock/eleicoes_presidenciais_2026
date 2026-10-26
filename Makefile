# Atalhos documentados. Todos chamam a CLI `eleicoes` dentro do ambiente gerido pelo uv.
YEAR ?= 2026
UF   ?= MG
RUN  := uv run eleicoes

.PHONY: setup inventory ingest validate transform analyze dashboard test lint format pilot national

setup:            ## instala o ambiente fixado no uv.lock (inclui dashboard e modelagem)
	uv sync --all-extras --locked

inventory:        ## catálogo CKAN do TSE + HEAD de cada arquivo
	$(RUN) inventory

ingest:           ## download + validação bruta + extração (UF=MG | UF=ALL)
	$(RUN) ingest --year $(YEAR) --uf $(UF)

validate:         ## status dos manifestos; falha se houver recurso incompatível
	$(RUN) validate

transform:        ## Bronze → Silver → Gold + relatório de qualidade
	$(RUN) transform --uf $(UF)

analyze:          ## quadros descritivos a partir da Gold
	$(RUN) analyze

dashboard:        ## exploração local em Streamlit
	uv run streamlit run dashboard/app.py

pilot:            ## piloto MG completo
	$(MAKE) ingest UF=MG && $(MAKE) validate && $(MAKE) transform UF=MG && $(MAKE) analyze

national:         ## universo nacional + exterior
	$(MAKE) ingest UF=ALL && $(MAKE) validate && $(MAKE) transform UF=ALL && $(MAKE) analyze

test:
	uv run pytest

lint:
	uv run ruff check . && uv run ruff format --check .

format:
	uv run ruff format . && uv run ruff check --fix .
