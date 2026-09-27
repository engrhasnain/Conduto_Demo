# Conduto · Project Intelligence (MVP demo)

Demo for the second Conduto meeting. It shows how scattered project data (Excel cost sheets, Microsoft Project
schedules, PDF contracts and change orders, Dynamics GP ledger exports) becomes one consolidated,
verified and traceable view of project control and profitability, independent of the ERP decision.

**It runs fully without any AI key.** A local engine handles everything:
- two small models trained at startup with scikit-learn;
- read-only SQL for every number;
- keyword search over the documents.

A Claude key only adds free-form answers and reading scanned PDFs.

**All data is synthetic.** 18 fictional projects (Ecuador, Peru, Brazil) and 150 generated source files in the
formats Conduto actually uses. Project, client and person names are invented, and the UI says so everywhere.

## Screens

| Screen | What it shows |
|---|---|
| **Portfolio** | All projects in USD: forecast vs bid margin, cost and schedule efficiency, pending change orders, alerts, auto-generated insights, and a strip linking to data quality. **Filters at the top** (status, country, terrain, health, search) drive every card, chart and table. **Every card opens the list behind it** (projects, contracts, margins, each pending change order with its PDF). Export to Excel |
| **Data & quality** | 150 files → 11.7k records → 18 projects → 100% traceable. Every counter, file-type chip, quality check and coverage cell opens the files or records behind it. Four automatic checks (see below) and a list of the problems they found, filterable by country. Cost-without-progress anomalies, coverage per project, and the trained models with their measured accuracy |
| **Project** | KPIs (each tile opens its detail: the cost and schedule efficiency tiles open an activity-by-activity breakdown); the "where is the margin going" waterfall and its drivers; S-curve; schedule Gantt; cost by activity; detected anomalies; the accounting-vs-Excel check for that project; change orders; events; welding production. **Every number opens its source**: the Excel cell, PDF page, Microsoft Project task or GP ledger row |
| **Ask** | Questions in ES/EN/PT. Without a key, a local classifier understands 19 question types, then runs read-only SQL or document search. Answers cite PDF pages and exact Excel/GP cells, and show how they were built. With a key, Claude answers free-form questions |
| **Load data** | A guided four-step flow (choose a file → the system reads it → you check → saved and traceable), with a plain explanation of why the screen exists. It shows what was understood in one sentence, lists only what needs a person's check, and keeps the technical detail folded away (see below) |
| **Benchmarks** | Historical cost per inch of diameter per kilometre and per kilometre, by terrain (filterable; each terrain card opens its projects), an overrun heatmap by activity, and a bid estimator |
| **Methodology** | Architecture, design principles, roadmap, and the data we need for discovery |

The four automatic checks on the Data & quality screen:
- **Workbook totals:** each Excel file against its own TOTAL row.
- **Reports vs Excel:** the cumulative cost quoted in each monthly PDF against the workbook.
- **ERP vs Excel:** Dynamics GP against the Excel, by project, month and cost type.
- **Traceability:** every value keeps a pointer to its source.

What Load data does with each file type:
- **Excel:** labels are mapped by the trained model. Totals are reconciled against the file's own total row, and new formats are saved as templates.
- **PDF:** fields are extracted and each one is verified word-for-word in the document (groundedness check).
- **Scanned PDF:** it is detected and queued for OCR with a cost estimate, never guessed.
- **Every file:** a person confirms the import, then sees the KPI impact before and after.

Language switch (ES/EN/PT) is in the top bar. `?lang=en` in any URL opens it in English.

### What the demo "discovers" (planted on purpose, found automatically)

- **EC-2503:** margin falls from 17% to 4.5%, driven by river crossings (directional drilling) executed without approval, rain standby and rock excavation. USD 3.4M in pending change orders.
- **ERP vs Excel:**
  - an invoice posted in GP but missing in the Excel (EC-2503);
  - an Excel accrual not yet in GP (PE-2410);
  - a duplicated GP transaction (BR-2501).
- **Stale report:** the EC-2503 April 2026 report quotes March's cumulative cost.
- **Unexplained spend:** two cost spikes with no event or change order to explain them (PE-2410, BR-2501).

## Local models (no AI key)

| Model | What it does | Measured on | Accuracy |
|---|---|---|---|
| Cost-line mapper (char n-grams + logistic regression) | Excel labels in ES/PT/EN, abbreviated or misspelled → 18 standard activities | 82 hand-written labels never used for training | ~96% |
| Question classifier (words + char n-grams, entities masked) | Question → one of 19 question types, in 3 languages | 65 hand-written questions | ~89% |

Both train in a few seconds at startup. The errors are shown on the Data & quality screen; that is why a person
reviews every import. Where the local engine is unsure, it falls back to document search instead of guessing.

