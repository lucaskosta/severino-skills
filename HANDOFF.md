# HANDOFF — Leia isto primeiro

> Este repo (`severino`) está **zerado de propósito**. Esta sessão começa fria. Leia este arquivo **antes de qualquer coisa**, depois o [SPEC.md](SPEC.md) (o plano completo).

## O que é

**Severino** — uma suíte portável de skills de gestão financeira pessoal, em forma de produto (genérico, sem dado pessoal dentro). O plano inteiro está em [SPEC.md](SPEC.md).

Estrutura alvo do repo:
```
severino/
├── SPEC.md      ← o plano (fonte da verdade do design)
├── HANDOFF.md   ← este arquivo
├── skills/      ← as 4 SKILL.md (a construir)
└── engine/      ← schema.sql, gerador, templates, deriva estado.json (a construir)
```

## As 4 skills (nomes definitivos)

| Skill | Função |
|---|---|
| `severino-pergunta` | abre a ficha (onboarding por blocos) |
| `severino-anota` | o motor: registra movimento na hora + consolida + 12 gráficos |
| `severino-pente-fino` | fecha o mês (checklist dos recorrentes) |
| `severino-conselheiro` | diagnóstico + estratégia + bronca/conselho |

## Persona & Tom — Severino (vale pra TUDO que for gerado)

O personagem que cuida do dinheiro: **zelador/contador antigo, durão de fora, coração mole**. Anota tudo, sabe onde cada centavo foi parar, dá bronca quando merece e elogia quando o cara segura. Sempre do lado do usuário — a bronca é de quem se importa.

**Voz:** fala de gente, direta (*"ó"*, *"olha aqui"*, *"rapaz"*, *"vô te falar"*); honesto, sem dourar a pílula; humor sutil, nunca palhaçada; firme mas acolhedor; educação financeira na lata, como quem ensina pro neto. **Toda mensagem ao usuário sai nessa voz.** (Detalhe em SPEC §2.)

## Dado de teste (a instância nº 1 = o Taru)

O produto roda contra um diretório de dados. Para desenvolver/testar, aponte para o cockpit do Taru (NÃO copiar o dado pra cá — fica lá):

| Item | Caminho absoluto |
|---|---|
| Diretório de dados | `/Users/taru/IA/assistente/Financeiro/` |
| Banco (fonte da verdade) | `/Users/taru/IA/assistente/Financeiro/finance-mcp-server/data/finance.db` |
| Gerador atual de gráficos | `/Users/taru/IA/assistente/Financeiro/scripts/update_finance_graphs.py` |
| Convenções/categorias atuais | `/Users/taru/IA/assistente/Financeiro/CONVENCOES.md` |
| Skill atual (vira `severino-anota`) | `/Users/taru/IA/assistente/.github/skills/finance-sync/SKILL.md` |

> ⚠️ O MCP `finance-mcp` **não está conectado** no Claude Code. Gravar no SQLite direto com `sqlite3` (backup antes: `cp finance.db finance.db.bak-YYYYMMDD`). Gráficos: `python3 .../scripts/update_finance_graphs.py YYYY-MM`.

## Por onde começar — Fase 0 (refatorar o motor)

1. **Desacoplar os gráficos do markdown:** o gerador atual lê valores por regex dos mds (frágil, preso ao formato do Taru). Fazer ele ler de um `estado.json` derivado do DB. (SPEC §3 e §7.)
2. **Migrar o dado atual pro DB completo:** popular as tabelas novas (`income_sources`, `accounts`, `cards`, `debts`, `investments`, `recurring_items`, `strategy`) a partir do que já existe nos mds do Taru. Usar `budgets`/`goals` (hoje vazias).
3. Validar gerando o painel do mês corrente a partir do DB.

Sem a Fase 0 as 4 skills não têm chão. Depois: Fase 1 (`severino-anota`) → 2 (`severino-pergunta`) → 3 (`severino-pente-fino`) → 4 (`severino-conselheiro`). (SPEC §10.)

## Regras de ouro

- **Nada de dado pessoal neste repo** — só código genérico. O dado do Taru fica no cockpit.
- Cada fato mora num lugar só; DB é a fonte da verdade, md é leitura.
- Responder em **pt-BR**. Todo texto-usuário na voz do Severino.
