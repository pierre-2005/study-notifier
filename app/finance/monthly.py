from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from app.finance.parser import Transaction
from app.finance.budget import monthly_budget_values, category_status


def month_key(tx: Transaction) -> str | None:
    try:
        return datetime.strptime(tx.date, "%Y-%m-%d").strftime("%Y-%m")
    except Exception:
        return None


def month_label(key: str) -> str:
    try:
        return datetime.strptime(key, "%Y-%m").strftime("%B %Y")
    except Exception:
        return key


def included_spending(tx: Transaction) -> bool:
    return bool(tx.included and tx.transaction_type in ("Purchase", "Refund/Credit"))


def all_months(transactions: Iterable[Transaction]) -> list[str]:
    months = {m for tx in transactions if (m := month_key(tx))}
    return sorted(months)


def monthly_category_totals(transactions: Iterable[Transaction]) -> dict[str, dict[str, float]]:
    out = defaultdict(lambda: defaultdict(float))
    for tx in transactions:
        m = month_key(tx)
        if not m or not included_spending(tx):
            continue
        out[m][tx.category or "Other"] += tx.amount
    return {m: dict(v) for m, v in out.items()}


def monthly_bank_totals(transactions: Iterable[Transaction]) -> dict[str, dict[str, float]]:
    out = defaultdict(lambda: defaultdict(float))
    for tx in transactions:
        m = month_key(tx)
        if not m or not included_spending(tx):
            continue
        out[m][tx.bank or "Unknown"] += tx.amount
    return {m: dict(v) for m, v in out.items()}


def monthly_transaction_counts(transactions: Iterable[Transaction]) -> dict[str, dict[str, int]]:
    out = defaultdict(lambda: defaultdict(int))
    for tx in transactions:
        m = month_key(tx)
        if not m:
            continue
        out[m][tx.bank or "Unknown"] += 1
    return {m: dict(v) for m, v in out.items()}


def overview(transactions: list[Transaction], budget_data: dict) -> dict:
    months = all_months(transactions)
    cats = monthly_category_totals(transactions)
    banks = monthly_bank_totals(transactions)
    counts = monthly_transaction_counts(transactions)
    planned = monthly_budget_values(budget_data)
    budget_total = planned["total_expenses"]

    rows = []
    for m in months:
        cat_map = cats.get(m, {})
        total = sum(cat_map.values())
        top_cat, top_amt = ("—", 0.0)
        positives = [(k, v) for k, v in cat_map.items() if v > 0]
        if positives:
            top_cat, top_amt = max(positives, key=lambda kv: kv[1])
        diff = budget_total - total
        status, utilization = category_status(total, budget_total)
        rows.append({
            "month": m,
            "label": month_label(m),
            "total": total,
            "budget": budget_total,
            "difference": diff,
            "status": status,
            "utilization": utilization,
            "top_category": top_cat,
            "top_amount": top_amt,
            "scotia": banks.get(m, {}).get("Scotiabank", 0.0),
            "bmo": banks.get(m, {}).get("BMO", 0.0),
            "scotia_count": counts.get(m, {}).get("Scotiabank", 0),
            "bmo_count": counts.get(m, {}).get("BMO", 0),
        })

    totals = [r["total"] for r in rows]
    avg = sum(totals) / len(totals) if totals else 0.0
    highest = max(rows, key=lambda r: r["total"]) if rows else None
    lowest = min(rows, key=lambda r: r["total"]) if rows else None

    current_change = None
    if len(rows) >= 2:
        prev, cur = rows[-2], rows[-1]
        delta = cur["total"] - prev["total"]
        pct = (delta / prev["total"] * 100.0) if prev["total"] else None
        current_change = {"delta": delta, "percent": pct, "previous": prev, "current": cur}

    return {
        "months": months,
        "rows": rows,
        "categories": cats,
        "banks": banks,
        "counts": counts,
        "average": avg,
        "highest": highest,
        "lowest": lowest,
        "budget_total": budget_total,
        "current_change": current_change,
    }


def comparison(transactions: list[Transaction], budget_data: dict, month_a: str, month_b: str, categories: list[str]) -> dict:
    ov = overview(transactions, budget_data)
    cats = ov["categories"]
    budget = monthly_budget_values(budget_data)["expenses"]
    all_categories = list(dict.fromkeys(categories + list(cats.get(month_a, {}).keys()) + list(cats.get(month_b, {}).keys())))
    rows = []
    for cat in all_categories:
        a = cats.get(month_a, {}).get(cat, 0.0)
        b = cats.get(month_b, {}).get(cat, 0.0)
        delta = b - a
        pct = (delta / a * 100.0) if a else (None if b == 0 else float("inf"))
        rows.append({
            "category": cat,
            "a": a,
            "b": b,
            "delta": delta,
            "percent": pct,
            "budget": budget.get(cat, 0.0),
        })
    rows.sort(key=lambda r: abs(r["delta"]), reverse=True)

    total_a = sum(cats.get(month_a, {}).values())
    total_b = sum(cats.get(month_b, {}).values())
    total_delta = total_b - total_a
    total_pct = (total_delta / total_a * 100.0) if total_a else None

    increases = [r for r in rows if r["delta"] > 0.005]
    decreases = [r for r in rows if r["delta"] < -0.005]
    over_budget = []
    for r in rows:
        if r["budget"] > 0 and r["b"] > r["budget"]:
            over_budget.append({**r, "over": r["b"] - r["budget"]})
    over_budget.sort(key=lambda r: r["over"], reverse=True)

    return {
        "month_a": month_a,
        "month_b": month_b,
        "label_a": month_label(month_a),
        "label_b": month_label(month_b),
        "rows": rows,
        "total_a": total_a,
        "total_b": total_b,
        "total_delta": total_delta,
        "total_percent": total_pct,
        "increases": increases,
        "decreases": decreases,
        "over_budget": over_budget,
    }
