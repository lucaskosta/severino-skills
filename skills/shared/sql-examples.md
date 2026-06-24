# SQL de referência — Severino v2

> Fonte única de INSERTs corretos para o schema v2.
> Carregue este arquivo quando precisar escrever SQL fora do padrão.

## Conferir category_id

```sql
-- Buscar id de uma categoria pelo nome (raiz)
SELECT id, name, budget_group, essential FROM categories WHERE name = 'Moradia' AND parent_id IS NULL;

-- Buscar subcategoria
SELECT id, name FROM categories WHERE name = 'Aluguel/Prestação' AND parent_id = 1;

-- Listar todas as raízes
SELECT id, name, kind, budget_group, essential FROM categories WHERE parent_id IS NULL ORDER BY sort_order;

-- Listar subcategorias de uma raiz
SELECT id, name FROM categories WHERE parent_id = 1 ORDER BY sort_order;
```

## profile (1 linha, id=1)

```sql
INSERT OR IGNORE INTO profile (id, name, income_stability, dependents, household)
VALUES (1, 'Usuário', 'stable', 0, 'single');

UPDATE profile SET
  name = 'Nome',
  income_stability = 'stable',   -- 'stable' | 'variable'
  dependents = 1,
  household = 'family'           -- 'single' | 'couple' | 'family'
WHERE id = 1;
```

## income_sources

```sql
INSERT INTO income_sources (name, amount, type, frequency, status)
VALUES ('Salário', 3000.00, 'salary', 'monthly', 'active');
-- type: 'salary' | 'freelance' | 'investment' | 'benefit' | 'other'
-- frequency: 'monthly' | 'one_time' | 'irregular'
-- status: 'active' | 'pending' | 'received' | 'inactive'

-- Renda pontual esperada para um mês específico
INSERT INTO income_sources (name, amount, type, frequency, status, expected_date)
VALUES ('Freelance projeto X', 1500.00, 'freelance', 'one_time', 'pending', '2026-07-15');
```

## accounts

```sql
INSERT INTO accounts (name, bank, balance, type)
VALUES ('Conta corrente', 'Banco', 0.00, 'checking');
-- type: 'checking' | 'savings' | 'caixinha' | 'investment'
```

## cards

```sql
INSERT INTO cards (name, bank, credit_limit, current_balance, due_day)
VALUES ('Cartão Principal', 'Banco', 5000.00, 0.00, 10);
-- status: 'active' | 'blocked' | 'cancelled'
```

## debts

```sql
INSERT INTO debts (name, creditor, installment_amount, installments_paid, installments_total,
                   balance_remaining, monthly_rate, due_day, type)
VALUES ('Empréstimo pessoal', 'Banco', 200.00, 3, 24, 4200.00, 0.05, 15, 'loan');
-- type: 'loan' | 'financing' | 'card_debt' | 'other'
-- monthly_rate: decimal (0.05 = 5%/mês)
```

## investments

```sql
INSERT INTO investments (name, type, amount, availability)
VALUES ('CDB Banco', 'cdb', 5000.00, 'blocked');
-- type: 'credit_letter' | 'cdb' | 'savings' | 'stocks' | 'other'
-- availability: 'available' | 'blocked' | 'partial'
```

## recurring_items

```sql
-- Buscar category_id antes de inserir
SELECT id FROM categories WHERE name = 'Aluguel/Prestação';

INSERT INTO recurring_items (name, category_id, amount, due_day, payment_method)
VALUES ('Aluguel', 18, 1200.00, 5, 'pix');
-- payment_method: 'debit' | 'credit' | 'pix' | 'boleto' | 'cash'
-- variable=1 para valor estimado (água, luz)

-- Item com valor cheio (desconto por antecipação)
INSERT INTO recurring_items (name, category_id, amount, full_amount, due_day, payment_method)
VALUES ('Escola', 37, 550.00, 600.00, 10, 'pix');
```

## transactions

```sql
-- Despesa comum
INSERT INTO transactions (date, description, amount, type, category_id)
VALUES ('2026-07-10', 'Pagamento aluguel', 1200.00, 'expense',
        (SELECT id FROM categories WHERE name='Aluguel/Prestação'));

-- Receita
INSERT INTO transactions (date, description, amount, type, category_id)
VALUES ('2026-07-05', 'Salário julho', 3000.00, 'income',
        (SELECT id FROM categories WHERE name='Salário' AND system=1));

-- Transferência para reserva (pay-yourself-first)
INSERT INTO transactions (date, description, amount, type, category_id)
VALUES ('2026-07-05', 'Reserva julho 10%', 300.00, 'transfer',
        (SELECT id FROM categories WHERE name='Reserva/Poupança' AND system=1));
```

## goals

```sql
INSERT INTO goals (name, kind, target_amount, current_amount, target_date, priority, created_at)
VALUES ('Reserva de emergência', 'emergency_fund', 9000.00, 0.00, '2027-06-01', 1, datetime('now'));
-- kind: 'emergency_fund' | 'purchase' | 'debt_free' | 'investment' | 'custom'
-- name é UNIQUE — verificar antes de inserir
```

## strategy (gerada pela IA, não pelo usuário)

```sql
-- Desativar a anterior
UPDATE strategy SET active = 0 WHERE active = 1;

-- Gravar recomendação do conselheiro
INSERT INTO strategy (primary_focus, budget_framework, debt_method,
                      reserve_target_months, reserve_pct, source, notes, active)
VALUES ('debt_payoff', 'zero_based', 'avalanche', 3, 0.05, 'ai',
        'Gerada pelo conselheiro em 2026-07-01', 1);
-- primary_focus: 'debt_payoff' | 'emergency_fund' | 'budgeting' | 'investing' | 'custom'
-- budget_framework: '50_30_20' | 'zero_based' | 'envelope' | 'free'
-- debt_method: 'avalanche' | 'snowball' | 'none'
-- source: 'ai' | 'user'
```
