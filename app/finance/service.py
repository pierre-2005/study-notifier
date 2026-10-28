from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.db import get_conn
from app.exports import CsvWriter
from app.finance import budget, monthly
from app.document_process import worker_environment, DOCUMENT_SLOTS
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
        return "â€”"
    return f"{value:+.1f}%"


def parse_amount(value: str) -> float:
    return float(budget.money_decimal(value, signed=True))


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
        bump_budget_revision(conn)
        conn.commit()
    return True


def load_rules() -> dict[str, list[str]]:
    categories = list_categories()
    rules = {category: [] for category in categories}
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
        if not DOCUMENT_SLOTS.acquire(timeout=5):raise ValueError('Two documents are already being processed. Try again shortly.')
        try:
            process=subprocess.run([sys.executable,'-m','app.finance.worker',tmp_path],input=json.dumps({'rules':rules,'categories':categories}),text=True,encoding='utf-8',capture_output=True,timeout=45,env=worker_environment())
        except subprocess.TimeoutExpired as exc:raise ValueError('Statement processing took too long. Split the PDF and try again.') from exc
        finally:DOCUMENT_SLOTS.release()
        if process.returncode:raise ValueError('Unable to read this statement. Use an unencrypted BMO or Scotiabank PDF with at most 60 pages.')
        transactions=[Transaction(**row) for row in json.loads(process.stdout)]
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


