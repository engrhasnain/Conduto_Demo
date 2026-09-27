"""Writes a project's cost-control workbook in its country's format and returns the
cell locator of every value, so database rows can point back to the exact cell."""
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..config import STATUS_PERIOD
from ..i18n import COST_TYPE_ORDER, MONTHS
from .simulate import SimResult
from .templates import TEMPLATES

HEADER_FILL = PatternFill("solid", fgColor="1F3A5F")
SUB_FILL = PatternFill("solid", fgColor="E8EEF5")
HEADER_FONT = Font(bold=True, color="FFFFFF")
BOLD = Font(bold=True)


def month_header(period: str, style: str):
    y, m = int(period[:4]), int(period[5:])
    if style == "date":
        return datetime(y, m, 1)
    if style == "iso":
        return period
    return f"{MONTHS['pt'][m - 1]}/{str(y)[2:]}"


def month_label(period: str, lang_style: str) -> str:
    y, m = int(period[:4]), int(period[5:])
    lang = "pt" if lang_style == "pt" else "es"
    return f"{MONTHS[lang][m - 1]}-{str(y)[2:]}"


def _header(ws, row: int, values: list, start_col: int = 1):
    for i, v in enumerate(values):
        c = ws.cell(row=row, column=start_col + i, value=v)
        c.fill, c.font = HEADER_FILL, HEADER_FONT
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def write_cost_workbook(sim: SimResult, path, tpl_key: str) -> dict:
    tpl = TEMPLATES[tpl_key]
    spec = sim.spec
    sh = tpl["sheets"]
    loc = {"budget": {}, "cost": {}, "progress": {}, "production": {}, "bid_margin": None}
    wb = Workbook()
    months = sim.periods
    first_month_col = 5

    # ---- Summary ----
    ws = wb.active
    ws.title = sh["summary"]
    ws["A1"] = tpl["title"]
    ws["A1"].font = Font(bold=True, size=13)
    lab = tpl["summary_labels"]
    status_label = month_label(sim.periods[-1] if sim.closed else STATUS_PERIOD, tpl["month_style"])
    rows = [
        (lab[0], f"{spec['code']} – {spec['name']}"), (lab[1], spec["client"]), (lab[2], sim.currency),
        (lab[3], status_label), (lab[4], sim.contract), (lab[5], sim.bid_margin),
    ]
    for i, (k, v) in enumerate(rows, start=2):
        ws.cell(row=i, column=1, value=k).font = BOLD
        c = ws.cell(row=i, column=2, value=v)
        if i == 6:
            c.number_format = "#,##0.00"
        if i == 7:
            c.number_format = "0.0%"
    loc["bid_margin"] = f"{sh['summary']}!B7"
    _header(ws, 9, list(tpl["summary_table"]))
    r = 10
    last = sim.n - 1
    for i, (code, *_rest) in enumerate(sim.activities, start=1):
        budget = sum(sim.budget_orig[code].values())
        actual = sum(sum(v) for v in sim.costs[code].values())
        ws.cell(row=r, column=1, value=tpl["code_fmt"].format(i=i))
        ws.cell(row=r, column=2, value=tpl["labels"][code])
        ws.cell(row=r, column=3, value=budget).number_format = "#,##0"
        ws.cell(row=r, column=4, value=actual).number_format = "#,##0"
        pct = sim.actual[code][last] * tpl["progress_scale"]
        ws.cell(row=r, column=5, value=round(pct, 4)).number_format = "0.0%" if tpl["progress_scale"] == 1 else "0.0"
        r += 1
    ws.cell(row=r + 1, column=1, value=tpl["note"]).font = Font(italic=True, color="888888")
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 42
    for col in "CDE":
        ws.column_dimensions[col].width = 20

    # ---- Monthly costs ----
    ws = wb.create_sheet(sh["cost"])
    ws["A1"] = f"{tpl['cost_title']} ({sim.currency})"
    ws["A1"].font = Font(bold=True, size=12)
    ws["A2"] = f"{spec['code']} – {spec['name']}"
    hr = tpl["header_row"]
    _header(ws, hr, list(tpl["headers"]) + [tpl["budget_header"]])
    for t, p in enumerate(months):
        c = ws.cell(row=hr, column=first_month_col + t, value=month_header(p, tpl["month_style"]))
        c.fill, c.font = HEADER_FILL, HEADER_FONT
        if tpl["month_style"] == "date":
            c.number_format = "mmm-yy"
    total_col = first_month_col + len(months)
    _header(ws, hr, [tpl["total_header"]], start_col=total_col)
    r = hr + 1
    grand = [0.0] * (len(months) + 1)
    for i, (code, *_rest) in enumerate(sim.activities, start=1):
        sub = [0.0] * (len(months) + 1)
        for ct in COST_TYPE_ORDER:
            ws.cell(row=r, column=1, value=tpl["code_fmt"].format(i=i))
            ws.cell(row=r, column=2, value=tpl["labels"][code])
            ws.cell(row=r, column=3, value=tpl["cost_types"][ct])
            b = sim.budget_orig[code][ct]
            ws.cell(row=r, column=4, value=b).number_format = "#,##0"
            loc["budget"][(code, ct)] = f"{sh['cost']}!D{r}"
            sub[0] += b
            row_total = 0.0
            for t in range(len(months)):
                v = sim.costs[code][ct][t]
                col = first_month_col + t
                ws.cell(row=r, column=col, value=v).number_format = "#,##0"
                loc["cost"][(code, ct, t)] = f"{sh['cost']}!{get_column_letter(col)}{r}"
                sub[t + 1] += v
                row_total += v
            ws.cell(row=r, column=total_col, value=row_total).number_format = "#,##0"
            r += 1
        grand = [g + s for g, s in zip(grand, sub)]
        if tpl["subtotal_prefix"]:
            ws.cell(row=r, column=2, value=tpl["subtotal_prefix"] + tpl["labels"][code]).font = BOLD
            ws.cell(row=r, column=4, value=sub[0]).number_format = "#,##0"
            for t in range(len(months)):
                ws.cell(row=r, column=first_month_col + t, value=sub[t + 1]).number_format = "#,##0"
            ws.cell(row=r, column=total_col, value=sum(sub[1:])).number_format = "#,##0"
            for col in range(1, total_col + 1):
                ws.cell(row=r, column=col).fill = SUB_FILL
            r += 1
    ws.cell(row=r, column=2, value=tpl["total_label"]).font = BOLD
    ws.cell(row=r, column=4, value=grand[0]).number_format = "#,##0"
    for t in range(len(months)):
        ws.cell(row=r, column=first_month_col + t, value=grand[t + 1]).number_format = "#,##0"
    ws.cell(row=r, column=total_col, value=sum(grand[1:])).number_format = "#,##0"
    ws.freeze_panes = ws.cell(row=hr + 1, column=first_month_col)
    ws.column_dimensions["B"].width = 36
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    for t in range(len(months) + 1):
        ws.column_dimensions[get_column_letter(first_month_col + t)].width = 13

    # ---- Physical progress ----
    ws = wb.create_sheet(sh["progress"])
    ws["A1"] = f"{spec['code']} – {spec['name']}"
    ws["A1"].font = Font(bold=True, size=12)
    _header(ws, hr, list(tpl["progress_headers"]))
    for t, p in enumerate(months):
        c = ws.cell(row=hr, column=4 + t, value=month_header(p, tpl["month_style"]))
        c.fill, c.font = HEADER_FILL, HEADER_FONT
        if tpl["month_style"] == "date":
            c.number_format = "mmm-yy"
    r = hr + 1
    scale = tpl["progress_scale"]
    for i, (code, *_rest) in enumerate(sim.activities, start=1):
        for kind, series in ((tpl["progress_labels"][0], sim.planned[code]), (tpl["progress_labels"][1], sim.actual[code])):
            ws.cell(row=r, column=1, value=tpl["code_fmt"].format(i=i))
            ws.cell(row=r, column=2, value=tpl["labels"][code])
            ws.cell(row=r, column=3, value=kind)
            for t in range(len(months)):
                c = ws.cell(row=r, column=4 + t, value=round(series[t] * scale, 6 if scale == 1 else 4))
                c.number_format = "0.0%" if scale == 1 else "0.00"
                if kind == tpl["progress_labels"][1]:
                    loc["progress"][(code, t)] = f"{sh['progress']}!{get_column_letter(4 + t)}{r}"
            r += 1
    ws.column_dimensions["B"].width = 36
    ws.freeze_panes = ws.cell(row=hr + 1, column=4)

    # ---- Production (pipelines) ----
    if sim.production:
        ws = wb.create_sheet(sh["production"])
        ws["A1"] = f"{spec['code']} – {spec['name']}"
        ws["A1"].font = Font(bold=True, size=12)
        _header(ws, 3, list(tpl["production_headers"]))
        for t, prod in enumerate(sim.production):
            r = 4 + t
            ws.cell(row=r, column=1, value=month_header(prod["period"], tpl["month_style"]))
            if tpl["month_style"] == "date":
                ws.cell(row=r, column=1).number_format = "mmm-yy"
            ws.cell(row=r, column=2, value=prod["km"]).number_format = "0.00"
            ws.cell(row=r, column=3, value=prod["welds"])
            ws.cell(row=r, column=4, value=prod["repairs"])
            loc["production"][t] = f"{sh['production']}!B{r}"
        for col in "ABCD":
            ws.column_dimensions[col].width = 22

    wb.save(path)
    return loc
