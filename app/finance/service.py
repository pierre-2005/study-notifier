from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.db import get_conn
from app.finance import budget, monthly
from app.finance.db import now_iso
from app.finance.parser import (
    STANDARD_CATEGORIES,
    TRANSACTION_TYPES,
    Transaction,
    default_rules_for,
    parse_statement,
)


def money(value) -> str:
    try:
        v = float(value or 0)
    except Exception:
        v = 0.0
    return f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}"


def percent(value) -> str:
    if value == float("inf"):
        return "New"
    if value is None:
        return "—"
    return f"{value:+.1f}%"


def parse_amount(value: str) -> float:
    try:
        return float(str(value or "0").replace("$", "").replace(",", "").strip() or 0)
    except Exception:
        return 0.0


def clean_text(value: str, max_len: int = 500) -> str:
    return " ".join(str(value or "").split()).strip()[:max_len]


def file_signature_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def list_categories() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT name FROM finance_categories ORDER BY CASE WHEN name='Other' THEN 1 ELSE 0 END, name").fetchall()
    names = [r["name"] for r in rows]
    if not names:
        return list(STANDARD_CATEGORIES)
    return names


def add_category(name: str) -> bool:
    name = clean_text(name, 80)
    if not name:
        return False
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM finance_categories WHERE name=?", (name,)).fetchone()
        if exists:
            return False
        ts = now_iso()
        conn.execute("INSERT INTO finance_categories(name, is_custom, created_at_utc) VALUES(?,?,?)", (name, 1, ts))
        conn.execute(
            """
            INSERT OR IGNORE INTO finance_budget_rows(section, name, amount, frequency, created_at_utc, updated_at_utc)
            VALUES('expenses', ?, 0, 'Monthly', ?, ?)
            """,
            (name, ts, ts),
        )
        conn.commit()
    return True


def load_rules() -> dict[str, list[str]]:
    categories = list_categories()
    rules = default_rules_for(categories)
    with get_conn() as conn:
        rows = conn.execute("SELECT category, keyword FROM finance_merchant_rules ORDER BY category, keyword").fetchall()
    for r in rows:
        rules.setdefault(r["category"], [])
        if r["keyword"] not in rules[r["category"]]:
            rules[r["category"]].append(r["keyword"])
    return {c: rules.get(c, []) for c in categories}


def add_rule(category: str, keyword: str) -> bool:
    category = clean_text(category, 120)
    keyword = clean_text(keyword, 120)
    if not category or not keyword or category not in list_categories():
        return False
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO finance_merchant_rules(category, keyword, created_at_utc) VALUES(?,?,?)",
            (category, keyword, now_iso()),
        )
        conn.commit()
    return True


