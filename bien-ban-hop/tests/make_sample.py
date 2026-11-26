"""Tạo dữ liệu mẫu để tự kiểm thử: cuộc họp giả lập 4 người (giọng tổng hợp edge-tts),
xuất MP3, MP4 (giao diện họp trực tuyến có nhãn tên người nói), transcript .txt/.vtt và danh sách người tham gia.
Nội dung, tên người và email đều là GIẢ ĐỊNH, chỉ dùng để kiểm thử.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from PIL import Image, ImageDraw  # noqa: E402

from common import fmt_t, probe, run_ff  # noqa: E402
from frames import font, wrap  # noqa: E402

OUT = Path(__file__).parent / "du-lieu-mau"
P = {
    "H": ("Trần Minh Hoàng", "vi-VN-NamMinhNeural", "+0%", "+0Hz"),
    "A": ("Nguyễn Thu Hà", "vi-VN-HoaiMyNeural", "+0%", "+0Hz"),
    "D": ("Lê Văn Đức", "vi-VN-NamMinhNeural", "-10%", "-14Hz"),
    "L": ("Phạm Ngọc Lan", "vi-VN-HoaiMyNeural", "+8%", "+18Hz"),
}
SLIDES = {
    "agenda": ("Kế hoạch bán hàng Tết 2027", ["Kết quả quý III", "Ngân sách quảng cáo Tết", "Chương trình khuyến mãi", "Quà tặng, kho, vận chuyển"]),
    "q3": ("Kết quả chiến dịch quý III", ["Doanh số online +12%", "Chi phí quảng cáo/đơn +8%", "Hiệu quả nhất: mạng xã hội", "Video ngắn chưa đạt kỳ vọng"]),
    "budget": ("Ngân sách quảng cáo Tết", ["Đề xuất marketing: 500 triệu", "Mức duyệt tối đa: 450 triệu", "Vượt mức: xin TGĐ ~2 tuần"]),
    "promo": ("Chương trình khuyến mãi", ["Giảm 15% đơn từ 1 triệu", "Quà tặng hộp lì xì", "Kế hoạch truyền thông"]),
    "gift": ("Quà tặng & tồn kho", ["Báo giá hộp lì xì: 3 nhà cung cấp", "In thiệp cảm ơn khách hàng", "Kiểm tra tồn kho trước Tết"]),
    "risk": ("Rủi ro vận chuyển dịp Tết", ["Đơn vị vận chuyển quá tải", "Nguy cơ giao hàng chậm", "Đơn vị dự phòng: chưa quyết"]),
}
LINES = [
    ("H", "agenda", "Chào mọi người, tôi là Hoàng, hôm nay tôi chủ trì cuộc họp kế hoạch bán hàng Tết năm 2027. Mục tiêu là chốt ngân sách quảng cáo và phân công chuẩn bị chương trình khuyến mãi."),
    ("H", "agenda", "Mời chị Lan ghi biên bản giúp anh."),
    ("L", "agenda", "Dạ vâng, em là Lan, em sẽ ghi biên bản cuộc họp hôm nay."),
    ("H", "q3", "Đầu tiên, mời chị Hà báo cáo nhanh kết quả chiến dịch quý ba."),
    ("A", "q3", "Vâng, em là Hà bên marketing. Quý ba doanh số online tăng mười hai phần trăm, nhưng chi phí quảng cáo trên mỗi đơn hàng cũng tăng khoảng tám phần trăm."),
    ("A", "q3", "Kênh hiệu quả nhất vẫn là mạng xã hội, còn video ngắn thì chưa đạt kỳ vọng."),
    ("H", "budget", "Về ngân sách quảng cáo Tết, mời anh Đức cho ý kiến về khả năng chi."),
    ("D", "budget", "Tôi là Đức, phụ trách kế toán. Ngân sách tối đa công ty duyệt được là bốn trăm năm mươi triệu đồng cho cả chiến dịch."),
    ("A", "budget", "Em đề xuất năm trăm triệu, vì giá quảng cáo dịp Tết thường tăng mạnh."),
    ("D", "budget", "Nếu vượt bốn trăm năm mươi triệu thì phải xin thêm phê duyệt của tổng giám đốc, sẽ mất khoảng hai tuần."),
    ("H", "budget", "Vậy chúng ta chốt ngân sách quảng cáo Tết là bốn trăm năm mươi triệu đồng, không xin thêm."),
    ("H", "promo", "Tiếp theo là chương trình khuyến mãi. Hà ơi, em trình bày phương án nhé."),
    ("A", "promo", "Bên em đề xuất giảm giá mười lăm phần trăm cho đơn từ một triệu, kèm quà tặng hộp lì xì."),
    ("H", "promo", "Thống nhất phương án giảm mười lăm phần trăm cho đơn từ một triệu đồng."),
    ("H", "promo", "Chị Hà phụ trách hoàn thiện kế hoạch truyền thông, gửi tôi trước thứ Sáu tuần sau."),
    ("D", "gift", "Về hộp lì xì, tôi sẽ lấy báo giá của ba nhà cung cấp trước ngày 23 tháng 11."),
    ("L", "gift", "Em lo phần đặt in thiệp cảm ơn khách hàng."),
    ("H", "gift", "Còn việc kiểm tra tồn kho trước Tết thì hôm nay chưa có người nhận, cần hỏi lại bộ phận kho."),
    ("L", "risk", "Em lo ngại dịp Tết các đơn vị vận chuyển thường quá tải, có thể giao hàng chậm."),
    ("H", "risk", "Đây là rủi ro lớn. Việc chọn thêm đơn vị vận chuyển dự phòng thì chưa quyết, để họp sau."),
    ("H", "agenda", "Anh Đức giao cho bên kế toán lập bảng theo dõi chi phí quảng cáo hằng tuần, hạn chót ngày 4 tháng 12."),
    ("D", "agenda", "Vâng, tôi nhận."),
    ("H", "agenda", "Cảm ơn mọi người, cuộc họp kết thúc."),
]
GAP = 0.6
INTRO = 6.0
OUTRO = 5.0


async def tts(lines, d: Path):
    import edge_tts
    for i, (k, _, text) in enumerate(lines):
        p = d / f"l{i:02d}.mp3"
        if p.exists() and p.stat().st_size > 0:
            continue
        _, voice, rate, pitch = P[k]
        for attempt in range(10):
            try:
                await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(p))
                break
            except Exception as e:  # noqa: BLE001
                print(f"  thử lại dòng {i} ({e.__class__.__name__})")
                await asyncio.sleep(3 + attempt * 2)
        else:
            raise SystemExit(f"Không tạo được giọng đọc cho dòng {i}")


def frame(slide_key, speaker_key, out: Path):
    W, H = 1280, 720
    im = Image.new("RGB", (W, H), (32, 33, 36))
    dr = ImageDraw.Draw(im)
    # vùng chia sẻ màn hình (slide)
    sx0, sy0, sx1, sy1 = 24, 24, 1000, 600
    dr.rectangle((sx0, sy0, sx1, sy1), fill=(250, 250, 247))
    title, bullets = SLIDES[slide_key]
    dr.rectangle((sx0, sy0, sx1, sy0 + 10), fill=(25, 70, 120))
    y = sy0 + 50
    for line in wrap(title, font(46, True), sx1 - sx0 - 100, dr):
        dr.text((sx0 + 50, y), line, font=font(46, True), fill=(20, 20, 20))
        y += 58
    y += 25
    for b in bullets:
        dr.ellipse((sx0 + 55, y + 16, sx0 + 67, y + 28), fill=(25, 70, 120))
        dr.text((sx0 + 85, y), b, font=font(32), fill=(40, 40, 40))
        y += 62
    dr.text((sx1 - 230, sy1 - 40), "Phòng Kinh doanh", font=font(20), fill=(140, 140, 140))
    # dải ô người tham gia bên phải
    for i, k in enumerate("HADL"):
        name = P[k][0]
        x0, y0 = 1020, 24 + i * 144
        active = k == speaker_key
        dr.rectangle((x0, y0, 1256, y0 + 132), fill=(60, 64, 67), outline=(138, 180, 248) if active else (60, 64, 67), width=4)
        dr.ellipse((x0 + 88, y0 + 22, x0 + 148, y0 + 82), fill=(95, 99, 104))
        dr.text((x0 + 118, y0 + 52), name.split()[-1][0], font=font(30, True), fill=(255, 255, 255), anchor="mm")
        dr.text((x0 + 12, y0 + 100), name, font=font(18), fill=(230, 230, 230))
    # nhãn tên người đang nói (góc dưới trái)
    name = P[speaker_key][0]
    dr.rounded_rectangle((24, 628, 24 + 24 + dr.textlength(name, font=font(30, True)) + 24, 690), 8, fill=(0, 0, 0))
    dr.text((48, 640), name, font=font(30, True), fill=(255, 255, 255))
    im.save(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_tmp"
    tmp.mkdir(exist_ok=True)
    print("Tạo giọng đọc (edge-tts)…")
    asyncio.run(tts(LINES, tmp))
    durs = [probe(tmp / f"l{i:02d}.mp3")["duration"] for i in range(len(LINES))]
    # nhạc nền mở/kết (hợp âm tổng hợp) để thử bộ lọc câu ảo giác
    music = "0.15*sin(2*PI*220*t)*(1+0.5*sin(2*PI*2*t))+0.12*sin(2*PI*277*t)+0.10*sin(2*PI*330*t)+0.05*sin(2*PI*440*t*(1+0.01*sin(2*PI*5*t)))"
    run_ff(["-f", "lavfi", "-i", f"aevalsrc={music}:s=24000:d={INTRO}", "-ac", "1", tmp / "intro.wav"])
    run_ff(["-f", "lavfi", "-i", f"aevalsrc={music}:s=24000:d={OUTRO}", "-ac", "1", tmp / "outro.wav"])
    run_ff(["-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono", "-t", str(GAP), tmp / "gap.wav"])
    for i in range(len(LINES)):
        run_ff(["-i", tmp / f"l{i:02d}.mp3", "-ar", "24000", "-ac", "1", tmp / f"l{i:02d}.wav"])
    parts = ["intro.wav"]
    for i in range(len(LINES)):
        parts += [f"l{i:02d}.wav", "gap.wav"]
    parts.append("outro.wav")
    (tmp / "a.txt").write_text("\n".join(f"file '{p}'" for p in parts), encoding="utf-8")
    run_ff(["-f", "concat", "-safe", "0", "-i", tmp / "a.txt", "-c:a", "pcm_s16le", tmp / "full.wav"])
    run_ff(["-i", tmp / "full.wav", "-c:a", "libmp3lame", "-b:a", "96k", OUT / "hop-mau.mp3"])
    # khung hình + thời gian
    t = INTRO
    vlist, txt, vtt = [], [], ["WEBVTT", ""]
    frame("agenda", "H", tmp / "f_intro.png")
    vlist.append(("f_intro.png", INTRO))
    base_h, base_m = 9, 0
    for i, ((k, sl, text), d) in enumerate(zip(LINES, durs)):
        fp = f"f{i:02d}.png"
        frame(sl, k, tmp / fp)
        vlist.append((fp, d + GAP))
        name = P[k][0]
        clock = f"{base_h + int((t // 3600)):02d}:{base_m + int(t // 60) % 60:02d}:{int(t % 60):02d}"
        txt.append(f"[{fmt_t(t) if t >= 3600 else '00:' + fmt_t(t)}] {name}: {text}")
        vtt += [f"{i + 1}", f"{ts(t)} --> {ts(t + d)}", f"<v {name}>{text}", ""]
        t += d + GAP
    vlist.append(("f_intro.png", OUTRO))
    conc = []
    for f, d in vlist:
        conc += [f"file '{f}'", f"duration {d:.3f}"]
    conc.append(f"file '{vlist[-1][0]}'")
    (tmp / "v.txt").write_text("\n".join(conc), encoding="utf-8")
    run_ff(["-f", "concat", "-safe", "0", "-i", tmp / "v.txt", "-i", tmp / "full.wav", "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-r", "10", "-c:a", "aac", "-b:a", "96k",
            "-shortest", OUT / "hop-mau.mp4"])
    (OUT / "hop-mau.txt").write_text("\n".join(txt), encoding="utf-8")
    (OUT / "hop-mau.vtt").write_text("\n".join(vtt), encoding="utf-8")
    (OUT / "nguoi-tham-gia.csv").write_text(
        "ten,email,vai_tro\n"
        "Trần Minh Hoàng,hoang.tm@example.com,Giám đốc kinh doanh (chủ trì)\n"
        "Nguyễn Thu Hà,ha.nt@example.com,Trưởng nhóm Marketing\n"
        "Lê Văn Đức,duc.lv@example.com,Kế toán\n"
        "Phạm Ngọc Lan,,Chăm sóc khách hàng (thư ký)\n", encoding="utf-8")
    print("Đã tạo:", *sorted(p.name for p in OUT.iterdir() if p.is_file()))


def ts(s):
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{sec:06.3f}"


if __name__ == "__main__":
    main()
