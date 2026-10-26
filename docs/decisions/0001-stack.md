# ADR 0001 — Stack local, sem infraestrutura distribuída

Data: 2026-10-26 · Status: aceita

**Contexto.** O volume do MVP (votação por seção de um cargo, dois turnos) cabe em uma máquina.
A especificação pede reprodutibilidade, versões fixas e ausência de infraestrutura distribuída.

**Decisão.** Python 3.12+, DuckDB 2.0 (SQL e leitura de CSV latin-1), Parquet, Polars 2.1
(pandas 3.1 só onde bibliotecas de modelagem exigirem), pytest, Ruff, Typer, Streamlit + Plotly,
scikit-learn + statsmodels. Ambiente gerido por **uv** com `uv.lock` versionado. Sem orquestrador:
CLI + Makefile + GitHub Actions.

**Consequências.** `make setup` reproduz o ambiente exato. Um orquestrador só entra se houver
necessidade operacional demonstrada (ex.: agendamento com dependências entre muitos recursos).