def delete_rule(category: str, keyword: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM finance_merchant_rules WHERE category=? AND keyword=?", (category, keyword))
        conn.commit()


def signature_exists(signature: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM finance_imports WHERE signature=?", (signature,)).fetchone()
    return bool(row)


def tx_exists(tx: Transaction) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM finance_transactions
            WHERE date=? AND description=? AND amount=? AND bank=? AND source_file=?
            """,
            (tx.date, tx.description, float(tx.amount), tx.bank, tx.source_file),
        ).fetchone()
    return bool(row)


def insert_transaction(conn, tx: Transaction) -> bool:
    ts = now_iso()
    try:
        conn.execute(
            """
            INSERT INTO finance_transactions(
              date, description, amount, category, bank, source_file, transaction_type, included, note, created_at_utc, updated_at_utc
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                tx.date,
                tx.description,
                float(tx.amount),
                tx.category,
                tx.bank,
                tx.source_file,
                tx.transaction_type,
                1 if tx.included else 0,
                tx.note,
                ts,
                ts,
            ),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def import_pdf_bytes(filename: str, data: bytes) -> dict:
    signature = file_signature_bytes(data)
    clean_name = Path(filename).name
    if signature_exists(signature):
        return {"filename": clean_name, "status": "duplicate", "parsed": 0, "inserted": 0, "bank": ""}

    import tempfile

    suffix = ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        rules = load_rules()
        categories = list_categories()
        transactions = parse_statement(tmp_path, rules=rules, categories=categories)
    finally:
        try:
            Path(tmp_path).unlink()
        except FileNotFoundError:
            pass

    if not transactions:
        raise ValueError("The statement was recognized, but no transactions were extracted.")

    bank = transactions[0].bank if transactions else "Unknown"
    inserted = 0
    with get_conn() as conn:
        for tx in transactions:
            tx.source_file = clean_name
            if insert_transaction(conn, tx):
                inserted += 1
        conn.execute(
            "INSERT OR IGNORE INTO finance_imports(signature, filename, bank, transaction_count, imported_at_utc) VALUES(?,?,?,?,?)",
            (signature, clean_name, bank, len(transactions), now_iso()),
        )
        conn.commit()

    return {"filename": clean_name, "status": "imported", "parsed": len(transactions), "inserted": inserted, "bank": bank}


def transaction_from_row(r) -> Transaction:
    return Transaction(
        date=r["date"],
        description=r["description"],
        amount=float(r["amount"]),
        category=r["category"],
        bank=r["bank"],
        source_file=r["source_file"],
        transaction_type=r["transaction_type"],
        included=bool(r["included"]),
        note=r["note"] or "",
    )


def load_transactions(include_excluded: bool = True, category: str = "All", month: str = "") -> list[Transaction]:
    sql = "SELECT * FROM finance_transactions WHERE 1=1"
    params: list = []
    if not include_excluded:
        sql += " AND included=1"
    if category and category != "All":
        sql += " AND category=?"
        params.append(category)
    if month:
        sql += " AND date LIKE ?"
        params.append(month + "-%")
    sql += " ORDER BY date DESC, id DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [transaction_from_row(r) for r in rows]


def list_transaction_rows(include_excluded: bool = False, category: str = "All", month: str = "") -> list:
    sql = "SELECT * FROM finance_transactions WHERE 1=1"
    params: list = []
    if not include_excluded:
        sql += " AND included=1"
    if category and category != "All":
        sql += " AND category=?"
        params.append(category)
    if month:
        sql += " AND date LIKE ?"
        params.append(month + "-%")
    sql += " ORDER BY date DESC, id DESC"
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_transaction(tx_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM finance_transactions WHERE id=?", (tx_id,)).fetchone()


def update_transaction(tx_id: int, data: dict) -> None:
    category = data.get("category") if data.get("category") in list_categories() else "Other"
    tx_type = data.get("transaction_type") if data.get("transaction_type") in TRANSACTION_TYPES else "Other"
    amount = parse_amount(data.get("amount", "0"))
    if tx_type == "Refund/Credit":
        amount = -abs(amount)
    elif tx_type in ("Deposit", "Payment/Transfer", "Correction") and str(data.get("amount", "")).strip().startswith("-"):
        amount = -abs(amount)
    else:
        amount = abs(amount)
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE finance_transactions
            SET date=?, description=?, amount=?, category=?, transaction_type=?, included=?, note=?, updated_at_utc=?
            WHERE id=?
            """,
            (
                clean_text(data.get("date", ""), 20),
                clean_text(data.get("description", ""), 500),
                amount,
                category,
                tx_type,
                1 if data.get("included") else 0,
                clean_text(data.get("note", ""), 500),
                now_iso(),
                tx_id,
            ),
        )
        conn.commit()


def delete_transaction(tx_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM finance_transactions WHERE id=?", (tx_id,))
        conn.commit()


def imports() -> list:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM finance_imports ORDER BY imported_at_utc DESC").fetchall()


def clear_statement_history() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM finance_transactions")
        conn.execute("DELETE FROM finance_imports")
        conn.commit()


def remove_month(month_key: str) -> int:
    with get_conn() as conn:
        before = conn.execute("SELECT COUNT(*) AS c FROM finance_transactions").fetchone()["c"]
        conn.execute("DELETE FROM finance_transactions WHERE date LIKE ?", (month_key + "-%",))
        after = conn.execute("SELECT COUNT(*) AS c FROM finance_transactions").fetchone()["c"]
        conn.commit()
    return int(before - after)


def budget_data() -> dict:
    categories = list_categories()
    data = budget.default_budget(categories)
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM finance_budget_rows ORDER BY section, name").fetchall()
        name_setting = conn.execute("SELECT value FROM finance_settings WHERE key='budget_name'").fetchone()
    if name_setting:
        data["name"] = name_setting["value"]
    for r in rows:
        section = r["section"]
        name = r["name"]
        if section not in data:
            data[section] = {}
        data[section][name] = {"amount": float(r["amount"]), "frequency": budget.normalize_frequency(r["frequency"])}
    return data


def save_budget_rows(name: str, rows: list[dict]) -> None:
    ts = now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO finance_settings(key, value) VALUES('budget_name', ?)",
            (clean_text(name, 120),),
        )
        for r in rows:
            section = clean_text(r.get("section", ""), 40)
            row_name = clean_text(r.get("name", ""), 180)
            if not section or not row_name:
                continue
            amount = max(0.0, parse_amount(r.get("amount", "0")))
            frequency = budget.normalize_frequency(r.get("frequency", "Monthly"))
            # UPDATE-first remains compatible with databases created by older
            # releases where finance_budget_rows has no composite UNIQUE index.
            # Do not rely on SQLite ON CONFLICT(section,name) being available.
            result = conn.execute(
                """UPDATE finance_budget_rows
                   SET amount=?, frequency=?, updated_at_utc=?
                   WHERE section=? AND name=?""",
                (amount, frequency, ts, section, row_name),
            )
            if result.rowcount == 0:
                conn.execute(
                    """INSERT INTO finance_budget_rows
                       (section,name,amount,frequency,created_at_utc,updated_at_utc)
                       VALUES(?,?,?,?,?,?)""",
                    (section, row_name, amount, frequency, ts, ts),
                )
        conn.commit()


def add_budget_row(section: str, name: str) -> bool:
    section = clean_text(section, 40)
    name = clean_text(name, 180)
    if section not in ("custom_income", "expenses", "custom_savings") or not name:
        return False
    if section == "expenses":
        add_category(name)
    ts = now_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO finance_budget_rows(section, name, amount, frequency, created_at_utc, updated_at_utc)
            VALUES(?,?,?,?,?,?)
            """,
            (section, name, 0, "Monthly", ts, ts),
        )
        changed = conn.total_changes > 0
        conn.commit()
    return changed


def budget_rows_for_template(data: dict) -> list[dict]:
    rows: list[dict] = []
    for section, label in [
        ("income", "Income"),
        ("custom_income", "Custom income"),
        ("expenses", "Expenses"),
        ("savings", "Savings goals"),
        ("custom_savings", "Custom savings goals"),
    ]:
        for idx, (name, src) in enumerate(data.get(section, {}).items()):
            key = f"{section}_{idx}"
            if section in ("income", "custom_income"):
                chart_kind, chart_group = "income", ""
            elif section in ("savings", "custom_savings"):
                chart_kind, chart_group = "outflow", "Savings"
            else:
                chart_kind, chart_group = "outflow", budget.chart_group_for_expense(name)
            rows.append({
                "key": key,
                "section": section,
                "section_label": label,
                "name": name,
                "amount": src.get("amount", 0),
                "frequency": src.get("frequency", "Monthly"),
                "chart_kind": chart_kind,
                "chart_group": chart_group,
            })
    return rows


def finance_summary() -> dict:
    txs = load_transactions(include_excluded=False)
    bd = budget_data()
    analysis = budget.analyze_budget(bd, txs, list_categories())
    ov = monthly.overview(txs, bd)
    total = sum(tx.amount for tx in txs if tx.included and tx.transaction_type in ("Purchase", "Refund/Credit"))
    return {
        "transaction_count": len(txs),
        "included_total": total,
        "monthly_average": ov["average"],
        "months_count": len(ov["months"]),
        "cash_left": analysis["actual_cash_after"],
        "over_budget_count": len([r for r in analysis["rows"] if r["status"] == "Over"]),
        "latest_change": ov["current_change"],
    }


def export_transactions_csv() -> str:
    rows = list_transaction_rows(include_excluded=True)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Date", "Bank", "Description", "Amount", "Category", "Type", "Included in Spending", "Note", "Source File"])
    for r in rows:
        writer.writerow([r["date"], r["bank"], r["description"], f"{float(r['amount']):.2f}", r["category"], r["transaction_type"], "Yes" if r["included"] else "No", r["note"], r["source_file"]])
    return out.getvalue()


def export_summary_csv() -> str:
    txs = load_transactions(include_excluded=False)
    totals = {c: 0.0 for c in list_categories()}
    for tx in txs:
        if tx.included:
            totals[tx.category] = totals.get(tx.category, 0.0) + tx.amount
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Category", "Total"])
    for c in list_categories():
        writer.writerow([c, f"{totals.get(c, 0.0):.2f}"])
    writer.writerow(["TOTAL SPENDING", f"{sum(totals.values()):.2f}"])
    return out.getvalue()


def export_monthly_csv() -> str:
    txs = load_transactions(include_excluded=False)
    bd = budget_data()
    ov = monthly.overview(txs, bd)
    categories = list(dict.fromkeys(list_categories() + [c for m in ov["categories"].values() for c in m]))
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Month", "Total Spending", "Monthly Budget", "Under/Over", "Scotiabank", "BMO"] + categories)
    for r in ov["rows"]:
        cmap = ov["categories"].get(r["month"], {})
        writer.writerow([r["label"], round(r["total"], 2), round(r["budget"], 2), round(r["difference"], 2), round(r["scotia"], 2), round(r["bmo"], 2)] + [round(cmap.get(c, 0.0), 2) for c in categories])
    return out.getvalue()
