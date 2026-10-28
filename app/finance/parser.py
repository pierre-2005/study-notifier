from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

STANDARD_CATEGORIES = [
    "Mortgage or rent", "Property tax", "Electricity, gas and water", "Homeowner or renter's insurance",
    "Condo fees", "Home security service", "Maintenance costs",
    "Internet, cable and home phone", "Mobile phone", "Streaming media subscriptions", "Other digital subscriptions",
    "Groceries", "Meal kits and food-delivery services", "Cafés and coffee shops", "Restaurants (dine-in, delivery or takeout)",
    "Personal loan payments", "Credit card or line of credit interest", "Student loan payments",
    "Car loan or lease payments", "Gas and electric vehicle charging", "Repairs and maintenance",
    "Insurance and registration", "Parking and tolls", "Public transit", "Ride-share and taxis", "Car- or bike-share membership",
    "Children's clothes", "Childcare", "Children's recreation", "Tuition and tutoring", "Eldercare and other dependants",
    "Pet care", "Dry-cleaning and laundry", "Insurance premiums", "Prescription drugs", "Dental and eye care",
    "Hair, spa and beauty services", "Fitness, sports and club memberships", "Mental health and wellbeing",
    "Clothing and accessories", "Housewares and decor", "Personal care products",
    "Tickets for events and attractions", "Hobbies and recreation", "Gifts", "Charitable donations", "Professional fees",
    "Other",
]

DEFAULT_RULES = {
    "Electricity, gas and water": ["ENMAX", "EPCOR", "ATCO", "FORTIS", "DIRECT ENERGY", "HYDRO"],
    "Internet, cable and home phone": ["SHAW CABLE", "SHAW CABLESYSTEMS"],
    "Mobile phone": ["TELUS", "ROGERS", "BELL", "FIDO", "KOODO"],
    "Streaming media subscriptions": ["NETFLIX", "SPOTIFY", "DISNEY PLUS", "DISNEY+", "CRAVE"],
    "Other digital subscriptions": ["OPENAI", "CHATGPT", "GAMMA.APP", "THETAWISE", "APPLE.COM/BILL", "KOBO"],
    "Gas and electric vehicle charging": ["COSTCO GAS", "PETRO-CANADA", "PETRO CANADA", "SHELL", "ESSO", "MOBIL", "HUSKY", "CO-OP GAS", "COOP GAS", "CALG CO-OP GAS", "TSUU T'INA GAS", "TSUU T'INA NATI", "SOUTHSIDE SER", "FAS GAS", "CENTEX"],
    "Groceries": ["COSTCO WHOLESALE", "COSTCO WHOLESAL", "SAFEWAY", "SOBEYS", "SAVE ON FOODS", "SAVE-ON-FOODS", "SUPERSTORE", "NO FRILLS", "FRESHCO", "WALMART", "LOBLAWS", "REAL CANADIAN", "T&T SUPERMARKET", "T AND T"],
    "Restaurants (dine-in, delivery or takeout)": ["MCDONALD", "WENDY", "SUBWAY", "DOMINO", "CHIPOTLE", "DOORDASHCHIPOTLE", "KFC", "POPEYES", "BURGER KING", "TIM HORTON", "A&W", "A & W", "PIZZA HUT", "COSMIC PIZZA", "SENIORE'S PIZZA", "SENIORE’S PIZZA", "JOEY", "PORCH KITCHEN", "BLOWERS AND GRAFTON", "BLOWERS AND GRA", "CACTUS CLUB", "LEOPOLDS TAVERN", "HAYDEN BLOCK", "FAHAD RESTAURAN", "TURKISH KEBAB", "SUSHI", "SHAWARMA", "KOREAN BBQ", "PHO 26", "RESTAURANT", "TAVERN", "SMOKEHOUSE", "KITCHEN & COCKTA", "GRILL", "BISTRO", "STEAKHOUSE"],
    "Meal kits and food-delivery services": ["DOORDASHDASHPASS", "UBER EATS", "SKIPTHEDISHES"],
    "Parking and tolls": ["UCALGARY PARKING", "HANGTAG PARKING", "INDIGO PARK", "PARKPLUS"],
    "Clothing and accessories": ["FOOT LOCKER", "SPORT CHEK"],
    "Housewares and decor": ["RONA", "HOME DEPOT", "IKEA"],
    "Charitable donations": ["ST MINA CHURCH"],
    "Other": [],
}

MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1
)}

TRANSACTION_TYPES = [
    "Purchase", "Refund/Credit", "Payment/Transfer", "Deposit", "Transfer/Withdrawal", "Correction", "Other",
]


@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    category: str
    bank: str
    source_file: str
    transaction_type: str = "Purchase"
    included: bool = True
    note: str = ""

    def key(self) -> tuple:
        return (self.date, self.description, round(self.amount, 2), self.bank, self.source_file)


def default_rules_for(categories: Iterable[str]) -> dict[str, list[str]]:
    return {c: list(DEFAULT_RULES.get(c, [])) for c in categories}


def categorize(description: str, rules: dict[str, list[str]], categories: list[str] | None = None) -> str:
    categories = categories or STANDARD_CATEGORIES
    upper = re.sub(r"\s+", " ", description.upper())
    for category in categories:
        if category == "Other":
            continue
        for keyword in rules.get(category, []):
            k = keyword.strip().upper()
            if k and k in upper:
                return category
    return "Other"


def infer_year(text: str, filename: str = "") -> int:
    filename_years = re.findall(r"(?<!\d)(20\d{2})(?!\d)", filename)
    if filename_years:
        return int(filename_years[-1])
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", text)]
    now = datetime.now().year
    sensible = [y for y in years if 2000 <= y <= now + 1]
    if sensible:
        return max(sensible)
    return now


def iso_date(month: str, day: str | int, year: int) -> str:
    m = MONTHS.get(month[:3].lower())
    if not m:
        return f"{month} {day} {year}"
    return f"{year:04d}-{m:02d}-{int(day):02d}"


def read_pdf(path: str | Path, password: str = "") -> tuple[str, list[str], str]:
    path = Path(path)
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        if not password or reader.decrypt(password) == 0:
            raise ValueError(f"{path.name} is password protected.")

    if len(reader.pages)>60: raise ValueError("Use at most 60 pages per statement.")
    normal_pages: list[str] = []
    layout_pages: list[str] = []
    for page in reader.pages:
        normal_pages.append((page.extract_text() or "").replace("\u00a0", " "))
        try:
            layout = page.extract_text(extraction_mode="layout") or ""
        except Exception:
            layout = ""
        layout_pages.append(layout.replace("\u00a0", " "))
        if sum(map(len,normal_pages))+sum(map(len,layout_pages))>1_000_000:raise ValueError("Statement text exceeds the extraction limit.")

    normal = "\n".join(normal_pages)
    layout = "\n".join(layout_pages)
    detection = (normal + "\n" + layout).upper()
    if "SCOTIABANK" in detection or "SCOTIA INSURANCE" in detection or "SCOTIAINSURANCE.COM" in detection or "DAY-TO-DAY BANKING" in detection or "OPENING BALANCE ON JUNE" in detection:
        bank = "Scotiabank"
    elif "BMO" in detection or "BANK OF MONTREAL" in detection:
        bank = "BMO"
    elif "TRANSACTIONS SINCE YOUR LAST STATEMENT" in detection and "BMO CARDHOLDER" in detection:
        bank = "BMO"
    else:
        bank = "Unknown"
    return normal, layout_pages, bank


def _clean_desc(desc: str) -> str:
    desc = re.sub(r"\s+", " ", desc).strip()
    desc = re.sub(r"^(?:Apos|Opos|Aips)\s+", "", desc, flags=re.I)
    return desc.strip(" -")


def _clean_scotia_sidebar(desc: str) -> str:
    markers = [
        " Take steps towards", " your family from the", " unexpected.", " Scotia Insurance",
        " offers personalized", " Term Life, Travel", " Accidental Death", " Critical Illness",
        " Insurance so you can feel", " confident that your coverage", " fits your specific needs",
        " Check out the offers", " quote on any coverage", " scotiainsurance.com",
    ]
    lowered = desc.lower()
    cut = len(desc)
    for marker in markers:
        pos = lowered.find(marker.lower())
        if pos >= 0:
            cut = min(cut, pos)
    return desc[:cut].strip()