def transaction_page(include_excluded=False,category='All',month='',query='',page=1,page_size=50):
    where,params=['1=1'],[]
    if not include_excluded:where.append('included=1')
    if category and category!='All':where.append('category=?');params.append(category)
    if month:
        if not re.fullmatch(r'\d{4}-\d{2}',month):raise ValueError('Choose a valid month.')
        datetime.strptime(month+'-01','%Y-%m-%d')
        where.append('date>=? AND date<?');params.extend([month+'-01', (datetime(int(month[:4])+int(month[5:])//12,int(month[5:])%12+1,1)).strftime('%Y-%m-%d')])
    if query:
        where.append('(description LIKE ? OR note LIKE ?)');params.extend(['%'+query[:200]+'%']*2)
    clause=' AND '.join(where)
    with get_conn() as conn:
        summary=conn.execute("SELECT COUNT(*) AS count,COALESCE(SUM(CASE WHEN included=1 AND transaction_type IN ('Purchase','Refund/Credit') THEN amount ELSE 0 END),0) AS total FROM finance_transactions WHERE "+clause,params).fetchone()
        pages=max(1,(summary['count']+page_size-1)//page_size);page=max(1,min(page,pages))
        rows=conn.execute('SELECT * FROM finance_transactions WHERE '+clause+' ORDER BY date DESC,id DESC LIMIT ? OFFSET ?',(*params,page_size,(page-1)*page_size)).fetchall()
        months=[r[0] for r in conn.execute("SELECT DISTINCT substr(date,1,7) FROM finance_transactions ORDER BY 1")]
    return {'rows':rows,'count':summary['count'],'total':summary['total'],'page':page,'pages':pages,'months':months}


def list_transaction_rows(include_excluded=False,category='All',month='',limit=None):
    # Exports intentionally include every requested row. Interactive views use SQL pagination.
    sql='SELECT * FROM finance_transactions WHERE 1=1';params=[]
    if not include_excluded:sql+=' AND included=1'
    if category and category!='All':sql+=' AND category=?';params.append(category)
    if month:sql+=' AND date LIKE ?';params.append(month+'-%')
    sql+=' ORDER BY date DESC,id DESC'
    if limit is not None:sql+=' LIMIT ?';params.append(limit)
    with get_conn() as conn:return conn.execute(sql,params).fetchall()


def get_transaction(tx_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM finance_transactions WHERE id=?", (tx_id,)).fetchone()


def update_transaction(tx_id: int, data: dict) -> None:
    category = data.get("category") if data.get("category") in list_categories() else "Other"
    tx_type = data.get("transaction_type") if data.get("transaction_type") in TRANSACTION_TYPES else "Other"
    day = str(data.get("date", ""))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day): raise ValueError("Enter a valid date.")
    datetime.strptime(day, "%Y-%m-%d")
    if not clean_text(data.get("description", "")): raise ValueError("Description is required.")
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
    if not re.fullmatch(r"\d{4}-\d{2}", month_key): raise ValueError("Choose a valid month.")
    datetime.strptime(month_key + "-01", "%Y-%m-%d")
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
    with get_conn() as conn:
        settings = {r["key"]: r["value"] for r in conn.execute("SELECT key,value FROM finance_settings WHERE key IN ('budget_revision','budget_stages')")}
    try: data["revision"] = int(settings.get("budget_revision", "0"))
    except (ValueError, TypeError): data["revision"] = 0
    try:
        stages = json.loads(settings.get("budget_stages", "{}"))
        data["stages"] = stages if isinstance(stages, dict) else {}
    except (ValueError, TypeError): data["stages"] = {}
    return data


class BudgetConflict(ValueError):
    pass


def save_budget_rows(name: str, rows: list[dict], revision=None) -> int:
    if len(rows) > 500: raise ValueError("A budget supports up to 500 categories.")
    if len(str(name)) > 120: raise ValueError("Budget name must be 120 characters or less.")
    clean, seen = [], set()
    for r in rows:
        section, row_name = str(r.get("section", "")), str(r.get("name", "")).strip()
        if section not in ("income", "custom_income", "expenses", "savings", "custom_savings"):
            raise ValueError("Choose a valid budget section.")
        if not row_name or len(row_name) > 180: raise ValueError("Category names must be 1 to 180 characters.")
        identity = (section, row_name.casefold())
        if identity in seen: raise ValueError("A category appears more than once.")
        seen.add(identity)
        amount = budget.money_decimal(r.get("amount", "0"))
        frequency = r.get("frequency", "Monthly")
        if frequency not in budget.FREQUENCIES: raise ValueError("Choose a valid payment frequency.")
        stage = r.get("stage", "")
        if section == "expenses" and stage and stage not in ("essentials", "flexible"):
            raise ValueError("Choose Essentials or Flexible spending.")
        clean.append((section, row_name, float(amount), frequency, stage))
    ts = now_iso()
    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        old = conn.execute("SELECT value FROM finance_settings WHERE key='budget_revision'").fetchone()
        current = int(old["value"]) if old and str(old["value"]).isdigit() else 0
        if revision is not None:
            try: supplied = int(revision)
            except (ValueError, TypeError): raise ValueError("Invalid budget revision.")
            if supplied != current:
                raise BudgetConflict("A newer budget was saved in another tab. Your edits are still here. Open the saved budget in a new tab to compare before reloading.")
        old_stages = conn.execute("SELECT value FROM finance_settings WHERE key='budget_stages'").fetchone()
        try: stages = json.loads(old_stages["value"]) if old_stages else {}
        except (ValueError, TypeError): stages = {}
        if not isinstance(stages, dict): stages = {}
        for section, row_name, amount, frequency, stage in clean:
            # UPDATE-first also supports historical tables with no composite unique key.
            result = conn.execute("UPDATE finance_budget_rows SET amount=?,frequency=?,updated_at_utc=? WHERE section=? AND name=?",
                                  (amount, frequency, ts, section, row_name))
            if result.rowcount == 0:
                conn.execute("INSERT INTO finance_budget_rows(section,name,amount,frequency,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)",
                             (section, row_name, amount, frequency, ts, ts))
            if section == "expenses":
                conn.execute("INSERT OR IGNORE INTO finance_categories(name,is_custom,created_at_utc) VALUES(?,1,?)", (row_name, ts))
                if stage: stages[row_name] = stage
        for key, value in (("budget_name", name.strip()), ("budget_revision", str(current + 1)), ("budget_stages", json.dumps(stages))):
            conn.execute("INSERT OR REPLACE INTO finance_settings(key,value) VALUES(?,?)", (key, value))
        conn.commit()
    return current + 1


def add_budget_row(section: str, name: str) -> bool:
    name=clean_text(name,180)
    if section not in ('custom_income','expenses','custom_savings') or not name:return False
    ts=now_iso()
    with get_conn() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM finance_budget_rows WHERE section=? AND name=?',(section,name)).fetchone():return False
        conn.execute("INSERT INTO finance_budget_rows(section,name,amount,frequency,created_at_utc,updated_at_utc) VALUES(?,?,0,'Monthly',?,?)",(section,name,ts,ts))
        if section=='expenses':conn.execute('INSERT OR IGNORE INTO finance_categories(name,is_custom,created_at_utc) VALUES(?,1,?)',(name,ts))
        bump_budget_revision(conn);conn.commit()
    return True


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
                "stage": budget.stage_for(section, name, data.get("stages")),
                "visible": bool(float(src.get("amount", 0))) or name in budget.COMMON_ROWS,
                "monthly": budget.monthlyize(src.get("amount", 0), src.get("frequency", "Monthly")),
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
    writer = CsvWriter(out)
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
    writer = CsvWriter(out)
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
    writer = CsvWriter(out)
    writer.writerow(["Month", "Total Spending", "Monthly Budget", "Under/Over", "Scotiabank", "BMO"] + categories)
    for r in ov["rows"]:
        cmap = ov["categories"].get(r["month"], {})
        writer.writerow([r["label"], round(r["total"], 2), round(r["budget"], 2), round(r["difference"], 2), round(r["scotia"], 2), round(r["bmo"], 2)] + [round(cmap.get(c, 0.0), 2) for c in categories])
    return out.getvalue()


def bump_budget_revision(conn):
    row=conn.execute("SELECT value FROM finance_settings WHERE key='budget_revision'").fetchone()
    current=int(row['value']) if row and str(row['value']).isdigit() else 0
    conn.execute("INSERT OR REPLACE INTO finance_settings(key,value) VALUES('budget_revision',?)",(str(current+1),))
