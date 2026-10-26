# Limites de interpretação

1. **O voto é secreto.** Dados agregados não permitem afirmar que pessoas de determinada idade,
   sexo, renda, religião ou escolaridade votaram em determinado candidato.
2. **Perfil do eleitorado descreve cadastro**; perfil de comparecimento descreve participação.
   Nenhum dos dois revela voto individual.
3. **Associação territorial ≠ comportamento individual** (falácia ecológica). Frases adequadas:
   "municípios com maior proporção de X apresentaram maior variação de Y". Inadequadas: "X mudou
   de voto e causou a vitória".
4. **Decomposições são contábeis.** Mostram onde e em que componente a margem mudou; não indicam
   quem retornou às urnas, trocou de candidato ou deixou de anular.
5. **Causalidade** exige pergunta causal, mecanismo, temporalidade, exposição observável e
   estratégia de identificação. Sem isso, o projeto entrega associações e hipóteses não identificadas.
6. **Anomalias estatísticas não são evidência de fraude.** São motivo para validar dados e contexto.
7. **Mudança de liderança durante a apuração** não pode ser estudada sem série oficial de
   snapshots com timestamp e cobertura.
8. **Piloto MG** testa o pipeline; não sustenta conclusões nacionais.
9. **Excepcionalidade histórica** só vale para a série efetivamente processada e harmonizada.
10. **Snapshots:** os arquivos do TSE são republicados com o mesmo nome. Este projeto guarda
    manifestos (URL, SHA-256, geração, coleta) no Git e os arquivos brutos fora dele; se o TSE
    substituir um arquivo, uma reprodução futura pode obter outro conteúdo — o manifesto permite
    detectar a divergência, mas não recuperar o conteúdo anterior (ver ADR 0002).
11. **Fontes externas (IBGE)** têm anos de referência e universos próprios; defasagens são
    registradas e variáveis externas nunca são atribuídas ao TSE.
