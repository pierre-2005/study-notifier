from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

from app.finance.parser import STANDARD_CATEGORIES, Transaction

FREQUENCIES = ["Annually", "Quarterly", "Semi-annually", "Monthly", "Biweekly", "Weekly"]
ANNUAL_MULTIPLIERS = {
    "Annually": 1,
    "Quarterly": 4,
    "Semi-annually": 2,
    "Monthly": 12,
    "Biweekly": 26,
    "Weekly": 52,
}

INCOME_ROWS = [
    "Employment income",
    "Household members' employment income",
    "Rental income",
    "Pension income",
    "Benefits and support payments",
]

EXPENSE_GROUPS = {
    "Housing": [
        "Mortgage or rent", "Property tax", "Electricity, gas and water",
        "Homeowner or renter's insurance", "Condo fees", "Home security service", "Maintenance costs",
    ],
    "Communications": [
        "Internet, cable and home phone", "Mobile phone", "Streaming media subscriptions", "Other digital subscriptions",
    ],
    "Food": [
        "Groceries", "Meal kits and food-delivery services", "CafÃ©s and coffee shops",
        "Restaurants (dine-in, delivery or takeout)",
    ],
    "Debt payments": [
        "Personal loan payments", "Credit card or line of credit interest", "Student loan payments",
    ],
    "Transportation": [
        "Car loan or lease payments", "Gas and electric vehicle charging", "Repairs and maintenance",
        "Insurance and registration", "Parking and tolls", "Public transit", "Ride-share and taxis",
        "Car- or bike-share membership",
    ],
    "Family": [
        "Children's clothes", "Childcare", "Children's recreation", "Tuition and tutoring",
        "Eldercare and other dependants", "Pet care", "Dry-cleaning and laundry",
    ],
    "Health and wellbeing": [
        "Insurance premiums", "Prescription drugs", "Dental and eye care", "Hair, spa and beauty services",
        "Fitness, sports and club memberships", "Mental health and wellbeing",
    ],
    "Shopping": [
        "Clothing and accessories", "Housewares and decor", "Personal care products",
    ],
    "Recreation": [
        "Tickets for events and attractions", "Hobbies and recreation",
    ],
    "Gifts, donations and professional fees": [
        "Gifts", "Charitable donations", "Professional fees",
    ],
}

STANDARD_EXPENSE_ROWS = [item for rows in EXPENSE_GROUPS.values() for item in rows]

SAVINGS_ROWS = [
    "Emergency fund", "Retirement", "Home purchase or renovations", "Vacations",
    "Major purchases", "Education", "Future family expenses",
]


def money_decimal(value, *, signed=False) -> Decimal:
    """Reject malformed money before writes, with deterministic cents."""
    raw = str(value if value is not None else "").strip() or "0"
    if raw.startswith("$"): raw = raw[1:]
    pattern = r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,6})?"
    if signed: pattern = "-?" + pattern
    if len(raw) > 30 or not re.fullmatch(pattern, raw):
        raise ValueError("Enter a valid amount, such as 125.50.")
    try:
        amount = Decimal(raw.replace(",", ""))
        if not amount.is_finite() or abs(amount) > Decimal("999999999.99"):
            raise ValueError("Amount must be within 999,999,999.99.")
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid amount.") from exc


def _number(value) -> float:
    return float(money_decimal(value))


STAGES = [("income", "Income"), ("essentials", "Essentials"),
          ("flexible", "Flexible spending"), ("savings", "Savings"), ("review", "Review")]
FLEXIBLE_TERMS = ("streaming", "subscription", "meal kit", "food-delivery", "café", "restaurant",
                  "recreation", "hobbies", "tickets", "gifts", "donation", "beauty", "spa", "decor")
COMMON_ROWS = {"Employment income", "Mortgage or rent", "Groceries", "Electricity, gas and water",
               "Mobile phone", "Public transit", "Restaurants (dine-in, delivery or takeout)",
               "Streaming media subscriptions", "Emergency fund"}


def stage_for(section: str, name: str, overrides: dict | None = None) -> str:
    if section in ("income", "custom_income"): return "income"
    if section in ("savings", "custom_savings"): return "savings"
    override = (overrides or {}).get(name)
    if override in ("essentials", "flexible"): return override
    return "flexible" if any(term in name.lower() for term in FLEXIBLE_TERMS) else "essentials"


