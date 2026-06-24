-- Severino — schema genérico v2
-- Cria todas as tabelas do zero.
-- Rodar: sqlite3 finance.db < engine/schema.sql

-- ─── A. FATOS ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS profile (
    id               INTEGER PRIMARY KEY CHECK(id = 1),
    name             TEXT,
    currency         TEXT    NOT NULL DEFAULT 'BRL',
    locale           TEXT    NOT NULL DEFAULT 'pt-BR',
    income_stability TEXT    CHECK(income_stability IN ('stable','variable')) DEFAULT 'stable',
    dependents       INTEGER NOT NULL DEFAULT 0,
    household        TEXT    CHECK(household IN ('single','couple','family')),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    parent_id    INTEGER REFERENCES categories(id),
    kind         TEXT    NOT NULL CHECK(kind IN ('expense','income','transfer')),
    budget_group TEXT    CHECK(budget_group IN ('needs','wants','savings')),
    essential    INTEGER NOT NULL DEFAULT 0,
    icon         TEXT,
    color        TEXT,
    open_finance TEXT,
    system       INTEGER NOT NULL DEFAULT 1,
    active       INTEGER NOT NULL DEFAULT 1,
    sort_order   INTEGER DEFAULT 0,
    UNIQUE(name, parent_id)
);

