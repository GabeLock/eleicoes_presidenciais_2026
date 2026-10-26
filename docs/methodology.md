# Metodologia

## Definição operacional de "virada"

"Virada histórica" é tratada como **hipótese**. Três fenômenos distintos são separados, cada um
com seus próprios dados:

| Fenômeno | Definição | Dados necessários | Status no MVP |
|---|---|---|---|
| **Inversão entre turnos** | Sejam A o finalista com mais votos no **resultado final do 1º turno** (Brasil + exterior) e B o outro finalista. Há inversão se `M_BR,1 = votos_A,1 − votos_B,1 > 0` e `M_BR,2 = votos_A,2 − votos_B,2 < 0`. | Resultados finais dos dois turnos (votação por seção, reconciliada) | **Escopo do MVP** |
| **Mudança de liderança durante a apuração** | A liderança muda entre snapshots sucessivos da divulgação de um mesmo turno. | Série de snapshots oficiais com timestamp e % de seções totalizadas | **Indisponível** até que uma série oficial seja localizada; resultados finais e horários isolados não reconstituem a sequência |
| **Divergência em relação a pesquisas** | Diferença entre o resultado e estimativas de pesquisas registradas. | Pesquisas registradas, com margem e data de campo | Fora do escopo |

A **excepcionalidade** (H5) só pode ser afirmada contra uma série histórica processada no mesmo
universo e com as mesmas definições. Até a expansão 2018/2022 (e depois 1989–2014, identificando
pleitos sem 2º turno), a comparação fica restrita aos anos efetivamente processados.

Regras: empate no 1º turno entre finalistas torna A ambíguo e bloqueia a classificação; a
inversão é calculada no universo completo (UFs + exterior), nunca no piloto MG.

## Unidades e universos

- **Unidade principal de comparação:** município (TSE), com exterior tratado como conjunto próprio
  de "municípios" (UF = ZZ), mantido na reconciliação nacional e excluído de cruzamentos com IBGE.
- **Seção:** retida na Silver; comparação seção a seção só com painel pareado validado
  (entradas/saídas registradas e resultado comparado ao universo completo).
- **Universos distintos:** população residente (IBGE) ≠ eleitorado apto (TSE) ≠ comparecimento.

## Indicadores (por território e turno, sempre com numerador e denominador)

| Indicador | Numerador | Denominador |
|---|---|---|
| Abstenção | abstenções | aptos |
| Comparecimento | comparecimento | aptos |
| Brancos / Nulos | brancos / nulos (digitados) | comparecimento |
| Válidos | votos válidos | comparecimento |
| Participação do candidato | votos do candidato | votos válidos |
| Margem | votos A − votos B (votos) e (A − B)/válidos (p.p.) | — / válidos |

Agregações recalculam razões a partir das somas (Σnum/Σden). Variações de taxas são expressas em
**pontos percentuais**. Nulos digitados ficam separados de anulações jurídicas.

O percentual do vencedor não é comparado diretamente entre turnos sem considerar que o número de
concorrentes cai (no 1º turno, todos os candidatos são mantidos separados).

## Decomposição territorial exata

`M_it = votos_A_it − votos_B_it`, `Contribuição_i = M_i2 − M_i1`, e
`Σ_i Contribuição_i = M_BR,2 − M_BR,1` (identidade inteira; o pipeline verifica que fecha).
Relatamos contribuições positivas, negativas e o saldo líquido. A participação de um território no
saldo pode passar de ±100% quando o saldo é pequeno frente a contribuições de sinais opostos.

## Decomposição simétrica (volume × margem relativa)

Para `V_it > 0`, `d_it = M_it / V_it` e
`ΔM_i = média(d_i1, d_i2)·ΔV_i + média(V_i1, V_i2)·Δd_i`. Linhas com `V = 0` são sinalizadas e
ficam fora dessa decomposição (a exata continua válida).

## Identidade multiplicativa

`votos_candidato = aptos × taxa_comparecimento × taxa_validos × participação_candidato`.
A variação é decomposta por **Shapley** (média sobre as 24 ordens dos 4 fatores), o que distribui
as interações sem privilegiar fator. É contabilidade: não identifica quem voltou às urnas, quem
mudou de candidato ou deixou de anular.

## Qualidade e bloqueio

Contagens inteiras reconciliam **exatamente** quando universo e versão são iguais. Falhas críticas
(turno ausente, esquema divergente, duplicidade na granularidade, reconciliação seção → município
que não fecha, decomposição que não fecha) marcam a base como **BLOQUEADA** e impedem a
publicação de conclusões. Checagens não críticas (ex.: aptos ≠ comparecimento + abstenção em
universos diferentes) são reportadas e investigadas, não forçadas.

A identidade aptos = comparecimento + abstenção só vale para seções instaladas. A camada por
seção é reconciliada com os arquivos por zona e por município; quando as versões diferem
(datas de geração distintas), as diferenças são reportadas com diagnóstico por UF
(`reports/quality/<run_id>_diag/`). Ver ADR 0004.