def normalize_frequency(value: str, default: str = "Monthly") -> str:
    return value if value in FREQUENCIES else default


def row(amount=0.0, frequency="Monthly") -> dict:
    return {"amount": _number(amount), "frequency": normalize_frequency(frequency)}


def normalize_rows(saved: dict, names: list[str], default_frequency="Monthly") -> dict:
    out = {}
    for name in names:
        src = saved.get(name, {}) if isinstance(saved, dict) else {}
        out[name] = row(src.get("amount", 0.0), src.get("frequency", default_frequency))
    return out


def default_budget(categories: list[str] | None = None) -> dict:
    categories = categories or list(STANDARD_CATEGORIES)
    return {
        "name": "",
        "income": normalize_rows({}, INCOME_ROWS),
        "custom_income": {},
        "expenses": normalize_rows({}, categories),
        "savings": normalize_rows({}, SAVINGS_ROWS),
        "custom_savings": {},
    }


def annualize(amount: float, frequency: str) -> float:
    return _number(amount) * ANNUAL_MULTIPLIERS.get(frequency, 12)


def monthlyize(amount: float, frequency: str) -> float:
    return annualize(amount, frequency) / 12.0


def monthly_budget_values(data: dict) -> dict:
    income = {}
    for section in ("income", "custom_income"):
        for name, r in data.get(section, {}).items():
            income[name] = monthlyize(r.get("amount", 0), r.get("frequency", "Monthly"))
    expenses = {
        name: monthlyize(r.get("amount", 0), r.get("frequency", "Monthly"))
        for name, r in data.get("expenses", {}).items()
    }
    savings = {}
    for section in ("savings", "custom_savings"):
        for name, r in data.get(section, {}).items():
            savings[name] = monthlyize(r.get("amount", 0), r.get("frequency", "Monthly"))
    return {
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "total_income": sum(income.values()),
        "total_expenses": sum(expenses.values()),
        "total_savings": sum(savings.values()),
    }


def actual_monthly_averages(transactions: list[Transaction], categories: list[str]) -> tuple[dict[str, float], int, dict[str, dict[str, float]]]:
    by_month: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    months = set()
    for tx in transactions:
        if not tx.included or tx.transaction_type not in ("Purchase", "Refund/Credit"):
            continue
        try:
            month = datetime.strptime(tx.date, "%Y-%m-%d").strftime("%Y-%m")
        except Exception:
            continue
        months.add(month)
        by_month[month][tx.category] += tx.amount

    all_categories = list(dict.fromkeys(categories + [tx.category for tx in transactions if tx.category]))
    totals = {c: 0.0 for c in all_categories}
    for month in months:
        for category in all_categories:
            totals[category] += max(0.0, by_month[month].get(category, 0.0))
    count = len(months)
    averages = {c: (totals[c] / count if count else 0.0) for c in all_categories}
    return averages, count, {m: dict(v) for m, v in by_month.items()}


def category_status(actual: float, budget: float) -> tuple[str, float]:
    if budget <= 0:
        return ("No budget", 0.0) if actual > 0 else ("Good", 0.0)
    utilization = actual / budget
    if utilization > 1.0:
        return "Over", utilization
    if utilization >= 0.80:
        return "Watch", utilization
    return "Good", utilization


def analyze_budget(data: dict, transactions: list[Transaction], categories: list[str] | None = None) -> dict:
    categories = categories or list(STANDARD_CATEGORIES)
    planned = monthly_budget_values(data)
    all_categories = list(dict.fromkeys(list(planned["expenses"].keys()) + categories))
    actual, month_count, monthly_detail = actual_monthly_averages(transactions, all_categories)
    rows = []
    for category in all_categories:
        budget = planned["expenses"].get(category, 0.0)
        act = actual.get(category, 0.0)
        status, util = category_status(act, budget)
        rows.append({
            "category": category,
            "budget": budget,
            "actual": act,
            "difference": budget - act,
            "status": status,
            "utilization": util,
        })

    actual_total = sum(actual.values())
    planned_cash_after = planned["total_income"] - planned["total_expenses"] - planned["total_savings"]
    actual_cash_after = planned["total_income"] - actual_total - planned["total_savings"]
    return {
        "planned": planned,
        "actual": actual,
        "rows": rows,
        "months": month_count,
        "monthly_detail": monthly_detail,
        "actual_total": actual_total,
        "planned_cash_after": planned_cash_after,
        "actual_cash_after": actual_cash_after,
        "recommendations": build_recommendations(rows, transactions, actual_cash_after, planned),
    }


