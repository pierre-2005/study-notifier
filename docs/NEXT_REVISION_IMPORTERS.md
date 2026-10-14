# Next revision: Intelligent Syllabus and Bank Statement Imports

These are planned workflows, **not included** in 3.4.2. Neither should automatically write data before the user's review.

## A. Syllabus → complete course plan

1. **Upload:** PDF, DOCX, text and photos/scans. Process files only for the signed-in account, with size/type limits and temporary storage.
2. **Read & recognize:** First attempt text extraction. For scanned pages, use document OCR. Extract course code, title, term, professor/contacts, meeting times and location, assessments, grading weights, due dates, exam windows, reading schedules and office hours. Mark every item with its source page and confidence.
3. **Resolve ambiguity:** Dates often say "Week 5" or "TBA". Ask for semester start and timezone and display uncertain values separately; never silently invent them. Flag weights that do not total 100% and assessment dates that conflict.
4. **Review before saving:** Split-pane preview alongside the original pages. Toggle which courses, classes, assignments, reminders and exams to import; edit names, weights and dates. Show any matches already in MLO.
5. **Atomic commit:** Create course records and assessment items in the existing models so they appear in Study, Tasks, Calendar and notifications. Use source fingerprints and an explicit update strategy to prevent duplicates.
6. **Security:** Ignore instructions embedded in uploaded documents, don't leak school materials to other accounts, restrict file access, purge raw documents on request, log import errors without raw personal content.

Acceptance test: upload representative university syllabi, verify the date/weight parser against expected ground truth, correct one uncertain date, approve a preview and ensure the next upload does not produce duplicates.

## B. E-statements → normalized bank transactions

1. **Upload:** Prioritize bank-provided CSV or OFX/QFX, with PDF statement extraction and scanned-document OCR as fallbacks. Do not request bank passwords or logins for statement upload.
2. **Identify bank format:** Detect headers, date styles, debit/credit sign conventions, currency, opening/closing balance, transaction fields and statement range. Support format-specific parsers for different banks; keep a generic parser as fallback.
3. **Normalize:** Extract posted date, effective date, merchant/payee, description, amount, currency, account nickname, bank transaction ID and balance where present. Distinguish payments, internal transfers, reversals, refunds and income from expenses.
4. **Reconcile:** Preview extracted rows with confidence and totals checks against the statement; flag mixed currencies, ambiguous debit/credit signs, unknown merchants and duplicate rows. Show duplicates already imported across multiple statements.
5. **User-approved classification:** Assign categories based on existing rules and feedback, with confidence flags. Allow batch corrections before import and optionally save future classification rules.
6. **Commit to Money:** Import only approved rows into the existing finance transactions/budget model, with idempotency and audit history. Do not automatically add transfers as expenses or double count credit-card payments.
7. **Privacy:** File-size/type controls, encrypted sensitive tokens where applicable, protected attachments, account-level isolation, configurable retention, safe processing of untrusted PDFs and CSV formula injection protection on exports.

Acceptance test: sample anonymized statements from multiple formats/banks, validate signed totals and dates, reconcile against sample balances, duplicate import safely and verify other accounts cannot see imported transactions.

## Technology approach

Use deterministic parsers for structured CSV/OFX first. For variable PDF syllabi and statements, use a document-processing service that can return structured JSON with page/row citations, schema validation and confidence estimates. OCR/AI should be optional; never rely on a generative model alone for financial totals or deadlines. Keep previews and confirmation authoritative. Local OCR or hosted AI must be an explicit privacy choice.
