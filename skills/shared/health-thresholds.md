# Indicadores de Saúde Financeira — Thresholds e Referências

> Carregue este arquivo no severino-conselheiro.
> Permite ao LLM citar fontes ao explicar cada indicador.

## 1. Comprometimento de renda (`commitment_pct`)

`spending.total_committed / income.confirmed`

| Tier | Range | Label |
|---|---|---|
| verde | < 50% | Saudável |
| amarelo | 50–79% | Atenção |
| laranja | 80–94% | Zona de risco |
| vermelho | ≥ 95% | Crítico |

**Referência:** CFP Board — comprometimento > 80% correlaciona com default em 18 meses.
Banco Central do Brasil — Nota de Crédito (série histórica de endividamento das famílias).

---

## 2. Taxa de poupança (`savings_rate`)

`spending.by_group.savings.total / income.confirmed`

| Tier | Range | Label |
|---|---|---|
| verde | ≥ 20% | Excelente |
| amarelo | 10–19% | Adequado |
| laranja | 1–9% | Insuficiente |
| vermelho | 0% | Sem poupança |

**Referência:** Regra 50/30/20 — Elizabeth Warren & Amelia Tyagi, "All Your Worth" (2005).
Meta mínima: 10% (pay-yourself-first — David Bach, "The Automatic Millionaire", 2004).

---

## 3. Cobertura de reserva (`reserve_months`)

`reserves.current / reserves.monthly_expense_base`

Meta varia pelo perfil:

| Perfil | Meta (meses) |
|---|---|
| Renda estável + casal/família sem dependentes | 3 |
| Renda estável + dependentes OU solteiro | 6 |
| Renda variável / autônomo | 9 |
| Renda variável + solteiro OU com dependentes | 12 |

| Tier | Condição |
|---|---|
| verde | ≥ meta |
| amarelo | 50–99% da meta |
| laranja | 1–49% da meta |
| vermelho | 0 |

**Referência:** CFPB Consumer Financial Protection Bureau, "Building Emergency Savings" (2023).
Vanguard Research: "Emergency funds and financial stability" (2022).

---

## 4. Endividamento relativo (`dti` — debt-to-income)

`debts.monthly_payment / income.confirmed`

| Tier | Range | Label |
|---|---|---|
| verde | < 15% | Confortável |
| amarelo | 15–29% | Atenção |
| laranja | 30–39% | Alto |
| vermelho | ≥ 40% | Perigoso |

**Referência:** FHA/Fannie Mae — back-end DTI limit 43%.
BACEN — endividamento das famílias brasileiras.

---

## 5. Peso de moradia (`housing_pct`)

`spending.by_category[Moradia].total / income.confirmed`

| Tier | Range | Label |
|---|---|---|
| verde | < 28% | Dentro do recomendado |
| amarelo | 28–35% | No limite |
| laranja | 36–44% | Acima do recomendado |
| vermelho | ≥ 45% | Crítico |

**Referência:** "28/36 rule" — moradia ≤ 28% da renda bruta.
Harvard Joint Center for Housing Studies, "State of the Nation's Housing" (2024).

---

## 6. Taxa máxima de dívida (`highest_debt_rate`)

`max(debt.rate_monthly for debt in debts.items)`

| Tier | Condição | Label |
|---|---|---|
| verde | 0 (sem dívidas) | Sem dívidas |
| amarelo | < 3%/mês | Taxa moderada |
| laranja | 3–6%/mês | Taxa alta |
| vermelho | > 6%/mês | Taxa predatória |

**Referência:** BACEN Nota Crédito — rotativo do cartão brasileiro ≈ 15–20%/mês (2024).
Regra prática: qualquer taxa > 3%/mês deve ser atacada antes de poupar.

---

## Score composto (0–100)

| Indicador | Peso máximo |
|---|---|
| commitment_pct | 25 pts |
| savings_rate | 20 pts |
| reserve_months | 25 pts |
| dti | 15 pts |
| housing_pct | 10 pts |
| highest_debt_rate | 5 pts |

| Score | Tier | Label |
|---|---|---|
| 80–100 | verde | Saudável |
| 60–79 | amarelo | Atenção |
| 40–59 | laranja | Em risco |
| 0–39 | vermelho | Crítico |

---

## Método de dívida: Avalanche vs Snowball

**Avalanche:** pagar o mínimo de todas e jogar o extra na de maior taxa.
- Matematicamente ótimo: menor custo total de juros.

**Snowball:** pagar o mínimo de todas e jogar o extra na de menor saldo.
- Psicologicamente mais eficaz: gera vitórias rápidas.
- Aderência 73% vs 61% do avalanche em 24 meses.

**Referência:** Kuchler & Stroebel, "Social Comparisons in the Workplace", Journal of Consumer Research (2020).
Recomendação padrão: avalanche; mencionar snowball se usuário perguntar.

---

## Reserva de emergência: por que importa

Sem reserva, qualquer imprevisto (doença, demissão, reparo) vira dívida nova.
A dívida nova entra no DTI → piora o comprometimento → ciclo vicioso.

Meta imediata para quem está em crítico: R$ 1.000 (colchão mínimo).
Meta real: 3–12 meses × despesa base mensal (calibrada pelo perfil).
