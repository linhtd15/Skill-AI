"""Bảng Action Items (Excel): danh sách chọn trạng thái, tô đỏ việc quá hạn, sheet tổng hợp theo người."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from common import clock, fmt_t

UNASSIGNED = "Chưa xác định"
HEAD = PatternFill("solid", fgColor="E7E5E0")
THIN = Side(style="thin", color="BBBBBB")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
COLS = [("STT", 5), ("Mã", 6), ("Công việc", 46), ("Người phụ trách", 20), ("Email", 26), ("Thời hạn", 12),
        ("Trạng thái", 14), ("Còn lại (ngày)", 10), ("Căn cứ (trích nguyên văn, mốc giờ)", 52), ("Chủ đề", 22), ("Ghi chú", 24)]


def _rows(bb):
    emails = {p["ten"]: p.get("email") for p in bb.get("nguoi_tham_gia", [])}
    topics = {t["id"]: t.get("tieu_de", "") for t in bb.get("chu_de", [])}
    meta = bb.get("meta", {})
    for a in bb.get("hanh_dong", []):
        q = (a.get("trich_dan") or [{}])[0]
        owner = a.get("phu_trach") or UNASSIGNED
        tm = clock(meta, q.get("t"))
        basis = f"[{fmt_t(q.get('t'))}{' – ' + tm if tm else ''}] {q.get('nguoi', '')}: “{q.get('text', '')}”"
        yield a, owner, emails.get(owner) or "", basis, topics.get(a.get("chu_de"), "")


def _sheet_tasks(ws, rows, cfg, title):
    ws.title = "Việc cần làm"
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([])
    ws.append([c for c, _ in COLS])
    for i, (c, w) in enumerate(COLS, 1):
        cell = ws.cell(row=3, column=i)
        cell.font, cell.fill, cell.border = Font(bold=True), HEAD, BOX
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    r = 4
    for n, (a, owner, email, basis, topic) in enumerate(rows, 1):
        han = dt.date.fromisoformat(a["han"]) if a.get("han") else None
        ws.append([n, a["id"], a["cong_viec"], owner, email, han, cfg["viec"]["trang_thai"][0],
                   f'=IF(F{r}="","",F{r}-TODAY())', basis, topic, "" if han else "Chưa có hạn – cần xác nhận"])
        for c in range(1, len(COLS) + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = BOX
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=r, column=6).number_format = "DD/MM/YYYY"
        if owner == UNASSIGNED:
            ws.cell(row=r, column=4).font = Font(bold=True, color="B42318")
        r += 1
    last = max(r - 1, 4)
    dv = DataValidation(type="list", formula1='"' + ",".join(cfg["viec"]["trang_thai"]) + '"', allow_blank=False,
                        showErrorMessage=True, errorTitle="Trạng thái", error="Chọn trạng thái trong danh sách.")
    ws.add_data_validation(dv)
    dv.add(f"G4:G{last + 50}")
    rng = f"A4:K{last + 50}"
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'AND($F4<>"",$F4<TODAY(),$G4<>"Hoàn thành",$G4<>"Huỷ")'],
        fill=PatternFill("solid", fgColor="F8D7D3"), font=Font(color="9B1C1C", bold=True)))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'AND($F4<>"",$F4-TODAY()<={cfg["viec"]["canh_bao_truoc_ngay"]},$F4>=TODAY(),$G4<>"Hoàn thành",$G4<>"Huỷ")'],
        fill=PatternFill("solid", fgColor="FFF1C2")))
    ws.conditional_formatting.add(rng, FormulaRule(formula=['$G4="Hoàn thành"'], font=Font(color="777777", strike=True)))
    ws.freeze_panes = "D4"
    ws.auto_filter.ref = f"A3:K{last}"
    ws.sheet_view.zoomScale = 110
    return last


def _sheet_people(wb, rows, last):
    ws = wb.create_sheet("Theo người")
    ws.append(["Người phụ trách", "Email", "Tổng việc", "Hoàn thành", "Đang làm", "Quá hạn", "Hạn gần nhất"])
    for i, w in enumerate([24, 28, 10, 11, 10, 9, 14], 1):
        c = ws.cell(row=1, column=i)
        c.font, c.fill, c.border = Font(bold=True), HEAD, BOX
        ws.column_dimensions[get_column_letter(i)].width = w
    people = []
    for a, owner, email, *_ in rows:
        if owner not in [p[0] for p in people]:
            people.append((owner, email))
    R = f"'Việc cần làm'!$D$4:$D${last + 50}"
    G = f"'Việc cần làm'!$G$4:$G${last + 50}"
    F = f"'Việc cần làm'!$F$4:$F${last + 50}"
    for i, (owner, email) in enumerate(people, 2):
        ws.append([owner, email, f'=COUNTIF({R},A{i})', f'=COUNTIFS({R},A{i},{G},"Hoàn thành")',
                   f'=COUNTIFS({R},A{i},{G},"Đang làm")',
                   f'=COUNTIFS({R},A{i},{F},"<"&TODAY(),{G},"<>Hoàn thành",{G},"<>Huỷ")',
                   f'=IFERROR(MINIFS({F},{R},A{i}),"")'])
        ws.cell(row=i, column=7).number_format = "DD/MM/YYYY"
        for c in range(1, 8):
            ws.cell(row=i, column=c).border = BOX
        if owner == UNASSIGNED:
            ws.cell(row=i, column=1).font = Font(bold=True, color="B42318")
    ws.conditional_formatting.add(f"F2:F{len(people) + 1}", FormulaRule(formula=["F2>0"], font=Font(bold=True, color="B42318"),
                                                                       fill=PatternFill("solid", fgColor="F8D7D3")))
    ws.freeze_panes = "A2"


def build(bb, out: Path, cfg, only_owner: str | None = None):
    rows = list(_rows(bb))
    if only_owner:
        rows = [r for r in rows if r[1] == only_owner]
    wb = Workbook()
    meta = bb.get("meta", {})
    title = f"Việc cần làm – {meta.get('tieu_de', '')} (họp {meta.get('ngay_hop', '')})"
    if only_owner:
        title = f"Phiếu giao việc – {only_owner} – {meta.get('tieu_de', '')}"
    last = _sheet_tasks(wb.active, rows, cfg, title)
    if not only_owner:
        _sheet_people(wb, rows, last)
    wb.save(out)
    return out
