#!/usr/bin/env python3
"""Gera os SVGs do painel a partir do estado.json (v2).

Uso:
    python engine/render_graphs.py 2026-07 --data-dir "$SEVERINO_DATA_DIR"
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

PALETTE  = ["#38bdf8", "#22c55e", "#f59e0b", "#ef4444", "#a78bfa", "#f472b6", "#14b8a6"]
TIER_CLR = {"verde": "#22c55e", "amarelo": "#f59e0b", "laranja": "#f97316", "vermelho": "#ef4444"}


def month_slug(ym: str) -> str:
    y, m = ym.split("-")
    return f"{MONTHS_TITLE[int(m)].lower()}-{y}"


def month_title(ym: str) -> str:
    y, m = ym.split("-")
    return f"{MONTHS_TITLE[int(m)]} {y}"


def fmt_brl(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def fmt_pct(v: float) -> str:
    return f"{v:.1f}%".replace(".", ",")


def sw(value: float, max_value: float, max_width: int = 620) -> int:
    if max_value <= 0:
        return 0
    return max(8, int((value / max_value) * max_width))


def load_estado(ym: str, data_dir: Path) -> dict:
    slug = month_slug(ym)
    p = data_dir / "meses" / slug / "estado.json"
    if not p.exists():
        raise FileNotFoundError(f"estado.json não encontrado: {p}\n  → rode derive_estado.py primeiro")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ─── V1: Fluxo — Entra × Sai ─────────────────────────────────────────────────

def build_flow_svg(title: str, flow: dict, income: dict, gen: str) -> str:
    confirmed  = flow["income_confirmed"]
    pending    = flow["income_pending"]
    spending   = flow["spending_total"]
    balance    = flow["balance"]
    lbl        = flow["balance_label"]
    total_in   = confirmed + pending
    base       = max(total_in, spending) or 1.0
    res_color  = "#22c55e" if balance >= 0 else "#ef4444"

    sources_svg = ""
    for idx, s in enumerate(income["sources"]):
        y = 330 + idx * 22
        color = "#86efac" if s["status"] == "confirmed" else "#fcd34d"
        sources_svg += f'<text x="460" y="{y}" fill="{color}" font-size="13" font-family="Arial, sans-serif">{s["name"]}: {fmt_brl(s["amount"])}</text>'

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — entra × sai</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Entradas confirmadas vs comprometimento total do mês • {gen}</text>

  <text x="36" y="136" fill="#86efac" font-size="15" font-family="Arial, sans-serif">Entra (confirmado)</text>
  <rect x="220" y="120" width="620" height="32" rx="10" fill="#1e293b"/>
  <rect x="220" y="120" width="{sw(confirmed, base, 620)}" height="32" rx="10" fill="#22c55e"/>
  <text x="838" y="142" text-anchor="end" fill="#f8fafc" font-size="15" font-weight="700" font-family="Arial, sans-serif">{fmt_brl(confirmed)}</text>

  <text x="36" y="192" fill="#fcd34d" font-size="15" font-family="Arial, sans-serif">Entra (pendente)</text>
  <rect x="220" y="176" width="620" height="32" rx="10" fill="#1e293b"/>
  <rect x="220" y="176" width="{sw(pending, base, 620)}" height="32" rx="10" fill="#f59e0b" opacity="0.6"/>
  <text x="838" y="198" text-anchor="end" fill="#f8fafc" font-size="15" font-family="Arial, sans-serif">{fmt_brl(pending)}</text>

  <text x="36" y="248" fill="#fca5a5" font-size="15" font-family="Arial, sans-serif">Sai (comprometido)</text>
  <rect x="220" y="232" width="620" height="32" rx="10" fill="#1e293b"/>
  <rect x="220" y="232" width="{sw(spending, base, 620)}" height="32" rx="10" fill="#ef4444"/>
  <text x="838" y="254" text-anchor="end" fill="#f8fafc" font-size="15" font-weight="700" font-family="Arial, sans-serif">{fmt_brl(spending)}</text>

  <rect x="36" y="290" width="190" height="92" rx="16" fill="#111827" stroke="{res_color}"/>
  <text x="58" y="320" fill="#cbd5e1" font-size="13" font-family="Arial, sans-serif">{lbl.capitalize()}</text>
  <text x="58" y="358" fill="{res_color}" font-size="28" font-weight="700" font-family="Arial, sans-serif">{fmt_brl(abs(balance))}</text>

  {sources_svg}
</svg>
'''


# ─── V2: Breakdown 50/30/20 ──────────────────────────────────────────────────

def build_breakdown_svg(title: str, breakdown: dict, gen: str) -> str:
    groups = breakdown["by_group"]
    total  = sum(g["total"] for g in groups) or 1.0
    radius, cx, cy = 88, 180, 225
    circ   = 2 * math.pi * radius
    offset = 0.0
    circles, legend = [], []

    colors = {"needs": "#38bdf8", "wants": "#a78bfa", "savings": "#22c55e"}
    for idx, g in enumerate(groups):
        color   = colors.get(g["group"], PALETTE[idx])
        segment = circ * (g["total"] / total)
        circles.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{color}" stroke-width="34" '
            f'stroke-linecap="butt" stroke-dasharray="{segment:.2f} {circ:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        y = 130 + idx * 58
        tgt = g["target_pct"]
        diff = g["pct"] - tgt
        diff_str = f"+{diff:.1f}pp acima" if diff > 0 else f"{diff:.1f}pp abaixo"
        diff_clr = "#ef4444" if (g["group"] != "savings" and diff > 5) or (g["group"] == "savings" and diff < -5) else "#22c55e"
        legend.append(
            f'<rect x="390" y="{y-12}" width="14" height="14" rx="3" fill="{color}"/>'
            f'<text x="416" y="{y}" fill="#e2e8f0" font-size="16" font-family="Arial, sans-serif">{g["label"]}</text>'
            f'<text x="840" y="{y}" text-anchor="end" fill="#cbd5e1" font-size="14" font-family="Arial, sans-serif">{fmt_brl(g["total"])} · {fmt_pct(g["pct"])} <tspan fill="{diff_clr}">({diff_str} da meta {tgt}%)</tspan></text>'
        )
        offset += segment

    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — 50/30/20</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Distribuição por grupo · meta: necessidades 50% · desejos 30% · poupança 20% • {gen}</text>

  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#1e293b" stroke-width="34"/>
  {' '.join(circles)}
  <circle cx="{cx}" cy="{cy}" r="56" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
  <text x="{cx}" y="{cy-8}" text-anchor="middle" fill="#94a3b8" font-size="13" font-family="Arial, sans-serif">Total</text>
  <text x="{cx}" y="{cy+16}" text-anchor="middle" fill="#f8fafc" font-size="19" font-weight="700" font-family="Arial, sans-serif">{fmt_brl(total)}</text>

  {' '.join(legend)}
  <text x="36" y="394" fill="#94a3b8" font-size="13" font-family="Arial, sans-serif">Regra 50/30/20: Elizabeth Warren, "All Your Worth" (2005).</text>
</svg>
'''


# ─── V3: Categorias (barras horizontais) ──────────────────────────────────────

def build_categories_svg(title: str, categories: dict, income: float, gen: str) -> str:
    items = [i for i in categories["items"] if i["total"] > 0]
    items.sort(key=lambda x: -x["total"])
    max_v  = max((i["total"] for i in items), default=1.0)
    total  = sum(i["total"] for i in items)
    bars   = []
    for idx, cat in enumerate(items[:8]):
        y     = 110 + idx * 36
        color = "#38bdf8" if cat["essential"] else "#a78bfa"
        pct   = cat["total"] / income * 100 if income else 0
        bars.append(
            f'<text x="36" y="{y}" fill="#e2e8f0" font-size="14" font-family="Arial, sans-serif">{cat["name"]}</text>'
            f'<rect x="200" y="{y-13}" width="490" height="18" rx="9" fill="#1e293b"/>'
            f'<rect x="200" y="{y-13}" width="{sw(cat["total"], max_v, 490)}" height="18" rx="9" fill="{color}"/>'
            f'<text x="838" y="{y}" text-anchor="end" fill="#f8fafc" font-size="13" font-family="Arial, sans-serif">{fmt_brl(cat["total"])} · {fmt_pct(pct)}</text>'
        )
    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — categorias</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Peso de cada categoria sobre a renda · <tspan fill="#38bdf8">■ necessidade</tspan>  <tspan fill="#a78bfa">■ desejo</tspan> • {gen}</text>
  {''.join(bars)}
  <rect x="36" y="372" width="828" height="34" rx="10" fill="#111827" stroke="#334155"/>
  <text x="58" y="395" fill="#cbd5e1" font-size="14" font-family="Arial, sans-serif">Total categorias:</text>
  <text x="838" y="395" text-anchor="end" fill="#f8fafc" font-size="16" font-weight="700" font-family="Arial, sans-serif">{fmt_brl(total)}</text>
</svg>
'''


# ─── V4: Calendário ──────────────────────────────────────────────────────────

def build_calendar_svg(title: str, calendar: dict, gen: str) -> str:
    items   = calendar["items"]
    max_v   = max((i["amount"] for i in items), default=1.0)
    bars    = []
    for idx, item in enumerate(items):
        x      = 50 + idx * 76
        h      = max(8, int((item["amount"] / max_v) * 160))
        y      = 285 - h
        color  = "#22c55e" if item["paid"] else "#38bdf8"
        bars.append(
            f'<rect x="{x}" y="{y}" width="52" height="{h}" rx="7" fill="{color}" opacity="{"1" if item["paid"] else "0.85"}"/>'
            f'<text x="{x+26}" y="306" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="Arial, sans-serif">{item["due_day"]}</text>'
            f'<text x="{x+26}" y="{max(102, y-6)}" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="Arial, sans-serif">{fmt_brl(item["amount"])}</text>'
        )
    total_paid   = calendar["total_paid"]
    total_unpaid = calendar["total_unpaid"]
    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — calendário</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Vencimentos do mês · <tspan fill="#22c55e">■ pago</tspan>  <tspan fill="#38bdf8">■ pendente</tspan> • {gen}</text>
  <line x1="40" y1="286" x2="860" y2="286" stroke="#334155" stroke-width="1"/>
  {''.join(bars)}
  <rect x="36" y="334" width="380" height="56" rx="14" fill="#111827" stroke="#22c55e"/>
  <text x="58" y="360" fill="#86efac" font-size="13" font-family="Arial, sans-serif">Pago</text>
  <text x="58" y="382" fill="#f8fafc" font-size="22" font-weight="700" font-family="Arial, sans-serif">{fmt_brl(total_paid)}</text>
  <rect x="484" y="334" width="380" height="56" rx="14" fill="#111827" stroke="#ef4444"/>
  <text x="506" y="360" fill="#fca5a5" font-size="13" font-family="Arial, sans-serif">A pagar</text>
  <text x="506" y="382" fill="#f8fafc" font-size="22" font-weight="700" font-family="Arial, sans-serif">{fmt_brl(total_unpaid)}</text>
</svg>
'''


# ─── V5: Radar de saúde (barras lineares) ────────────────────────────────────

def build_health_svg(title: str, radar: dict, gen: str) -> str:
    indicators = radar["indicators"]
    score      = radar["score"]
    tier       = radar["tier"]
    tier_color = TIER_CLR.get(tier, "#94a3b8")
    bars = []
    for idx, ind in enumerate(indicators):
        y     = 110 + idx * 44
        color = TIER_CLR.get(ind["tier"], "#94a3b8")
        pct   = ind["score"] / ind["max"] if ind["max"] else 0
        bars.append(
            f'<text x="36" y="{y}" fill="#e2e8f0" font-size="14" font-family="Arial, sans-serif">{ind["label"]}</text>'
            f'<rect x="200" y="{y-13}" width="490" height="18" rx="9" fill="#1e293b"/>'
            f'<rect x="200" y="{y-13}" width="{int(pct*490)}" height="18" rx="9" fill="{color}"/>'
            f'<text x="700" y="{y}" fill="{color}" font-size="13" font-family="Arial, sans-serif">{ind["tier"]}</text>'
            f'<text x="838" y="{y}" text-anchor="end" fill="#94a3b8" font-size="12" font-family="Arial, sans-serif">{ind["score"]}/{ind["max"]}pts</text>'
        )
    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — saúde financeira</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">6 indicadores citáveis · score 0–100 · thresholds baseados em CFP Board / BACEN / CFPB • {gen}</text>
  {''.join(bars)}
  <rect x="36" y="378" width="220" height="32" rx="10" fill="#111827" stroke="{tier_color}"/>
  <text x="58" y="399" fill="{tier_color}" font-size="16" font-weight="700" font-family="Arial, sans-serif">Score: {score}/100 — {tier}</text>
</svg>
'''


# ─── V6: Ciclo do cartão (condicional) ───────────────────────────────────────

def build_card_cycle_svg(title: str, card_cycle: dict, gen: str) -> str:
    items = card_cycle["items"]
    max_v = max((i["used"] for i in items), default=1.0)
    bars  = []
    for idx, card in enumerate(items):
        y      = 120 + idx * 72
        pct    = card["pct_used"]
        color  = "#22c55e" if pct < 30 else ("#f59e0b" if pct < 70 else "#ef4444")
        bars.append(
            f'<text x="36" y="{y}" fill="#e2e8f0" font-size="15" font-family="Arial, sans-serif">{card["name"]}</text>'
            f'<text x="36" y="{y+18}" fill="#64748b" font-size="12" font-family="Arial, sans-serif">Limite {fmt_brl(card["limit"])} · vence dia {card["due_day"]}</text>'
            f'<rect x="36" y="{y+24}" width="620" height="20" rx="10" fill="#1e293b"/>'
            f'<rect x="36" y="{y+24}" width="{sw(card["used"], max_v, 620)}" height="20" rx="10" fill="{color}"/>'
            f'<text x="838" y="{y+38}" text-anchor="end" fill="#f8fafc" font-size="14" font-family="Arial, sans-serif">{fmt_brl(card["used"])} · {fmt_pct(pct)}</text>'
        )
    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — cartões</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Utilização do limite · <tspan fill="#22c55e">■ &lt;30%</tspan>  <tspan fill="#f59e0b">■ 30–70%</tspan>  <tspan fill="#ef4444">■ &gt;70%</tspan> · recomendado: manter abaixo de 30% • {gen}</text>
  {''.join(bars)}
  <text x="36" y="390" fill="#94a3b8" font-size="13" font-family="Arial, sans-serif">Utilização acima de 30% do limite pode afetar score de crédito.</text>
</svg>
'''


# ─── V7: Timeline de dívidas (condicional) ───────────────────────────────────

def build_debt_timeline_svg(title: str, debt_timeline: dict, gen: str) -> str:
    items   = debt_timeline["items"]
    freed   = debt_timeline["total_freed_monthly"]
    bars    = []
    max_out = max((d["outstanding"] for d in items), default=1.0)
    for idx, d in enumerate(items):
        y      = 120 + idx * 68
        color  = PALETTE[idx % len(PALETTE)]
        rate_y = f"{d['rate_monthly']*100:.2f}%/mês"
        payoff_str = f" · quitação {d['payoff_month']}" if d.get("payoff_month") else ""
        bars.append(
            f'<text x="36" y="{y}" fill="#e2e8f0" font-size="14" font-family="Arial, sans-serif">{d["name"]}</text>'
            f'<text x="36" y="{y+17}" fill="#64748b" font-size="12" font-family="Arial, sans-serif">{rate_y} · parcela {fmt_brl(d["installment"])} · restam {d["remaining_count"]}x{payoff_str}</text>'
            f'<rect x="36" y="{y+22}" width="620" height="18" rx="9" fill="#1e293b"/>'
            f'<rect x="36" y="{y+22}" width="{sw(d["outstanding"], max_out, 620)}" height="18" rx="9" fill="{color}"/>'
            f'<text x="838" y="{y+35}" text-anchor="end" fill="#f8fafc" font-size="13" font-family="Arial, sans-serif">{fmt_brl(d["outstanding"])}</text>'
        )
    return f'''
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#0f172a"/>
  <text x="36" y="46" fill="#f8fafc" font-size="28" font-family="Arial, sans-serif" font-weight="700">{title} — dívidas (avalanche)</text>
  <text x="36" y="74" fill="#94a3b8" font-size="16" font-family="Arial, sans-serif">Ordem de ataque por taxa · ao quitar cada uma, redirecionar parcela para a próxima • {gen}</text>
  {''.join(bars)}
  <rect x="36" y="372" width="828" height="36" rx="12" fill="#111827" stroke="#22c55e"/>
  <text x="58" y="396" fill="#86efac" font-size="14" font-family="Arial, sans-serif">Total liberado ao quitar tudo:</text>
  <text x="838" y="396" text-anchor="end" fill="#f8fafc" font-size="18" font-weight="700" font-family="Arial, sans-serif">{fmt_brl(freed)}/mês</text>
</svg>
'''


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Gera SVGs do painel a partir do estado.json v2.")
    parser.add_argument("year_month", help="YYYY-MM")
    parser.add_argument("--data-dir", required=True, type=Path, help="Caminho para Financeiro/")
    args = parser.parse_args()

    try:
        datetime.strptime(args.year_month, "%Y-%m")
    except ValueError:
        print("Formato inválido — use YYYY-MM", file=sys.stderr)
        return 1

    e    = load_estado(args.year_month, args.data_dir)
    ch   = e["charts"]
    slug = month_slug(args.year_month)
    gen  = datetime.now().strftime("%d/%m/%Y %H:%M")
    t    = month_title(args.year_month)

    out = args.data_dir / "graficos"
    out.mkdir(parents=True, exist_ok=True)

    files: dict[Path, str] = {
        out / f"{slug}-entra-vs-sai.svg":   build_flow_svg(t, ch["flow"], e["income"], gen),
        out / f"{slug}-breakdown.svg":       build_breakdown_svg(t, ch["breakdown"], gen),
        out / f"{slug}-categorias.svg":      build_categories_svg(t, ch["categories"], e["income"]["confirmed"], gen),
        out / f"{slug}-calendario.svg":      build_calendar_svg(t, ch["calendar"], gen),
        out / f"{slug}-saude.svg":           build_health_svg(t, ch["health_radar"], gen),
    }
    if "card_cycle" in ch:
        files[out / f"{slug}-cartoes.svg"] = build_card_cycle_svg(t, ch["card_cycle"], gen)
    if "debt_timeline" in ch:
        files[out / f"{slug}-dividas.svg"] = build_debt_timeline_svg(t, ch["debt_timeline"], gen)

    for path, content in files.items():
        path.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"✓ {path.relative_to(args.data_dir.parent)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
