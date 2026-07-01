#!/usr/bin/env python3
"""Gera RESUMO-YYYY-MM.html auto-contido a partir de estado.json + SVGs.

Uso:
    python engine/generate_html.py 2026-07 --data-dir "$SEVERINO_DATA_DIR"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

MONTHS_TITLE = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

TIER_COLOR = {
    "verde":    "#22c55e",
    "amarelo":  "#f59e0b",
    "laranja":  "#f97316",
    "vermelho": "#ef4444",
}

INDICATOR_LABEL = {
    "commitment_pct":    "Comprometimento de renda",
    "savings_rate":      "Taxa de poupança",
    "reserve_months":    "Cobertura de reserva",
    "dti":               "Dívidas / Renda (DTI)",
    "housing_pct":       "Peso de moradia",
    "highest_debt_rate": "Maior taxa de juros",
}

FLAG_LABEL = {
    "predatory_debt_rate":  "Taxa predatória (>6%/mês) — atacar imediatamente",
    "high_debt_rate":       "Taxa alta de juros (>3%/mês)",
    "commitment_critical":  "Mais de 95% da renda comprometida",
    "commitment_high":      "80–95% da renda comprometida",
    "no_savings":           "Sem poupança este mês",
    "no_reserve":           "Sem reserva de emergência",
    "reserve_partial":      "Reserva abaixo da meta",
    "housing_over":         "Moradia acima de 35% da renda",
    "dti_high":             "Parcelas de dívida acima de 30% da renda",
    "income_base_expected": "Salário ainda pendente — diagnóstico usa renda esperada",
}

FLAG_TIER = {
    "predatory_debt_rate":  "vermelho",
    "commitment_critical":  "vermelho",
    "no_savings":           "vermelho",
    "no_reserve":           "vermelho",
    "high_debt_rate":       "laranja",
    "commitment_high":      "laranja",
    "dti_high":             "laranja",
    "reserve_partial":      "amarelo",
    "housing_over":         "amarelo",
    "income_base_expected": "amarelo",
}

FOCUS_LABEL = {
    "debt_payoff":    "Quitar dívidas",
    "emergency_fund": "Construir reserva",
    "budgeting":      "Equilibrar orçamento",
    "investing":      "Investir",
    "custom":         "Personalizado",
}

FRAMEWORK_LABEL = {
    "50_30_20":   "50/30/20",
    "zero_based": "Orçamento base zero",
    "envelope":   "Método envelope",
    "free":       "Monitoramento leve",
}

FLAG_ICON = {
    "vermelho": "🚨",
    "laranja":  "⚠️",
    "amarelo":  "ℹ️",
}

SVG_FILES = [
    ("entra-vs-sai",  "Entra × Sai"),
    ("breakdown",     "Distribuição 50/30/20"),
    ("categorias",    "Categorias de gasto"),
    ("saude",         "Indicadores de saúde"),
    ("calendario",    "Calendário de vencimentos"),
    ("cartoes",       "Cartões de crédito"),
    ("dividas",       "Dívidas — Avalanche"),
]

CSS = """
:root{--bg:#0f172a;--s:#1e293b;--s2:#111827;--b:#334155;--t:#f8fafc;--t2:#e2e8f0;--mu:#64748b;--mu2:#94a3b8;--ve:#22c55e;--am:#f59e0b;--la:#f97316;--vm:#ef4444;--bl:#38bdf8;--pu:#a78bfa}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--t);font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',Roboto,sans-serif;font-size:15px;line-height:1.6}
.wrap{max-width:900px;margin:0 auto;padding:20px 16px 48px}
/* header */
.hdr{margin-bottom:24px}.hdr-row{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:6px}.hdr h1{font-size:30px;font-weight:800;letter-spacing:-.5px}.hdr .sub{font-size:13px;color:var(--mu2)}
.score-badge{display:inline-flex;align-items:center;gap:8px;padding:8px 16px;border-radius:24px;font-weight:700;font-size:17px;border:2px solid;white-space:nowrap}
/* cards */
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:28px}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
@media(max-width:560px){.grid3,.grid2{grid-template-columns:1fr}.hdr h1{font-size:24px}}
.card{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:16px 18px}
.card .lbl{font-size:11px;color:var(--mu2);text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px}
.card .val{font-size:22px;font-weight:800;margin-bottom:3px;line-height:1.2}
.card .sub{font-size:12px;color:var(--mu)}
/* section */
.sec{margin-bottom:28px}
.sec h2{font-size:11px;font-weight:700;color:var(--mu2);text-transform:uppercase;letter-spacing:1px;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid var(--b)}
/* kpi */
.kpi-list{display:flex;flex-direction:column;gap:14px}
.kpi-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:5px}
.kpi-name{font-size:14px;font-weight:500}
.kpi-right{display:flex;align-items:center;gap:8px}
.kpi-val{font-size:13px;color:var(--mu2)}
.tier-tag{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;padding:2px 8px;border-radius:8px}
.kpi-bg{background:var(--s2);border-radius:6px;height:7px}
.kpi-fill{height:7px;border-radius:6px}
/* reco */
.reco-focus{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:18px;margin-bottom:14px}
.reco-focus .fl{font-size:11px;color:var(--mu2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.reco-focus .fv{font-size:20px;font-weight:700;margin-bottom:6px}
.reco-focus .fr{font-size:13px;color:var(--mu2);line-height:1.5}
.reco-item{background:var(--s);border:1px solid var(--b);border-radius:12px;padding:14px 16px}
.reco-item .rl{font-size:11px;color:var(--mu2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.reco-item .rv{font-size:16px;font-weight:700;margin-bottom:4px}
.reco-item .rr{font-size:12px;color:var(--mu);line-height:1.5}
/* avalanche */
.av-list{display:flex;flex-direction:column;gap:10px;margin-top:12px}
.av-item{background:var(--s2);border:1px solid var(--b);border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:12px}
.av-rank{width:28px;height:28px;background:var(--b);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;color:var(--mu2);flex-shrink:0}
.av-info{flex:1}
.av-name{font-size:14px;font-weight:600;margin-bottom:2px}
.av-meta{font-size:12px;color:var(--mu)}
.av-payoff{font-size:12px;font-weight:600;color:var(--ve);white-space:nowrap}
/* alerts */
.alerts{display:flex;flex-direction:column;gap:8px;margin-top:14px}
.alert{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;border-radius:10px;font-size:14px}
.alert.vermelho{background:rgba(239,68,68,.08);border-left:3px solid var(--vm)}
.alert.laranja{background:rgba(249,115,22,.08);border-left:3px solid var(--la)}
.alert.amarelo{background:rgba(245,158,11,.08);border-left:3px solid var(--am)}
.alert .ai{font-size:16px;flex-shrink:0;margin-top:1px}
.alert .at{color:var(--t2);line-height:1.4}
/* calendar */
.cal-totals{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px}
@media(max-width:560px){.cal-totals{grid-template-columns:repeat(2,1fr)}}
.cal-t-card{background:var(--s2);border-radius:10px;padding:10px 14px}
.cal-t-lbl{font-size:10px;color:var(--mu2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px}
.cal-t-val{font-size:17px;font-weight:700}
.cal-list{display:flex;flex-direction:column}
.cal-item{display:flex;align-items:center;gap:14px;padding:10px 4px;border-bottom:1px solid var(--b)}
.cal-item:last-child{border-bottom:none}
.cal-item.income{background:rgba(34,197,94,.04)}
.cal-day{width:36px;height:36px;background:var(--s2);border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;color:var(--t2);flex-shrink:0}
.cal-item.income .cal-day{background:rgba(34,197,94,.15);color:var(--ve)}
.cal-arrow{font-size:12px;font-weight:700;flex-shrink:0;width:18px;text-align:center}
.cal-name{flex:1;font-size:14px}
.cal-amt{font-weight:700;font-size:14px;white-space:nowrap;margin-right:4px}
.cal-amt.income-amt{color:var(--ve)}
.cal-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.cal-dot.paid{background:var(--ve)}
.cal-dot.unpaid{background:var(--b);border:2px solid var(--mu)}
/* consolidated */
.flow-table{background:var(--s);border:1px solid var(--b);border-radius:14px;overflow:hidden}
.flow-row{display:flex;justify-content:space-between;align-items:center;padding:13px 18px;border-bottom:1px solid var(--b)}
.flow-row:last-child{border-bottom:none}
.flow-row.total{background:var(--s2)}
.flow-label{font-size:14px;color:var(--t2)}
.flow-val{font-size:15px;font-weight:700}
.flow-row.total .flow-label{font-weight:600;font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:var(--mu2)}
.flow-row.total .flow-val{font-size:18px}
/* analysis paragraphs */
.analysis-block{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:20px 22px;margin-bottom:14px}
.analysis-block .atitle{font-size:11px;font-weight:700;color:var(--mu2);text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px}
.analysis-block .abody{font-size:15px;line-height:1.75;color:var(--t2)}
/* svgs */
.svg-item{margin-bottom:20px}
.svg-title{font-size:12px;font-weight:600;color:var(--mu2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.svg-box{border-radius:12px;overflow:hidden;border:1px solid var(--b)}
.svg-box svg{width:100%;height:auto;display:block}
/* footer */
.footer{text-align:center;color:var(--mu);font-size:12px;padding:20px 0 0;margin-top:32px;border-top:1px solid var(--b)}
"""


# ─── helpers ──────────────────────────────────────────────────────────────────

def month_slug(ym: str) -> str:
    y, m = ym.split("-")
    return f"{MONTHS_TITLE[int(m)].lower()}-{y}"


def month_title(ym: str) -> str:
    y, m = ym.split("-")
    return f"{MONTHS_TITLE[int(m)]} de {y}"


def brl(v: float) -> str:
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$&nbsp;{s}"


def pct(v: float) -> str:
    return f"{v * 100:.1f}%".replace(".", ",")


def tc(tier: str) -> str:
    return TIER_COLOR.get(tier, "#94a3b8")


def load_svg(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_text(encoding="utf-8").strip()
    if "<?xml" in raw:
        raw = raw[raw.index("<svg"):]
    return raw


# ─── sections ─────────────────────────────────────────────────────────────────

def s_header(estado: dict, ym: str) -> str:
    diag   = estado["diagnosis"]
    score  = diag["score"]
    tier   = diag["tier"]
    color  = tc(tier)
    income = estado["income"]
    gen    = datetime.now().strftime("%d/%m/%Y %H:%M")

    using_expected = "income_base_expected" in diag.get("flags", [])
    base_note = " (renda esperada)" if using_expected else ""

    return f"""
<div class="hdr">
  <div class="hdr-row">
    <div>
      <h1>Severino</h1>
      <div class="sub">{month_title(ym)}{base_note} · gerado em {gen}</div>
    </div>
    <span class="score-badge" style="color:{color};border-color:{color}">{score}/100 — {tier.capitalize()}</span>
  </div>
</div>"""


def s_summary(estado: dict) -> str:
    income   = estado["income"]
    spending = estado["spending"]
    balance  = income["confirmed"] - spending["total_committed"]
    b_label  = "Sobra" if balance >= 0 else "Déficit"
    b_color  = "#22c55e" if balance >= 0 else "#ef4444"
    c_color  = "#22c55e" if income["confirmed"] > 0 else "#f59e0b"

    return f"""
<div class="grid3">
  <div class="card">
    <div class="lbl">Renda confirmada</div>
    <div class="val" style="color:{c_color}">{brl(income["confirmed"])}</div>
    <div class="sub">+{brl(income["pending"])} pendente</div>
  </div>
  <div class="card">
    <div class="lbl">Comprometido</div>
    <div class="val">{brl(spending["total_committed"])}</div>
    <div class="sub">pago: {brl(spending["paid"])}</div>
  </div>
  <div class="card">
    <div class="lbl">{b_label}</div>
    <div class="val" style="color:{b_color}">{brl(abs(balance))}</div>
    <div class="sub">confirmado − comprometido</div>
  </div>
</div>"""


def s_health(diagnosis: dict) -> str:
    ind = diagnosis["indicators"]
    rows = []
    for key, label in INDICATOR_LABEL.items():
        if key not in ind:
            continue
        i = ind[key]
        fill = int(i["points"] / i["max"] * 100) if i["max"] else 0
        color = tc(i["tier"])

        if key == "reserve_months":
            val_str = f'{i["value"]:.1f} meses'.replace(".", ",")
        elif key == "highest_debt_rate":
            val_str = (pct(i["value"]) + "/mês") if i["value"] > 0 else "sem dívidas"
        else:
            val_str = pct(i["value"])

        rows.append(f"""
<div>
  <div class="kpi-top">
    <span class="kpi-name">{label}</span>
    <div class="kpi-right">
      <span class="kpi-val">{val_str}</span>
      <span class="tier-tag" style="background:{color}20;color:{color}">{i["tier"]}</span>
    </div>
  </div>
  <div class="kpi-bg"><div class="kpi-fill" style="width:{fill}%;background:{color}"></div></div>
</div>""")

    return f"""
<div class="sec">
  <h2>Saúde financeira</h2>
  <div class="kpi-list">{"".join(rows)}</div>
</div>"""


def s_recommendation(estado: dict) -> str:
    reco  = estado.get("recommendation", {})
    diag  = estado["diagnosis"]
    flags = diag.get("flags", [])

    if not reco:
        return ""

    focus         = FOCUS_LABEL.get(reco.get("primary_focus", ""), reco.get("primary_focus", ""))
    focus_reason  = reco.get("focus_reason", "")
    framework     = FRAMEWORK_LABEL.get(reco.get("budget_framework", ""), "")
    fw_reason     = reco.get("framework_reason", "")
    reserve_pct   = reco.get("reserve_pct", 0.10)
    pay           = reco.get("pay_yourself_first", 0)
    debt_method   = reco.get("debt_method", "none")
    method_reason = reco.get("method_reason", "")

    # Avalanche order
    av_html = ""
    if debt_method != "none" and reco.get("avalanche_order"):
        av_items = []
        for idx, d in enumerate(reco["avalanche_order"], 1):
            payoff = d.get("payoff_month", "")
            payoff_html = f'<div class="av-payoff">quitação {payoff}</div>' if payoff else ""
            rate_str = pct(d["rate"]) + "/mês"
            av_items.append(f"""
<div class="av-item">
  <div class="av-rank">{idx}º</div>
  <div class="av-info">
    <div class="av-name">{d["name"]}</div>
    <div class="av-meta">{rate_str} · parcela {brl(d["installment"])} · saldo {brl(d["outstanding"])}</div>
  </div>
  {payoff_html}
</div>""")
        method_label = "Avalanche" if debt_method == "avalanche" else "Snowball"
        av_html = f"""
<div class="reco-item" style="margin-bottom:14px">
  <div class="rl">Método de quitação: {method_label}</div>
  <div class="rr">{method_reason}</div>
  <div class="av-list">{"".join(av_items)}</div>
</div>"""

    # Alerts
    alert_items = []
    for flag in flags:
        ftier = FLAG_TIER.get(flag, "amarelo")
        flabel = FLAG_LABEL.get(flag, flag)
        icon = FLAG_ICON.get(ftier, "ℹ️")
        alert_items.append(f"""
<div class="alert {ftier}">
  <span class="ai">{icon}</span>
  <span class="at">{flabel}</span>
</div>""")
    alerts_html = f'<div class="alerts">{"".join(alert_items)}</div>' if alert_items else ""

    return f"""
<div class="sec">
  <h2>Recomendação</h2>
  <div class="reco-focus">
    <div class="fl">Foco principal</div>
    <div class="fv">{focus}</div>
    <div class="fr">{focus_reason}</div>
  </div>
  <div class="grid2" style="margin-bottom:14px">
    <div class="reco-item">
      <div class="rl">Framework de orçamento</div>
      <div class="rv">{framework}</div>
      <div class="rr">{fw_reason}</div>
    </div>
    <div class="reco-item">
      <div class="rl">Pay-yourself-first</div>
      <div class="rv">{brl(pay)}/mês</div>
      <div class="rr">{int(reserve_pct * 100)}% da renda reservada antes de qualquer gasto</div>
    </div>
  </div>
  {av_html}
  {alerts_html}
</div>"""


def s_calendar(calendar: dict) -> str:
    items = calendar.get("items", [])
    if not items:
        return ""

    total_paid     = calendar.get("total_paid", 0)
    total_unpaid   = calendar.get("total_unpaid", 0)
    total_in       = calendar.get("total_in", 0)
    total_received = calendar.get("total_received", 0)

    rows = []
    for item in items:
        is_income = item.get("flow") == "in"
        paid_cls  = "paid" if item["paid"] else "unpaid"
        item_cls  = "cal-item income" if is_income else "cal-item"
        arrow     = "↑" if is_income else "↓"
        arrow_col = "color:var(--ve)" if is_income else "color:var(--mu)"
        amt_cls   = "cal-amt income-amt" if is_income else "cal-amt"
        prefix    = "+" if is_income else "−"
        rows.append(f"""
<div class="{item_cls}">
  <div class="cal-day">{item["due_day"]}</div>
  <span class="cal-arrow" style="{arrow_col}">{arrow}</span>
  <div class="cal-name">{item["name"]}</div>
  <div class="{amt_cls}">{prefix}&nbsp;{brl(item["amount"])}</div>
  <div class="cal-dot {paid_cls}"></div>
</div>""")

    return f"""
<div class="sec">
  <h2>Calendário do mês</h2>
  <div class="cal-totals">
    <div class="cal-t-card">
      <div class="cal-t-lbl">A receber</div>
      <div class="cal-t-val" style="color:var(--ve)">{brl(total_in)}</div>
    </div>
    <div class="cal-t-card">
      <div class="cal-t-lbl">Recebido</div>
      <div class="cal-t-val" style="color:var(--ve)">{brl(total_received)}</div>
    </div>
    <div class="cal-t-card">
      <div class="cal-t-lbl">A pagar</div>
      <div class="cal-t-val" style="color:var(--vm)">{brl(total_unpaid)}</div>
    </div>
    <div class="cal-t-card">
      <div class="cal-t-lbl">Pago</div>
      <div class="cal-t-val" style="color:var(--mu2)">{brl(total_paid)}</div>
    </div>
  </div>
  <div class="card">
    <div class="cal-list">{"".join(rows)}</div>
  </div>
</div>"""


def s_consolidated(estado: dict) -> str:
    c   = estado.get("consolidated", {})
    inc = estado["income"]
    if not c:
        return ""

    proj = c["projected_balance"]
    proj_color = "#22c55e" if proj >= 0 else "#ef4444"
    conf_bal = c["confirmed_balance"]
    conf_color = "#22c55e" if conf_bal >= 0 else "#ef4444"

    return f"""
<div class="sec">
  <h2>Posição consolidada</h2>
  <div class="flow-table">
    <div class="flow-row">
      <span class="flow-label">↑ Renda esperada</span>
      <span class="flow-val" style="color:var(--ve)">{brl(c["expected_in"])}</span>
    </div>
    <div class="flow-row" style="padding-left:32px">
      <span class="flow-label" style="color:var(--mu)">· confirmada</span>
      <span class="flow-val" style="color:var(--mu2)">{brl(c["confirmed_in"])}</span>
    </div>
    <div class="flow-row" style="padding-left:32px">
      <span class="flow-label" style="color:var(--mu)">· pendente</span>
      <span class="flow-val" style="color:var(--mu2)">{brl(c["pending_in"])}</span>
    </div>
    <div class="flow-row">
      <span class="flow-label">↓ Total comprometido</span>
      <span class="flow-val" style="color:var(--vm)">− {brl(c["committed_out"])}</span>
    </div>
    <div class="flow-row" style="padding-left:32px">
      <span class="flow-label" style="color:var(--mu)">· pago</span>
      <span class="flow-val" style="color:var(--mu2)">{brl(c["paid_out"])}</span>
    </div>
    <div class="flow-row" style="padding-left:32px">
      <span class="flow-label" style="color:var(--mu)">· pendente</span>
      <span class="flow-val" style="color:var(--mu2)">{brl(c["unpaid_out"])}</span>
    </div>
    <div class="flow-row total">
      <span class="flow-label">Saldo projetado</span>
      <span class="flow-val" style="color:{proj_color}">{brl(proj)}</span>
    </div>
    <div class="flow-row total">
      <span class="flow-label">Saldo confirmado</span>
      <span class="flow-val" style="color:{conf_color}">{brl(conf_bal)}</span>
    </div>
    <div class="flow-row">
      <span class="flow-label" style="color:var(--mu)">Meta poupança (pay-yourself-first)</span>
      <span class="flow-val" style="color:var(--pu)">{brl(c["savings_target"])}/mês</span>
    </div>
  </div>
</div>"""


def s_analysis(analysis: dict) -> str:
    if not analysis:
        return ""

    diag_text   = analysis.get("diagnosis_text", "")
    advice_text = analysis.get("advice_text", "")

    if not diag_text and not advice_text:
        return ""

    blocks = []
    if diag_text:
        blocks.append(f"""
<div class="analysis-block">
  <div class="atitle">O que o Severino viu</div>
  <div class="abody">{diag_text}</div>
</div>""")
    if advice_text:
        blocks.append(f"""
<div class="analysis-block">
  <div class="atitle">O que fazer agora</div>
  <div class="abody">{advice_text}</div>
</div>""")

    return f"""
<div class="sec">
  <h2>Análise</h2>
  {"".join(blocks)}
</div>"""


def s_reserves(estado: dict) -> str:
    res = estado.get("reserves", {})
    inv = estado.get("investments", {})
    return f"""
<div class="sec">
  <h2>Reserva e patrimônio</h2>
  <div class="grid2">
    <div class="card">
      <div class="lbl">Reserva atual</div>
      <div class="val">{brl(res.get("current", 0))}</div>
      <div class="sub">meta {brl(res.get("target", 0))} ({res.get("target_months", 3)} meses)</div>
    </div>
    <div class="card">
      <div class="lbl">Investimentos</div>
      <div class="val">{brl(inv.get("total", 0))}</div>
      <div class="sub">líquido: {brl(inv.get("liquid", 0))}</div>
    </div>
  </div>
</div>"""


def s_charts(svg_dir: Path, slug: str) -> str:
    sections = []
    for suffix, label in SVG_FILES:
        content = load_svg(svg_dir / f"{slug}-{suffix}.svg")
        if content:
            sections.append(f"""
<div class="svg-item">
  <div class="svg-title">{label}</div>
  <div class="svg-box">{content}</div>
</div>""")
    if not sections:
        return ""
    return f"""
<div class="sec">
  <h2>Gráficos</h2>
  {"".join(sections)}
</div>"""


# ─── assembler ────────────────────────────────────────────────────────────────

def build_html(estado: dict, svg_dir: Path, ym: str,
               analysis: dict | None = None) -> str:
    slug = month_slug(ym)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Severino — {month_title(ym)}</title>
  <style>{CSS}</style>
</head>
<body>
<div class="wrap">
  {s_header(estado, ym)}
  {s_analysis(analysis or {})}
  {s_summary(estado)}
  {s_consolidated(estado)}
  {s_health(estado["diagnosis"])}
  {s_recommendation(estado)}
  {s_reserves(estado)}
  {s_calendar(estado.get("calendar", {}))}
  {s_charts(svg_dir, slug)}
  <div class="footer">
    Severino v2 · dados locais, nunca sincronizados
  </div>
</div>
</body>
</html>"""


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Gera RESUMO-YYYY-MM.html do mês.")
    parser.add_argument("year_month", help="YYYY-MM")
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--analysis-json", type=Path, default=None,
                        help="JSON com {diagnosis_text, advice_text} a embutir no HTML")
    args = parser.parse_args()

    try:
        datetime.strptime(args.year_month, "%Y-%m")
    except ValueError:
        print("Formato inválido — use YYYY-MM", file=sys.stderr)
        return 1

    slug        = month_slug(args.year_month)
    estado_path = args.data_dir / "meses" / slug / "estado.json"

    if not estado_path.exists():
        print(f"estado.json não encontrado: {estado_path}", file=sys.stderr)
        print("→ rode derive_estado.py primeiro", file=sys.stderr)
        return 1

    with open(estado_path, encoding="utf-8") as f:
        estado = json.load(f)

    analysis = {}
    if args.analysis_json and args.analysis_json.exists():
        with open(args.analysis_json, encoding="utf-8") as f:
            analysis = json.load(f)

    svg_dir  = args.data_dir / "graficos"
    html     = build_html(estado, svg_dir, args.year_month, analysis)
    out_path = args.data_dir / "meses" / slug / f"RESUMO-{args.year_month}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✓ {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
