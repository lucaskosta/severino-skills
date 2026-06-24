-- Severino — schema adicional (roda sobre o finance.db existente)
-- Mantém: transactions, budgets, goals
-- Adiciona: income_sources, accounts, cards, debts, investments, recurring_items, strategy

CREATE TABLE IF NOT EXISTS income_sources (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    amount         REAL    NOT NULL,
    type           TEXT    NOT NULL CHECK(type IN ('salary','freelance','investment','other')),
    frequency      TEXT    NOT NULL CHECK(frequency IN ('monthly','one_time','irregular')),
    status         TEXT    NOT NULL DEFAULT 'active'
                           CHECK(status IN ('active','pending','received','inactive')),
    expected_date  TEXT,   -- YYYY-MM-DD; null para mensais
    notes          TEXT    NOT NULL DEFAULT '',
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    bank        TEXT    NOT NULL,
    balance     REAL    NOT NULL DEFAULT 0,
    type        TEXT    NOT NULL CHECK(type IN ('checking','savings','caixinha','investment')),
    notes       TEXT    NOT NULL DEFAULT '',
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cards (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL,
    bank              TEXT    NOT NULL,
    credit_limit      REAL,
    current_balance   REAL    NOT NULL DEFAULT 0,   -- fatura corrente (a pagar este mês)
    deferred_balance  REAL    NOT NULL DEFAULT 0,   -- represado pro mês seguinte
    due_day           INTEGER,                       -- dia fixo de vencimento
    due_date          TEXT,                          -- data exata da fatura corrente YYYY-MM-DD
    status            TEXT    NOT NULL DEFAULT 'active'
                              CHECK(status IN ('active','blocked','cancelled')),
    notes             TEXT    NOT NULL DEFAULT '',
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS debts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    creditor            TEXT    NOT NULL,
    installment_amount  REAL    NOT NULL,
    installments_paid   INTEGER NOT NULL DEFAULT 0,
    installments_total  INTEGER NOT NULL,
    balance_remaining   REAL    NOT NULL,
    monthly_rate        REAL,   -- decimal (ex: 0.0875 para 8,75%/mês)
    due_day             INTEGER,
    type                TEXT    NOT NULL DEFAULT 'loan'
                                CHECK(type IN ('loan','financing','card_debt','other')),
    status              TEXT    NOT NULL DEFAULT 'active'
                                CHECK(status IN ('active','paid','deferred')),
    notes               TEXT    NOT NULL DEFAULT '',
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS investments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    type           TEXT    NOT NULL
                   CHECK(type IN ('credit_letter','cdb','savings','stocks','other')),
    amount         REAL    NOT NULL,
    availability   TEXT    NOT NULL DEFAULT 'blocked'
                   CHECK(availability IN ('available','blocked','partial')),
    expected_date  TEXT,   -- data estimada de resgate YYYY-MM-DD
    notes          TEXT    NOT NULL DEFAULT '',
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- recurring_items: gastos fixos recorrentes + essenciais do mês
-- group_name define o bloco:
--   fixas      → contas fixas (aluguel, escola, internet, academia, jiu, material)
--   essenciais → supermercado, compra_unica, outros não rastreados
--   utils      → utilities variáveis (água, luz)
--   atrasados  → saldos pendentes / pagamentos únicos do mês (imobiliária, etc.)
--   adiado     → valor empurrado pro mês seguinte
-- subgroup: subdivisão opcional (ex: 'supermercado'|'compra_unica'|'outros' para essenciais)
CREATE TABLE IF NOT EXISTS recurring_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    category        TEXT    NOT NULL,
    amount          REAL    NOT NULL,
    full_amount     REAL,   -- valor cheio quando há desconto por pagamento antecipado
    due_day         INTEGER,
    payment_method  TEXT    NOT NULL DEFAULT 'debit'
                    CHECK(payment_method IN ('debit','credit','pix','boleto')),
    group_name      TEXT    NOT NULL
                    CHECK(group_name IN ('fixas','essenciais','utils','atrasados','adiado')),
    subgroup        TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    notes           TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- strategy: plano financeiro ativo (uma linha por versão; active=1 é o vigente)
CREATE TABLE IF NOT EXISTS strategy (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    debt_method          TEXT    NOT NULL DEFAULT 'avalanche'
                                 CHECK(debt_method IN ('avalanche','snowball')),
    reserve_target       REAL    NOT NULL DEFAULT 0,
    reserve_current      REAL    NOT NULL DEFAULT 0,
    reserve_pct          REAL    NOT NULL DEFAULT 0.10,  -- % de toda entrada p/ reserva
    grocery_weekly_limit REAL,
    notes                TEXT    NOT NULL DEFAULT '',
    created_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    active               INTEGER NOT NULL DEFAULT 1
);
