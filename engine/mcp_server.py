#!/usr/bin/env python3
"""Severino MCP Server — stdio transport.

Tools expostos:
  anota_transacao   — registra gasto / receita / transferência
  listar_categorias — lista categorias do DB (para o LLM resolver IDs)
  consulta_estado   — deriva e devolve estado.json do mês

Configuração em ~/.claude/claude_desktop_config.json (ou settings.json do Claude Code):

    {
      "mcpServers": {
        "severino": {
          "command": "python3",
          "args": ["/caminho/para/severino/engine/mcp_server.py"],
          "env": {
            "SEVERINO_HOME": "/caminho/para/severino",
            "SEVERINO_DATA_DIR": "/caminho/para/seus/dados"
          }
        }
      }
    }

Dependência:
    pip install mcp
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# ─── Config ───────────────────────────────────────────────────────────────────

SEVERINO_HOME = Path(os.environ["SEVERINO_HOME"])
SEVERINO_DATA_DIR = Path(os.environ["SEVERINO_DATA_DIR"])
DB_PATH = SEVERINO_DATA_DIR / "finance-mcp-server" / "data" / "finance.db"

mcp = FastMCP("severino")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def resolve_category(cur: sqlite3.Cursor, nome: str) -> Optional[int]:
    """Busca category_id por nome exato ou parcial (case-insensitive)."""
    row = cur.execute(
        "SELECT id FROM categories WHERE lower(name) = lower(?) AND active=1 LIMIT 1",
        (nome,),
    ).fetchone()
    if row:
        return row["id"]
    row = cur.execute(
        "SELECT id, name FROM categories WHERE lower(name) LIKE lower(?) AND active=1 LIMIT 1",
        (f"%{nome}%",),
    ).fetchone()
    return row["id"] if row else None


# ─── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
def listar_categorias(kind: Optional[str] = None) -> str:
    """Lista categorias disponíveis no banco.

    Args:
        kind: Filtro opcional — 'expense', 'income' ou 'transfer'.
              Se omitido, retorna todas.

    Returns:
        JSON com lista de {id, name, parent_name, kind, budget_group}.
    """
    with get_conn() as conn:
        cur = conn.cursor()
        query = """
            SELECT c.id, c.name, p.name AS parent_name, c.kind, c.budget_group
            FROM categories c
            LEFT JOIN categories p ON p.id = c.parent_id
            WHERE c.active = 1
            {where}
            ORDER BY c.kind, c.sort_order, c.name
        """
        if kind:
            rows = cur.execute(
                query.format(where="AND c.kind = ?"), (kind,)
            ).fetchall()
        else:
            rows = cur.execute(query.format(where="")).fetchall()

    return json.dumps([dict(r) for r in rows], ensure_ascii=False)


@mcp.tool()
def anota_transacao(
    descricao: str,
    valor: float,
    tipo: str,
    categoria: str,
    data: Optional[str] = None,
    notas: Optional[str] = None,
    conta_id: Optional[int] = None,
    cartao_id: Optional[int] = None,
    parcela_divida_nome: Optional[str] = None,
) -> str:
    """Registra uma transação financeira no banco.

    Args:
        descricao: Texto livre descrevendo o lançamento.
        valor: Valor em BRL (positivo sempre; o tipo define a direção).
        tipo: 'expense', 'income' ou 'transfer'.
        categoria: Nome da categoria (exato ou parcial). Ex: 'Supermercado', 'Salário'.
        data: Data no formato YYYY-MM-DD. Padrão: hoje.
        notas: Observação livre opcional.
        conta_id: ID da conta debitada/creditada (opcional).
        cartao_id: ID do cartão usado (opcional).
        parcela_divida_nome: Se for parcela de dívida, nome da dívida para atualizar
                             installments_paid e balance_remaining automaticamente.

    Returns:
        JSON com {transaction_id, saldo_do_dia, aviso} após gravar.
    """
    if tipo not in ("expense", "income", "transfer"):
        return json.dumps({"erro": f"tipo inválido: {tipo!r}. Use expense, income ou transfer."})

    data_iso = data or date.today().isoformat()

    with get_conn() as conn:
        cur = conn.cursor()

        category_id = resolve_category(cur, categoria)
        if category_id is None:
            cats = cur.execute(
                "SELECT name FROM categories WHERE active=1 AND kind=? ORDER BY name LIMIT 10",
                (tipo,),
            ).fetchall()
            sugestoes = [r["name"] for r in cats]
            return json.dumps({
                "erro": f"Categoria {categoria!r} não encontrada.",
                "sugestoes": sugestoes,
            }, ensure_ascii=False)

        cur.execute(
            """
            INSERT INTO transactions (date, description, amount, type, category_id,
                                      account_id, card_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data_iso, descricao, valor, tipo, category_id,
             conta_id, cartao_id, notas or ""),
        )
        transaction_id = cur.lastrowid

        aviso = None
        if parcela_divida_nome:
            updated = cur.execute(
                """
                UPDATE debts SET
                  installments_paid = installments_paid + 1,
                  balance_remaining = balance_remaining - ?
                WHERE lower(name) LIKE lower(?) AND status = 'active'
                """,
                (valor, f"%{parcela_divida_nome}%"),
            ).rowcount
            if not updated:
                aviso = f"Dívida {parcela_divida_nome!r} não encontrada — transação gravada sem atualizar débito."

        conn.commit()

    # Derivar estado do mês para devolver saldo do dia
    ano_mes = data_iso[:7]
    estado = _derivar_estado(ano_mes)
    saldo = estado.get("income", {}).get("confirmed", 0) - estado.get("spending", {}).get("paid", 0)

    result: dict = {"transaction_id": transaction_id, "saldo_do_dia": round(saldo, 2)}
    if aviso:
        result["aviso"] = aviso
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def consulta_estado(ano_mes: Optional[str] = None) -> str:
    """Deriva e retorna o estado financeiro do mês.

    Args:
        ano_mes: Mês no formato YYYY-MM. Padrão: mês atual.

    Returns:
        Conteúdo do estado.json gerado pelo derive_estado.py.
    """
    ym = ano_mes or date.today().strftime("%Y-%m")
    estado = _derivar_estado(ym)
    return json.dumps(estado, ensure_ascii=False, indent=2)


# ─── Interno ──────────────────────────────────────────────────────────────────

def _derivar_estado(ano_mes: str) -> dict:
    derive_script = SEVERINO_HOME / "engine" / "derive_estado.py"
    result = subprocess.run(
        [sys.executable, str(derive_script), ano_mes, "--data-dir", str(SEVERINO_DATA_DIR)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"erro": result.stderr.strip()}

    slug = _month_slug(ano_mes)
    estado_file = SEVERINO_DATA_DIR / "meses" / slug / "estado.json"
    if estado_file.exists():
        return json.loads(estado_file.read_text())
    return {"aviso": "derive_estado.py rodou mas estado.json não encontrado."}


def _month_slug(ym: str) -> str:
    meses = ["janeiro","fevereiro","março","abril","maio","junho",
             "julho","agosto","setembro","outubro","novembro","dezembro"]
    y, m = ym.split("-")
    return f"{meses[int(m)-1]}-{y}"


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
