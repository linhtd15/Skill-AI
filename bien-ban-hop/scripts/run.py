"""Agent biên bản họp – điểm vào dòng lệnh.

  run.py chuan-bi <file> [--nguoi DS] [--ngay-hop YYYY-MM-DD] [--gio-bat-dau HH:MM] [--so-nguoi N] [--ra THU_MUC]
  run.py kiem-chung <thu_muc_lam_viec>
  run.py xuat <thu_muc_lam_viec> [--mat-khau MK] [--khong-mo]
  run.py email <thu_muc_lam_viec> [--link URL] [--tu "Tên <email>"]
  run.py nhan-dien-lai <thu_muc_lam_viec> [--nguoi DS]
  run.py dat-ten <thu_muc_lam_viec> S2 "Họ Tên"
  run.py goi-gmail <thu_muc_lam_viec> [--thu-ve EMAIL]   # gói gửi qua Gmail connector (base64)
  run.py da-gui <thu_muc_lam_viec> --trang-thai DA_GUI|NHAP|DA_GUI_THU [--ghi-chu ...]
  run.py tu-kiem-tra [--day-du]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import BBError, fmt_t, load_config, open_file, read_json, slug, write_json  # noqa: E402


def log(*a):
    print(*a, flush=True)


def parse_people(arg: str | None):
    if not arg:
        return []
    p = Path(arg)
    out = []
    if p.exists():
        if p.suffix.lower() == ".json":
            data = read_json(p)
            return [{"ten": x["ten"], "email": x.get("email") or None, "vai_tro": x.get("vai_tro", "")} for x in data]
        text = p.read_text(encoding="utf-8-sig")
        rows = list(csv.reader(text.splitlines()))
        if rows and rows[0] and rows[0][0].strip().lower() in ("ten", "tên", "họ tên", "ho ten", "name"):
            rows = rows[1:]
        for r in rows:
            if r and r[0].strip():
                out.append({"ten": r[0].strip(), "email": (r[1].strip() if len(r) > 1 and r[1].strip() else None),
                            "vai_tro": r[2].strip() if len(r) > 2 else ""})
        return out
    for item in re.split(r"[;\n]", arg):
        item = item.strip()
        if not item:
            continue
        m = re.match(r"(.+?)\s*<([^>]+)>", item)
        out.append({"ten": m[1].strip(), "email": m[2].strip(), "vai_tro": ""} if m else {"ten": item, "email": None, "vai_tro": ""})
    return out


def write_ban_ghi(work, tr, speakers):
    names = {k: v["ten"] for k, v in speakers.items()}
    lines = [f"# Bản ghi: {tr['nguon']} – {fmt_t(tr['thoi_luong'])} – định dạng dòng: #id [mm:ss] Người nói (cụm): lời", ""]
    for s in tr["segments"]:
        who = names.get(s.get("speaker"), s.get("speaker_label") or "Chưa xác định")
        flag = "  ⚠ĐÃ LỌC" if s.get("flag") else ""
        lines.append(f"#{s['id']} [{fmt_t(s.get('start'))}] {who} ({s.get('speaker', '-')}): {s['text']}{flag}")
    (work / "ban-ghi.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    from common import contains
    kw = load_config()["kiem_chung"]["tu_khoa_bat_buoc"]
    cand = [l for s, l in zip(tr["segments"], lines[2:]) if not s.get("flag") and any(contains(s["text"], k) for k in kw)]
    (work / "cau-tu-khoa.txt").write_text(
        "Các câu chứa từ khoá – PHẢI đưa vào biên bản hoặc ghi vào 'bo_qua' kèm lý do:\n" + "\n".join(cand) + "\n",
        encoding="utf-8")
    return lines, cand


def print_speakers(speakers):
    for k, v in speakers.items():
        cc = ", ".join(sorted({c['loai'] for c in v['can_cu']})) or "không có căn cứ"
        log(f"   {k}: {v['ten']}  [{v['do_tin']}; {cc}; nói {fmt_t(v['thoi_luong_noi'])}]")
    unk = [k for k, v in speakers.items() if v["ten"] == "Chưa xác định" or v.get("do_tin") == "thap"]
    if unk:
        log(f"⚠ Cần hỏi người dùng tên của: {', '.join(unk)}")


def cmd_reid(a):
    """Nhận diện lại người nói (ví dụ sau khi bổ sung danh sách người tham gia) – không phiên âm lại."""
    import speakers as spk_mod
    work = Path(a.work).resolve()
    tr = read_json(work / "transcript.json")
    people = parse_people(a.nguoi) if a.nguoi else read_json(work / "nguoi-tham-gia.json")
    write_json(work / "nguoi-tham-gia.json", people)
    if tr["loai"] == "transcript":
        speakers = spk_mod.from_labels(tr["segments"], people)
    else:
        speakers = spk_mod.assign_names(tr["segments"], people, Path(tr["duong_dan"]) if tr["loai"] == "video" else None,
                                        work, load_config(), log)
    write_json(work / "transcript.json", tr)
    write_json(work / "speakers.json", speakers)
    write_ban_ghi(work, tr, speakers)
    print_speakers(speakers)
    return 0


def cmd_prepare(a):
    import ingest
    import speakers as spk_mod
    cfg = load_config()
    src = Path(a.file).resolve()
    kind = ingest.detect(src)
    base = (Path(a.ra) if a.ra else Path.cwd() / cfg["thu_muc_dau_ra"]).resolve()
    work = base / f"{a.ngay_hop or dt.date.today().isoformat()}-{slug(src.stem)}"
    work.mkdir(parents=True, exist_ok=True)
    people = parse_people(a.nguoi)
    log(f"▶ Chuẩn bị: {src.name} ({kind}) → {work}")
    t0 = time.time()
    filtered = []
    if kind == "transcript":
        segs = ingest.load_transcript(src)
        dur = max((s.get("end") or 0) for s in segs)
    else:
        from common import probe
        dur = probe(src)["duration"]
        segs, filtered = ingest.transcribe_media(src, work, cfg, [p["ten"] for p in people], log, dur)
        if not [s for s in segs if not s.get("flag")]:
            raise BBError("Không nhận được lời nói nào trong bản ghi (có thể chỉ có nhạc/tạp âm).")
    for i, s in enumerate(segs, 1):
        s["id"] = i
    if kind == "transcript":
        speakers = spk_mod.from_labels(segs, people)
        if not speakers:
            log("  • Transcript không có tên người nói → người nói 'Chưa xác định'")
    else:
        spk_mod.diarize(work / "audio.wav", segs, cfg, a.so_nguoi or (len(people) or None), log)
        speakers = spk_mod.assign_names(segs, people, src if kind == "video" else None, work, cfg, log)
    tr = {"nguon": src.name, "duong_dan": str(src), "loai": kind, "thoi_luong": dur, "segments": segs, "ao_giac_da_loc": filtered}
    write_json(work / "transcript.json", tr)
    write_json(work / "speakers.json", speakers)
    write_json(work / "nguoi-tham-gia.json", people)
    _, cand = write_ban_ghi(work, tr, speakers)
    skeleton = {
        "meta": {"tieu_de": "", "muc_dich": "", "ngay_hop": a.ngay_hop, "gio_bat_dau": a.gio_bat_dau, "gio_ket_thuc": None,
                 "dia_diem": None, "hinh_thuc": None, "co_quan": cfg.get("co_quan_mac_dinh") or None, "so": None,
                 "dia_danh": cfg.get("dia_danh_mac_dinh") or None, "chu_tri": None, "thu_ky": None, "so_ban": None, "nguon": src.name},
        "nguoi_tham_gia": people or [{"ten": v["ten"], "email": None, "vai_tro": "", "speaker": k} for k, v in speakers.items()],
        "tom_tat": [], "chu_de": [], "quyet_dinh": [], "hanh_dong": [], "van_de_mo": [], "bo_qua": [], "can_lam_ro": []}
    if not (work / "bien-ban.json").exists():
        write_json(work / "bien-ban.khung.json", skeleton)
    log(f"✔ Xong sau {time.time() - t0:.0f}s: {len(segs)} đoạn, {len(speakers)} người nói, {len(filtered)} vùng ảo giác đã lọc, {len(cand)} câu chứa từ khoá.")
    print_speakers(speakers)
    log(f"THU_MUC_LAM_VIEC={work}")
    return work


def cmd_name(a):
    """Người dùng xác nhận tên cho một cụm giọng."""
    work = Path(a.work).resolve()
    spk = read_json(work / "speakers.json")
    if a.cum not in spk:
        raise BBError(f"Không có cụm giọng {a.cum}. Các cụm: {', '.join(spk)}")
    spk[a.cum]["ten"] = a.ten
    spk[a.cum]["do_tin"] = "cao"
    spk[a.cum]["can_cu"] = [{"loai": "nguoi_dung_xac_nhan", "ten": a.ten, "seg": None,
                             "trich": "Người dùng xác nhận"}] + [c for c in spk[a.cum].get("can_cu", []) if c.get("ten") == a.ten]
    write_json(work / "speakers.json", spk)
    write_ban_ghi(work, read_json(work / "transcript.json"), spk)
    log(f"✔ {a.cum} = {a.ten} (căn cứ: người dùng xác nhận)")
    return 0


def cmd_verify(a):
    import verify
    work = Path(a.work).resolve()
    rep = verify.run(work, log)
    log((work / "kiem-chung.md").read_text(encoding="utf-8"))
    return 0 if rep["trang_thai"] == "DAT" else 2


def cmd_export(a):
    import build_emails
    import build_excel
    import build_pdf
    import build_reader
    import frames
    import verify
    cfg = load_config()
    work = Path(a.work).resolve()
    rep = verify.run(work, log)
    if rep["trang_thai"] != "DAT":
        log((work / "kiem-chung.md").read_text(encoding="utf-8"))
        log("⛔ ĐÃ CHẶN XUẤT BẢN – sửa bien-ban.json theo danh sách lỗi rồi chạy lại.")
        return 2
    bb = verify.require_verified(work)
    tr = read_json(work / "transcript.json")
    spk = read_json(work / "speakers.json")
    wave = None
    if tr["loai"] == "video":
        log("▶ Chụp ảnh dẫn chứng từ video")
        images = frames.video_frames(Path(tr["duong_dan"]), bb, work, log)
    elif tr["loai"] == "audio":
        log("▶ Tạo hình minh hoạ + dạng sóng (chỉ có âm thanh)")
        images, wave = frames.audio_illustrations(work / "audio.wav", bb, work, tr["thoi_luong"])
    else:
        images = {}
    images = {k: v for k, v in images.items() if v}
    log("▶ Dàn trang bản in PDF")
    pdf = work / "bien-ban.pdf"
    info = build_pdf.build(bb, rep, spk, images, pdf, cfg)
    if info.get("vuot_trang"):
        log(f"⚠ Bản in vẫn {info['trang']} trang > {cfg['ban_in']['so_trang_toi_da']} ở mức thu gọn tối đa – cần rút gọn nội dung bien-ban.json.")
        return 3
    log(f"   {info['trang']} trang (mức thu gọn {info['muc_thu_gon']}, trang cuối lấp {int(info['trang_cuoi_lap_day'] * 100)}%)")
    log("▶ Bản trình đọc web")
    html = work / "bien-ban-doc.html"
    build_reader.build(bb, rep, spk, images, tr, wave, info, html, cfg, a.mat_khau)
    log("▶ Excel Action Items")
    xlsx = work / "viec-can-lam.xlsx"
    build_excel.build(bb, xlsx, cfg)
    log("▶ Email giao việc (chưa gửi)")
    idx, missing = build_emails.build(bb, work, cfg, a.link)
    write_json(work / "ket-qua.json", {"pdf": str(pdf), "html": str(html), "excel": str(xlsx), "pdf_info": info,
                                       "email": str(work / "email" / "danh-sach-email.json"), "thieu_email": missing,
                                       "khoa_mat_khau": bool(a.mat_khau)})
    log(f"✔ Bản in: {pdf}\n✔ Bản trình đọc: {html}{' (đã khoá mật khẩu)' if a.mat_khau else ''}\n✔ Excel: {xlsx}\n"
        f"✔ Email: {len(idx)} người – xem trước: {work / 'email' / 'xem-truoc-email.md'}")
    if missing:
        log(f"⚠ THIẾU EMAIL: {', '.join(missing)} – phải hỏi người dùng bổ sung trước khi gửi.")
    if not a.khong_mo:
        open_file(pdf)
        open_file(html)
    return 0


def cmd_email(a):
    import build_emails
    import verify
    work = Path(a.work).resolve()
    bb = verify.require_verified(work)
    idx, missing = build_emails.build(bb, work, load_config(), a.link, a.tu)
    log(f"✔ {len(idx)} email (chưa gửi). Xem trước: {work / 'email' / 'xem-truoc-email.md'}")
    if missing:
        log(f"⚠ THIẾU EMAIL: {', '.join(missing)}")
    return 0


MIME = {".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".ics": "text/calendar",
        ".pdf": "application/pdf"}


def cmd_gmail(a):
    """Tạo email/gui-gmail.json: mỗi thư gồm to, subject, body, attachments (base64) để Claude gọi Gmail connector.
    --thu-ve: gửi thử tất cả về một địa chỉ (tiêu đề thêm '[THỬ – cho <tên>]')."""
    import base64
    work = Path(a.work).resolve()
    d = read_json(work / "email" / "danh-sach-email.json")
    out = []
    for e in d["email"]:
        to = a.thu_ve or e["email"]
        if not to:
            continue
        atts = []
        for f in e["dinh_kem"]:
            fp = Path(f)
            if not fp.is_absolute() or not fp.exists():
                fp = work / "email" / fp.name
            atts.append({"filename": fp.name, "mimeType": MIME.get(fp.suffix.lower(), "application/octet-stream"),
                         "content": base64.b64encode(fp.read_bytes()).decode()})
        subj = (f"[THỬ – cho {e['nguoi']}] " if a.thu_ve else "") + e["tieu_de"]
        out.append({"nguoi": e["nguoi"], "to": [to], "subject": subj, "body": e["noi_dung"], "attachments": atts})
    write_json(work / "email" / "gui-gmail.json", out)
    skipped = [e["nguoi"] for e in d["email"] if not (a.thu_ve or e["email"])]
    log(f"✔ {len(out)} thư sẵn sàng: {work / 'email' / 'gui-gmail.json'}")
    if skipped:
        log(f"⚠ Bỏ qua vì thiếu email: {', '.join(skipped)}")
    return 0


def cmd_sent(a):
    from datetime import datetime
    work = Path(a.work).resolve()
    p = work / "email" / "danh-sach-email.json"
    d = read_json(p)
    d["trang_thai"] = a.trang_thai
    d.setdefault("lich_su", []).append({"luc": datetime.now().isoformat(timespec="minutes"), "trang_thai": a.trang_thai,
                                        "ghi_chu": a.ghi_chu or ""})
    write_json(p, d)
    log(f"✔ Ghi nhận trạng thái email: {a.trang_thai}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Agent biên bản họp")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("chuan-bi")
    p.add_argument("file")
    p.add_argument("--nguoi")
    p.add_argument("--ngay-hop")
    p.add_argument("--gio-bat-dau")
    p.add_argument("--so-nguoi", type=int)
    p.add_argument("--ra")
    p = sub.add_parser("nhan-dien-lai")
    p.add_argument("work")
    p.add_argument("--nguoi")
    p = sub.add_parser("dat-ten")
    p.add_argument("work")
    p.add_argument("cum")
    p.add_argument("ten")
    p = sub.add_parser("kiem-chung")
    p.add_argument("work")
    p = sub.add_parser("xuat")
    p.add_argument("work")
    p.add_argument("--mat-khau")
    p.add_argument("--link")
    p.add_argument("--khong-mo", action="store_true")
    p = sub.add_parser("email")
    p.add_argument("work")
    p.add_argument("--link")
    p.add_argument("--tu")
    p = sub.add_parser("goi-gmail")
    p.add_argument("work")
    p.add_argument("--thu-ve")
    p = sub.add_parser("da-gui")
    p.add_argument("work")
    p.add_argument("--trang-thai", required=True, choices=["DA_GUI", "NHAP", "DA_GUI_THU", "CHUA_GUI"])
    p.add_argument("--ghi-chu")
    p = sub.add_parser("tu-kiem-tra")
    p.add_argument("--day-du", action="store_true", help="thêm phiên âm MP3 (chậm)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "chuan-bi":
            cmd_prepare(a)
            return 0
        if a.cmd == "nhan-dien-lai":
            return cmd_reid(a)
        if a.cmd == "dat-ten":
            return cmd_name(a)
        if a.cmd == "kiem-chung":
            return cmd_verify(a)
        if a.cmd == "xuat":
            return cmd_export(a)
        if a.cmd == "email":
            return cmd_email(a)
        if a.cmd == "goi-gmail":
            return cmd_gmail(a)
        if a.cmd == "da-gui":
            return cmd_sent(a)
        if a.cmd == "tu-kiem-tra":
            import selftest
            return selftest.main(full=a.day_du)
    except BBError as e:
        log(f"⛔ LỖI: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
