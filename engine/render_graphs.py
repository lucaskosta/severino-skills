#!/usr/bin/env python3
"""Gera os 12 SVGs do painel a partir do estado.json.

Uso:
    python engine/render_graphs.py 2026-07 --data-dir /Users/taru/IA/assistente/Financeiro
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

MONTHS_TITLE = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

PALETTE = ["#38bdf8", "#22c55e", "#f59e0b", "#ef4444", "#a78bfa", "#f472b6", "#14b8a6"]


def month_slug(year_month: str) -> str:
    y, m = year_month.split("-")
    return f"{MONTHS_TITLE[int(m)].lower()}-{y}"


def month_title(year_month: str) -> str:
    y, m = year_month.split("-")
    return f"{MONTHS_TITLE[int(m)]} {y}"


def fmt_brl(value: float) -> str:
    formatted = f"{value:,.2f}"
    return f"R$ {formatted}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value: float) -> str:
    return f"{value:.1f}%".replace(".", ",")


def scale_width(value: float, max_value: float, max_width: int = 620) -> int:
    if max_value <= 0:
        return 0
    return max(18, int((value / max_value) * max_width))


def write_svg(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def load_estado(year_month: str, data_dir: Path) -> dict:
    slug = month_slug(year_month)
    estado_path = data_dir / "meses" / slug / "estado.json"
    if not estado_path.exists():
        raise FileNotFoundError(f"estado.json não encontrado: {estado_path}\n  → rode derive_estado.py primeiro")
    with open(estado_path, encoding="utf-8") as f:
        e = json.load(f)

    itens  = e["itens_fixos"]
    blocos = e["blocos"]
    perf   = e["perfil"]
    res    = e["resultado"]
    ale    = e["alertas"]

    entries = [(ent["status"], ent["descricao"], ent["valor"]) for ent in e["entradas"]]
    received_total = sum(v for s, _, v in entries if "✅" in s)
    pending_total  = sum(v for s, _, v in entries if "⏳" in s)

    mf  = blocos["contas_fixas"]
    cm  = blocos["cartoes"]
    lm  = blocos["emprestimos"]
    ag  = blocos["agua_luz"]
    im  = blocos["imobiliaria_1x"]
    ov  = blocos["overdue_paid"]
    ad  = blocos["adiado"]

    return {
        "salary":            perf["salario"],
        "fixed_total":       perf["fixos_total"],
        "free_after_fixed":  perf["sobra_apos_fixos"],
        "month_fixed":       mf,
        "cards_month":       cm,
        "loans_month":       lm,
        "essentials":        blocos["essenciais"],
        "one_time":          blocos["compra_unica"],
        "supermarket":       blocos["supermercado"],
        "deferred":          ad,
        "overdue_paid":      ov,
        "agua":              ag,
        "imob":              im,
        "mp_repr":           blocos["mp_represado"],
        "outros":            blocos["outros_a_rastrear"],
        "aluguel":           itens["aluguel"],
        "internet":          itens["internet"],
        "escola":            itens["escola"],
        "material":          itens["material"],
        "academia":          itens["academia"],
        "jiu":               itens["jiu"],
        "entries":           entries,
        "received_total":    received_total,
        "pending_total":     pending_total,
        "cash_now":          e["caixa_em_maos"],
        "result_income":     res["entradas_confirmadas"],
        "result_commitments": res["compromissos"],
        "result_after_fixed": res["saldo_apos_fixo"],
        "result_essentials": res["essenciais_cartao"],
        "result_deficit":    res["deficit_proximo_cartao"],
        "calendar_events":   [(c["dia"], c["valor"]) for c in e["calendario"]],
        "school_discount":   ale["economia_escola"],
        "urgent_total":      ale["urgente_ate_dia_10"],
        "cash_categories": [
            ("Cartão (fatura)", cm),
            ("Contas fixas", mf),
            ("Empréstimos", lm),
            ("Água/Luz", ag),
            ("Imobiliária (1x)", im),
        ],
        "living_categories": [
            ("Essenciais", blocos["essenciais"]),
            ("Contas fixas", mf),
            ("Empréstimos", lm),
            ("Água/Luz", ag),
            ("Imobiliária (1x)", im),
        ],
        "commitment_blocks": [
            ("Contas fixas", mf),
            ("Cartões", cm),
            ("Empréstimos", lm),
            ("Atrasados pagos", ov),
            ("Adiado", ad),
        ],
    }


# ── builders SVG (idênticos ao gerador original) ──────────────────────────────

def build_category_donut_svg(title: str, items, generated_at: str, subtitle: str, note: str) -> str:
    items = [(label, value) for label, value in items if value > 0]
    total = sum(value for _, value in items) or 1.0
    radius = 88
    circumference = 2 * math.pi * radius
    center_x, center_y = 180, 215
    offset = 0.0
    circles, legend = [], []

    for idx, (label, value) in enumerate(items):
        color = PALETTE[idx % len(PALETTE)]
        segment = circumference * (value / total)
        circles.append(
            f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="none" stroke="{color}" stroke-width="34" '
            f'stroke-linecap="butt" stroke-dasharray="{segment:.2f} {circumference:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {center_x} {center_y})"/>'
        )
        percent = (value / total) * 100
        y = 116 + idx * 38
        legend.append(
            f'<rect x="390" y="{y - 12}" width="14" height="14" rx="3" fill="{color}"/>'
            f'<text x="416" y="{y}" fill="#e2e8f0" font-size="16" font-family="Arial, sans-serif">{label}</text>'
            f'<text x="840" y="{y}" text-anchor="end" fill="#cbd5e1" font-size="15" font-family="Arial, sans-serif">{fmt_brl(value)} • {fmt_pct(percent)}</text>'
        )
        offset += segment

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title}</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">{subtitle} • Atualizado em {generated_at}</text>

  <circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="none" stroke="#1e293b" stroke-width="34"/>
  {' '.join(circles)}
  <circle cx="{center_x}" cy="{center_y}" r="56" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
  <text x="{center_x}" y="206" text-anchor="middle" fill="#f8fafc" font-size="14" font-family="Arial, sans-serif">Total do mês</text>
  <text x="{center_x}" y="228" text-anchor="middle" fill="#f8fafc" font-size="20" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(total)}</text>

  {' '.join(legend)}

  <text x="36" y="386" fill="#94a3b8" font-size="14" font-family="Arial, sans-serif">{note}</text>
</svg>
'''


def build_salary_vs_fixed_svg(title: str, metrics: dict, generated_at: str) -> str:
    salary = float(metrics["salary"])
    fixed_total = float(metrics["fixed_total"])
    free_after_fixed = float(metrics["free_after_fixed"])
    commitment = (fixed_total / salary) * 100 if salary else 0.0
    fixed_width = scale_width(fixed_total, salary, max_width=620)
    free_width = max(0, 620 - fixed_width)

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — salário x gastos fixos</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Leitura estrutural do mês: quanto o salário já nasce comprometido • Atualizado em {generated_at}</text>

  <rect x="140" y="125" width="620" height="42" rx="12" fill="#1e293b"/>
  <rect x="140" y="125" width="{fixed_width}" height="42" rx="12" fill="#2563eb"/>
  <rect x="{140 + fixed_width}" y="125" width="{free_width}" height="42" rx="12" fill="#22c55e"/>

  <text x="140" y="112" fill="#e2e8f0" font-size="16" font-family="Arial, sans-serif">Salário mensal base</text>
  <text x="760" y="112" text-anchor="end" fill="#f8fafc" font-size="18" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(salary)}</text>

  <rect x="70" y="220" width="240" height="112" rx="16" fill="#111827" stroke="#1d4ed8"/>
  <text x="92" y="252" fill="#93c5fd" font-size="14" font-family="Arial, sans-serif">Fixos recorrentes</text>
  <text x="92" y="286" fill="#f8fafc" font-size="26" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(fixed_total)}</text>
  <text x="92" y="312" fill="#cbd5e1" font-size="14" font-family="Arial, sans-serif">{fmt_pct(commitment)} do salário já comprometidos</text>

  <rect x="330" y="220" width="240" height="112" rx="16" fill="#111827" stroke="#16a34a"/>
  <text x="352" y="252" fill="#86efac" font-size="14" font-family="Arial, sans-serif">Sobra após fixos</text>
  <text x="352" y="286" fill="#f8fafc" font-size="26" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(free_after_fixed)}</text>
  <text x="352" y="312" fill="#cbd5e1" font-size="14" font-family="Arial, sans-serif">Antes de mercado e compra única</text>

  <rect x="590" y="220" width="240" height="112" rx="16" fill="#111827" stroke="#f59e0b"/>
  <text x="612" y="252" fill="#fcd34d" font-size="14" font-family="Arial, sans-serif">Leitura prática</text>
  <text x="612" y="283" fill="#f8fafc" font-size="18" font-family="Arial, sans-serif" font-weight="700">Base ainda pressionada</text>
  <text x="612" y="306" fill="#cbd5e1" font-size="13" font-family="Arial, sans-serif">O aperto aparece quando entram</text>
  <text x="612" y="324" fill="#cbd5e1" font-size="13" font-family="Arial, sans-serif">mercado, farmácia e outros extras.</text>

  <text x="36" y="386" fill="#94a3b8" font-size="14" font-family="Arial, sans-serif">Dica: tente manter essa faixa fixa o mais perto possível de 50% do salário para ganhar folga no mês.</text>
</svg>
'''


def build_entries_svg(title: str, metrics: dict, generated_at: str) -> str:
    entries = metrics["entries"]
    received_total = float(metrics["received_total"])
    pending_total = float(metrics["pending_total"])
    cash_now = float(metrics["cash_now"])
    max_value = max((value for _, _, value in entries), default=1.0)
    rows = []

    for idx, (status, label, value) in enumerate(entries):
        y = 122 + idx * 42
        color = "#22c55e" if "✅" in status else "#f59e0b"
        width = scale_width(value, max_value, max_width=360)
        status_label = "Recebido" if "✅" in status else "Pendente"
        rows.append(
            f'<text x="46" y="{y}" fill="#e2e8f0" font-size="15" font-family="Arial, sans-serif">{label}</text>'
            f'<text x="220" y="{y}" fill="{color}" font-size="13" font-family="Arial, sans-serif">{status_label}</text>'
            f'<rect x="280" y="{y - 12}" width="380" height="16" rx="8" fill="#1e293b"/>'
            f'<rect x="280" y="{y - 12}" width="{width}" height="16" rx="8" fill="{color}"/>'
            f'<text x="828" y="{y}" text-anchor="end" fill="#f8fafc" font-size="15" font-family="Arial, sans-serif">{fmt_brl(value)}</text>'
        )

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — entradas do mês</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Comparativo entre o que já entrou e o que ainda está pendente • Atualizado em {generated_at}</text>

  {''.join(rows)}

  <rect x="46" y="324" width="240" height="64" rx="16" fill="#111827" stroke="#16a34a"/>
  <text x="68" y="352" fill="#86efac" font-size="14" font-family="Arial, sans-serif">Recebido</text>
  <text x="68" y="378" fill="#f8fafc" font-size="24" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(received_total)}</text>

  <rect x="330" y="324" width="240" height="64" rx="16" fill="#111827" stroke="#f59e0b"/>
  <text x="352" y="352" fill="#fcd34d" font-size="14" font-family="Arial, sans-serif">Pendente</text>
  <text x="352" y="378" fill="#f8fafc" font-size="24" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(pending_total)}</text>

  <rect x="614" y="324" width="240" height="64" rx="16" fill="#111827" stroke="#38bdf8"/>
  <text x="636" y="352" fill="#7dd3fc" font-size="14" font-family="Arial, sans-serif">Caixa em mãos</text>
  <text x="636" y="378" fill="#f8fafc" font-size="24" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(cash_now)}</text>
</svg>
'''


def build_commitments_svg(title: str, metrics: dict, generated_at: str) -> str:
    items = metrics["commitment_blocks"]
    items = [(label, value) for label, value in items if value > 0]
    max_value = max((value for _, value in items), default=1.0)
    total = sum(value for _, value in items)
    bars = []

    for idx, (label, value) in enumerate(items):
        y = 120 + idx * 48
        color = PALETTE[idx % len(PALETTE)]
        width = scale_width(value, max_value, max_width=430)
        bars.append(
            f'<text x="46" y="{y}" fill="#e2e8f0" font-size="15" font-family="Arial, sans-serif">{label}</text>'
            f'<rect x="220" y="{y - 12}" width="460" height="18" rx="9" fill="#1e293b"/>'
            f'<rect x="220" y="{y - 12}" width="{width}" height="18" rx="9" fill="{color}"/>'
            f'<text x="830" y="{y}" text-anchor="end" fill="#f8fafc" font-size="15" font-family="Arial, sans-serif">{fmt_brl(value)}</text>'
        )

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — compromissos do mês</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Peso dos blocos principais: fixos, cartões, empréstimos e contas pendentes • Atualizado em {generated_at}</text>

  {''.join(bars)}

  <rect x="46" y="334" width="808" height="48" rx="14" fill="#111827" stroke="#334155"/>
  <text x="68" y="363" fill="#cbd5e1" font-size="15" font-family="Arial, sans-serif">Pressão total mapeada entre mês corrente e adiamentos:</text>
  <text x="828" y="363" text-anchor="end" fill="#f8fafc" font-size="22" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(total)}</text>
</svg>
'''


def build_essentials_svg(title: str, metrics: dict, generated_at: str) -> str:
    salary = float(metrics["salary"])
    fixed_total = float(metrics["fixed_total"])
    one_time = float(metrics["one_time"])
    supermarket = float(metrics["supermarket"])
    combo = fixed_total + one_time + supermarket
    gap = salary - combo
    fixed_width = scale_width(fixed_total, salary, max_width=620)
    one_time_width = scale_width(one_time, salary, max_width=620)
    supermarket_width = scale_width(supermarket, salary, max_width=620)
    note = (
        f"Juntos, fixos + farmácia + supermercado passam do salário em {fmt_brl(abs(gap))}."
        if gap < 0
        else f"Depois desses 3 blocos, ainda restam {fmt_brl(gap)} do salário base."
    )

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — salário base x blocos principais</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Usando o salário como régua para fixos, farmácia/bebê/pet e supermercado • Atualizado em {generated_at}</text>

  <text x="140" y="112" fill="#e2e8f0" font-size="16" font-family="Arial, sans-serif">Salário base (referência completa)</text>
  <rect x="140" y="125" width="620" height="18" rx="9" fill="#22c55e"/>
  <text x="760" y="140" text-anchor="end" fill="#bbf7d0" font-size="16" font-family="Arial, sans-serif">{fmt_brl(salary)}</text>

  <text x="140" y="188" fill="#93c5fd" font-size="15" font-family="Arial, sans-serif">Contas fixas</text>
  <rect x="140" y="198" width="620" height="24" rx="8" fill="#1e293b"/>
  <rect x="140" y="198" width="{fixed_width}" height="24" rx="8" fill="#2563eb"/>
  <text x="760" y="216" text-anchor="end" fill="#bfdbfe" font-size="15" font-family="Arial, sans-serif">{fmt_brl(fixed_total)} • {fmt_pct((fixed_total / salary) * 100 if salary else 0)}</text>

  <text x="140" y="258" fill="#ddd6fe" font-size="15" font-family="Arial, sans-serif">Farmácia + bebê + pet</text>
  <rect x="140" y="268" width="620" height="24" rx="8" fill="#1e293b"/>
  <rect x="140" y="268" width="{one_time_width}" height="24" rx="8" fill="#8b5cf6"/>
  <text x="760" y="286" text-anchor="end" fill="#ddd6fe" font-size="15" font-family="Arial, sans-serif">{fmt_brl(one_time)} • {fmt_pct((one_time / salary) * 100 if salary else 0)}</text>

  <text x="140" y="328" fill="#fde68a" font-size="15" font-family="Arial, sans-serif">Supermercado</text>
  <rect x="140" y="338" width="620" height="24" rx="8" fill="#1e293b"/>
  <rect x="140" y="338" width="{supermarket_width}" height="24" rx="8" fill="#f59e0b"/>
  <text x="760" y="356" text-anchor="end" fill="#fde68a" font-size="15" font-family="Arial, sans-serif">{fmt_brl(supermarket)} • {fmt_pct((supermarket / salary) * 100 if salary else 0)}</text>

  <text x="36" y="392" fill="#94a3b8" font-size="14" font-family="Arial, sans-serif">{note}</text>
</svg>
'''


def build_result_svg(title: str, metrics: dict, generated_at: str) -> str:
    result_income = float(metrics["result_income"])
    result_commitments = float(metrics["result_commitments"])
    result_after_fixed = float(metrics["result_after_fixed"])
    result_essentials = float(metrics["result_essentials"])
    result_deficit = float(metrics["result_deficit"])

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — resultado final do mês</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Leitura em fluxo: entrada, consumo do mês e o rombo que vai para a próxima fatura • Atualizado em {generated_at}</text>

  <rect x="46" y="130" width="180" height="118" rx="18" fill="#111827" stroke="#22c55e"/>
  <text x="68" y="164" fill="#86efac" font-size="14" font-family="Arial, sans-serif">Entradas confirmadas</text>
  <text x="68" y="202" fill="#f8fafc" font-size="26" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(result_income)}</text>

  <text x="245" y="196" fill="#64748b" font-size="28">→</text>

  <rect x="276" y="130" width="180" height="118" rx="18" fill="#111827" stroke="#2563eb"/>
  <text x="298" y="164" fill="#93c5fd" font-size="14" font-family="Arial, sans-serif">Fixas + empréstimos</text>
  <text x="298" y="202" fill="#f8fafc" font-size="26" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(result_commitments)}</text>
  <text x="298" y="224" fill="#cbd5e1" font-size="13" font-family="Arial, sans-serif">Sobra: {fmt_brl(result_after_fixed)}</text>

  <text x="475" y="196" fill="#64748b" font-size="28">→</text>

  <rect x="506" y="130" width="180" height="118" rx="18" fill="#111827" stroke="#f59e0b"/>
  <text x="528" y="164" fill="#fcd34d" font-size="14" font-family="Arial, sans-serif">Essenciais no cartão</text>
  <text x="528" y="202" fill="#f8fafc" font-size="26" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(result_essentials)}</text>

  <text x="705" y="196" fill="#64748b" font-size="28">→</text>

  <rect x="676" y="270" width="178" height="92" rx="18" fill="#111827" stroke="#ef4444"/>
  <text x="698" y="302" fill="#fca5a5" font-size="14" font-family="Arial, sans-serif">Déficit projetado</text>
  <text x="698" y="334" fill="#f8fafc" font-size="24" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(result_deficit)}</text>

  <text x="36" y="386" fill="#94a3b8" font-size="14" font-family="Arial, sans-serif">Os essenciais ({fmt_brl(result_essentials)}) vão pro cartão e viram a fatura do mês seguinte.</text>
</svg>
'''


def build_calendar_svg(title: str, metrics: dict, generated_at: str) -> str:
    events = metrics["calendar_events"]
    max_value = max((value for _, value in events), default=1.0)
    bars = []

    for idx, (day, value) in enumerate(events):
        x = 70 + idx * 100
        height = int((value / max_value) * 170) if max_value else 0
        y = 290 - height
        bars.append(
            f'<rect x="{x}" y="{y}" width="46" height="{height}" rx="8" fill="#38bdf8"/>'
            f'<text x="{x + 23}" y="310" text-anchor="middle" fill="#e2e8f0" font-size="14" font-family="Arial, sans-serif">{day}</text>'
            f'<text x="{x + 23}" y="{max(110, y - 10)}" text-anchor="middle" fill="#cbd5e1" font-size="11" font-family="Arial, sans-serif">{fmt_brl(value)}</text>'
        )

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — calendário de pressão</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Dias em que o mês concentrou mais valor ou decisão financeira • Atualizado em {generated_at}</text>

  <line x1="56" y1="290" x2="850" y2="290" stroke="#334155" stroke-width="2"/>
  {''.join(bars)}

  <text x="36" y="386" fill="#94a3b8" font-size="14" font-family="Arial, sans-serif">Derivado automaticamente dos vencimentos do perfil.</text>
</svg>
'''


def build_alerts_svg(title: str, metrics: dict, generated_at: str) -> str:
    cash_now = float(metrics["cash_now"])
    urgent_total = float(metrics["urgent_total"])
    school_discount = float(metrics["school_discount"])
    deferred = float(metrics["deferred"])

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — alertas e prioridades</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Quatro lembretes visuais para decisão rápida • Atualizado em {generated_at}</text>

  <rect x="46" y="118" width="185" height="112" rx="18" fill="#111827" stroke="#38bdf8"/>
  <text x="68" y="150" fill="#7dd3fc" font-size="14">Caixa atual</text>
  <text x="68" y="186" fill="#f8fafc" font-size="26" font-weight="700">{fmt_brl(cash_now)}</text>

  <rect x="252" y="118" width="185" height="112" rx="18" fill="#111827" stroke="#ef4444"/>
  <text x="274" y="150" fill="#fca5a5" font-size="14">Urgente até dia 10</text>
  <text x="274" y="186" fill="#f8fafc" font-size="26" font-weight="700">{fmt_brl(urgent_total)}</text>

  <rect x="458" y="118" width="185" height="112" rx="18" fill="#111827" stroke="#22c55e"/>
  <text x="480" y="150" fill="#86efac" font-size="14">Economia da escola</text>
  <text x="480" y="186" fill="#f8fafc" font-size="26" font-weight="700">{fmt_brl(school_discount)}</text>

  <rect x="664" y="118" width="190" height="112" rx="18" fill="#111827" stroke="#f59e0b"/>
  <text x="686" y="150" fill="#fcd34d" font-size="14">Adiado p/ próx. mês</text>
  <text x="686" y="186" fill="#f8fafc" font-size="26" font-weight="700">{fmt_brl(deferred)}</text>

  <text x="46" y="290" fill="#e2e8f0" font-size="18" font-family="Arial, sans-serif" font-weight="700">Prioridade prática</text>
  <text x="46" y="322" fill="#cbd5e1" font-size="15" font-family="Arial, sans-serif">1. preservar caixa  2. evitar corte  3. ganhar desconto  4. impedir nova bola de neve</text>
  <text x="46" y="386" fill="#94a3b8" font-size="14" font-family="Arial, sans-serif">Esses alertas resumem o que merece atenção imediata no mês.</text>
</svg>
'''


def build_cashflow_svg(title: str, metrics: dict, generated_at: str) -> str:
    salary = float(metrics["salary"])
    on_hand = float(metrics["cash_now"])
    imob = float(metrics["imob"])
    income = salary + on_hand
    cash_out = (
        float(metrics["cards_month"]) + float(metrics["month_fixed"])
        + float(metrics["loans_month"]) + float(metrics["agua"]) + imob
    )
    result = income - cash_out
    base = max(income, cash_out) or 1.0
    res_color = "#22c55e" if result >= 0 else "#ef4444"
    res_label = "sobra" if result >= 0 else "falta"
    note = (
        f"Entra = salário {fmt_brl(salary)} + {fmt_brl(on_hand)} da caixinha (guardados pra imobiliária, que está no 'Sai'). "
        f"Fim do mês: {fmt_brl(result)} de {res_label}."
    )
    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — entra × sai (caixa do mês)</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Tudo que entra (salário + caixa) contra tudo que sai do bolso • Atualizado em {generated_at}</text>

  <text x="40" y="150" fill="#86efac" font-size="16" font-family="Arial, sans-serif">Entra (salário + caixinha)</text>
  <rect x="290" y="134" width="560" height="34" rx="10" fill="#1e293b"/>
  <rect x="290" y="134" width="{scale_width(income, base, max_width=560)}" height="34" rx="10" fill="#22c55e"/>
  <text x="838" y="158" text-anchor="end" fill="#f8fafc" font-size="16" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(income)}</text>

  <text x="40" y="218" fill="#fca5a5" font-size="16" font-family="Arial, sans-serif">Sai (caixa do mês)</text>
  <rect x="290" y="202" width="560" height="34" rx="10" fill="#1e293b"/>
  <rect x="290" y="202" width="{scale_width(cash_out, base, max_width=560)}" height="34" rx="10" fill="#ef4444"/>
  <text x="838" y="226" text-anchor="end" fill="#f8fafc" font-size="16" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(cash_out)}</text>

  <rect x="40" y="276" width="380" height="86" rx="16" fill="#111827" stroke="{res_color}"/>
  <text x="62" y="308" fill="#cbd5e1" font-size="14" font-family="Arial, sans-serif">Sobra no fim do mês</text>
  <text x="62" y="346" fill="{res_color}" font-size="30" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(result)}</text>

  <rect x="440" y="276" width="410" height="86" rx="16" fill="#111827" stroke="#38bdf8"/>
  <text x="462" y="304" fill="#7dd3fc" font-size="14" font-family="Arial, sans-serif">O que entra</text>
  <text x="462" y="332" fill="#e2e8f0" font-size="15" font-family="Arial, sans-serif">Salário {fmt_brl(salary)}</text>
  <text x="462" y="354" fill="#e2e8f0" font-size="15" font-family="Arial, sans-serif">+ Caixinha {fmt_brl(on_hand)}</text>

  <text x="36" y="392" fill="#94a3b8" font-size="14" font-family="Arial, sans-serif">{note}</text>
</svg>
'''


def build_where_svg(title: str, metrics: dict, generated_at: str) -> str:
    buckets = [
        ("Cartão (fatura)", float(metrics["cards_month"])),
        ("Moradia + contas", float(metrics["aluguel"]) + float(metrics["internet"]) + float(metrics["agua"])),
        ("Filhos (escola)", float(metrics["escola"]) + float(metrics["material"])),
        ("Empréstimos", float(metrics["loans_month"])),
        ("Imobiliária (1x)", float(metrics["imob"])),
        ("Saúde (jiu+academia)", float(metrics["academia"]) + float(metrics["jiu"])),
    ]
    buckets = [(l, v) for l, v in buckets if v > 0]
    buckets.sort(key=lambda b: b[1], reverse=True)
    total = sum(v for _, v in buckets) or 1.0
    max_value = max((v for _, v in buckets), default=1.0)
    bars = []
    for idx, (label, value) in enumerate(buckets):
        y = 126 + idx * 44
        color = PALETTE[idx % len(PALETTE)]
        width = scale_width(value, max_value, max_width=430)
        pct = (value / total) * 100
        bars.append(
            f'<text x="46" y="{y}" fill="#e2e8f0" font-size="15" font-family="Arial, sans-serif">{label}</text>'
            f'<rect x="250" y="{y - 13}" width="440" height="20" rx="10" fill="#1e293b"/>'
            f'<rect x="250" y="{y - 13}" width="{width}" height="20" rx="10" fill="{color}"/>'
            f'<text x="838" y="{y}" text-anchor="end" fill="#f8fafc" font-size="14" font-family="Arial, sans-serif">{fmt_brl(value)} • {fmt_pct(pct)}</text>'
        )
    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — pra onde vai o dinheiro</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Saída de caixa do mês, em blocos do dia a dia • Atualizado em {generated_at}</text>

  {''.join(bars)}

  <rect x="46" y="356" width="792" height="40" rx="12" fill="#111827" stroke="#334155"/>
  <text x="68" y="382" fill="#cbd5e1" font-size="15" font-family="Arial, sans-serif">Total que sai do bolso no mês:</text>
  <text x="818" y="382" text-anchor="end" fill="#f8fafc" font-size="20" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(total)}</text>
</svg>
'''


def build_card_cycle_svg(title: str, metrics: dict, generated_at: str) -> str:
    paid = float(metrics["cards_month"])
    essentials = float(metrics["essentials"])
    outros = float(metrics["outros"])
    mp_repr = float(metrics["mp_repr"])
    forming = essentials + outros + mp_repr
    base = max(paid, forming) or 1.0
    paid_w = scale_width(paid, base, max_width=540)
    form_w = scale_width(forming, base, max_width=540)
    delta = forming - paid
    arrow = "subindo" if delta > 0 else "caindo"
    note = (
        f"A próxima fatura está {arrow} {fmt_brl(abs(delta))} vs a deste mês. "
        f"Quebrar o ciclo = pagar essenciais no débito e segurar o cartão."
    )
    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — ciclo do cartão</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">A fatura que você paga agora vs a que está se formando para o mês que vem • Atualizado em {generated_at}</text>

  <text x="40" y="150" fill="#7dd3fc" font-size="16" font-family="Arial, sans-serif">Fatura paga este mês</text>
  <rect x="310" y="134" width="540" height="34" rx="10" fill="#1e293b"/>
  <rect x="310" y="134" width="{paid_w}" height="34" rx="10" fill="#38bdf8"/>
  <text x="846" y="158" text-anchor="end" fill="#f8fafc" font-size="16" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(paid)}</text>

  <text x="40" y="218" fill="#fca5a5" font-size="16" font-family="Arial, sans-serif">Fatura formando p/ o mês que vem</text>
  <rect x="310" y="202" width="540" height="34" rx="10" fill="#1e293b"/>
  <rect x="310" y="202" width="{form_w}" height="34" rx="10" fill="#ef4444"/>
  <text x="846" y="226" text-anchor="end" fill="#f8fafc" font-size="16" font-family="Arial, sans-serif" font-weight="700">{fmt_brl(forming)}</text>

  <rect x="40" y="272" width="810" height="62" rx="14" fill="#111827" stroke="#f59e0b"/>
  <text x="62" y="300" fill="#fcd34d" font-size="15" font-family="Arial, sans-serif">Composição da fatura que vem:</text>
  <text x="62" y="323" fill="#cbd5e1" font-size="14" font-family="Arial, sans-serif">Essenciais {fmt_brl(essentials)}   +   Outros gastos {fmt_brl(outros)}   +   MP represado {fmt_brl(mp_repr)}</text>

  <text x="36" y="392" fill="#94a3b8" font-size="14" font-family="Arial, sans-serif">{note}</text>
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera SVGs do painel financeiro a partir do estado.json.")
    parser.add_argument("year_month", help="YYYY-MM")
    parser.add_argument("--data-dir", required=True, type=Path, help="Caminho para Financeiro/")
    args = parser.parse_args()

    try:
        datetime.strptime(args.year_month, "%Y-%m")
    except ValueError:
        print("Formato inválido — use YYYY-MM", file=sys.stderr)
        return 1

    title = month_title(args.year_month)
    slug = month_slug(args.year_month)
    metrics = load_estado(args.year_month, args.data_dir)
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    graficos_dir = args.data_dir / "graficos"
    graficos_dir.mkdir(parents=True, exist_ok=True)

    files = {
        graficos_dir / f"{slug}-categorias-gastos.svg": build_category_donut_svg(
            f"{title} — saída de caixa",
            metrics["cash_categories"],
            generated_at,
            "O que realmente sai do bolso no mês (cartão = compras de meses anteriores)",
            f"Insight: a fatura do cartão ({fmt_brl(float(metrics['cards_month']))}) é o maior bloco — quebrar o ciclo elimina esse peso.",
        ),
        graficos_dir / f"{slug}-custo-vida.svg": build_category_donut_svg(
            f"{title} — custo de vida",
            metrics["living_categories"],
            generated_at,
            "Quanto custa viver no mês (essenciais contam; cartão é só o meio de pagar)",
            f"Insight: os essenciais ({fmt_brl(float(metrics['essentials']))}) pesam quase como as fixas — por isso o corte do mercado importa.",
        ),
        graficos_dir / f"{slug}-entra-vs-sai.svg": build_cashflow_svg(title, metrics, generated_at),
        graficos_dir / f"{slug}-pra-onde-vai.svg": build_where_svg(title, metrics, generated_at),
        graficos_dir / f"{slug}-ciclo-cartao.svg": build_card_cycle_svg(title, metrics, generated_at),
        graficos_dir / f"{slug}-salario-vs-fixos.svg": build_salary_vs_fixed_svg(title, metrics, generated_at),
        graficos_dir / f"{slug}-essenciais.svg": build_essentials_svg(title, metrics, generated_at),
        graficos_dir / f"{slug}-entradas.svg": build_entries_svg(title, metrics, generated_at),
        graficos_dir / f"{slug}-compromissos.svg": build_commitments_svg(title, metrics, generated_at),
        graficos_dir / f"{slug}-resultado-final.svg": build_result_svg(title, metrics, generated_at),
        graficos_dir / f"{slug}-calendario.svg": build_calendar_svg(title, metrics, generated_at),
        graficos_dir / f"{slug}-alertas.svg": build_alerts_svg(title, metrics, generated_at),
    }

    for path, content in files.items():
        write_svg(path, content)
        print(f"✓ {path.relative_to(args.data_dir.parent)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
