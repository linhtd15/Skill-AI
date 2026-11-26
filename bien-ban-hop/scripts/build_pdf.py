"""Bản in A4 (PDF) theo Mẫu A + quy tắc lap-bien-ban.md, tối đa N trang, tự thu gọn."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from xml.sax.saxutils import escape as esc

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

from common import clock, fmt_t, vn_date_long

RED = colors.HexColor("#B42318")
GREY = colors.HexColor("#555555")
LINE = colors.HexColor("#999999")


def register_fonts():
    base = Path("C:/Windows/Fonts")
    try:
        pdfmetrics.registerFont(TTFont("TNR", str(base / "times.ttf")))
        pdfmetrics.registerFont(TTFont("TNR-B", str(base / "timesbd.ttf")))
        pdfmetrics.registerFont(TTFont("TNR-I", str(base / "timesi.ttf")))
        pdfmetrics.registerFont(TTFont("TNR-BI", str(base / "timesbi.ttf")))
    except Exception:  # noqa: BLE001
        pdfmetrics.registerFont(TTFont("TNR", str(base / "arial.ttf")))
        pdfmetrics.registerFont(TTFont("TNR-B", str(base / "arialbd.ttf")))
        pdfmetrics.registerFont(TTFont("TNR-I", str(base / "ariali.ttf")))
        pdfmetrics.registerFont(TTFont("TNR-BI", str(base / "arialbi.ttf")))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("TNR", normal="TNR", bold="TNR-B", italic="TNR-I", boldItalic="TNR-BI")


class NumberedCanvas(rl_canvas.Canvas):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._saved)
        for st in self._saved:
            self.__dict__.update(st)
            self.setFont("TNR", 9)
            self.setFillColor(GREY)
            self.drawCentredString(A4[0] / 2, 10 * mm, f"Trang {self._pageNumber}/{n}")
            super().showPage()
        super().save()


class Doc(BaseDocTemplate):
    def __init__(self, path, **kw):
        super().__init__(path, pagesize=A4, leftMargin=25 * mm, rightMargin=15 * mm,
                         topMargin=15 * mm, bottomMargin=17 * mm, title=kw.pop("title", "Biên bản họp"),
                         author="Agent biên bản họp", **kw)
        fr = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f", leftPadding=0,
                   rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="p", frames=[fr])])
        self.last_y = None

    def afterFlowable(self, f):
        if getattr(self, "frame", None) is not None:
            self.last_y = self.frame._y


# ------------------------------------------------------------ dựng nội dung
LEVELS = [
    # cỡ chữ, rộng ảnh(cm), trích ở bảng, rút gọn
    dict(fs=12.5, img=5.4, quote_in_table=True, trim=0),
    dict(fs=12, img=5.0, quote_in_table=True, trim=0),
    dict(fs=11.5, img=4.6, quote_in_table=False, trim=0),
    dict(fs=11, img=4.2, quote_in_table=False, trim=0),
    dict(fs=10.5, img=3.8, quote_in_table=False, trim=1),
    dict(fs=10, img=3.4, quote_in_table=False, trim=2),
    dict(fs=9.5, img=3.0, quote_in_table=False, trim=3),
]


def first_sentence(s):
    for sep in (". ", "; "):
        if sep in s:
            return s.split(sep)[0].rstrip(".") + "."
    return s


def styles(fs):
    S = {}
    S["body"] = ParagraphStyle("body", fontName="TNR", fontSize=fs, leading=fs * 1.25, alignment=TA_JUSTIFY, spaceAfter=fs * 0.25)
    S["small"] = ParagraphStyle("small", parent=S["body"], fontSize=fs * 0.75, leading=fs * 0.95, textColor=GREY, alignment=TA_LEFT)
    S["cell"] = ParagraphStyle("cell", parent=S["body"], fontSize=fs * 0.86, leading=fs * 1.05, alignment=TA_LEFT, spaceAfter=0)
    S["cellb"] = ParagraphStyle("cellb", parent=S["cell"], fontName="TNR-B")
    S["h"] = ParagraphStyle("h", parent=S["body"], fontName="TNR-B", fontSize=fs, spaceBefore=fs * 0.55, spaceAfter=fs * 0.25, alignment=TA_LEFT)
    S["title"] = ParagraphStyle("title", parent=S["body"], fontName="TNR-B", fontSize=fs + 2.5, leading=(fs + 2.5) * 1.2, alignment=TA_CENTER, spaceAfter=1)
    S["sub"] = ParagraphStyle("sub", parent=S["body"], fontName="TNR-B", alignment=TA_CENTER, spaceAfter=fs * 0.5)
    S["hdr"] = ParagraphStyle("hdr", parent=S["body"], fontSize=fs - 0.5, leading=(fs - 0.5) * 1.2, alignment=TA_CENTER, spaceAfter=0)
    S["quote"] = ParagraphStyle("q", parent=S["body"], fontName="TNR-I", fontSize=fs * 0.92, leading=fs * 1.12, textColor=colors.HexColor("#222222"), alignment=TA_LEFT)
    S["sig"] = ParagraphStyle("sig", parent=S["body"], fontName="TNR-B", alignment=TA_CENTER, spaceAfter=0)
    return S


def P(t, s):
    return Paragraph(t, s)


def build_story(bb, rep, spk, images, L, cfg):
    S = styles(L["fs"])
    meta = bb.get("meta", {})
    story = []
    CB = "[CẦN BỔ SUNG"
    co_quan = meta.get("co_quan") or cfg.get("co_quan_mac_dinh") or f"{CB}: TÊN CƠ QUAN]"
    so = meta.get("so") or "Số: ....../BB-......"
    dia_danh = meta.get("dia_danh") or cfg.get("dia_danh_mac_dinh") or "[Địa danh]"
    hdr = Table([
        [P(f"<b>{esc(co_quan.upper())}</b>", S["hdr"]), P("<b>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</b>", S["hdr"])],
        [P("―――――", S["hdr"]), P("<b>Độc lập - Tự do - Hạnh phúc</b><br/>―――――――――――", S["hdr"])],
        [P(esc(so if so.startswith("Số") else "Số: " + so), S["hdr"]),
         P(f"<i>{esc(dia_danh)}, {vn_date_long(meta.get('ngay_hop'))}</i>", S["hdr"])],
    ], colWidths=[6.6 * cm, None])
    hdr.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    story += [hdr, Spacer(1, L["fs"] * 0.6), P("BIÊN BẢN HỌP", S["title"]), P(esc(meta.get("tieu_de", "")), S["sub"])]

    # I. Thời gian, địa điểm, thành phần
    gio = meta.get("gio_bat_dau")
    tg = (f"bắt đầu {gio.replace(':', ' giờ ')} phút, " if gio else "bắt đầu [CHƯA RÕ] giờ, ") + vn_date_long(meta.get("ngay_hop"))
    people = bb.get("nguoi_tham_gia", [])
    present = [p for p in people if not p.get("vang")]
    absent = [p for p in people if p.get("vang")]
    tp = "; ".join(f"{esc(p['ten'])}" + (f" ({esc(p['vai_tro'])})" if p.get("vai_tro") else "") for p in present)
    ab = "; ".join(f"{esc(p['ten'])} – {esc(p.get('ly_do_vang') or 'lý do [CHƯA RÕ]')}" for p in absent) or "không"
    story += [P("I. THỜI GIAN, ĐỊA ĐIỂM, THÀNH PHẦN", S["h"]),
              P(f"- Thời gian: {tg}. Địa điểm/Hình thức: {esc(meta.get('dia_diem') or '[CHƯA RÕ]')}"
                f"{' – ' + esc(meta['hinh_thuc']) if meta.get('hinh_thuc') else ''}.", S["body"]),
              P(f"- Chủ trì: {esc(meta.get('chu_tri') or '[CHƯA RÕ]')}. Thư ký: {esc(meta.get('thu_ky') or '[CHƯA RÕ]')}.", S["body"]),
              P(f"- Thành phần tham dự (có mặt {len(present)}/{len(people)}): {tp}. Vắng: {ab}.", S["body"]),
              P(f"- Mục đích: {esc(meta.get('muc_dich', ''))}", S["body"])]

    # II. Tóm tắt
    tt = bb.get("tom_tat", [])
    if L["trim"] >= 2:
        tt = tt[:4]
    story += [P("II. TÓM TẮT", S["h"])] + [P(f"• {esc(x)}", S["body"]) for x in tt]

    # III. Diễn biến
    story.append(P("III. DIỄN BIẾN CUỘC HỌP", S["h"]))
    topics = bb.get("chu_de", [])
    if L["trim"] >= 3:
        topics = topics[:8]
    imgw = L["img"] * cm
    for i, t in enumerate(topics):
        q = next((x for x in t.get("trich_dan", []) if x.get("chinh")), (t.get("trich_dan") or [None])[0])
        ck = clock(meta, t.get("bat_dau"))
        tm = f"{ck} · {fmt_t(t.get('bat_dau'))}" if ck else fmt_t(t.get("bat_dau"))
        body = t.get("tom_tat", "")
        if L["trim"] >= 1:
            body = first_sentence(body)
        left = [P(f"<b>{i + 1}. [{tm}] {esc(t.get('tieu_de', ''))}</b>", S["body"]), P(esc(body), S["body"])]
        if q:
            left.append(P(f"“{esc(q['text'])}” — {esc(q.get('nguoi', ''))}, {fmt_t(q.get('t'))}", S["quote"]))
        img = images.get(t["id"])
        if img:
            from PIL import Image as PI
            w, h = PI.open(img["file"]).size
            right = [Image(img["file"], width=imgw, height=imgw * h / w),
                     P(esc(img["chu_thich"]), S["small"])]
            row = Table([[left, right]], colWidths=[None, imgw + 0.2 * cm])
        else:
            row = Table([[left]], colWidths=[None])
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (0, 0), 6), ("RIGHTPADDING", (1, 0), (1, 0), 0),
                                 ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                                 ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE)]))
        story.append(KeepTogether(row))

    def grid(data, widths, header=True):
        t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                               ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                               ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        return t

    # IV. Kết luận / quyết định
    story.append(P("IV. KẾT LUẬN CỦA CHỦ TRÌ (QUYẾT ĐỊNH)", S["h"]))
    qd = bb.get("quyet_dinh", [])
    if qd:
        rows = [[P("<b>Mã</b>", S["cell"]), P("<b>Nội dung</b>", S["cell"]), P("<b>Thời điểm</b>", S["cell"])]]
        for d in qd:
            q = (d.get("trich_dan") or [{}])[0]
            txt = esc(d["noi_dung"])
            if L["quote_in_table"] and q.get("text"):
                txt += f"<br/><font size={L['fs'] * 0.78}><i>“{esc(q['text'])}” — {esc(q.get('nguoi', ''))}</i></font>"
            rows.append([P(d["id"], S["cell"]), P(txt, S["cell"]),
                         P(f"{clock(meta, q.get('t')) or ''} ({fmt_t(q.get('t'))})", S["cell"])])
        story.append(grid(rows, [1.2 * cm, None, 2.6 * cm]))
    else:
        story.append(P("Không có quyết định nào được chốt. Cuộc họp chưa đưa ra kết luận về các nội dung đã thảo luận.", S["body"]))

    # V. Phân công
    story.append(P("V. PHÂN CÔNG THỰC HIỆN (KẾ HOẠCH HÀNH ĐỘNG)", S["h"]))
    acts = bb.get("hanh_dong", [])
    if acts:
        rows = [[P(f"<b>{h}</b>", S["cell"]) for h in ("Mã", "Công việc", "Phụ trách", "Thời hạn", "Căn cứ")]]
        for a in acts:
            q = (a.get("trich_dan") or [{}])[0]
            owner = esc(a["phu_trach"]) if a.get("phu_trach") else '<font color="#B42318"><b>Chưa xác định</b></font>'
            han = (dt.date.fromisoformat(a["han"]).strftime("%d/%m/%Y") if a.get("han") else
                   '<font color="#B42318">Chưa có hạn</font>')
            cc = f"{fmt_t(q.get('t'))} – {esc(q.get('nguoi', ''))}"
            if L["quote_in_table"] and q.get("text"):
                cc += f": <i>“{esc(q['text'])}”</i>"
            rows.append([P(a["id"], S["cell"]), P(esc(a["cong_viec"]), S["cell"]), P(owner, S["cell"]),
                         P(han, S["cell"]), P(cc, S["cell"])])
        story.append(grid(rows, [1.0 * cm, None, 3.0 * cm, 2.0 * cm, 5.2 * cm if L["quote_in_table"] else 3.2 * cm]))
    else:
        story.append(P("Không có công việc nào được giao trong cuộc họp.", S["body"]))

    # VI. Vấn đề còn mở
    story.append(P("VI. VẤN ĐỀ CÒN MỞ / CẦN XÁC NHẬN", S["h"]))
    vm = bb.get("van_de_mo", [])
    items = [f"• {'<b>[Rủi ro]</b> ' if v.get('loai') == 'RUI_RO' else ''}{esc(v['noi_dung'])}" for v in vm]
    items += [f"• Cần làm rõ: {esc(c.get('cau_hoi') or c.get('muc'))}" for c in bb.get("can_lam_ro", [])[:3 if L['trim'] else 6]]
    story += [P(x, S["body"]) for x in items] or [P("Không có.", S["body"])]

    # Kết thúc + ký
    gk = meta.get("gio_ket_thuc")
    end_txt = (f"Biên bản kết thúc vào lúc {gk.replace(':', ' giờ ')} phút cùng ngày" if gk
               else "Biên bản kết thúc vào lúc [CHƯA RÕ] giờ [CHƯA RÕ] phút cùng ngày")
    closing = P(end_txt + ", đã được đọc lại cho các thành viên cùng nghe và thống nhất ký tên. "
                f"Biên bản được lập thành {meta.get('so_ban') or '[..]'} bản có giá trị như nhau.", S["body"])
    sig = Table([[P("THƯ KÝ", S["sig"]), P("CHỦ TRÌ", S["sig"])],
                 [P("<i>(Ký, ghi rõ họ tên)</i>", S["hdr"]), P("<i>(Ký, ghi rõ họ tên)</i>", S["hdr"])],
                 [Spacer(1, L["fs"] * 3.2), Spacer(1, L["fs"] * 3.2)],
                 [P(f"<b>{esc(meta.get('thu_ky') or '')}</b>", S["hdr"]), P(f"<b>{esc(meta.get('chu_tri') or '')}</b>", S["hdr"])]])
    sig.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    story.append(KeepTogether([closing, Spacer(1, 4), sig]))

    # chân trang ghi chú
    st = rep["thong_ke"]
    basis = []
    for k, v in spk.items():
        kinds = sorted({c["loai"] for c in v.get("can_cu", [])})
        lab = {"tu_gioi_thieu": "tự giới thiệu", "duoc_goi_ten": "được gọi tên", "nhan_video": "nhãn tên trên video",
               "nhan_transcript": "nhãn trong transcript", "nguoi_dung_xac_nhan": "người dùng xác nhận"}
        basis.append(f"{v['ten']} ({', '.join(lab.get(x, x) for x in kinds) or 'chưa có căn cứ'})")
    note = (f"<b>Kiểm chứng:</b> {st['khop']}/{st['trich_dan']} trích dẫn khớp nguyên văn bản ghi; mọi người phụ trách và thời hạn "
            f"đều có câu nói làm căn cứ. <b>Nhận diện người nói:</b> {esc('; '.join(basis))}. "
            f"<b>Lưu ý:</b> Biên bản do trợ lý AI lập nháp từ bản ghi ({esc(meta.get('nguon', ''))}); mốc trong ngoặc là thời điểm trên bản ghi; "
            "cần thư ký và chủ trì đối chiếu trước khi ký.")
    if L["trim"]:
        note += " Bản in đã được rút gọn cho vừa khổ giấy; xem đầy đủ ở bản trình đọc."
    story += [Spacer(1, 6), P(note, S["small"])]
    return story


def build(bb, rep, spk, images, out: Path, cfg) -> dict:
    register_fonts()
    maxp = cfg["ban_in"]["so_trang_toi_da"]
    min_last = cfg["ban_in"]["trang_cuoi_toi_thieu"]
    result = None
    for li, L in enumerate(LEVELS):
        doc = Doc(str(out), title=bb.get("meta", {}).get("tieu_de", "Biên bản họp"))
        doc.build(build_story(bb, rep, spk, images, L, cfg), canvasmaker=NumberedCanvas)
        from pypdf import PdfReader
        pages = len(PdfReader(str(out)).pages)
        fill = 1 - (doc.last_y - doc.bottomMargin) / doc.height if doc.last_y is not None else 1
        result = {"trang": pages, "muc_thu_gon": li, "trang_cuoi_lap_day": round(fill, 2)}
        if pages > maxp:
            continue
        if pages > 1 and fill < min_last and li + 1 < len(LEVELS):
            # thử thu gọn thêm để kéo vài dòng lẻ về trang trước
            doc2_path = out.with_suffix(".try.pdf")
            for L2 in LEVELS[li + 1:li + 3]:
                d2 = Doc(str(doc2_path))
                d2.build(build_story(bb, rep, spk, images, L2, cfg), canvasmaker=NumberedCanvas)
                p2 = len(PdfReader(str(doc2_path)).pages)
                if p2 < pages:
                    doc2_path.replace(out)
                    result = {"trang": p2, "muc_thu_gon": LEVELS.index(L2),
                              "trang_cuoi_lap_day": round(1 - (d2.last_y - d2.bottomMargin) / d2.height, 2)}
                    break
            doc2_path.unlink(missing_ok=True)
        return result
    result["vuot_trang"] = True
    return result
