"""Bản trình đọc web một file (bien-ban-doc.html), ảnh nhúng sẵn, tuỳ chọn khoá mật khẩu AES-GCM/PBKDF2."""
from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path

from PIL import Image

from common import SKILL_DIR, clock, fmt_t, initials, vn_date, vn_date_long

LAB = {"tu_gioi_thieu": "tự giới thiệu", "duoc_goi_ten": "được người khác gọi tên", "nhan_video": "nhãn tên trên video",
       "nhan_transcript": "nhãn tên trong file transcript", "nguoi_dung_xac_nhan": "người dùng xác nhận"}


def data_uri(path, width=760, q=72):
    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def payload(bb, rep, spk, images, tr, wave, pdf_info):
    meta = bb.get("meta", {})

    def Q(q):
        if not q:
            return None
        return {"text": q.get("text"), "nguoi": q.get("nguoi", ""), "tm": fmt_t(q.get("t")), "clock": clock(meta, q.get("t")),
                "chinh": bool(q.get("chinh"))}

    dur = tr.get("thoi_luong") or 0
    people = []
    for p in bb.get("nguoi_tham_gia", []):
        people.append({"ten": p["ten"], "vai_tro": p.get("vai_tro", ""), "vang": bool(p.get("vang")), "av": initials(p["ten"])})
    st = rep["thong_ke"]
    nn = []
    for k, v in spk.items():
        kinds = []
        for c in v.get("can_cu", []):
            s = LAB.get(c["loai"], c["loai"])
            if c.get("trich") and c["loai"] != "nhan_transcript":
                s += f" (“{c['trich']}”)"
            if s not in kinds:
                kinds.append(s)
        nn.append({"ten": v["ten"], "giay": v.get("thoi_luong_noi", 0), "tm": fmt_t(v.get("thoi_luong_noi", 0)),
                   "can_cu": "; ".join(kinds[:3]) or "chưa có căn cứ – cần người dùng xác nhận"})
    nn.sort(key=lambda x: -x["giay"])
    return {
        "meta": {"tieu_de": meta.get("tieu_de", ""), "muc_dich": meta.get("muc_dich", ""), "ngay": vn_date(meta.get("ngay_hop")),
                 "ngay_dai": vn_date_long(meta.get("ngay_hop")).capitalize()
                 + (f", {meta['gio_bat_dau']}" if meta.get("gio_bat_dau") else ""),
                 "thoi_luong": f"Thời lượng {fmt_t(dur)}" if dur else "", "nguon": meta.get("nguon", tr.get("nguon", "")),
                 "chu_tri": meta.get("chu_tri")},
        "nguoi": people,
        "tom_tat": bb.get("tom_tat", []),
        "counts": {"qd": len(bb.get("quyet_dinh", [])), "viec": len(bb.get("hanh_dong", [])), "mo": len(bb.get("van_de_mo", [])),
                   "khop": st["khop"], "tong": st["trich_dan"]},
        "viec": [{"id": a["id"], "cong_viec": a["cong_viec"], "phu_trach": a.get("phu_trach"), "han": a.get("han"),
                  "han_goc": a.get("han_goc"), "chu_de": a.get("chu_de"), "q": Q((a.get("trich_dan") or [None])[0]) or {}}
                 for a in bb.get("hanh_dong", [])],
        "quyet_dinh": [{"id": d["id"], "noi_dung": d["noi_dung"], "chu_de": d.get("chu_de"), "q": Q((d.get("trich_dan") or [None])[0])}
                       for d in bb.get("quyet_dinh", [])],
        "chu_de": [{"id": t["id"], "tieu_de": t.get("tieu_de", ""), "tm": fmt_t(t.get("bat_dau")), "clock": clock(meta, t.get("bat_dau")),
                    "tom_tat": t.get("tom_tat", ""), "trich": [Q(q) for q in t.get("trich_dan", [])],
                    "anh": ({"src": data_uri(images[t["id"]]["file"]), "chu_thich": images[t["id"]]["chu_thich"]}
                            if images.get(t["id"]) else None)} for t in bb.get("chu_de", [])],
        "van_de_mo": [{"id": v["id"], "noi_dung": v["noi_dung"], "loai": v.get("loai", "CON_MO"), "chu_de": v.get("chu_de"),
                       "q": Q((v.get("trich_dan") or [None])[0])} for v in bb.get("van_de_mo", [])],
        "ghi_chu": {"trang_thai": "ĐẠT" if rep["trang_thai"] == "DAT" else "KHÔNG ĐẠT", "bo_qua": st.get("cau_tu_khoa_bo_qua", 0),
                    "nguoi_noi": nn, "can_lam_ro": [c.get("cau_hoi") or c.get("muc") for c in bb.get("can_lam_ro", [])],
                    "ao_giac": [f"{fmt_t(a['start'])}: “{a['text']}” – {a['ly_do']}" for a in tr.get("ao_giac_da_loc", [])],
                    "canh_bao": rep.get("canh_bao", []), "dang_song": data_uri(wave, 1100, 80) if wave else None,
                    "ban_in": f"{pdf_info.get('trang', '?')} trang"},
    }


def encrypt(obj, password, iterations):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations).derive(password.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, json.dumps(obj, ensure_ascii=False).encode("utf-8"), None)
    b = lambda x: base64.b64encode(x).decode()  # noqa: E731
    return {"salt": b(salt), "iv": b(iv), "ct": b(ct), "iter": iterations}


def build(bb, rep, spk, images, tr, wave, pdf_info, out: Path, cfg, password: str | None = None):
    data = payload(bb, rep, spk, images, tr, wave, pdf_info)
    enc = bool(password)
    if enc:
        data = encrypt(data, password, cfg["ban_doc"]["pbkdf2_vong_lap"])
    tpl = (SKILL_DIR / "templates" / "reader.html").read_text(encoding="utf-8")
    title = bb.get("meta", {}).get("tieu_de", "Biên bản họp")
    if enc:
        title = "Biên bản họp (có mật khẩu)"
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (tpl.replace("__TITLE__", title.replace("<", "&lt;"))
               .replace("__ENC__", "true" if enc else "false")
               .replace("__PAYLOAD__", js))
    out.write_text(html, encoding="utf-8")
    return out