def _parse_bmo(normal_text: str, filename: str, rules: dict[str, list[str]], categories: list[str]) -> list[Transaction]:
    year = infer_year(normal_text, filename)
    lines = [re.sub(r"\s+", " ", x).strip() for x in normal_text.splitlines()]
    start_re = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.\s*(\d{1,2})\s+"
                          r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.\s*(\d{1,2})\s+(.*)$", re.I)

    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if not line:
            continue
        if start_re.match(line):
            if current:
                blocks.append(current)
            current = [line]
        elif current is not None:
            if line.upper().startswith(("SUBTOTAL FOR", "TOTAL FOR CARD", "PAGE ")):
                blocks.append(current)
                current = None
            else:
                current.append(line)
    if current:
        blocks.append(current)

    out: list[Transaction] = []
    amount_re = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s*(CR))?(?!\d)", re.I)
    for block in blocks:
        m = start_re.match(block[0])
        if not m:
            continue
        month, day, _post_month, _post_day, remainder = m.groups()
        joined = " ".join([remainder] + block[1:])
        amounts = list(amount_re.finditer(joined))
        if not amounts:
            continue
        am = amounts[-1]
        amount = float(am.group(1).replace(",", ""))
        is_credit = bool(am.group(2))
        desc = _clean_desc(joined[:am.start()])
        if not desc:
            continue
        if is_credit:
            amount = -amount
        is_payment = is_credit and any(k in desc.upper() for k in ("TRSF FROM/DE", "ACCT/CPT", "PAYMENT"))
        if is_payment:
            tx_type = "Payment/Transfer"
            included = False
            note = "Card payment/transfer excluded from spending"
        elif is_credit:
            tx_type = "Refund/Credit"
            included = True
            note = "Refund/credit reduces the matching spending category"
        else:
            tx_type = "Purchase"
            included = True
            note = ""
        out.append(Transaction(
            date=iso_date(month, day, year),
            description=desc,
            amount=amount,
            category=categorize(desc, rules, categories),
            bank="BMO",
            source_file=filename,
            transaction_type=tx_type,
            included=included,
            note=note,
        ))
    return out


def _scotia_records_to_transactions(records: list[dict], filename: str, rules: dict[str, list[str]], categories: list[str]) -> list[Transaction]:
    out: list[Transaction] = []
    for r in records:
        kind_upper = r["kind"].upper()
        if "ERROR CORRECTION" in kind_upper:
            amount = -abs(r["amount"])
            included = False
            tx_type = "Correction"
            note = "Scotiabank error correction excluded"
        elif "DEPOSIT" in kind_upper or "PAYROLL" in kind_upper or kind_upper == "GST":
            amount = -abs(r["amount"])
            included = False
            tx_type = "Deposit"
            note = "Deposit/income excluded from spending"
        elif "WITHDRAWAL" in kind_upper:
            amount = abs(r["amount"])
            included = False
            tx_type = "Transfer/Withdrawal"
            note = "Transfer/withdrawal excluded from spending by default"
        else:
            amount = abs(r["amount"])
            included = True
            tx_type = "Purchase"
            note = ""

        out.append(Transaction(
            date=r["date"],
            description=r["description"],
            amount=amount,
            category=categorize(r["description"], rules, categories),
            bank="Scotiabank",
            source_file=filename,
            transaction_type=tx_type,
            included=included,
            note=note,
        ))

    for idx, tx in enumerate(out):
        if tx.transaction_type != "Correction":
            continue
        correction_amount = abs(tx.amount)
        corr_words = set(re.findall(r"[A-Z0-9]+", tx.description.upper()))
        for prev_idx in range(idx - 1, max(-1, idx - 5), -1):
            prev = out[prev_idx]
            if prev.date != tx.date or prev.transaction_type != "Purchase" or not prev.included:
                continue
            if abs(prev.amount - correction_amount) > 0.001:
                continue
            prev_words = set(re.findall(r"[A-Z0-9]+", prev.description.upper()))
            overlap = len(corr_words & prev_words)
            if overlap >= 2 or prev.description.upper() in tx.description.upper() or tx.description.upper() in prev.description.upper():
                prev.included = False
                prev.note = "Temporary pre-authorization reversed by Scotiabank error correction"
                break
    return out


