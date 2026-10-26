# Hipóteses (registradas antes de qualquer modelo)

Registro: 2026-10-26, commit inicial. Alterações posteriores devem ser feitas por PR, com data e
justificativa, sem apagar a versão anterior.

Unidade de análise padrão: município (TSE), Brasil sem exterior para covariáveis IBGE; exterior
analisado à parte. Ponderação padrão: votos válidos médios dos dois turnos (sensibilidade: sem peso
e eleitorado apto).

| ID | Hipótese | Alvo (y) | Covariáveis | Tipo | Limite principal |
|---|---|---|---|---|---|
| H1 | Mudanças territoriais no comparecimento se associam à mudança da margem | Δ margem relativa (p.p.) entre turnos | Δ comparecimento (p.p.) | Descritiva (usa os dois turnos) | Associação ecológica; não identifica quem compareceu |
| H2 | Redução de inválidos se associa à expansão de votos dos finalistas | Δ (votos A + votos B)/aptos | Δ (brancos + nulos)/comparecimento | Descritiva | Mesmo eleitor pode ter mudado de inválido para válido ou não — não observável |
| H3 | A composição da votação dos eliminados se associa ao padrão do 2º turno | Δ margem relativa | Participação de cada eliminado no 1º turno (votos válidos) | Preditiva (só informação do 1º turno) | Não é transferência individual; inferência ecológica é opcional e exige limites |
| H4 | Características territoriais ajudam a explicar heterogeneidade | Δ margem relativa | Porte populacional, urbanização, renda, escolaridade, idade (IBGE, anteriores à eleição) | Descritiva/Preditiva | Defasagem temporal; universo IBGE ≠ eleitorado |
| H5 | O padrão de 2026 é incomum na série histórica processada | Δ margem nacional e dispersão territorial | — | Comparação histórica | Válida só para anos processados no mesmo universo |

## Regras de modelagem

- Proibido usar como preditor qualquer componente que determine algebricamente o alvo
  (ex.: votos de A no 2º turno para explicar Δ margem).
- Modelos preditivos (H3, H4) usam apenas informação disponível antes do 2º turno.
- Comparação obrigatória contra **baseline** (ex.: Δ margem = média ponderada nacional), regressão
  interpretável e, se agregar valor, um modelo não linear. Métricas: MAE/RMSE ponderados.
- Validação por **blocos geográficos** (ex.: deixar uma UF/mesorregião de fora), nunca só divisão
  aleatória; análise de resíduos espaciais; sementes fixas.
- Intervalos só quando corresponderem a um modelo e uma incerteza explícitos; bootstrap, se usado,
  respeita dependência espacial (blocos).
- SHAP e importância de variáveis explicam o modelo, não causas.