def build_recommendations(rows: list[dict], transactions: list[Transaction], cash_after: float, planned: dict) -> list[str]:
    recs: list[str] = []
    over = sorted((r for r in rows if r["status"] == "Over"), key=lambda r: r["actual"] - r["budget"], reverse=True)
    watch = sorted((r for r in rows if r["status"] == "Watch"), key=lambda r: r["utilization"], reverse=True)
    no_budget = sorted((r for r in rows if r["status"] == "No budget" and r["actual"] > 0), key=lambda r: r["actual"], reverse=True)

    if not over and not watch and not no_budget:
        recs.append("You are within every spending limit you entered. Your current category limits look sustainable based on the statements loaded.")

    discretionary_terms = (
        "restaurant", "cafÃ©", "coffee", "streaming", "digital subscription", "recreation",
        "tickets", "hobbies", "gifts", "clothing", "beauty", "ride-share", "food-delivery",
    )
    essential_terms = ("rent", "mortgage", "property tax", "electricity", "insurance", "prescription", "childcare", "student loan")

    for r in over:
        over_by = r["actual"] - r["budget"]
        name_lower = r["category"].lower()
        if any(k in name_lower for k in discretionary_terms):
            action = "This is a good place to cut, pause, or set a stricter weekly limit."
        elif any(k in name_lower for k in essential_terms):
            action = "This looks more essential, so first check whether the budget amount is realistic before trying to cut it."
        elif "grocer" in name_lower:
            action = "Review large grocery runs and mixed-retailer purchases before cutting necessities."
        elif "gas" in name_lower or "transport" in name_lower:
            action = "Review driving frequency, fuel choice, parking, or whether this budget simply needs to be higher."
        else:
            action = "Review the largest purchases below and decide whether they were one-time or can be reduced."
        recs.append(f"{r['category']} is about ${over_by:,.2f}/month over budget. {action}")
        top = top_transactions_for_category(transactions, r["category"], 3)
        if top:
            recs.append("Largest items to review: " + ", ".join(f"{t.description} (${abs(t.amount):,.2f})" for t in top) + ".")

    if watch:
        recs.append("Close to the limit: " + ", ".join(f"{r['category']} ({r['utilization']*100:.0f}%)" for r in watch[:6]) + ".")
    if no_budget:
        recs.append("You have spending with no budget set for: " + ", ".join(f"{r['category']} (${r['actual']:,.0f}/mo)" for r in no_budget[:6]) + ". Add limits if you want these tracked.")

    if cash_after < 0:
        recs.append(f"Your average spending plus savings goals are about ${abs(cash_after):,.2f}/month above the income entered. Start with the over-budget discretionary categories, then reconsider savings timing or fixed-cost assumptions if needed.")
    else:
        recs.append(f"After average spending and ${planned['total_savings']:,.2f}/month of savings goals, about ${cash_after:,.2f}/month remains unallocated.")

    if planned["total_savings"] <= 0:
        recs.append("No savings goal is currently funded. Consider assigning some of the remaining cash to an emergency fund or another goal.")
    return recs


def top_transactions_for_category(transactions: list[Transaction], category: str, limit: int = 3) -> list[Transaction]:
    candidates = [
        tx for tx in transactions
        if tx.included and tx.transaction_type == "Purchase" and tx.category == category and tx.amount > 0
    ]
    return sorted(candidates, key=lambda t: t.amount, reverse=True)[:limit]

# Visual grouping used by the CIBC-inspired annual breakdown card.
BUDGET_CHART_GROUPS = ["Housing", "Essentials", "Transportation", "Living", "Personal spending", "Savings"]


def chart_group_for_expense(name: str) -> str:
    if name in EXPENSE_GROUPS.get("Housing", []):
        return "Housing"
    if name in EXPENSE_GROUPS.get("Transportation", []):
        return "Transportation"
    if name in (EXPENSE_GROUPS.get("Communications", []) + EXPENSE_GROUPS.get("Food", []) + EXPENSE_GROUPS.get("Debt payments", [])):
        return "Essentials"
    if name in (EXPENSE_GROUPS.get("Family", []) + EXPENSE_GROUPS.get("Health and wellbeing", [])):
        return "Living"
    return "Personal spending"