CREATE TABLE IF NOT EXISTS income_sources (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    amount        REAL    NOT NULL,
    type          TEXT    NOT NULL CHECK(type IN ('salary','freelance','investment','benefit','other')),
    frequency     TEXT    NOT NULL CHECK(frequency IN ('monthly','one_time','irregular')),
    status        TEXT    NOT NULL DEFAULT 'active'
                          CHECK(status IN ('active','pending','received','inactive')),
    expected_date TEXT,
    notes         TEXT    NOT NULL DEFAULT '',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    bank       TEXT    NOT NULL,
    balance    REAL    NOT NULL DEFAULT 0,
    type       TEXT    NOT NULL CHECK(type IN ('checking','savings','caixinha','investment')),
    notes      TEXT    NOT NULL DEFAULT '',
    updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cards (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    bank             TEXT    NOT NULL,
    credit_limit     REAL,
    current_balance  REAL    NOT NULL DEFAULT 0,
    deferred_balance REAL    NOT NULL DEFAULT 0,
    due_day          INTEGER,
    due_date         TEXT,
    status           TEXT    NOT NULL DEFAULT 'active'
                             CHECK(status IN ('active','blocked','cancelled')),
    notes            TEXT    NOT NULL DEFAULT '',
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS debts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT    NOT NULL,
    creditor           TEXT    NOT NULL,
    installment_amount REAL    NOT NULL,
    installments_paid  INTEGER NOT NULL DEFAULT 0,
    installments_total INTEGER NOT NULL,
    balance_remaining  REAL    NOT NULL,
    monthly_rate       REAL,
    due_day            INTEGER,
    type               TEXT    NOT NULL DEFAULT 'loan'
                               CHECK(type IN ('loan','financing','card_debt','other')),
    status             TEXT    NOT NULL DEFAULT 'active'
                               CHECK(status IN ('active','paid','deferred')),
    notes              TEXT    NOT NULL DEFAULT '',
    created_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS investments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    type          TEXT    NOT NULL
                  CHECK(type IN ('credit_letter','cdb','savings','stocks','other')),
    amount        REAL    NOT NULL,
    availability  TEXT    NOT NULL DEFAULT 'blocked'
                  CHECK(availability IN ('available','blocked','partial')),
    expected_date TEXT,
    notes         TEXT    NOT NULL DEFAULT '',
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recurring_items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    category_id    INTEGER REFERENCES categories(id),
    amount         REAL    NOT NULL,
    full_amount    REAL,
    frequency      TEXT    NOT NULL DEFAULT 'monthly'
                   CHECK(frequency IN ('monthly','weekly','yearly')),
    due_day        INTEGER,
    payment_method TEXT    CHECK(payment_method IN ('debit','credit','pix','boleto','cash')),
    variable       INTEGER NOT NULL DEFAULT 0,
    active         INTEGER NOT NULL DEFAULT 1,
    notes          TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,
    description TEXT    NOT NULL,
    amount      REAL    NOT NULL,
    type        TEXT    NOT NULL CHECK(type IN ('income','expense','transfer')),
    category_id INTEGER REFERENCES categories(id),
    account_id  INTEGER REFERENCES accounts(id),
    card_id     INTEGER REFERENCES cards(id),
    notes       TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ─── B. OBJETIVO ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS goals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL UNIQUE,
    kind           TEXT    CHECK(kind IN ('emergency_fund','purchase','debt_free','investment','custom')),
    target_amount  REAL    NOT NULL,
    current_amount REAL    NOT NULL DEFAULT 0,
    target_date    TEXT,
    priority       INTEGER DEFAULT 0,
    status         TEXT    NOT NULL DEFAULT 'active'
                   CHECK(status IN ('active','done','paused')),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS budgets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    year_month  TEXT    NOT NULL,
    amount      REAL    NOT NULL,
    UNIQUE(category_id, year_month)
);

-- ─── C. ESTRATÉGIA ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS strategy (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_focus         TEXT    CHECK(primary_focus IN ('debt_payoff','emergency_fund','budgeting','investing','custom')),
    budget_framework      TEXT    CHECK(budget_framework IN ('50_30_20','zero_based','envelope','free')),
    debt_method           TEXT    CHECK(debt_method IN ('avalanche','snowball','none')),
    reserve_target_months REAL,
    reserve_pct           REAL    NOT NULL DEFAULT 0.10,
    weekly_grocery_limit  REAL,
    source                TEXT    NOT NULL DEFAULT 'ai' CHECK(source IN ('ai','user')),
    notes                 TEXT    NOT NULL DEFAULT '',
    created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    active                INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS health_snapshot (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    taken_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    score             INTEGER,
    commitment_pct    REAL,
    reserve_months    REAL,
    dti               REAL,
    savings_rate      REAL,
    housing_pct       REAL,
    highest_debt_rate REAL,
    notes             TEXT    NOT NULL DEFAULT ''
);

-- ─── SEED: taxonomia BR genérica ─────────────────────────────────────────────
-- Raízes (parent_id NULL)

INSERT OR IGNORE INTO categories (id, name, parent_id, kind, budget_group, essential, sort_order) VALUES
-- necessidades
(1,  'Moradia',            NULL, 'expense', 'needs',   1, 10),
(2,  'Alimentação',        NULL, 'expense', 'needs',   1, 20),
(3,  'Transporte',         NULL, 'expense', 'needs',   1, 30),
(4,  'Saúde',              NULL, 'expense', 'needs',   1, 40),
(5,  'Educação',           NULL, 'expense', 'needs',   1, 50),
(6,  'Filhos/Dependentes', NULL, 'expense', 'needs',   1, 60),
(7,  'Dívidas',            NULL, 'expense', 'needs',   1, 70),
(8,  'Taxas & Impostos',   NULL, 'expense', 'needs',   1, 80),
-- desejos
(9,  'Pessoal & Lazer',    NULL, 'expense', 'wants',   0, 90),
(10, 'Pets',               NULL, 'expense', 'wants',   0, 100),
(11, 'Outros',             NULL, 'expense', 'wants',   0, 110),
-- receitas
(12, 'Salário',            NULL, 'income',  NULL,      0, 10),
(13, 'Renda Extra',        NULL, 'income',  NULL,      0, 20),
(14, 'Rendimentos',        NULL, 'income',  NULL,      0, 30),
(15, 'Benefícios',         NULL, 'income',  NULL,      0, 40),
-- transferências
(16, 'Reserva/Poupança',   NULL, 'transfer','savings', 0, 10),
(17, 'Investimento',       NULL, 'transfer','savings', 0, 20);

-- Subcategorias de Moradia (parent=1)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Aluguel/Prestação', 1, 'expense', 'needs', 1, 1),
('Condomínio',        1, 'expense', 'needs', 1, 2),
('Energia',           1, 'expense', 'needs', 1, 3),
('Água',              1, 'expense', 'needs', 1, 4),
('Gás',               1, 'expense', 'needs', 1, 5),
('Internet/Telefone', 1, 'expense', 'needs', 1, 6);

-- Subcategorias de Alimentação (parent=2)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Supermercado',   2, 'expense', 'needs', 1, 1),
('Refeição fora',  2, 'expense', 'needs', 1, 2),
('Delivery',       2, 'expense', 'needs', 1, 3);

-- Subcategorias de Transporte (parent=3)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Combustível',         3, 'expense', 'needs', 1, 1),
('Transporte público',  3, 'expense', 'needs', 1, 2),
('Apps (Uber/99)',      3, 'expense', 'needs', 1, 3),
('Manutenção',          3, 'expense', 'needs', 1, 4);

-- Subcategorias de Saúde (parent=4)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Plano de saúde', 4, 'expense', 'needs', 1, 1),
('Farmácia',       4, 'expense', 'needs', 1, 2),
('Consultas',      4, 'expense', 'needs', 1, 3);

-- Subcategorias de Educação (parent=5)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Mensalidade', 5, 'expense', 'needs', 1, 1),
('Cursos',      5, 'expense', 'needs', 1, 2),
('Material',    5, 'expense', 'needs', 1, 3);

-- Subcategorias de Filhos/Dependentes (parent=6)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Creche/Escola',  6, 'expense', 'needs', 1, 1),
('Cuidados',       6, 'expense', 'needs', 1, 2);

-- Subcategorias de Dívidas (parent=7)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Parcela de empréstimo', 7, 'expense', 'needs', 1, 1),
('Financiamento',         7, 'expense', 'needs', 1, 2),
('Fatura de cartão',      7, 'expense', 'needs', 1, 3);

-- Subcategorias de Taxas & Impostos (parent=8)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Tarifa bancária', 8, 'expense', 'needs', 1, 1),
('Impostos',        8, 'expense', 'needs', 1, 2);

-- Subcategorias de Pessoal & Lazer (parent=9)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Vestuário',     9, 'expense', 'wants', 0, 1),
('Assinaturas',   9, 'expense', 'wants', 0, 2),
('Lazer',         9, 'expense', 'wants', 0, 3),
('Beleza',        9, 'expense', 'wants', 0, 4),
('Academia',      9, 'expense', 'wants', 0, 5),
('Esporte',       9, 'expense', 'wants', 0, 6),
('Restaurantes',  9, 'expense', 'wants', 0, 7);

-- Subcategorias de Renda Extra (parent=13)
INSERT OR IGNORE INTO categories (name, parent_id, kind, budget_group, essential, sort_order) VALUES
('Freelance',  13, 'income', NULL, 0, 1),
('Bico',       13, 'income', NULL, 0, 2),
('Honorários', 13, 'income', NULL, 0, 3);
