"""Bộ tự kiểm thử: dữ liệu mẫu (transcript .txt/.vtt/.docx, MP3 khi --day-du) + tình huống lỗi.
Kết quả ghi vào tests/ket-qua-kiem-thu.md.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import time
import traceback
from pathlib import Path

from common import SKILL_DIR, BBError, load_config, read_json, write_json

T = SKILL_DIR / "tests"
DATA = T / "du-lieu-mau"
FIX = T / "fixtures" / "bien-ban-transcript.json"
OUT = T / "_out"


def run_cli(*args):
    import run
    return run.main([str(a) for a in args])


def prepare(src, name, *extra):
    import run
    a = run.argparse.Namespace(file=str(src), nguoi=str(DATA / "nguoi-tham-gia.csv"), ngay_hop="2026-11-19",
                               gio_bat_dau="09:00", so_nguoi=None, ra=str(OUT / name))
    for k, v in extra:
        setattr(a, k, v)
    return run.cmd_prepare(a)


def verify_with(work, bb):
    import verify
    write_json(work / "bien-ban.json", bb)
    return verify.run(work, lambda *a: None)


def main(full=False):
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    rows = []
    gold = read_json(FIX)
    ctx = {}

    def case(peas, name, fn):
        t0 = time.time()
        try:
            msg = fn() or ""
            rows.append((peas, name, "ĐẠT", msg, time.time() - t0))
        except AssertionError as e:
            rows.append((peas, name, "KHÔNG ĐẠT", str(e), time.time() - t0))
        except Exception as e:  # noqa: BLE001
            rows.append((peas, name, "LỖI", f"{e.__class__.__name__}: {e}", time.time() - t0))
            traceback.print_exc()

    # ---------------- S: đầu vào hợp lệ
    def t_txt():
        w = prepare(DATA / "hop-mau.txt", "txt")
        ctx["w"] = w
        tr = read_json(w / "transcript.json")
        sp = read_json(w / "speakers.json")
        assert len(tr["segments"]) == 23, f"tách {len(tr['segments'])} đoạn, cần 23"
        assert {v["ten"] for v in sp.values()} == {"Trần Minh Hoàng", "Nguyễn Thu Hà", "Lê Văn Đức", "Phạm Ngọc Lan"}
        return "23 đoạn, 4 người nói (căn cứ: nhãn trong transcript)"
    case("S", "Transcript .txt có mốc giờ + tên", t_txt)

    def t_vtt():
        w = prepare(DATA / "hop-mau.vtt", "vtt")
        tr = read_json(w / "transcript.json")
        assert len(tr["segments"]) == 23 and tr["segments"][14]["start"] > 60
        return f"23 cue, mốc #15 = {tr['segments'][14]['start']:.1f}s"
    case("S", "Transcript .vtt (nhãn <v Tên>)", t_vtt)

    def t_docx():
        import docx
        d = docx.Document()
        for line in (DATA / "hop-mau.txt").read_text(encoding="utf-8").splitlines():
            d.add_paragraph(line)
        p = OUT / "hop-mau.docx"
        d.save(p)
        w = prepare(p, "docx")
        assert len(read_json(w / "transcript.json")["segments"]) == 23
        return "23 đoạn"
    case("S", "Transcript .docx", t_docx)

    # ---------------- P: xuất bản đầy đủ từ transcript
    def t_export():
        w = ctx["w"]
        write_json(w / "bien-ban.json", gold)
        rc = run_cli("xuat", w, "--khong-mo")
        assert rc == 0, f"xuat trả mã {rc}"
        res = read_json(w / "ket-qua.json")
        assert res["pdf_info"]["trang"] <= 4, f"PDF {res['pdf_info']['trang']} trang"
        from openpyxl import load_workbook
        wb = load_workbook(w / "viec-can-lam.xlsx")
        ws = wb["Việc cần làm"]
        assert ws.data_validations.dataValidation, "thiếu danh sách chọn trạng thái"
        assert len(ws.conditional_formatting) >= 1, "thiếu tô màu quá hạn"
        assert "Theo người" in wb.sheetnames
        em = read_json(w / "email" / "danh-sach-email.json")
        assert len(em["email"]) == 3 and em["thieu_email"] == ["Phạm Ngọc Lan"]
        ics = sorted((w / "email").glob("*.ics"))
        assert len(list((w / "email").glob("*.eml"))) == 2 and len(ics) == 2, "số .eml/.ics sai (việc không có hạn thì không tạo lịch)"
        for f in ics:
            raw = f.read_bytes()
            assert b"\r\r\n" not in raw and raw.count(b"\r\n") > 5 and b"BEGIN:VEVENT" in raw, f"{f.name} sai chuẩn CRLF/iCalendar"
        html = (w / "bien-ban-doc.html").read_text(encoding="utf-8")
        assert "QUAN TRỌNG" in html and "Literata" in html
        return f"PDF {res['pdf_info']['trang']} trang; Excel có danh sách chọn + tô đỏ + sheet theo người; 2 .eml, 2 .ics đúng chuẩn CRLF"
    case("P", "Xuất đủ PDF + bản đọc + Excel + email", t_export)

    # ---------------- chống bịa / bỏ sót
    def expect_block(mut, needle):
        def f():
            bb = copy.deepcopy(gold)
            mut(bb)
            rep = verify_with(ctx["w"], bb)
            assert rep["trang_thai"] == "CHAN", "KHÔNG bị chặn"
            hit = [e for e in rep["loi"] if needle in e]
            assert hit, f"chặn nhưng sai lý do: {rep['loi'][:2]}"
            return "Chặn: " + hit[0][:110]
        return f

    case("P", "Trích dẫn bịa → chặn", expect_block(
        lambda b: b["quyet_dinh"][0]["trich_dan"][0].update(text="chốt ngân sách sáu trăm triệu đồng"), "KHÔNG tìm thấy"))
    case("P", "Trích dẫn bịa không có seg → chặn", expect_block(
        lambda b: b["chu_de"][1]["trich_dan"].append({"text": "doanh số tăng gấp đôi"}), "KHÔNG tìm thấy"))
    case("P", "Gán người phụ trách sai → chặn", expect_block(
        lambda b: b["hanh_dong"][2].update(phu_trach="Nguyễn Thu Hà"), "không được nêu tên"))
    case("P", "Thời hạn không được nói → chặn", expect_block(
        lambda b: b["hanh_dong"][2].update(han="2026-11-30", han_goc="cuối tháng"), "không xuất hiện"))
    case("P", "Quy đổi hạn sai → chặn", expect_block(
        lambda b: b["hanh_dong"][0].update(han="2026-11-20"), "khác 'han'"))

    def nodate(b):
        b["meta"]["ngay_hop"] = None
    case("P", "Hạn tương đối khi chưa biết ngày họp → chặn", expect_block(nodate, "chưa biết ngày họp"))
    case("P", "Bỏ sót câu chứa từ khoá → chặn", expect_block(lambda b: b.update(bo_qua=[]), "BỎ SÓT"))
    case("P", "Bỏ qua không ghi lý do → chặn", expect_block(lambda b: b.update(bo_qua=[{"seg": 3, "ly_do": ""}]), "thiếu lý do"))

    def t_tamper():
        import verify
        w = ctx["w"]
        verify_with(w, gold)
        bb = copy.deepcopy(gold)
        bb["tom_tat"][0] = "Sửa sau kiểm chứng"
        write_json(w / "bien-ban.json", bb)
        try:
            verify.require_verified(w)
        except BBError as e:
            write_json(w / "bien-ban.json", gold)
            return str(e)
        raise AssertionError("sửa sau kiểm chứng vẫn xuất được")
    case("P", "Sửa biên bản sau kiểm chứng → chặn", t_tamper)

    # ---------------- ảo giác Whisper
    def t_hallu():
        from ingest import is_hallucination
        cfg = load_config()
        bad = ["Hãy subscribe cho kênh Ghiền Mì Gõ để không bỏ lỡ những video hấp dẫn",
               "Cảm ơn các bạn đã theo dõi và hẹn gặp lại", "ok ok ok ok ok ok ok ok ok ok ok ok"]
        assert all(is_hallucination(x, cfg) for x in bad)
        assert not is_hallucination("Chị Hà phụ trách hoàn thiện kế hoạch truyền thông", cfg)
        w = ctx["w"]
        tr = read_json(w / "transcript.json")
        tr2 = copy.deepcopy(tr)
        tr2["segments"].append({"id": 99, "start": 150, "end": 153, "speaker": "S1", "text": "Cảm ơn các bạn đã theo dõi"})
        write_json(w / "transcript.json", tr2)
        bb = copy.deepcopy(gold)
        bb["chu_de"][5]["trich_dan"].append({"seg": 99, "text": "Cảm ơn các bạn đã theo dõi"})
        rep = verify_with(w, bb)
        write_json(w / "transcript.json", tr)
        assert rep["trang_thai"] == "CHAN" and any("ảo giác" in e for e in rep["loi"])
        return "Nhận diện 3/3 câu ảo giác; trích câu ảo giác → chặn"
    case("A", "Lọc câu ảo giác Whisper", t_hallu)

    # ---------------- S: đầu vào lỗi
    def expect_err(path_maker, needle):
        def f():
            p = path_maker()
            try:
                prepare(p, "loi")
            except BBError as e:
                assert needle in str(e), f"thông báo: {e}"
                return str(e)
            raise AssertionError("không báo lỗi")
        return f

    def mk(name, data):
        def f():
            p = OUT / name
            p.write_bytes(data)
            return p
        return f
    case("S", "File rỗng", expect_err(mk("rong.mp3", b""), "rỗng"))
    case("S", "File video hỏng", expect_err(mk("hong.mp4", os.urandom(50000)), "hỏng"))
    case("S", "Sai định dạng (.pdf)", expect_err(mk("tai-lieu.pdf", b"%PDF-1.4 test"), "không được hỗ trợ"))
    case("S", "Transcript rỗng nội dung", expect_err(mk("trong.txt", b"   \n\n"), "không có nội dung"))

    # ---------------- E: email, mã hoá
    def t_missing_email():
        em = read_json(ctx["w"] / "email" / "danh-sach-email.json")
        lan = next(x for x in em["email"] if x["nguoi"] == "Phạm Ngọc Lan")
        assert lan["email"] is None and lan["eml"] is None and em["trang_thai"] == "CHUA_GUI"
        prev = (ctx["w"] / "email" / "xem-truoc-email.md").read_text(encoding="utf-8")
        assert "THIẾU EMAIL" in prev
        return "Không tạo .eml cho người thiếu email; xem trước ghi ⚠ THIẾU EMAIL; trạng thái CHUA_GUI"
    case("E", "Thiếu email → không tạo thư, yêu cầu bổ sung", t_missing_email)

    def t_encrypt():
        import base64
        import re
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        w = ctx["w"]
        write_json(w / "bien-ban.json", gold)  # các ca trước cố ý ghi dữ liệu sai
        rc = run_cli("xuat", w, "--khong-mo", "--mat-khau", "thu-nghiem-123")
        assert rc == 0
        html = (w / "bien-ban-doc.html").read_text(encoding="utf-8")
        assert "ngân sách quảng cáo" not in html.lower() and "thu-nghiem-123" not in html
        p = json.loads(re.search(r'<script id="bb-data" type="application/json">(.*?)</script>', html, re.S)[1])
        key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=base64.b64decode(p["salt"]),
                         iterations=p["iter"]).derive(b"thu-nghiem-123")
        data = json.loads(AESGCM(key).decrypt(base64.b64decode(p["iv"]), base64.b64decode(p["ct"]), None))
        assert data["meta"]["tieu_de"] == gold["meta"]["tieu_de"]
        run_cli("xuat", w, "--khong-mo")
        return "Không lộ nội dung/mật khẩu; giải mã AES-GCM/PBKDF2 đúng"
    case("E", "Khoá bản đọc bằng mật khẩu", t_encrypt)

    def t_gmail():
        import base64
        w = ctx["w"]
        assert run_cli("goi-gmail", w) == 0
        g = read_json(w / "email" / "gui-gmail.json")
        assert len(g) == 2 and all(x["to"][0].endswith("@example.com") for x in g), "gói gửi thật phải bỏ qua người thiếu email"
        for x in g:
            for a in x["attachments"]:
                assert base64.b64decode(a["content"]) == (w / "email" / a["filename"]).read_bytes()
        assert run_cli("goi-gmail", w, "--thu-ve", "thu@example.org") == 0
        g = read_json(w / "email" / "gui-gmail.json")
        assert len(g) == 3 and all(x["subject"].startswith("[THỬ – cho ") and x["to"] == ["thu@example.org"] for x in g)
        assert run_cli("da-gui", w, "--trang-thai", "DA_GUI_THU", "--ghi-chu", "kiểm thử") == 0
        em = read_json(w / "email" / "danh-sach-email.json")
        assert em["trang_thai"] == "DA_GUI_THU" and em["lich_su"][-1]["ghi_chu"] == "kiểm thử"
        return "Gói gửi thật: 2 thư (bỏ qua người thiếu email); gửi thử: 3 thư có tiền tố [THỬ]; đính kèm base64 khớp file; ghi lịch sử gửi"
    case("E", "Gói gửi Gmail + ghi trạng thái gửi", t_gmail)

    if full:
        def t_mp3():
            w = prepare(DATA / "hop-mau.mp3", "mp3")
            src = SKILL_DIR.parents[2] / "bien-ban" / "2026-11-19-hop-mau" / "bien-ban.json"
            assert src.exists(), "cần chạy video mẫu trước để có bien-ban.json"
            bb = read_json(src)
            for sec in ("chu_de", "quyet_dinh", "hanh_dong", "van_de_mo"):
                for it in bb[sec]:
                    for q in it.get("trich_dan", []):
                        q.pop("seg", None)
                        q.pop("t", None)
            bb["bo_qua"] = []
            bb["meta"]["nguon"] = "hop-mau.mp3"
            rep = verify_with(w, bb)
            import re as _re
            # Bản phiên âm MP3 có thể khác chữ so với video → câu trích phải bị CHẶN; mô phỏng Claude sửa lại.
            other = [e for e in rep["loi"] if "BỎ SÓT" not in e and "KHÔNG tìm thấy" not in e]
            assert not other, f"lỗi ngoài dự kiến: {other[:2]}"
            bad = {m[1] for e in rep["loi"] for m in [_re.search(r"“(.+?)”", e)] if "KHÔNG tìm thấy" in e and m}
            for sec in ("chu_de", "quyet_dinh", "hanh_dong", "van_de_mo"):
                for it in bb[sec]:
                    it["trich_dan"] = [q for q in it.get("trich_dan", []) if q["text"] not in bad] or it.get("trich_dan", [])
            bb["bo_qua"] = [{"seg": int(_re.search(r"#(\d+)", e)[1]), "ly_do": "Thủ tục/tự giới thiệu (kiểm thử MP3)"}
                            for e in rep["loi"] if "BỎ SÓT" in e]
            write_json(w / "bien-ban.json", bb)
            rc = run_cli("xuat", w, "--khong-mo")
            assert rc == 0, "xuất MP3 bị chặn – xem " + str(w / "kiem-chung.md")
            assert (w / "anh" / "dang-song.png").exists()
            res = read_json(w / "ket-qua.json")
            return f"Phiên âm + {len(read_json(w / 'speakers.json'))} cụm giọng; hình minh hoạ + sóng âm; PDF {res['pdf_info']['trang']} trang"
        case("A", "MP3: phiên âm, minh hoạ, sóng âm, xuất", t_mp3)

    # ---------------- báo cáo
    ok = sum(r[2] == "ĐẠT" for r in rows)
    md = [f"# Kết quả tự kiểm thử ({ok}/{len(rows)} đạt) – {time.strftime('%d/%m/%Y %H:%M')}", "",
          "| PEAS | Tình huống | Kết quả | Chi tiết | Giây |", "|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3].replace('|', '/')[:160]} | {r[4]:.1f} |")
    (T / "ket-qua-kiem-thu.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0 if ok == len(rows) else 1
