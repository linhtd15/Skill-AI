"""Email giao việc riêng cho từng người: .eml (gửi tay) + phiếu giao việc .xlsx + lịch nhắc hạn .ics.

KHÔNG gửi. Việc gửi do Claude thực hiện qua Gmail connector CHỈ sau khi người dùng phê duyệt.
"""
from __future__ import annotations

import datetime as dt
import uuid
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

import build_excel
from common import clock, fmt_t, slug, vn_date, write_json

UNASSIGNED = "Chưa xác định"


def ics_for(person, tasks, meta, cfg):
    now = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//BienBanHop//VI", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    for a in tasks:
        if not a.get("han"):
            continue
        d = dt.date.fromisoformat(a["han"])
        desc = f"Việc {a['id']} giao trong cuộc họp \"{meta.get('tieu_de', '')}\" ngày {vn_date(meta.get('ngay_hop'))}."
        lines += ["BEGIN:VEVENT", f"UID:{uuid.uuid4()}@bienbanhop", f"DTSTAMP:{now}",
                  f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + dt.timedelta(days=1):%Y%m%d}",
                  f"SUMMARY:Hạn: {a['cong_viec'][:120]}".replace(",", "\\,"),
                  f"DESCRIPTION:{desc}".replace(",", "\\,"),
                  "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:Nhắc hạn: {a['cong_viec'][:80]}".replace(",", "\\,"),
                  f"TRIGGER:-P{cfg['viec']['nhac_truoc_ngay']}D", "END:VALARM", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def body_for(person, tasks, meta, link, cfg):
    L = [f"Chào anh/chị {person.split()[-1]},", "",
         f"Theo cuộc họp “{meta.get('tieu_de', '')}” ngày {vn_date(meta.get('ngay_hop'))}"
         f"{' do ' + meta['chu_tri'] + ' chủ trì' if meta.get('chu_tri') else ''}, anh/chị được giao các việc sau:", ""]
    for i, a in enumerate(tasks, 1):
        q = (a.get("trich_dan") or [{}])[0]
        tm = clock(meta, q.get("t"))
        L += [f"{i}. [{a['id']}] {a['cong_viec']}",
              f"   - Thời hạn: {vn_date(a['han']) if a.get('han') else 'chưa chốt – đề nghị anh/chị xác nhận'}",
              f"   - Căn cứ: {q.get('nguoi', '')} nói lúc {fmt_t(q.get('t'))}{' (' + tm + ')' if tm else ''}: “{q.get('text', '')}”", ""]
    if any(a.get("han") for a in tasks):
        L += ["Đính kèm: phiếu giao việc (Excel, có cột trạng thái) và lịch nhắc hạn (.ics – mở để thêm vào lịch).", ""]
    else:
        L += ["Đính kèm: phiếu giao việc (Excel, có cột trạng thái).", ""]
    if link:
        L += [f"Xem toàn bộ biên bản: {link}", ""]
    L += ["Nếu nội dung, người phụ trách hoặc thời hạn chưa đúng, anh/chị vui lòng phản hồi email này để điều chỉnh.", "",
          "Trân trọng,", meta.get("thu_ky") or cfg["email"]["ky_ten"]]
    return "\n".join(L)


def build(bb, work: Path, cfg, link: str | None = None, sender: str | None = None):
    out = work / "email"
    out.mkdir(exist_ok=True)
    meta = bb.get("meta", {})
    people = {p["ten"]: p for p in bb.get("nguoi_tham_gia", [])}
    by_owner = {}
    for a in bb.get("hanh_dong", []):
        if a.get("phu_trach"):
            by_owner.setdefault(a["phu_trach"], []).append(a)
    index, missing, preview = [], [], ["# Xem trước email giao việc (CHƯA GỬI)", ""]
    subj = cfg["email"]["tieu_de"].format(tieu_de=meta.get("tieu_de", ""), ngay=vn_date(meta.get("ngay_hop")))
    for person, tasks in by_owner.items():
        email = (people.get(person) or {}).get("email")
        s = slug(person)
        xlsx = out / f"phieu-giao-viec-{s}.xlsx"
        build_excel.build(bb, xlsx, cfg, only_owner=person)
        ics = out / f"lich-nhac-han-{s}.ics"
        has_due = any(a.get("han") for a in tasks)
        if has_due:
            ics.write_bytes(ics_for(person, tasks, meta, cfg).encode("utf-8"))  # giữ nguyên CRLF theo chuẩn iCalendar
        else:
            ics.unlink(missing_ok=True)
        body = body_for(person, tasks, meta, link, cfg)
        item = {"nguoi": person, "email": email, "tieu_de": subj, "noi_dung": body,
                "dinh_kem": [str(xlsx)] + ([str(ics)] if has_due else []), "eml": None, "viec": [a["id"] for a in tasks]}
        if not email:
            missing.append(person)
        else:
            m = EmailMessage()
            m["To"] = formataddr((person, email))
            if sender:
                m["From"] = sender
            m["Subject"] = subj
            m.set_content(body)
            m.add_attachment(xlsx.read_bytes(), maintype="application",
                             subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=xlsx.name)
            if has_due:
                m.add_attachment(ics.read_bytes(), maintype="text", subtype="calendar", filename=ics.name)
            eml = out / f"giao-viec-{s}.eml"
            eml.write_bytes(bytes(m))
            item["eml"] = str(eml)
        index.append(item)
        preview += [f"## {person} – {email or '⚠ THIẾU EMAIL'}", f"**Tiêu đề:** {subj}", "",
                    "```", body, "```", f"Đính kèm: {xlsx.name}" + (f", {ics.name}" if has_due else " (không có lịch nhắc vì việc chưa có hạn)"), ""]
    unassigned = [a["id"] for a in bb.get("hanh_dong", []) if not a.get("phu_trach")]
    if unassigned:
        preview += [f"> Việc chưa có người phụ trách (không tạo email): {', '.join(unassigned)}", ""]
    if missing:
        preview += [f"> ⚠ Thiếu địa chỉ email: {', '.join(missing)} – cần người dùng bổ sung trước khi gửi.", ""]
    write_json(out / "danh-sach-email.json", {"trang_thai": "CHUA_GUI", "thieu_email": missing, "email": index})
    (out / "xem-truoc-email.md").write_text("\n".join(preview), encoding="utf-8")
    return index, missing