def _parse_scotia(layout_pages: list[str], filename: str, rules: dict[str, list[str]], categories: list[str]) -> list[Transaction]:
    all_text = "\n".join(layout_pages)
    year = infer_year(all_text, filename)
    tx_start = re.compile(
        r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+"
        r"(Point\s+of\s+sale\s+purchase|Withdrawal|Deposit|Error\s+correction|Payroll\s+dep\.|GST)\s+(.*)$",
        re.I,
    )
    amount_re = re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})*\.\d{2})(?!\d)")

    records: list[dict] = []
    for page_text in layout_pages:
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in page_text.splitlines()]
        i = 0
        while i < len(lines):
            line = lines[i]
            m = tx_start.match(line)
            if not m:
                i += 1
                continue
            month, day, kind, rest = m.groups()
            nums = list(amount_re.finditer(rest))
            if not nums:
                i += 1
                continue
            amount = float(nums[0].group(1).replace(",", ""))

            details: list[str] = []
            j = i + 1
            while j < len(lines):
                candidate = lines[j]
                if not candidate:
                    j += 1
                    continue
                upper = candidate.upper()
                if tx_start.match(candidate) or upper.startswith(("PAGE ", "CONTINUED ON", "HERE'S WHAT HAPPENED", "AMOUNTS ", "DATE TRANSACTIONS", "CLOSING BALANCE")):
                    break
                details.append(candidate)
                break
            desc = _clean_scotia_sidebar(_clean_desc(" ".join(details))) or kind
            records.append({
                "date": iso_date(month, day, year),
                "kind": re.sub(r"\s+", " ", kind.title()).replace("Dep.", "dep."),
                "amount": amount,
                "description": desc,
            })
            i += 1

    return _scotia_records_to_transactions(records, filename, rules, categories)


def _parse_scotia_normal(normal_text: str, filename: str, rules: dict[str, list[str]], categories: list[str]) -> list[Transaction]:
    year = infer_year(normal_text, filename)
    text = re.sub(r"\s+", " ", normal_text).strip()
    month = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    kind = r"(?:Point\s+of\s+sale\s+purchase|Withdrawal|Deposit|Error\s+correction|Payroll\s+dep\.|GST)"
    money = r"\d{1,3}(?:,\d{3})*\.\d{2}"
    pat = re.compile(
        rf"\b({month})\s+(\d{{1,2}})\s+({kind})\s+({money})\s+({money})\s+(.*?)"
        rf"(?=\b{month}\s+\d{{1,2}}\s+{kind}|\b(?:Closing\s+Balance|Page\s+\d+\s+of\s+\d+)\b|$)",
        re.I,
    )

    records: list[dict] = []
    for m in pat.finditer(text):
        mon, day, tx_kind, amount_s, _balance, desc = m.groups()
        desc = re.sub(r"\bcontinued\s+on\s+next\s+page\b.*?\bDate\s+Transactions\s+withdrawn\s+\(\$\)\s+deposited\s+\(\$\)\s+Balance\s+\(\$\)\b", " ", desc, flags=re.I)
        desc = re.sub(r"\bHere's\s+what\s+happened\s+in\s+your\s+account(?:\s+\(continued\))?\b", " ", desc, flags=re.I)
        desc = re.sub(r"\bAmounts\s+Amounts\s+Date\s+Transactions\s+withdrawn\s+\(\$\)\s+deposited\s+\(\$\)\s+Balance\s+\(\$\)\b", " ", desc, flags=re.I)
        desc = _clean_scotia_sidebar(_clean_desc(desc)) or tx_kind
        records.append({
            "date": iso_date(mon, day, year),
            "kind": re.sub(r"\s+", " ", tx_kind.title()).replace("Dep.", "dep."),
            "amount": float(amount_s.replace(",", "")),
            "description": desc,
        })

    return _scotia_records_to_transactions(records, filename, rules, categories)


def parse_statement(
    path: str | Path,
    rules: dict[str, list[str]],
    categories: list[str] | None = None,
    password: str = "",
) -> list[Transaction]:
    path = Path(path)
    categories = categories or STANDARD_CATEGORIES
    normal, layout_pages, bank = read_pdf(path, password)
    if bank == "BMO":
        return _parse_bmo(normal, path.name, rules, categories)
    if bank == "Scotiabank":
        txs = _parse_scotia(layout_pages, path.name, rules, categories) if any(p.strip() for p in layout_pages) else []
        if not txs:
            txs = _parse_scotia_normal(normal, path.name, rules, categories)
        return txs
    raise ValueError(f"Could not recognize {path.name} as a supported BMO or Scotiabank statement.")
