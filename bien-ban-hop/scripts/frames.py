"""Bước 5: ảnh dẫn chứng cho từng mục diễn biến.

- Có video: chụp khung hình tại mốc câu trích chính; loại ảnh trùng slide/màn hình (dHash).
- Chỉ có âm thanh: tạo HÌNH MINH HOẠ (ghi rõ "hình minh hoạ, không phải ảnh chụp")
  kèm dạng sóng THẬT của đoạn ghi âm thuộc chủ đề, và dạng sóng toàn bộ bản ghi.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from common import fmt_t, run_ff

FONT_DIR = Path("C:/Windows/Fonts")


def font(size, bold=False):
    for n in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(str(FONT_DIR / n), size)
        except OSError:
            continue
    return ImageFont.load_default()


def dhash(im: Image.Image, n=16) -> int:
    g = im.convert("L").resize((n + 1, n))
    a = np.asarray(g, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def ham(a, b):
    return bin(a ^ b).count("1")


def grab(video, t, out: Path, width=720):
    run_ff(["-ss", f"{max(0, t):.2f}", "-i", video, "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "4", out], check=False)
    return out.exists()


def video_frames(video: Path, bb: dict, work: Path, log=print):
    d = work / "anh"
    d.mkdir(exist_ok=True)
    kept = []  # (hash, topic id)
    res = {}
    for t in bb.get("chu_de", []):
        qs = sorted(t.get("trich_dan", []), key=lambda q: not q.get("chinh"))
        times = [q["t"] + 1.0 for q in qs if q.get("t") is not None]
        if t.get("bat_dau") is not None:
            times.append(t["bat_dau"] + 2)
        chosen = None
        for tm in times:
            p = d / f"{t['id']}.jpg"
            if not grab(video, tm, p):
                continue
            im = Image.open(p)
            # bỏ vùng nhãn tên (đáy 15%) khi so trùng để chỉ so nội dung slide/màn hình
            h = dhash(im.crop((0, 0, im.width, int(im.height * 0.85))))
            dup = next((k for k in kept if ham(k[0], h) <= 8), None)
            if dup:
                continue
            chosen = (p, tm, h)
            break
        if chosen:
            kept.append((chosen[2], t["id"]))
            res[t["id"]] = {"file": str(chosen[0]), "t": chosen[1], "loai": "anh_chup",
                            "chu_thich": f"Ảnh chụp video lúc {fmt_t(chosen[1])}"}
        else:
            (d / f"{t['id']}.jpg").unlink(missing_ok=True)
            res[t["id"]] = None
            log(f"  • {t['id']}: khung hình trùng slide của mục trước → không lặp lại ảnh")
    return res


# ------------------------------------------------------------ chỉ có âm thanh
def load_wave(wav: Path):
    import soundfile as sf
    x, sr = sf.read(str(wav), dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    return x, sr


def draw_wave(draw, x, box, color, bg=None, bars=160):
    x0, y0, x1, y1 = box
    if bg:
        draw.rectangle(box, fill=bg)
    if len(x) == 0:
        return
    chunks = np.array_split(np.abs(x), bars)
    peaks = np.array([c.max() if len(c) else 0 for c in chunks])
    peaks = peaks / (peaks.max() + 1e-9)
    w = (x1 - x0) / bars
    mid = (y0 + y1) / 2
    for i, p in enumerate(peaks):
        hh = max(1, p * (y1 - y0) / 2 * 0.95)
        draw.rectangle((x0 + i * w + 1, mid - hh, x0 + (i + 1) * w - 1, mid + hh), fill=color)


def wrap(text, f, width, draw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=f) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def audio_illustrations(wav: Path, bb: dict, work: Path, duration: float):
    d = work / "anh"
    d.mkdir(exist_ok=True)
    x, sr = load_wave(wav)
    topics = bb.get("chu_de", [])
    res = {}
    palette = [(58, 74, 94), (84, 64, 52), (52, 84, 72), (78, 58, 88), (70, 70, 70)]
    for i, t in enumerate(topics):
        st = t.get("bat_dau") or 0
        en = topics[i + 1].get("bat_dau") if i + 1 < len(topics) and topics[i + 1].get("bat_dau") else duration
        W, H = 720, 405
        im = Image.new("RGB", (W, H), (246, 244, 240))
        dr = ImageDraw.Draw(im)
        col = palette[i % len(palette)]
        dr.rectangle((0, 0, W, 8), fill=col)
        # hình khối trang trí đơn giản (biểu tượng cuộc họp: bàn tròn + ghế)
        cx, cy = W - 110, 120
        dr.ellipse((cx - 55, cy - 55, cx + 55, cy + 55), outline=col, width=5)
        for k in range(6):
            a = k * np.pi / 3
            px, py = cx + 80 * np.cos(a), cy + 80 * np.sin(a)
            dr.ellipse((px - 13, py - 13, px + 13, py + 13), fill=col)
        dr.text((32, 34), f"CHỦ ĐỀ {i + 1}", font=font(20, True), fill=col)
        y = 66
        for line in wrap(t.get("tieu_de", ""), font(34, True), W - 260, dr)[:3]:
            dr.text((32, y), line, font=font(34, True), fill=(30, 30, 30))
            y += 42
        seg = x[int(st * sr):int(en * sr)]
        draw_wave(dr, seg, (32, 250, W - 32, 345), col, bg=(232, 229, 223))
        dr.text((32, 352), f"Sóng âm thật của đoạn ghi âm {fmt_t(st)} – {fmt_t(en)}", font=font(16), fill=(80, 80, 80))
        dr.text((32, 376), "Hình minh hoạ, không phải ảnh chụp", font=font(16, True), fill=(150, 40, 40))
        p = d / f"{t['id']}.jpg"
        im.save(p, quality=85)
        res[t["id"]] = {"file": str(p), "t": st, "loai": "minh_hoa",
                        "chu_thich": f"Hình minh hoạ (không phải ảnh chụp) – sóng âm {fmt_t(st)}–{fmt_t(en)}"}
    # dạng sóng toàn bộ bản ghi, đánh dấu chủ đề
    W, H = 1200, 220
    im = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    draw_wave(dr, x, (20, 20, W - 20, 170), (60, 60, 60), bars=400)
    for i, t in enumerate(topics):
        if t.get("bat_dau") is None:
            continue
        px = 20 + (W - 40) * t["bat_dau"] / max(duration, 1)
        dr.line((px, 10, px, 180), fill=(180, 40, 40), width=2)
        dr.text((px + 3, 182), str(i + 1), font=font(16, True), fill=(180, 40, 40))
    dr.text((20, 198), f"Dạng sóng toàn bộ bản ghi (0:00 – {fmt_t(duration)}); số = chủ đề", font=font(14), fill=(80, 80, 80))
    wp = d / "dang-song.png"
    im.save(wp)
    return res, str(wp)
