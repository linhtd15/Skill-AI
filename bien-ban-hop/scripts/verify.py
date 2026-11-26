"""Bước 4: KIỂM CHỨNG tự động. Trả về trạng thái DAT / CHAN.

CHẶN xuất bản khi:
  1. Câu trích dẫn không tìm thấy trong bản ghi (hoặc là câu ảo giác đã bị lọc).
  2. Người phụ trách không được nêu tên trong dẫn chứng và cũng không tự nhận việc.
  3. Thời hạn không được nói trong cuộc họp / ngày tương đối mà không biết ngày họp / quy đổi sai.
  4. Còn câu chứa từ khoá (chốt, thống nhất, giao, phụ trách, em sẽ, trước ngày…) chưa được đưa vào
     biên bản và cũng không được ghi lý do bỏ qua (mục "bo_qua").
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
from pathlib import Path

from common import (BBError, contains, fmt_t, load_config, norm, norm_loose, read_json, sha256_file,
                    write_json)
from ingest import is_hallucination

WD = {"hai": 0, "2": 0, "ba": 1, "3": 1, "tư": 2, "tu": 2, "4": 2, "năm": 3, "5": 3,
      "sáu": 4, "6": 4, "bảy": 5, "7": 5}


def resolve_deadline(phrase: str, meeting: dt.date | None):
    """→ (date|None, kieu) với kieu ∈ {tuyet_doi, tuong_doi, can_ngay_hop, mo_ho, khong_hieu}."""
    p = norm(phrase)
    m = re.search(r"ngày (\d{1,2}) tháng (\d{1,2})(?: năm (\d{4}))?", p) or \
        re.search(r"(?<!\d)(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{2,4}))?(?!\d)", p)
    if m:
        d, mo = int(m[1]), int(m[2])
        y = int(m[3]) if m[3] else None
        if y and y < 100:
            y += 2000
        if y is None:
            if meeting is None:
                return None, "can_ngay_hop"
            y = meeting.year + (1 if mo < meeting.month - 6 else 0)
        try:
            return dt.date(y, mo, d), "tuyet_doi"
        except ValueError:
            return None, "khong_hieu"
    rel = re.search(r"(ngày mai|ngày kia|thứ (hai|ba|tư|năm|sáu|bảy|[2-7])|chủ nhật|cuối tháng|cuối tuần|tuần sau|tuần tới|tháng sau)", p)
    if not rel:
        return None, "khong_hieu"
    if meeting is None:
        return None, "can_ngay_hop"
    if "ngày mai" in p:
        return meeting + dt.timedelta(days=1), "tuong_doi"
    if "ngày kia" in p:
        return meeting + dt.timedelta(days=2), "tuong_doi"
    if "cuối tháng" in p and "sau" not in p:
        return dt.date(meeting.year, meeting.month, calendar.monthrange(meeting.year, meeting.month)[1]), "tuong_doi"
    mw = re.search(r"thứ (hai|ba|tư|năm|sáu|bảy|[2-7])|chủ nhật", p)
    if mw:
        wd = 6 if mw[0] == "chủ nhật" else WD[mw[1]]
        monday = meeting - dt.timedelta(days=meeting.weekday())
        if re.search(r"tuần (sau|tới)", p):
            return monday + dt.timedelta(days=7 + wd), "tuong_doi"
        if "tuần này" in p:
            return monday + dt.timedelta(days=wd), "tuong_doi"
        d = monday + dt.timedelta(days=wd)
        if d <= meeting:
            d += dt.timedelta(days=7)
        return d, "tuong_doi"
    return None, "mo_ho"


def _given(name: str) -> str:
    t = norm_loose(name).split()
    return t[-1] if t else ""


def run(work: Path, log=print) -> dict:
    cfg = load_config()
    kc = cfg["kiem_chung"]
    tr = read_json(work / "transcript.json")
    segs = {s["id"]: s for s in tr["segments"]}
    spk_names = {k: v["ten"] for k, v in read_json(work / "speakers.json").items()} if (work / "speakers.json").exists() else {}
    bb_path = work / "bien-ban.json"
    if not bb_path.exists():
        raise BBError("Chưa có bien-ban.json trong thư mục làm việc (Claude cần viết dữ liệu biên bản trước).")
    bb = read_json(bb_path)
    meta = bb.get("meta", {})
    meeting = dt.date.fromisoformat(meta["ngay_hop"]) if meta.get("ngay_hop") else None
    errors, warns = [], []
    used = set()
    n_q = n_ok = 0

    def seg_name(s):
        return spk_names.get(s.get("speaker"), s.get("speaker_label") or s.get("speaker") or "Chưa xác định")

    def check_quote(q, where):
        nonlocal n_q, n_ok
        n_q += 1
        text = (q.get("text") or "").strip()
        if not text:
            errors.append(f"{where}: trích dẫn rỗng.")
            return False
        if is_hallucination(text, cfg):
            errors.append(f"{where}: “{text}” là câu ảo giác của Whisper, không được dùng làm dẫn chứng.")
            return False
        sid = q.get("seg")
        cand = []
        if sid in segs:
            cand = [sid]
        else:
            cand = [i for i, s in segs.items() if contains(s["text"], text)]
            if not cand:  # câu vắt qua 2 đoạn liền nhau
                ids = sorted(segs)
                cand = [a for a, b in zip(ids, ids[1:]) if contains(segs[a]["text"] + " " + segs[b]["text"], text)]
        ok_sid = None
        for c in cand:
            s = segs[c]
            nxt = segs.get(c + 1, {"text": ""})
            if contains(s["text"], text) or contains(s["text"] + " " + nxt["text"], text):
                ok_sid = c
                break
        if ok_sid is None:
            errors.append(f"{where}: KHÔNG tìm thấy câu trích “{text}” trong bản ghi"
                          + (f" (đoạn #{sid})" if sid else "") + ".")
            return False
        s = segs[ok_sid]
        if s.get("flag") == "ao_giac":
            errors.append(f"{where}: đoạn #{ok_sid} là tạp âm/ảo giác đã lọc, không dùng làm dẫn chứng.")
            return False
        if q.get("t") is not None and s.get("start") is not None and abs(float(q["t"]) - s["start"]) > kc["sai_lech_thoi_gian_giay"] + (s["end"] - s["start"]):
            errors.append(f"{where}: mốc thời gian {fmt_t(q['t'])} không khớp đoạn #{ok_sid} ({fmt_t(s['start'])}).")
            return False
        q["seg"] = ok_sid
        q["t"] = s.get("start")
        q["speaker"] = s.get("speaker")
        q["nguoi"] = seg_name(s)
        used.add(ok_sid)
        if contains(s["text"] + " " + segs.get(ok_sid + 1, {"text": ""})["text"], text) and not contains(s["text"], text):
            used.add(ok_sid + 1)
        n_ok += 1
        return True

    # ---- chủ đề / diễn biến
    topics = bb.get("chu_de", [])
    if not (5 <= len(topics) <= 10):
        warns.append(f"Diễn biến có {len(topics)} mục (khuyến nghị 5–10).")
    for t in topics:
        qs = t.get("trich_dan", [])
        if not qs:
            errors.append(f"Chủ đề {t.get('id')}: không có trích dẫn nguyên văn.")
        for q in qs:
            check_quote(q, f"Chủ đề {t.get('id')}")
        if qs and not any(q.get("chinh") for q in qs):
            qs[0]["chinh"] = True
        if t.get("bat_dau") is None and qs:
            t["bat_dau"] = min(q["t"] for q in qs if q.get("t") is not None) if any(q.get("t") is not None for q in qs) else None
        if len((t.get("tom_tat") or "").split()) > 40:
            warns.append(f"Chủ đề {t.get('id')}: tóm tắt dài hơn 40 từ.")
    for i, x in enumerate(bb.get("tom_tat", [])):
        if len(x.split()) > 25:
            warns.append(f"Tóm tắt ý {i + 1} dài hơn 25 từ.")
    if not (4 <= len(bb.get("tom_tat", [])) <= 6):
        warns.append("Tóm tắt nên có 4–6 ý.")

    # ---- quyết định
    for d in bb.get("quyet_dinh", []):
        if not d.get("trich_dan"):
            errors.append(f"Quyết định {d.get('id')}: thiếu trích dẫn chứng minh đã được chốt.")
        for q in d.get("trich_dan", []):
            check_quote(q, f"Quyết định {d.get('id')}")

    # ---- việc
    participants = bb.get("nguoi_tham_gia", [])
    names = {p["ten"] for p in participants} | {v for v in spk_names.values() if v != "Chưa xác định"}
    for a in bb.get("hanh_dong", []):
        aid = a.get("id")
        qs = a.get("trich_dan", [])
        if not qs:
            errors.append(f"Việc {aid}: thiếu trích dẫn căn cứ.")
        valid = [q for q in qs if check_quote(q, f"Việc {aid}")]
        owner = a.get("phu_trach")
        if owner:
            if owner not in names:
                errors.append(f"Việc {aid}: người phụ trách “{owner}” không có trong danh sách người tham gia/người nói.")
            basis = None
            for q in valid:
                if q.get("nguoi") == owner and any(contains(q["text"], w) for w in kc["tu_tu_nhan_viec"]):
                    basis = "tự nhận việc"
                    break
            if not basis:
                g, full = _given(owner), norm_loose(owner)
                for q in valid:
                    tq = norm_loose(q["text"])
                    if full in tq or (g and re.search(rf"\b{re.escape(g)}\b", tq)):
                        basis = f"được nêu tên bởi {q['nguoi']}"
                        break
            if not basis:
                errors.append(f"Việc {aid}: “{owner}” không được nêu tên trong dẫn chứng và cũng không tự nhận việc.")
            a["can_cu_phu_trach"] = basis
        else:
            warns.append(f"Việc {aid}: chưa xác định người phụ trách (sẽ tô đỏ, cần hỏi lại).")
        if a.get("han"):
            hg = a.get("han_goc")
            if not hg:
                errors.append(f"Việc {aid}: có thời hạn {a['han']} nhưng thiếu 'han_goc' (cụm từ nói trong họp).")
            elif not any(contains(q["text"], hg) for q in valid):
                errors.append(f"Việc {aid}: thời hạn “{hg}” không xuất hiện trong câu trích dẫn → không được nói trong cuộc họp.")
            else:
                d, kind = resolve_deadline(hg, meeting)
                if kind == "can_ngay_hop":
                    errors.append(f"Việc {aid}: “{hg}” là ngày tương đối/thiếu năm nhưng chưa biết ngày họp (meta.ngay_hop).")
                elif d is None:
                    errors.append(f"Việc {aid}: không quy đổi chắc chắn được “{hg}” thành ngày. Để trống 'han' và đưa vào mục cần làm rõ.")
                elif d.isoformat() != a["han"]:
                    errors.append(f"Việc {aid}: “{hg}” (họp ngày {meeting}) = {d.isoformat()}, khác 'han' = {a['han']}.")
                a["han_kieu"] = kind
        elif a.get("han_goc"):
            warns.append(f"Việc {aid}: có nói thời hạn “{a['han_goc']}” nhưng chưa quy đổi thành ngày.")

    # ---- vấn đề mở
    for v in bb.get("van_de_mo", []):
        for q in v.get("trich_dan", []):
            check_quote(q, f"Vấn đề mở {v.get('id')}")

    # ---- chống bỏ sót: câu có từ khoá
    skipped = {}
    for b in bb.get("bo_qua", []):
        if not (b.get("ly_do") or "").strip():
            errors.append(f"bo_qua đoạn #{b.get('seg')}: thiếu lý do bỏ qua.")
        else:
            skipped[b.get("seg")] = b["ly_do"]
    missing = []
    for sid, s in sorted(segs.items()):
        if s.get("flag"):
            continue
        hit = [k for k in kc["tu_khoa_bat_buoc"] if contains(s["text"], k)]
        if hit and sid not in used and sid not in skipped:
            missing.append(f"#{sid} [{fmt_t(s.get('start'))}] {seg_name(s)}: “{s['text']}” (từ khoá: {', '.join(hit)})")
    for m in missing:
        errors.append("Có thể BỎ SÓT – câu chứa từ khoá chưa đưa vào biên bản và chưa ghi lý do bỏ qua: " + m)

    status = "DAT" if not errors else "CHAN"
    rep = {"trang_thai": status, "loi": errors, "canh_bao": warns,
           "thong_ke": {"trich_dan": n_q, "khop": n_ok, "cau_tu_khoa_bo_qua": len(skipped),
                        "quyet_dinh": len(bb.get("quyet_dinh", [])), "viec": len(bb.get("hanh_dong", [])),
                        "van_de_mo": len(bb.get("van_de_mo", []))},
           "bien_ban_sha256": sha256_file(bb_path)}
    write_json(work / "kiem-chung.json", rep)
    write_json(work / "bien-ban.verified.json", bb)
    md = [f"# Kết quả kiểm chứng: {'ĐẠT' if status == 'DAT' else 'BỊ CHẶN'}", "",
          f"- Trích dẫn khớp bản ghi: {n_ok}/{n_q}", ""]
    if errors:
        md += ["## Lỗi chặn xuất bản", *[f"- {e}" for e in errors], ""]
    if warns:
        md += ["## Cảnh báo", *[f"- {w}" for w in warns], ""]
    (work / "kiem-chung.md").write_text("\n".join(md), encoding="utf-8")
    return rep


def require_verified(work: Path) -> dict:
    p = work / "kiem-chung.json"
    if not p.exists():
        raise BBError("Chưa chạy kiểm chứng. Không xuất bản.")
    rep = read_json(p)
    if rep["trang_thai"] != "DAT":
        raise BBError("Kiểm chứng KHÔNG ĐẠT – đã chặn xuất bản. Xem kiem-chung.md.")
    if rep["bien_ban_sha256"] != sha256_file(work / "bien-ban.json"):
        raise BBError("bien-ban.json đã bị sửa sau khi kiểm chứng. Hãy chạy kiểm chứng lại.")
    return read_json(work / "bien-ban.verified.json")
