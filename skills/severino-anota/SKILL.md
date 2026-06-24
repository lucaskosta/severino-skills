---
name: severino-anota
description: 'Use para registrar qualquer gasto, receita ou pagamento. Grava no DB e atualiza o estado do mês.'
argument-hint: 'O que registrar (ex: "paguei aluguel", "gastei 80 no mercado", "recebi 500")'
user-invocable: true
---

# severino-anota

**Quando invocar:** qualquer lançamento do dia a dia — paguei · gastei · recebi.

**DB:** `sqlite3 "$SEVERINO_DATA_DIR/finance-mcp-server/data/finance.db"`

Carregar `$SEVERINO_HOME/skills/shared/sql-examples.md` **só se** a transação tiver
tipo incomum (ex: transferência para reserva, categoria nova).

---

## Fluxo padrão (4 passos)

**1. Entender o lançamento**
- tipo: expense / income / transfer
- valor · descrição · data (padrão: hoje) · categoria

**2. Inferir category_id**
```sql
SELECT id, name, parent_id FROM categories WHERE name LIKE '%:termo%' AND active=1;
```
Se ambíguo → perguntar. Nunca inventar ID.

**3. Confirmar em 1 linha**
> "Registrar: Aluguel R$ 1.200,00 → Moradia/Aluguel · expense · hoje. Ok?"

**4. Gravar**
```sql
INSERT INTO transactions (date, description, amount, type, category_id)
VALUES (date('now'), :descricao, :valor, :tipo,
        (SELECT id FROM categories WHERE name = :categoria));
```

**Pagar-se primeiro (reserva):**
```sql
INSERT INTO transactions (date, description, amount, type, category_id)
VALUES (date('now'), 'Reserva ' || strftime('%Y-%m', 'now'), :valor, 'transfer',
        (SELECT id FROM categories WHERE name = 'Reserva/Poupança' AND system=1));
```

---

## Após gravar

```bash
python3 "$SEVERINO_HOME/engine/derive_estado.py" YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
```

Mostrar: saldo do dia = `income.confirmed − spending.paid` (do novo `estado.json`).

**Não comentar** a situação estratégica — isso é papel do `/severino-conselheiro`.

---

## Casos especiais

**Pagamento parcelado (nova parcela de dívida):**
```sql
-- 1. Registrar a transaction
INSERT INTO transactions (date, description, amount, type, category_id)
VALUES (date('now'), :descricao, :parcela, 'expense',
        (SELECT id FROM categories WHERE name = 'Parcela de empréstimo'));

-- 2. Atualizar o saldo da dívida
UPDATE debts SET
  installments_paid = installments_paid + 1,
  balance_remaining = balance_remaining - :parcela
WHERE name = :nome_divida AND status = 'active';
```

**Fatura de cartão:**
```sql
INSERT INTO transactions (date, description, amount, type, category_id)
VALUES (date('now'), 'Fatura ' || :nome_cartao, :valor, 'expense',
        (SELECT id FROM categories WHERE name = 'Fatura de cartão'));

UPDATE cards SET current_balance = 0, updated_at = datetime('now')
WHERE name = :nome_cartao;
```
