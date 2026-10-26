# ADR 0002 — Execução no GitHub Actions; armazenamento local + manifestos no Git

Data: 2026-10-26 · Status: aceita (decisão do responsável)

**Contexto.** O ambiente de desenvolvimento assistido não alcança `cdn.tse.jus.br`. O TSE
republica arquivos com o mesmo nome ("atualizado ao final de cada turno").

**Decisão.**
- Execuções com dados reais rodam no **GitHub Actions** (`pipeline.yml`, `workflow_dispatch`),
  com duração máxima configurada e sem rodar a cada commit.
- **Dados brutos e camadas Silver/Gold não vão para o Git** nem para armazenamento externo.
  O registro durável é o **manifesto** (`data/manifests/<run_id>/*.json`): URL, SHA-256, bytes,
  `Last-Modified`, data de geração declarada no arquivo, momento da coleta, turnos e cabeçalho.
  Manifestos, relatórios de qualidade e texto dos dicionários são devolvidos ao repositório por PR.
- Artefatos do Actions (retenção curta) são conveniência, não arquivo durável.
- A cópia bruta durável fica na máquina do responsável quando o pipeline é rodado localmente.

**Consequências / riscos aceitos.**
- Se o TSE substituir um arquivo, uma reprodução futura baixará o conteúdo novo; o SHA-256 do
  manifesto evidencia a divergência, mas o conteúdo anterior não é recuperável a partir do repositório.
- Mitigação possível no futuro (não adotada agora): publicar os ZIPs como assets de GitHub Releases.
