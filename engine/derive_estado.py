#!/usr/bin/env python3
"""Deriva estado.json de um mês a partir do DB.

Uso:
    python engine/derive_estado.py 2026-07 --data-dir /Users/taru/IA/assistente/Financeiro
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

MONTHS_TITLE = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def month_slug(year_month: str) -> str:
    y, m = year_month.split("-")
    return f"{MONTHS_TITLE[int(m)].lower()}-{y}"


def month_title(year_month: str) -> str:
    y, m = year_month.split("-")
    return f"{MONTHS_TITLE[int(m)]} {y}"


def derive(year_month: str, data_dir: Path) -> dict:
    db_path = data_dir / "finance-mcp-server" / "data" / "finance.db"
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # ── perfil ────────────────────────────────────────────────────────────────
    strat = cur.execute(
        "SELECT * FROM strategy WHERE active=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()

    salary_row = cur.execute(
        "SELECT amount, name FROM income_sources WHERE type='salary' AND frequency='monthly' AND status='active' LIMIT 1"
    ).fetchone()
    salary = float(salary_row["amount"]) if salary_row else 0.0

    fixas_sum = float(cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM recurring_items WHERE group_name='fixas' AND active=1"
    ).fetchone()[0])
    loans_sum = float(cur.execute(
        "SELECT COALESCE(SUM(installment_amount),0) FROM debts WHERE status='active'"
    ).fetchone()[0])
    fixed_total = fixas_sum + loans_sum
    free_after_fixed = salary - fixed_total

    # ── entradas do mês ───────────────────────────────────────────────────────
    entries: list[dict] = []

    if salary_row:
        # Considera recebido só se a transação existe E a data já passou (não é futura)
        today = date.today().isoformat()
        received_salary = float(cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income' AND date LIKE ? AND date <= ? AND category IN ('Salário','salario') AND description NOT LIKE '%PROJETADO%'",
            (f"{year_month}%", today),
        ).fetchone()[0])
        status_sal = "✅ recebido" if received_salary > 0 else "⏳ pendente"
        entries.append({"status": status_sal, "descricao": salary_row["name"], "valor": salary})

    # Rendas avulsas esperadas para o mês
    for r in cur.execute(
        "SELECT name, amount, status FROM income_sources WHERE frequency IN ('one_time','irregular') AND expected_date LIKE ? AND status IN ('pending','received')",
        (f"{year_month}%",),
    ):
        emoji = "✅ recebido" if r["status"] == "received" else "⏳ pendente"
        entries.append({"status": emoji, "descricao": r["name"], "valor": float(r["amount"])})

    received_total = sum(e["valor"] for e in entries if "✅" in e["status"])
    pending_total = sum(e["valor"] for e in entries if "⏳" in e["status"])

    # ── contas (caixa em mãos) ────────────────────────────────────────────────
    cash_now = float(cur.execute(
        "SELECT COALESCE(SUM(balance),0) FROM accounts WHERE type IN ('checking','caixinha')"
    ).fetchone()[0])

    # ── blocos mensais ────────────────────────────────────────────────────────
    month_fixed = fixas_sum  # contas fixas sem empréstimos

    cards = cur.execute(
        "SELECT name, bank, current_balance, deferred_balance, due_day, due_date FROM cards WHERE status='active'"
    ).fetchall()
    cards_month = sum(float(c["current_balance"]) for c in cards)
    mp_repr = sum(float(c["deferred_balance"]) for c in cards)

    debts = cur.execute(
        "SELECT name, creditor, installment_amount, due_day FROM debts WHERE status='active'"
    ).fetchall()
    loans_month = loans_sum

    # essenciais
    compra_unica = float(cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM recurring_items WHERE group_name='essenciais' AND subgroup='compra_unica' AND active=1"
    ).fetchone()[0])
    supermercado = float(cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM recurring_items WHERE group_name='essenciais' AND subgroup='supermercado' AND active=1"
    ).fetchone()[0])
    outros = float(cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM recurring_items WHERE group_name='essenciais' AND subgroup='outros' AND active=1"
    ).fetchone()[0])
    essentials = compra_unica + supermercado

    # utils (água/luz): prefere transactions do mês se existirem
    # utils: procura conta de água/luz real — exclui mineral (consumível) e PROJETADO
    agua_tx = float(cur.execute(
        """SELECT COALESCE(SUM(amount),0) FROM transactions
           WHERE type='expense' AND date LIKE ? AND date <= ?
           AND category IN ('Casa','utilidades')
           AND (description LIKE '%gua%' OR description LIKE '%Luz%')
           AND description NOT LIKE '%mineral%'
           AND description NOT LIKE '%PROJETADO%'""",
        (f"{year_month}%", date.today().isoformat()),
    ).fetchone()[0])
    agua_ri = float(cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM recurring_items WHERE group_name='utils' AND active=1"
    ).fetchone()[0])
    agua = agua_tx if agua_tx > 0 else agua_ri

    # atrasados / pagamentos únicos (imobiliária, etc.)
    imob = float(cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM recurring_items WHERE group_name='atrasados' AND active=1"
    ).fetchone()[0])
    overdue_paid = agua + imob

    adiado = float(cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM recurring_items WHERE group_name='adiado' AND active=1"
    ).fetchone()[0])

    # ── itens fixos individuais ───────────────────────────────────────────────
    def get_fixo(pattern: str) -> float:
        r = cur.execute(
            "SELECT amount FROM recurring_items WHERE name LIKE ? AND group_name='fixas' AND active=1 LIMIT 1",
            (f"%{pattern}%",),
        ).fetchone()
        return float(r["amount"]) if r else 0.0

    aluguel  = get_fixo("Aluguel")
    internet = get_fixo("Internet")
    escola   = get_fixo("Escola")
    material = get_fixo("Material")
    academia = get_fixo("Academia")
    jiu      = get_fixo("Jiu")

    escola_row = cur.execute(
        "SELECT amount, full_amount FROM recurring_items WHERE name LIKE '%Escola%' AND group_name='fixas' AND active=1 LIMIT 1"
    ).fetchone()
    school_discount = 0.0
    if escola_row and escola_row["full_amount"]:
        school_discount = float(escola_row["full_amount"]) - float(escola_row["amount"])

    # ── resultado ─────────────────────────────────────────────────────────────
    # compromissos = fixas + cartões + empréstimos + água  (imob vem da caixinha)
    result_commitments = month_fixed + cards_month + loans_month + agua
    result_after_fixed = salary - result_commitments
    result_deficit = essentials - result_after_fixed

    # ── calendário (derivado dos vencimentos) ─────────────────────────────────
    cal: dict[str, float] = defaultdict(float)

    for r in cur.execute(
        "SELECT amount, due_day FROM recurring_items WHERE group_name='fixas' AND active=1 AND due_day IS NOT NULL"
    ):
        cal[f"{int(r['due_day']):02d}"] += float(r["amount"])

    for d in debts:
        if d["due_day"]:
            cal[f"{int(d['due_day']):02d}"] += float(d["installment_amount"])

    for c in cards:
        if c["due_day"]:
            cal[f"{int(c['due_day']):02d}"] += float(c["current_balance"])

    for r in cur.execute(
        "SELECT amount, due_day FROM recurring_items WHERE group_name='utils' AND active=1 AND due_day IS NOT NULL"
    ):
        cal[f"{int(r['due_day']):02d}"] += float(r["amount"])

    for r in cur.execute(
        "SELECT amount, due_day FROM recurring_items WHERE group_name='atrasados' AND active=1 AND due_day IS NOT NULL"
    ):
        cal[f"{int(r['due_day']):02d}"] += float(r["amount"])

    calendario = [{"dia": d, "valor": round(v, 2)} for d, v in sorted(cal.items())]

    # urgente = tudo que vence entre dia 8 e 10 (pós-salário no dia 7)
    urgent_total = sum(v for d, v in cal.items() if 8 <= int(d) <= 10)

    con.close()

    return {
        "schema_version": 1,
        "mes": year_month,
        "titulo": month_title(year_month),
        "perfil": {
            "salario": salary,
            "fixos_total": round(fixed_total, 2),
            "sobra_apos_fixos": round(free_after_fixed, 2),
            "reserva_meta": float(strat["reserve_target"]) if strat else 0.0,
            "reserva_atual": float(strat["reserve_current"]) if strat else 0.0,
            "pct_reserva": float(strat["reserve_pct"]) if strat else 0.10,
            "grocery_weekly_limit": float(strat["grocery_weekly_limit"]) if strat and strat["grocery_weekly_limit"] else 300.0,
        },
        "entradas": entries,
        "caixa_em_maos": round(cash_now, 2),
        "blocos": {
            "contas_fixas": round(month_fixed, 2),
            "cartoes": round(cards_month, 2),
            "emprestimos": round(loans_month, 2),
            "essenciais": round(essentials, 2),
            "compra_unica": round(compra_unica, 2),
            "supermercado": round(supermercado, 2),
            "outros_a_rastrear": round(outros, 2),
            "agua_luz": round(agua, 2),
            "imobiliaria_1x": round(imob, 2),
            "adiado": round(adiado, 2),
            "mp_represado": round(mp_repr, 2),
            "overdue_paid": round(overdue_paid, 2),
        },
        "itens_fixos": {
            "aluguel": aluguel,
            "internet": internet,
            "escola": escola,
            "escola_cheio": round(escola + school_discount, 2),
            "material": material,
            "academia": academia,
            "jiu": jiu,
        },
        "resultado": {
            "entradas_confirmadas": round(salary, 2),
            "compromissos": round(result_commitments, 2),
            "saldo_apos_fixo": round(result_after_fixed, 2),
            "essenciais_cartao": round(essentials, 2),
            "deficit_proximo_cartao": round(result_deficit, 2),
        },
        "calendario": calendario,
        "alertas": {
            "caixa_atual": round(cash_now, 2),
            "urgente_ate_dia_10": round(urgent_total, 2),
            "economia_escola": round(school_discount, 2),
            "adiado": round(adiado, 2),
        },
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

    slug = month_slug(args.year_month)
    out_dir = args.data_dir / "meses" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "estado.json"
    out_path.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
