---
name: severino-pergunta
description: 'Onboarding financeiro completo em 8 blocos. Coleta dossiê sem julgamento. Grava no DB.'
argument-hint: 'Opcional: bloco a revisar (ex: "cartões", "dívidas"). Sem argumento = onboarding completo.'
user-invocable: true
---

# severino-pergunta

**Quando invocar:** primeira vez; ou "quero atualizar meus dados / revisar [bloco]".

---

## Preflight — rodar ANTES de qualquer pergunta

```bash
# 1. Checar variável obrigatória
if [ -z "$SEVERINO_DATA_DIR" ]; then
  echo "ERRO: SEVERINO_DATA_DIR não definida."
  echo "Execute: export SEVERINO_DATA_DIR=\"/caminho/para/seus/dados\""
  echo "Depois adicione ao ~/.zshrc para não precisar repetir."
  exit 1
fi

DB="$SEVERINO_DATA_DIR/finance-mcp-server/data/finance.db"

# 2. Criar DB + seed se não existe
mkdir -p "$(dirname "$DB")"
if [ ! -f "$DB" ]; then
  echo "Banco não encontrado — criando..."
  sqlite3 "$DB" < "$SEVERINO_HOME/engine/schema.sql"
fi

# 3. Verificar seed de categorias (deve ter ≥ 53)
COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM categories;")
if [ "$COUNT" -lt 53 ]; then
  echo "Seed incompleto ($COUNT categorias) — reaplicando schema..."
  sqlite3 "$DB" < "$SEVERINO_HOME/engine/schema.sql"
fi

echo "✓ DB pronto ($COUNT categorias)"
```

Se qualquer etapa falhar: parar e mostrar o erro exato antes de prosseguir.

Carregar após preflight:
```
Read: $SEVERINO_HOME/skills/shared/sql-examples.md
```

**DB:** `sqlite3 "$SEVERINO_DATA_DIR/finance-mcp-server/data/finance.db"`

---

## Regras absolutas

1. **Sem julgamento, sem estratégia.** Fase de dossiê — só fatos.
2. **Confirmar cada bloco** antes de gravar. Mostrar resumo, aguardar "ok".
3. **Se o usuário não souber:** pular com NULL ou 0. Não travar o fluxo.
4. **category_id sempre via SELECT** — nunca hardcode de ID.

---

## Bloco 0 — Perfil

Perguntar: nome · renda estável ou variável? · dependentes (qtd) · mora sozinho/casal/família?

```sql
INSERT OR IGNORE INTO profile (id, name, income_stability, dependents, household)
VALUES (1, :name, :income_stability, :dependents, :household);
-- income_stability: 'stable' | 'variable'
-- household: 'single' | 'couple' | 'family'
```

---

## Bloco 1 — Fontes de renda

Perguntar: salário fixo? Outras rendas mensais? Rendas pontuais esperadas este mês?

```sql
INSERT INTO income_sources (name, amount, type, frequency, status)
VALUES (:name, :amount, :type, :frequency, 'active');
-- type: 'salary' | 'freelance' | 'investment' | 'benefit' | 'other'
-- frequency: 'monthly' | 'one_time' | 'irregular'
```

---

## Bloco 2 — Categorias personalizadas

Mostrar as raízes do seed (já instaladas no DB):
> Moradia · Alimentação · Transporte · Saúde · Educação · Filhos/Dependentes
> Dívidas · Taxas & Impostos · Pessoal & Lazer · Pets · Outros

"Tem alguma categoria importante que não está aqui?" Se sim:

```sql
INSERT INTO categories (name, parent_id, kind, budget_group, essential, system)
VALUES (:name, :parent_id, 'expense', :budget_group, :essential, 0);
-- budget_group: 'needs' | 'wants' | 'savings'
-- system=0 = criada pelo usuário (pode editar/remover)
```

---

## Bloco 3 — Contas e cartões

```sql
INSERT INTO accounts (name, bank, balance, type)
VALUES (:name, :bank, :balance, :type);
-- type: 'checking' | 'savings' | 'caixinha' | 'investment'

INSERT INTO cards (name, bank, credit_limit, current_balance, due_day)
VALUES (:name, :bank, :limit, 0.00, :due_day);
```

---

## Bloco 4 — Dívidas e financiamentos

Para cada dívida: nome · credor · parcela · pagas · total · taxa/mês · dia venc.

```sql
INSERT INTO debts (name, creditor, installment_amount, installments_paid,
                   installments_total, balance_remaining, monthly_rate, due_day, type)
VALUES (:name, :creditor, :installment, :paid, :total, :balance, :rate, :due_day, :type);
-- type: 'loan' | 'financing' | 'card_debt' | 'other'
-- monthly_rate: decimal (0.05 = 5%/mês)
```

---

## Bloco 5 — Investimentos e patrimônio

```sql
INSERT INTO investments (name, type, amount, availability)
VALUES (:name, :type, :amount, :availability);
-- type: 'credit_letter' | 'cdb' | 'savings' | 'stocks' | 'other'
-- availability: 'available' | 'blocked' | 'partial'
```

---

## Bloco 6 — Recorrentes do mês

Para cada gasto fixo mensal: nome · categoria · valor · dia vencimento · forma de pagamento.

```sql
-- Sempre buscar category_id antes
SELECT id FROM categories WHERE name = :categoria_nome;

INSERT INTO recurring_items (name, category_id, amount, due_day, payment_method)
VALUES (:nome, :category_id, :valor, :due_day, :metodo);
-- payment_method: 'debit' | 'credit' | 'pix' | 'boleto' | 'cash'
-- Se valor varia (água/luz): variable=1
```

---

## Bloco 7 — Metas

```sql
INSERT INTO goals (name, kind, target_amount, current_amount, target_date, priority, created_at)
VALUES (:nome, :kind, :meta, 0.00, :data, :prioridade, datetime('now'));
-- kind: 'emergency_fund' | 'purchase' | 'debt_free' | 'investment' | 'custom'
-- name é UNIQUE — verificar antes de inserir
```

---

## Encerramento

```bash
python3 "$SEVERINO_HOME/engine/derive_estado.py" YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
python3 "$SEVERINO_HOME/engine/render_graphs.py"  YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
```

Mostrar: renda total · total de recorrentes · dívidas cadastradas · metas.
Concluir: "Dossiê completo. Use `/severino-anota` para registrar movimentos do mês."
**Não comentar a situação financeira** — isso é papel do `/severino-conselheiro`.