## Structure

```
backend/   FastAPI + SQLAlchemy (SQLite) + openpyxl/reportlab/pypdf + scikit-learn + Anthropic SDK (optional)
  app/seed/        synthetic data: real .xlsx / .pdf / .xml / GP exports + database with lineage
  app/ml/          label mapper, question classifier, entity extraction, training
  app/services/    KPIs (earned value), anomalies, ERP reconciliation, data quality, benchmarks, search,
                   ask (local engine + Claude agent), ingestion (Excel/PDF/Microsoft Project, groundedness, triage), export
  tests/           37 tests (API, ingestion round-trips, models, checks, SQL guard, mocked AI paths)
frontend/  Next.js 16 (App Router) + Tailwind 4 + ECharts
```

The dataset and models regenerate automatically on startup (about 15 s), so no database service is needed.

## Run locally

```bash
# backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt      # Windows (use .venv/bin/pip on macOS/Linux)
.venv/Scripts/python -m uvicorn app.main:app --port 8000
.venv/Scripts/python -m pytest -q                       # tests

# frontend (new terminal)
cd frontend
cp .env.example .env.local
npm install
npm run dev        # http://localhost:3000
```

Optional: set `ANTHROPIC_API_KEY` before starting the backend.
- **Ask:** open questions go to Claude (`claude-opus-5`, with server-side refusal fallback).
- **Load data:** unclear rows are sent to Claude, and scanned PDFs are read with vision.
- **Fallback:** if Claude is unreachable during the meeting, Ask falls back to the local engine automatically.

## Deploy for free

1. Push this folder to a GitHub repository.
2. **Backend on Render (free):** New → Blueprint → pick the repo (uses `render.yaml`). The key is optional. Note the URL.
3. **Frontend on Vercel (free):** New Project → import the repo → **Root Directory: `frontend`** →
   env var `NEXT_PUBLIC_API_URL` = the Render URL → Deploy.

Render's free plan sleeps after 15 min idle. The dataset and models are generated during the Render build, so a cold start only
has to boot (about 30–60 s). While the server wakes up, the frontend shows "the server is starting" and retries on its own for
about two minutes, so the first visit no longer needs a manual refresh.
**Open `<render-url>/api/health` a few minutes before the meeting.** "Reset demo" in the sidebar restores the clean dataset.

## Meeting script (~20 min)

1. **Problem (2 min).** Methodology page, "Where we start".
2. **Data & quality (3 min).** Start here, because this is the "global information management" gap:
   - 150 scattered files consolidated, 100% traceable.
   - Then the findings: an invoice in GP missing from the Excel, a duplicated GP entry, a stale monthly report, and spending nobody explained.
   - Line to use: *"Your data already contradicts itself; today nobody sees it."*
3. **Portfolio → EC-2503 (5 min).**
   - Waterfall from 17.0% to 4.5%, and its drivers.
   - Click **OC-007** to show the PDF. Click an activity row to show the exact Excel cell.
   - Show the anomaly and ERP cards.
4. **Load data (4 min).** Open "Why does this screen exist?" first.
   - `Historico_…2019.xlsx`: the local model maps 11/11 rows, with "Sold. + END" shown under "Needs your check"; totals reconcile; confirm and save; benchmarks go from 10 to 11.
   - The `OC-012` PDF: every field verified in the text.
   - The scanned `OC-013`: detected and queued for OCR. Line to use: *"We don't guess."*
5. **Ask (3 min).** Two or three suggested questions in Spanish, plus one of Oscar's own. Open "how this answer was built".
6. **Benchmarks (2 min).** Rainforest vs coast; the estimator.
7. **Next step (1 min).** Methodology → roadmap and data needed. Hand over the consolidated Excel.

### Likely questions

- **"Is this AI?"** The core is deterministic and verifiable: SQL, reconciliation, source links. Two small models run locally,
  and their accuracy is measured and shown. A large model is optional, for open questions and scans.
- **"Why not Power BI?"** Power BI charts structured data. The hard part is structuring and cross-checking Excel, PDF,
  Microsoft Project and GP. The consolidated export feeds Power BI.
- **"Wait for the ERP decision?"** This works with GP today and with SAP/D365 later, and clean history helps the migration.
- **"Where does the data live?"** It can be deployed in Conduto's own cloud. Everything is read-only, and the local engine needs no internet.

## Known limitations (demo scope)

- No login or roles.
- ERP data comes from an export, not a live Dynamics GP connector (planned for the pilot).
- SQLite instead of Postgres.
- Keyword (BM25) search instead of vector search.
- Microsoft Project is read from its XML export (native `.mpp` would need MPXJ).
- The local question engine covers the 19 question types listed on the Data & quality screen.
