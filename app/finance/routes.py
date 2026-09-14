from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.finance import budget, monthly, service
from app.finance.parser import TRANSACTION_TYPES
from app.meta import APP_VERSION

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["APP_VERSION"] = APP_VERSION
router = APIRouter(prefix="/finance", tags=["finance"])


def _uid(request: Request) -> int:
    user = getattr(request.state, "current_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return int(user["id"])


def template_context(request: Request, **extra):
    base = {
        "request": request,
        "money": service.money,
        "percent": service.percent,
        "frequencies": budget.FREQUENCIES,
        "transaction_types": TRANSACTION_TYPES,
    }
    base.update(extra)
    return base


@router.get("", response_class=HTMLResponse)
def finance_home(request: Request):
    uid = _uid(request)
    summary = service.finance_summary(uid)
    recent = service.list_transaction_rows(uid, include_excluded=False)[:8]
    imports = service.imports(uid)[:5]
    return templates.TemplateResponse(
        request,
        "finance_dashboard.html",
        template_context(request, summary=summary, recent=recent, imports=imports),
    )


@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request):
    return templates.TemplateResponse(
        request,
        "finance_import.html",
        template_context(request, imports=service.imports(_uid(request)), results=None, error=None),
    )


@router.post("/import", response_class=HTMLResponse)
async def import_pdfs(request: Request, files: list[UploadFile] = File(...)):
    results = []
    errors = []
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            errors.append(f"{f.filename or 'File'}: not a PDF file")
            continue
        try:
            data = await f.read()
            if not data:
                errors.append(f"{f.filename}: empty file")
                continue
            results.append(service.import_pdf_bytes(_uid(request), f.filename, data))
        except Exception as exc:
            errors.append(f"{f.filename}: {exc}")
    return templates.TemplateResponse(
        request,
        "finance_import.html",
        template_context(request, imports=service.imports(_uid(request)), results=results, error="\n".join(errors) if errors else None),
    )


@router.post("/clear")
def clear_finance_history(request: Request):
    service.clear_statement_history(_uid(request))
    return RedirectResponse("/finance/import", status_code=303)


@router.get("/transactions", response_class=HTMLResponse)
def transactions_page(
    request: Request,
    category: str = Query("All"),
    month: str = Query(""),
    show_excluded: bool = Query(False),
):
    uid = _uid(request)
    categories = service.list_categories(uid)
    rows = service.list_transaction_rows(uid, include_excluded=show_excluded, category=category, month=month)
    txs = service.load_transactions(uid, include_excluded=show_excluded, category=category, month=month)
    total = sum(tx.amount for tx in txs if tx.included and tx.transaction_type in ("Purchase", "Refund/Credit"))
    months = monthly.all_months(service.load_transactions(uid, include_excluded=True))
    return templates.TemplateResponse(
        request,
        "finance_transactions.html",
        template_context(
            request,
            rows=rows,
            categories=categories,
            selected_category=category,
            selected_month=month,
            months=months,
            show_excluded=show_excluded,
            total=total,
        ),
    )


