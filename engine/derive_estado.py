#!/usr/bin/env python3
"""Deriva estado.json de um mês a partir do DB.

Uso:
    python engine/derive_estado.py 2026-07 --data-dir "$SEVERINO_DATA_DIR"
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

MONTHS_TITLE = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

# ─── helpers ──────────────────────────────────────────────────────────────────

def month_slug(ym: str) -> str:
    y, m = ym.split("-")
    return f"{MONTHS_TITLE[int(m)].lower()}-{y}"


def month_title(ym: str) -> str:
    y, m = ym.split("-")
    return f"{MONTHS_TITLE[int(m)]} {y}"


def flt(v) -> float:
    return float(v) if v is not None else 0.0


def _payoff_month(remaining: int) -> str | None:
    if remaining <= 0:
        return None
    today = date.today()
    idx = (today.month - 1) + (remaining - 1)
    y = today.year + idx // 12
    m = idx % 12 + 1
    return f"{y}-{m:02d}"


# ─── income ───────────────────────────────────────────────────────────────────

def derive_income(cur, ym: str) -> dict:
    today = date.today().isoformat()

    salary_row = cur.execute(
        "SELECT id, name, amount FROM income_sources "
        "WHERE type='salary' AND frequency='monthly' AND status='active' LIMIT 1"
    ).fetchone()
    salary = flt(salary_row["amount"]) if salary_row else 0.0

    sources = []
    if salary_row:
        received = flt(cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions "
            "WHERE type='income' AND date LIKE ? AND date <= ? "
            "AND category_id=(SELECT id FROM categories WHERE name='Salário' AND system=1 LIMIT 1)",
            (f"{ym}%", today),
        ).fetchone()[0])
        sources.append({
            "name": salary_row["name"],
            "amount": salary,
            "status": "confirmed" if received > 0 else "pending",
        })

    for r in cur.execute(
        "SELECT name, amount, status FROM income_sources "
        "WHERE frequency IN ('one_time','irregular') AND expected_date LIKE ? "
        "AND status IN ('pending','received')",
        (f"{ym}%",),
    ):
        sources.append({
            "name": r["name"],
            "amount": flt(r["amount"]),
            "status": "confirmed" if r["status"] == "received" else "pending",
        })

    confirmed = sum(s["amount"] for s in sources if s["status"] == "confirmed")
    pending   = sum(s["amount"] for s in sources if s["status"] == "pending")
    return {
        "confirmed":       round(confirmed, 2),
        "pending":         round(pending, 2),
        "total_expected":  round(confirmed + pending, 2),
        "sources":         sources,
    }


# ─── spending ─────────────────────────────────────────────────────────────────

def derive_spending(cur, ym: str, income_confirmed: float) -> dict:
    today = date.today().isoformat()

    # Soma de recurring_items ativos + transactions do mês agrupadas por categoria raiz
    # 1. Recurring items ativos (recurring → será marcado paid via transaction no pente-fino)
    ri_rows = cur.execute(
        """SELECT ri.name, ri.amount, ri.due_day, ri.variable,
                  c.id AS cat_id, c.name AS cat_name, c.budget_group, c.essential,
                  COALESCE(c.parent_id, c.id) AS root_id
           FROM recurring_items ri
           JOIN categories c ON ri.category_id = c.id
           WHERE ri.active = 1""",
    ).fetchall()

    # 2. Transactions não-recorrentes do mês
    tx_rows = cur.execute(
        """SELECT t.amount, t.description, t.date,
                  c.id AS cat_id, c.name AS cat_name, c.budget_group, c.essential,
                  COALESCE(c.parent_id, c.id) AS root_id
           FROM transactions t
           JOIN categories c ON t.category_id = c.id
           WHERE t.type IN ('expense','transfer')
             AND t.date LIKE ?
             AND t.date <= ?""",
        (f"{ym}%", today),
    ).fetchall()

    # Raízes disponíveis
    roots = {r["id"]: r for r in cur.execute(
        "SELECT id, name, budget_group, essential FROM categories WHERE parent_id IS NULL AND active=1"
    ).fetchall()}

    # Acumular por categoria raiz
    root_totals: dict[int, float] = {}
    root_items:  dict[int, list]  = {}

    for ri in ri_rows:
        rid = ri["root_id"]
        root_totals[rid] = root_totals.get(rid, 0.0) + flt(ri["amount"])
        root_items.setdefault(rid, []).append({
            "name":     ri["name"],
            "amount":   flt(ri["amount"]),
            "due_day":  ri["due_day"],
            "variable": bool(ri["variable"]),
            "paid":     False,  # será atualizado via transactions no pente-fino
        })

    for tx in tx_rows:
        rid = tx["root_id"]
        root_totals[rid] = root_totals.get(rid, 0.0) + flt(tx["amount"])
        root_items.setdefault(rid, []).append({
            "name":   tx["description"],
            "amount": flt(tx["amount"]),
            "date":   tx["date"],
            "paid":   True,
        })

    # Montar by_category (só raízes com movimentação)
    by_category = []
    for rid, total in sorted(root_totals.items(), key=lambda x: -x[1]):
        if rid not in roots:
            continue
        root = roots[rid]
        by_category.append({
            "id":           rid,
            "name":         root["name"],
            "budget_group": root["budget_group"],
            "essential":    bool(root["essential"]),
            "total":        round(total, 2),
            "items":        root_items.get(rid, []),
        })

    # by_group (50/30/20)
    group_totals: dict[str, float] = {"needs": 0.0, "wants": 0.0, "savings": 0.0}
    for cat in by_category:
        g = cat["budget_group"]
        if g in group_totals:
            group_totals[g] += cat["total"]

    def pct(v: float) -> float:
        return round(v / income_confirmed * 100, 1) if income_confirmed else 0.0

    by_group = {
        g: {"total": round(t, 2), "pct_income": pct(t)}
        for g, t in group_totals.items()
    }

    total = round(sum(group_totals.values()), 2)

    # paid vs unpaid (via transactions existentes)
    paid = flt(cur.execute(
        "SELECT COALESCE(SUM(t.amount),0) FROM transactions t "
        "WHERE t.type IN ('expense','transfer') AND t.date LIKE ? AND t.date <= ?",
        (f"{ym}%", today),
    ).fetchone()[0])

    return {
        "total_committed": total,
        "paid":            round(paid, 2),
        "unpaid":          round(total - paid, 2),
        "by_group":        by_group,
        "by_category":     by_category,
    }


# ─── debts ────────────────────────────────────────────────────────────────────

def derive_debts(cur, income_confirmed: float) -> dict:
    rows = cur.execute(
        "SELECT name, creditor, installment_amount, installments_paid, "
        "installments_total, balance_remaining, monthly_rate, due_day "
        "FROM debts WHERE status='active' ORDER BY monthly_rate DESC NULLS LAST"
    ).fetchall()

    items = []
    monthly_payment = 0.0
    for r in rows:
        monthly_payment += flt(r["installment_amount"])
        remaining = r["installments_total"] - r["installments_paid"]
        items.append({
            "name":            r["name"],
            "creditor":        r["creditor"],
            "rate_monthly":    flt(r["monthly_rate"]),
            "installment":     flt(r["installment_amount"]),
            "paid_count":      r["installments_paid"],
            "total_count":     r["installments_total"],
            "remaining_count": remaining,
            "outstanding":     flt(r["balance_remaining"]),
            "due_day":         r["due_day"],
            "payoff_month":    _payoff_month(remaining),
        })

    total = round(sum(i["outstanding"] for i in items), 2)
    dti   = round(monthly_payment / income_confirmed, 3) if income_confirmed else 0.0

    return {
        "total_outstanding": total,
        "monthly_payment":   round(monthly_payment, 2),
        "dti":               dti,
        "items":             items,
    }


# ─── cards ────────────────────────────────────────────────────────────────────

def derive_cards(cur) -> dict:
    rows = cur.execute(
        "SELECT name, bank, credit_limit, current_balance, deferred_balance, due_day "
        "FROM cards WHERE status='active'"
    ).fetchall()

    items = []
    for r in rows:
        limit = flt(r["credit_limit"])
        used  = flt(r["current_balance"])
        items.append({
            "name":        r["name"],
            "bank":        r["bank"],
            "limit":       limit,
            "used":        used,
            "pct_used":    round(used / limit * 100, 1) if limit else 0.0,
            "deferred":    flt(r["deferred_balance"]),
            "due_day":     r["due_day"],
        })

    return {
        "total_open":  round(sum(i["used"]     for i in items), 2),
        "total_defer": round(sum(i["deferred"] for i in items), 2),
        "items":       items,
    }


# ─── reserves ─────────────────────────────────────────────────────────────────

def derive_reserves(cur, spending: dict) -> dict:
    reserve_cat = cur.execute(
        "SELECT id FROM categories WHERE name='Reserva/Poupança' AND system=1 LIMIT 1"
    ).fetchone()
    reserve_cat_id = reserve_cat["id"] if reserve_cat else None

    current = 0.0
    if reserve_cat_id:
        current = flt(cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions "
            "WHERE type='transfer' AND category_id=? AND date <= date('now')",
            (reserve_cat_id,),
        ).fetchone()[0])

    profile = cur.execute("SELECT * FROM profile WHERE id=1").fetchone()
    target_months = _reserve_target_months(profile)
    monthly_base  = spending["by_group"]["needs"]["total"]
    target        = round(target_months * monthly_base, 2)
    months_covered = round(current / monthly_base, 2) if monthly_base else 0.0

    # Atualiza strategy com reserva atual
    cur.execute("UPDATE strategy SET reserve_target_months=? WHERE active=1", (target_months,))

    return {
        "current":             round(current, 2),
        "target":              target,
        "target_months":       target_months,
        "months_covered":      months_covered,
        "monthly_expense_base": round(monthly_base, 2),
    }


def _reserve_target_months(profile) -> int:
    if not profile:
        return 3
    stability  = profile["income_stability"] or "stable"
    dependents = profile["dependents"] or 0
    household  = profile["household"] or "couple"
    if stability == "variable" and (dependents > 0 or household == "single"):
        return 12
    if stability == "variable":
        return 9
    if dependents > 0 or household == "single":
        return 6
    return 3


# ─── investments ──────────────────────────────────────────────────────────────

def derive_investments(cur) -> dict:
    rows = cur.execute(
        "SELECT name, type, amount, availability FROM investments"
    ).fetchall()
    items = [{"name": r["name"], "type": r["type"],
              "amount": flt(r["amount"]), "liquid": r["availability"] == "available"}
             for r in rows]
    return {
        "total":  round(sum(i["amount"] for i in items), 2),
        "liquid": round(sum(i["amount"] for i in items if i["liquid"]), 2),
        "items":  items,
    }


# ─── calendar ─────────────────────────────────────────────────────────────────

def derive_calendar(cur, ym: str) -> dict:
    today = date.today().isoformat()
    items = []

    # Recurring items com vencimento
    for r in cur.execute(
        """SELECT ri.name, ri.amount, ri.due_day,
                  c.budget_group, c.id AS cat_id
           FROM recurring_items ri
           JOIN categories c ON ri.category_id = c.id
           WHERE ri.active=1 AND ri.due_day IS NOT NULL
           ORDER BY ri.due_day""",
    ):
        due_date = f"{ym}-{int(r['due_day']):02d}"
        paid = flt(cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions "
            "WHERE type IN ('expense','transfer') AND date=? AND category_id=? AND date<=?",
            (due_date, r["cat_id"], today),
        ).fetchone()[0]) > 0
        items.append({
            "due_day":      r["due_day"],
            "name":         r["name"],
            "amount":       flt(r["amount"]),
            "paid":         paid,
            "budget_group": r["budget_group"],
            "category_id":  r["cat_id"],
        })

    # Dívidas
    for d in cur.execute(
        "SELECT name, installment_amount, due_day FROM debts WHERE status='active' AND due_day IS NOT NULL ORDER BY due_day"
    ):
        items.append({
            "due_day":      d["due_day"],
            "name":         d["name"],
            "amount":       flt(d["installment_amount"]),
            "paid":         False,
            "budget_group": "needs",
            "category_id":  None,
        })

    # Faturas de cartão
    for c in cur.execute(
        "SELECT name, current_balance, due_day FROM cards WHERE status='active' AND current_balance > 0 AND due_day IS NOT NULL ORDER BY due_day"
    ):
        items.append({
            "due_day":      c["due_day"],
            "name":         f"{c['name']} — cartão",
            "amount":       flt(c["current_balance"]),
            "paid":         False,
            "budget_group": "needs",
            "category_id":  None,
        })

    items.sort(key=lambda x: x["due_day"])
    total_paid   = round(sum(i["amount"] for i in items if i["paid"]), 2)
    total_unpaid = round(sum(i["amount"] for i in items if not i["paid"]), 2)

    return {
        "items":         items,
        "total_paid":    total_paid,
        "total_unpaid":  total_unpaid,
        "urgent_before": 10,
    }


# ─── health ───────────────────────────────────────────────────────────────────

HEALTH_WEIGHTS = {
    "commitment_pct":    25,
    "savings_rate":      20,
    "reserve_months":    25,
    "dti":               15,
    "housing_pct":       10,
    "highest_debt_rate":  5,
}


def _tier_commitment(v: float) -> str:
    if v < 0.50:  return "verde"
    if v < 0.80:  return "amarelo"
    if v < 0.95:  return "laranja"
    return "vermelho"


def _tier_savings(v: float) -> str:
    if v >= 0.20: return "verde"
    if v >= 0.10: return "amarelo"
    if v > 0.0:   return "laranja"
    return "vermelho"


def _tier_reserve(v: float, target: int) -> str:
    if v >= target:          return "verde"
    if v >= target * 0.5:    return "amarelo"
    if v > 0:                return "laranja"
    return "vermelho"


def _tier_dti(v: float) -> str:
    if v < 0.15:  return "verde"
    if v < 0.30:  return "amarelo"
    if v < 0.40:  return "laranja"
    return "vermelho"


def _tier_housing(v: float) -> str:
    if v < 0.28:  return "verde"
    if v < 0.36:  return "amarelo"
    if v < 0.45:  return "laranja"
    return "vermelho"


def _tier_debt_rate(v: float) -> str:
    if v == 0.0:  return "verde"
    if v < 0.03:  return "amarelo"
    if v < 0.06:  return "laranja"
    return "vermelho"


def _points(tier: str, weight: int) -> int:
    return {
        "verde":    weight,
        "amarelo":  round(weight * 0.65),
        "laranja":  round(weight * 0.25),
        "vermelho": 0,
    }[tier]


def compute_health(income: dict, spending: dict, debts: dict,
                   reserves: dict) -> tuple[dict, list[str]]:
    inc = income["confirmed"] or 1.0  # evitar divisão por zero

    housing_total = next(
        (c["total"] for c in spending["by_category"] if c["name"] == "Moradia"), 0.0
    )

    vals = {
        "commitment_pct":    spending["total_committed"] / inc,
        "savings_rate":      spending["by_group"]["savings"]["total"] / inc,
        "reserve_months":    reserves["months_covered"],
        "dti":               debts["dti"],
        "housing_pct":       housing_total / inc,
        "highest_debt_rate": max((d["rate_monthly"] for d in debts["items"]), default=0.0),
    }

    target_months = reserves["target_months"]
    tier_fns = {
        "commitment_pct":    _tier_commitment,
        "savings_rate":      _tier_savings,
        "reserve_months":    lambda v: _tier_reserve(v, target_months),
        "dti":               _tier_dti,
        "housing_pct":       _tier_housing,
        "highest_debt_rate": _tier_debt_rate,
    }

    indicators = {}
    score = 0
    for key, val in vals.items():
        tier = tier_fns[key](val)
        pts  = _points(tier, HEALTH_WEIGHTS[key])
        score += pts
        indicators[key] = {"value": round(val, 4), "tier": tier, "points": pts, "max": HEALTH_WEIGHTS[key]}

    if score >= 80:   tier_overall = "verde"
    elif score >= 60: tier_overall = "amarelo"
    elif score >= 40: tier_overall = "laranja"
    else:             tier_overall = "vermelho"

    # flags controláveis (acumulam)
    flags: list[str] = []
    v = vals["commitment_pct"]
    if v >= 0.95:  flags.append("commitment_critical")
    elif v >= 0.80: flags.append("commitment_high")
    if vals["savings_rate"] == 0.0:               flags.append("no_savings")
    if vals["reserve_months"] == 0.0:             flags.append("no_reserve")
    elif indicators["reserve_months"]["tier"] in ("laranja","amarelo"):
        flags.append("reserve_partial")
    if vals["highest_debt_rate"] > 0.06:          flags.append("predatory_debt_rate")
    elif vals["highest_debt_rate"] > 0.03:        flags.append("high_debt_rate")
    if vals["housing_pct"] > 0.35:                flags.append("housing_over")
    if vals["dti"] >= 0.30:                       flags.append("dti_high")

    diagnosis = {
        "score":      score,
        "tier":       tier_overall,
        "indicators": indicators,
        "flags":      flags,
    }
    return diagnosis, flags


# ─── recommendation ───────────────────────────────────────────────────────────

def compute_recommendation(flags: list[str], income: dict, debts: dict,
                            reserves: dict, spending: dict) -> dict:
    inc = income["confirmed"]

    # primary_focus (waterfall)
    if "predatory_debt_rate" in flags:
        focus = "debt_payoff"
        focus_reason = (
            f"Taxa máxima {max(d['rate_monthly'] for d in debts['items']):.2%}/mês "
            f"≈ {max(d['rate_monthly'] for d in debts['items'])*12:.0%}/ano. "
            "Qualquer poupança paralela rende menos que o custo dessa dívida."
        )
    elif "no_reserve" in flags and spending["total_committed"] / inc < 0.80:
        focus = "emergency_fund"
        focus_reason = "Sem reserva. Com margem disponível, priorizar colchão antes de qualquer meta."
    elif "commitment_critical" in flags or "dti_high" in flags:
        focus = "debt_payoff"
        focus_reason = "Comprometimento crítico bloqueia qualquer outra meta. Liquidar dívidas primeiro."
    elif "no_reserve" in flags:
        focus = "budgeting"
        focus_reason = "Sem margem pra poupar diretamente. Precisa liberar espaço no orçamento primeiro."
    elif any(True for _ in (r for r in [] if r)):  # placeholder goals check
        focus = "investing"
        focus_reason = "Saúde básica ok. Hora de crescer patrimônio."
    else:
        focus = "budgeting"
        focus_reason = "Manter equilíbrio e monitorar os grupos de gasto."

    # debt_method
    debt_method = "none"
    method_reason = "Sem dívidas ativas."
    avalanche_order = []
    if debts["items"]:
        sorted_av = sorted(debts["items"], key=lambda d: d["rate_monthly"], reverse=True)
        avalanche_order = [
            {"name": d["name"], "rate": d["rate_monthly"],
             "outstanding": d["outstanding"], "installment": d["installment"],
             "payoff_month": d.get("payoff_month")}
            for d in sorted_av
        ]
        debt_method = "avalanche"
        rates = [d["rate_monthly"] for d in debts["items"]]
        if len(rates) > 1 and max(rates) / min(rates) < 2.0:
            method_reason = "Taxas similares; avalanche e snowball produzem resultado parecido. Avalanche por padrão."
        else:
            method_reason = "Taxas diferentes; avalanche economiza mais juros. Snowball útil se precisar de motivação de vitória rápida."

    # budget_framework
    commitment = spending["total_committed"] / inc if inc else 1.0
    savings    = spending["by_group"]["savings"]["total"] / inc if inc else 0.0
    if commitment >= 0.95:
        framework = "zero_based"
        framework_reason = "Margem zero exige controle item a item."
    elif commitment >= 0.70:
        framework = "50_30_20"
        framework_reason = "Diagnóstico mostra onde ajustar (needs/wants/savings fora do ideal)."
    elif savings < 0.10:
        framework = "50_30_20"
        framework_reason = "Poupança baixa apesar de margem disponível; estrutura ajuda a reservar."
    else:
        framework = "free"
        framework_reason = "Saúde ok; monitoramento leve suficiente."

    # reserve_pct (pay-yourself-first)
    if commitment >= 0.80:
        reserve_pct = 0.05
    else:
        reserve_pct = 0.10

    pay_yourself = round(inc * reserve_pct, 2)

    # alerts a partir das flags
    FLAG_MESSAGES = {
        "predatory_debt_rate": "Taxa predatória (>6%/mês). Atacar imediatamente.",
        "high_debt_rate":      "Taxa alta (>3%/mês). Priorizar quitação.",
        "commitment_critical": "Mais de 95% da renda comprometida. Zona crítica.",
        "commitment_high":     "80–95% da renda comprometida. Atenção.",
        "no_savings":          "Taxa de poupança zero.",
        "no_reserve":          "Sem reserva. Qualquer imprevisto vira dívida nova.",
        "reserve_partial":     "Reserva abaixo da meta.",
        "housing_over":        "Moradia acima de 35% da renda.",
        "dti_high":            "Parcelas de dívida acima de 30% da renda.",
    }
    TIERS = {
        "predatory_debt_rate": "vermelho", "commitment_critical": "vermelho",
        "no_savings":          "vermelho", "no_reserve":          "vermelho",
        "high_debt_rate":      "laranja",  "commitment_high":     "laranja",
        "dti_high":            "laranja",  "reserve_partial":     "amarelo",
        "housing_over":        "amarelo",
    }
    alerts = [
        {"tier": TIERS.get(f, "amarelo"), "flag": f, "message": FLAG_MESSAGES.get(f, f)}
        for f in flags
    ]
    alerts.sort(key=lambda a: ["vermelho","laranja","amarelo","verde"].index(a["tier"]))

    return {
        "primary_focus":         focus,
        "budget_framework":      framework,
        "debt_method":           debt_method,
        "reserve_target_months": reserves["target_months"],
        "reserve_target":        reserves["target"],
        "reserve_pct":           reserve_pct,
        "pay_yourself_first":    pay_yourself,
        "focus_reason":          focus_reason,
        "method_reason":         method_reason,
        "framework_reason":      framework_reason,
        "avalanche_order":       avalanche_order,
        "alerts":                alerts,
        "source":                "ai",
        "generated_at":          datetime.now().isoformat(timespec="seconds"),
    }


# ─── charts ───────────────────────────────────────────────────────────────────

def derive_charts(income: dict, spending: dict, debts: dict,
                  cards: dict, reserves: dict, calendar: dict,
                  diagnosis: dict) -> dict:
    charts: dict = {}

    # V1 flow
    charts["flow"] = {
        "income_confirmed":   income["confirmed"],
        "income_pending":     income["pending"],
        "spending_total":     spending["total_committed"],
        "balance":            round(income["confirmed"] - spending["total_committed"], 2),
        "balance_label":      "sobra" if income["confirmed"] >= spending["total_committed"] else "déficit",
    }

    # V2 breakdown (50/30/20)
    charts["breakdown"] = {
        "by_group": [
            {"group": g, "label": lbl, "total": spending["by_group"][g]["total"],
             "pct": spending["by_group"][g]["pct_income"], "target_pct": tgt}
            for g, lbl, tgt in [
                ("needs",   "Necessidades", 50),
                ("wants",   "Desejos",      30),
                ("savings", "Poupança",     20),
            ]
        ],
        "framework": "50_30_20",
    }

    # V3 categories
    charts["categories"] = {
        "items": [
            {"name": c["name"], "total": c["total"],
             "pct_income": spending["by_group"].get(c["budget_group"], {}).get("pct_income", 0.0),
             "essential": c["essential"]}
            for c in spending["by_category"]
        ]
    }

    # V4 calendar
    charts["calendar"] = calendar

    # V5 health radar
    charts["health_radar"] = {
        "indicators": [
            {"key": k, "label": lbl, "value": diagnosis["indicators"][k]["value"],
             "tier": diagnosis["indicators"][k]["tier"],
             "score": diagnosis["indicators"][k]["points"],
             "max":   diagnosis["indicators"][k]["max"]}
            for k, lbl in [
                ("commitment_pct",    "Comprometimento"),
                ("savings_rate",      "Poupança"),
                ("reserve_months",    "Reserva"),
                ("dti",               "Dívidas/Renda"),
                ("housing_pct",       "Moradia"),
                ("highest_debt_rate", "Pior taxa"),
            ]
        ],
        "score": diagnosis["score"],
        "tier":  diagnosis["tier"],
    }

    # V6 card_cycle (condicional)
    if cards["items"]:
        charts["card_cycle"] = {"items": cards["items"], "total_open": cards["total_open"]}

    # V7 debt_timeline (condicional)
    if debts["items"]:
        charts["debt_timeline"] = {
            "method":              "avalanche",
            "items":               sorted(debts["items"], key=lambda d: d["rate_monthly"], reverse=True),
            "total_freed_monthly": debts["monthly_payment"],
        }

    return charts


# ─── health_snapshot ──────────────────────────────────────────────────────────

def save_health_snapshot(cur, diagnosis: dict, ym: str) -> None:
    ind = diagnosis["indicators"]
    cur.execute(
        "INSERT INTO health_snapshot "
        "(score, commitment_pct, reserve_months, dti, savings_rate, housing_pct, highest_debt_rate, notes) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            diagnosis["score"],
            ind["commitment_pct"]["value"],
            ind["reserve_months"]["value"],
            ind["dti"]["value"],
            ind["savings_rate"]["value"],
            ind["housing_pct"]["value"],
            ind["highest_debt_rate"]["value"],
            ym,
        ),
    )


# ─── main ─────────────────────────────────────────────────────────────────────

def derive(ym: str, data_dir: Path) -> dict:
    db_path = data_dir / "finance-mcp-server" / "data" / "finance.db"
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    income      = derive_income(cur, ym)
    spending    = derive_spending(cur, ym, income["confirmed"])
    debts       = derive_debts(cur, income["confirmed"])
    cards       = derive_cards(cur)
    reserves    = derive_reserves(cur, spending)
    investments = derive_investments(cur)
    calendar    = derive_calendar(cur, ym)
    diagnosis, flags = compute_health(income, spending, debts, reserves)
    recommendation   = compute_recommendation(flags, income, debts, reserves, spending)
    charts           = derive_charts(income, spending, debts, cards, reserves, calendar, diagnosis)

    save_health_snapshot(cur, diagnosis, ym)

    profile_row = cur.execute("SELECT * FROM profile WHERE id=1").fetchone()
    profile = {
        "income_stability":      profile_row["income_stability"] if profile_row else None,
        "dependents":            profile_row["dependents"]       if profile_row else 0,
        "household":             profile_row["household"]        if profile_row else None,
        "reserve_target_months": reserves["target_months"],
    } if profile_row else {}

    con.commit()
    con.close()

    return {
        "schema_version": 2,
        "meta": {
            "month":        ym,
            "title":        month_title(ym),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "currency":     "BRL",
            "locale":       "pt-BR",
        },
        "profile":        profile,
        "income":         income,
        "spending":       spending,
        "debts":          debts,
        "cards":          cards,
        "reserves":       reserves,
        "investments":    investments,
        "calendar":       calendar,
        "diagnosis":      diagnosis,
        "recommendation": recommendation,
        "charts":         charts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deriva estado.json do mês a partir do DB.")
    parser.add_argument("year_month", help="YYYY-MM")
    parser.add_argument("--data-dir", required=True, type=Path, help="Caminho para Financeiro/")
    args = parser.parse_args()

    try:
        datetime.strptime(args.year_month, "%Y-%m")
    except ValueError:
        print("Formato inválido — use YYYY-MM", file=sys.stderr)
        return 1

    estado = derive(args.year_month, args.data_dir)

    slug    = month_slug(args.year_month)
    out_dir = args.data_dir / "meses" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "estado.json"
    out_path.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
