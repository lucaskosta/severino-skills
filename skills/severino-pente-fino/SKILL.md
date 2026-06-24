---
name: severino-pente-fino
description: 'Fechamento do mês. Checklist dos recorrentes não pagos, item a item. Fecha o mês e sugere o conselheiro.'
argument-hint: 'Opcional: mês a fechar (ex: "2026-07"). Sem argumento = mês corrente.'
user-invocable: true
---

# severino-pente-fino

**Quando invocar:** fim de mês, antes de virar o mês.

**DB:** `sqlite3 "$SEVERINO_DATA_DIR/finance-mcp-server/data/finance.db"`

Carregar `$SEVERINO_HOME/skills/shared/sql-examples.md` antes do batch final.

---

## Fluxo (6 passos)

### 1. Determinar o mês

Usar o argumento ou perguntar se não informado.

```bash
python3 "$SEVERINO_HOME/engine/derive_estado.py" YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
```

### 2. Ler pendentes do calendário

```json
estado.json → calendar.items[paid=false]
```

### 3. Checklist item a item

Para cada item pendente:
> "**[nome]** — R$ [valor] (vence dia [due_day]) — pago? (s / n / valor diferente)"

- `s` → gravar transaction com o valor original
- `n` → pular (fica em aberto)
- valor diferente → gravar com o valor informado

### 4. Perguntar gastos não rastreados

> "Teve algum gasto de lazer, restaurante, vestuário ou outros no mês que não registrou?"

Se sim → `INSERT INTO transactions` com categoria `Pessoal & Lazer` ou `Outros`.

### 5. Batch INSERT

```sql
-- Para cada item confirmado como pago:
INSERT INTO transactions (date, description, amount, type, category_id)
VALUES (:data_pagamento, :descricao, :valor, 'expense',
        (SELECT id FROM categories WHERE name = :categoria));
```

**Fatura de cartão paga:**
```sql
INSERT INTO transactions (date, description, amount, type, category_id)
VALUES (:data, 'Fatura ' || :nome_cartao, :valor, 'expense',
        (SELECT id FROM categories WHERE name = 'Fatura de cartão'));

UPDATE cards SET current_balance = 0, updated_at = datetime('now')
WHERE name = :nome_cartao;
```

### 6. Fechar e rodar motor

```bash
python3 "$SEVERINO_HOME/engine/derive_estado.py" YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
python3 "$SEVERINO_HOME/engine/render_graphs.py"  YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
```

Mostrar resumo do mês fechado:
- Total pago · Total a pagar · Saldo
- Score de saúde (`diagnosis.score` + `diagnosis.tier` do estado.json)

Concluir: "Mês fechado. Quer ver o diagnóstico completo? → `/severino-conselheiro`"

---

## Regras

- **Não comentar** a situação financeira durante o checklist. Só confirmar pagamentos.
- **Comentário estratégico** é papel exclusivo do `/severino-conselheiro`.
- Itens que o usuário diz "n" → permanecem no calendário como `paid: false` até serem registrados.