@router.get("/transactions/{tx_id}", response_class=HTMLResponse)
def transaction_detail(request: Request, tx_id: int):
    tx = service.get_transaction(_uid(request), tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return templates.TemplateResponse(
        request,
        "finance_transaction_detail.html",
        template_context(request, tx=tx, categories=service.list_categories(_uid(request))),
    )


@router.post("/transactions/{tx_id}/update")
async def update_transaction(request: Request, tx_id: int):
    tx = service.get_transaction(_uid(request), tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    form = await request.form()
    service.update_transaction(
        _uid(request),
        tx_id,
        {
            "date": form.get("date", ""),
            "description": form.get("description", ""),
            "amount": form.get("amount", "0"),
            "category": form.get("category", "Other"),
            "transaction_type": form.get("transaction_type", "Other"),
            "included": bool(form.get("included")),
            "note": form.get("note", ""),
        },
    )
    return RedirectResponse(f"/finance/transactions/{tx_id}", status_code=303)


@router.post("/transactions/{tx_id}/delete")
def delete_transaction(request: Request, tx_id: int):
    service.delete_transaction(_uid(request), tx_id)
    return RedirectResponse("/finance/transactions", status_code=303)


@router.get("/budget", response_class=HTMLResponse)
def budget_page(request: Request):
    uid = _uid(request)
    data = service.budget_data(uid)
    txs = service.load_transactions(uid, include_excluded=False)
    analysis = budget.analyze_budget(data, txs, service.list_categories(uid))
    rows = service.budget_rows_for_template(data)
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["section_label"], []).append(r)
    return templates.TemplateResponse(
        request,
        "finance_budget.html",
        template_context(request, data=data, grouped=grouped, analysis=analysis),
    )


@router.post("/budget/save")
async def save_budget(request: Request):
    form = await request.form()
    rows = []
    for key in form.getlist("row_key"):
        rows.append({
            "section": form.get(f"section__{key}", ""),
            "name": form.get(f"name__{key}", ""),
            "amount": form.get(f"amount__{key}", "0"),
            "frequency": form.get(f"frequency__{key}", "Monthly"),
        })
    service.save_budget_rows(_uid(request), str(form.get("name", "")), rows)
    return RedirectResponse("/finance/budget", status_code=303)


@router.post("/budget/custom")
def add_budget_custom(request: Request, section: str = Form(...), name: str = Form(...)):
    service.add_budget_row(_uid(request), section, name)
    return RedirectResponse("/finance/budget", status_code=303)


@router.get("/monthly", response_class=HTMLResponse)
def monthly_page(request: Request, a: str = Query(""), b: str = Query("")):
    uid = _uid(request)
    txs = service.load_transactions(uid, include_excluded=False)
    data = service.budget_data(uid)
    ov = monthly.overview(txs, data)
    months = ov["months"]
    if months:
        if a not in months:
            a = months[-2] if len(months) >= 2 else months[-1]
        if b not in months:
            b = months[-1]
    cmp = monthly.comparison(txs, data, a, b, service.list_categories(uid)) if a and b else None
    return templates.TemplateResponse(
        request,
        "finance_monthly.html",
        template_context(request, overview=ov, months=months, selected_a=a, selected_b=b, comparison=cmp),
    )


@router.post("/monthly/remove")
def remove_month(request: Request, month_key: str = Form(...)):
    service.remove_month(_uid(request), month_key)
    return RedirectResponse("/finance/monthly", status_code=303)


@router.get("/rules", response_class=HTMLResponse)
def rules_page(request: Request):
    uid = _uid(request)
    categories = service.list_categories(uid)
    rules = service.load_rules(uid)
    return templates.TemplateResponse(
        request,
        "finance_rules.html",
        template_context(request, categories=categories, rules=rules),
    )


@router.post("/rules/category")
def add_category(request: Request, name: str = Form(...)):
    service.add_category(_uid(request), name)
    return RedirectResponse("/finance/rules", status_code=303)


@router.post("/rules/add")
def add_rule(request: Request, category: str = Form(...), keyword: str = Form(...)):
    service.add_rule(_uid(request), category, keyword)
    return RedirectResponse("/finance/rules", status_code=303)


@router.post("/rules/delete")
def remove_rule(request: Request, category: str = Form(...), keyword: str = Form(...)):
    service.delete_rule(_uid(request), category, keyword)
    return RedirectResponse("/finance/rules", status_code=303)


@router.get("/export/transactions.csv")
def export_transactions(request: Request):
    return StreamingResponse(
        iter([service.export_transactions_csv(_uid(request))]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finance_transactions.csv"},
    )


@router.get("/export/summary.csv")
def export_summary(request: Request):
    return StreamingResponse(
        iter([service.export_summary_csv(_uid(request))]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finance_summary.csv"},
    )


@router.get("/export/monthly.csv")
def export_monthly(request: Request):
    return StreamingResponse(
        iter([service.export_monthly_csv(_uid(request))]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finance_monthly.csv"},
    )
