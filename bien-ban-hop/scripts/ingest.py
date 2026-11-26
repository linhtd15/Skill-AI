"""Bước 1: nhận đầu vào → transcript.json (phân đoạn có mốc thời gian).

Hỗ trợ: .txt .docx .vtt .srt (transcript) | .mp3 .wav .m4a .aac .ogg .flac (âm thanh)
        | .mp4 .mov .mkv .webm .avi (video, bản ghi Google Meet/Zoom/Teams).
"""
from __future__ import annotations

import re
from pathlib import Path

from common import BBError, MODELS, contains, load_config, norm, parse_t, probe, run_ff

TRANSCRIPT_EXT = {".txt", ".docx", ".vtt", ".srt"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


def detect(path: Path) -> str:
    if not path.exists():
        raise BBError(f"Không tìm thấy file: {path}")
    if path.is_dir():
        raise BBError(f"Đây là thư mục, không phải file: {path}")
    ext = path.suffix.lower()
    if ext not in TRANSCRIPT_EXT | AUDIO_EXT | VIDEO_EXT:
        raise BBError(f"Định dạng '{ext or '(không có đuôi)'}' không được hỗ trợ. "
                      "Hãy dùng transcript (.txt .docx .vtt .srt), âm thanh (.mp3 .wav .m4a) hoặc video (.mp4).")
    if path.stat().st_size == 0:
        raise BBError(f"File rỗng (0 byte): {path.name}")
    if ext in TRANSCRIPT_EXT:
        return "transcript"
    info = probe(path)
    if not info["has_audio"]:
        if info["duration"] is None and not info["has_video"]:
            raise BBError(f"File hỏng hoặc không phải media hợp lệ: {path.name}. ffmpeg không đọc được.")
        raise BBError(f"File {path.name} không có kênh âm thanh nên không phiên âm được.")
    if not info["duration"] or info["duration"] < 1:
        raise BBError(f"File {path.name} quá ngắn hoặc hỏng (thời lượng không xác định).")
    return "video" if info["has_video"] and ext in VIDEO_EXT else "audio"


# ------------------------------------------------------------ transcript
TS = r"(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)"


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        try:
            import docx
            d = docx.Document(str(path))
        except Exception as e:  # noqa: BLE001
            raise BBError(f"File Word hỏng hoặc không đọc được: {path.name} ({e.__class__.__name__}).")
        return "\n".join(p.text for p in d.paragraphs)
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp1258", "latin-1"):
        try:
            txt = raw.decode(enc)
            if enc == "utf-16" and not raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
                continue
            return txt
        except UnicodeDecodeError:
            continue
    raise BBError(f"Không giải mã được nội dung file {path.name}.")


def parse_cues(text: str):
    """VTT / SRT."""
    segs = []
    blocks = re.split(r"\n\s*\n", text.replace("\r", ""))
    for b in blocks:
        lines = [l for l in b.strip().split("\n") if l.strip()]
        for i, l in enumerate(lines):
            m = re.match(rf"\s*{TS}\s*-->\s*{TS}", l)
            if m:
                body = " ".join(lines[i + 1:]).strip()
                spk = None
                mv = re.match(r"<v\s+([^>]+)>(.*)", body)
                if mv:
                    spk, body = mv[1].strip(), mv[2]
                body = re.sub(r"</?[^>]+>", "", body).strip()
                ms = re.match(r"^([A-ZÀ-Ỹ][^:]{1,40}):\s+(.*)", body)
                if not spk and ms:
                    spk, body = ms[1].strip(), ms[2]
                if body:
                    segs.append({"start": parse_t(m[1]), "end": parse_t(m[2]), "speaker_label": spk, "text": body})
                break
    return segs


def parse_plain(text: str):
    """TXT/DOCX: '[00:01:02] Tên: câu', '00:01:02 Tên: câu', 'Tên  0:01:02' + dòng nội dung (Teams), 'Tên: câu'."""
    segs = []
    lines = [l.rstrip() for l in text.replace("\r", "").split("\n")]
    pending_spk, pending_t = None, None
    for l in lines:
        s = l.strip()
        if not s:
            continue
        m = re.match(rf"^\[?{TS}\]?\s*[-–]?\s*([^:]{{1,40}}?):\s+(.+)$", s)
        if m:
            segs.append({"start": parse_t(m[1]), "speaker_label": m[2].strip(), "text": m[3].strip()})
            continue
        m = re.match(rf"^([^:\d][^:]{{0,40}}?)\s*[\[(]?{TS}[\])]?\s*$", s)  # Teams: "Tên 0:01:02"
        if m:
            pending_spk, pending_t = m[1].strip(), parse_t(m[2])
            continue
        m = re.match(rf"^\[?{TS}\]?\s+(.+)$", s)
        if m:
            segs.append({"start": parse_t(m[1]), "speaker_label": None, "text": m[2].strip()})
            continue
        m = re.match(r"^([A-ZÀ-Ỹ][\wÀ-ỹ .]{0,38}):\s+(.+)$", s)
        if m:
            segs.append({"start": pending_t, "speaker_label": m[1].strip(), "text": m[2].strip()})
            pending_t = None
            continue
        if pending_spk:
            segs.append({"start": pending_t, "speaker_label": pending_spk, "text": s})
            pending_spk, pending_t = None, None
            continue
        if segs:
            segs[-1]["text"] += " " + s
        else:
            segs.append({"start": None, "speaker_label": None, "text": s})
    for i, sg in enumerate(segs):
        if sg.get("end") is None:
            nxt = next((x["start"] for x in segs[i + 1:] if x.get("start") is not None), None)
            sg["end"] = nxt if nxt is not None else (sg["start"] + 10 if sg["start"] is not None else None)
    return segs


def load_transcript(path: Path):
    text = _read_text(path)
    if not text.strip():
        raise BBError(f"File transcript không có nội dung: {path.name}")
    segs = parse_cues(text) if path.suffix.lower() in (".vtt", ".srt") or "-->" in text else parse_plain(text)
    if not segs:
        raise BBError(f"Không tách được câu nào từ {path.name}. Kiểm tra định dạng transcript.")
    return segs


# ------------------------------------------------------------ media
def extract_wav(src: Path, dst: Path, start=None, end=None, clean=False):
    args = []
    if start is not None:
        args += ["-ss", f"{max(0, start):.2f}"]
    args += ["-i", str(src)]
    if end is not None and start is not None:
        args += ["-t", f"{end - start:.2f}"]
    af = "highpass=f=150,lowpass=f=4000,afftdn=nf=-25" if clean else None
    args += ["-vn", "-ac", "1", "-ar", "16000"]
    if af:
        args += ["-af", af]
    args += ["-c:a", "pcm_s16le", str(dst)]
    run_ff(args)


_MODEL = None


def whisper_model(cfg):
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        pa = cfg["phien_am"]
        _MODEL = WhisperModel(pa["mo_hinh_whisper"], device=pa.get("thiet_bi", "cpu"),
                              compute_type=pa.get("kieu_tinh", "int8"),
                              download_root=str(MODELS / "whisper"))
    return _MODEL


def is_hallucination(text: str, cfg) -> str | None:
    for p in cfg["phien_am"]["cau_ao_giac"]:
        if contains(text, p):
            return p
    words = norm(text).split()
    if len(words) >= 9:  # vòng lặp lặp lại cùng cụm
        tri = [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
        if tri and max(tri.count(t) for t in set(tri)) >= 4:
            return "lặp lại bất thường"
    return None


def _split_words(seg, gap):
    """Tách một đoạn Whisper tại khoảng lặng giữa các từ (thường là chỗ đổi người nói)."""
    words = list(seg.words or [])
    if not words:
        return [(seg.start, seg.end, seg.text.strip())]
    parts, cur = [], [words[0]]
    for w in words[1:]:
        if w.start - cur[-1].end >= gap:
            parts.append(cur)
            cur = [w]
        else:
            cur.append(w)
    parts.append(cur)
    return [(p[0].start, p[-1].end, "".join(w.word for w in p).strip()) for p in parts]


def transcribe(wav: Path, cfg, prompt: str | None = None, offset=0.0, strict=False):
    import soundfile as sf
    model = whisper_model(cfg)
    pa = cfg["phien_am"]
    audio, _sr = sf.read(str(wav), dtype="float32")  # wav 16 kHz mono do ffmpeg tạo, không cần PyAV
    segs, _ = model.transcribe(
        audio, language=pa.get("ngon_ngu", "vi"), beam_size=5, vad_filter=True, word_timestamps=True,
        vad_parameters={"min_silence_duration_ms": 400, "threshold": 0.6 if strict else 0.5},
        condition_on_previous_text=False, initial_prompt=None if strict else prompt,
        temperature=0.0 if strict else [0.0, 0.2, 0.4],
        no_speech_threshold=0.5 if strict else 0.6)
    out = []
    for s in segs:
        for st, en, t in _split_words(s, pa.get("tach_khi_lang_giay", 0.45)):
            if t:
                out.append({"start": round(st + offset, 2), "end": round(en + offset, 2), "text": t,
                            "no_speech": round(s.no_speech_prob, 3), "logprob": round(s.avg_logprob, 3)})
    return out


def flag_repeats(segs, duration=None, min_run=3):
    """Đánh dấu ảo giác dạng lặp: ≥3 đoạn liên tiếp giống hệt nhau (≥3 từ), hoặc nằm ngoài thời lượng bản ghi."""
    flags = [None] * len(segs)
    i = 0
    while i < len(segs):
        j = i
        key = norm(segs[i]["text"])
        while j + 1 < len(segs) and norm(segs[j + 1]["text"]) == key:
            j += 1
        if j - i + 1 >= min_run and len(key.split()) >= 3:
            for k in range(i, j + 1):
                flags[k] = f"lặp lại {j - i + 1} lần liên tiếp"
        i = j + 1
    if duration:
        for k, s in enumerate(segs):
            if s["start"] > duration + 0.5:
                flags[k] = flags[k] or "nằm ngoài thời lượng bản ghi"
    return flags


def transcribe_media(src: Path, work: Path, cfg, names=None, log=print, duration=None):
    wav = work / "audio.wav"
    extract_wav(src, wav)
    pa = cfg["phien_am"]
    prompt = "Biên bản cuộc họp tiếng Việt. " + pa.get("tu_vung_goi_y", "")
    if names:
        prompt += " Người tham dự: " + ", ".join(names) + "."
    log("  • Đang phiên âm (Whisper chạy trên máy, có thể mất vài phút)…")
    segs = transcribe(wav, cfg, prompt)
    rep = flag_repeats(segs, duration)
    bad = [i for i, s in enumerate(segs) if rep[i] or is_hallucination(s["text"], cfg)]
    if not bad:
        return segs, []
    # gộp các đoạn bị đánh dấu liền nhau thành vùng để phiên âm lại
    regions, cur = [], [bad[0]]
    for i in bad[1:]:
        if i == cur[-1] + 1:
            cur.append(i)
        else:
            regions.append(cur)
            cur = [i]
    regions.append(cur)
    filtered, final, drop = [], [], set(bad)
    final = [s for i, s in enumerate(segs) if i not in drop]
    for reg in regions:
        first, last = segs[reg[0]], segs[reg[-1]]
        st, en = first["start"], min(last["end"], duration or last["end"])
        why = rep[reg[0]] or is_hallucination(first["text"], cfg)
        log(f"  • Câu ảo giác [{st:.0f}s–{en:.0f}s] ×{len(reg)}: “{first['text']}” ({why}) → phiên âm lại đoạn này")
        redo = []
        if en - st > 0.5:
            tmp = work / "_redo.wav"
            extract_wav(src, tmp, max(0, st - 0.3), en + 0.3, clean=True)
            bad_texts = {norm(segs[i]["text"]) for i in reg}
            redo = [r for r in transcribe(tmp, cfg, offset=max(0, st - 0.3), strict=True)
                    if not is_hallucination(r["text"], cfg) and norm(r["text"]) not in bad_texts]
            if any(flag_repeats(redo)):
                redo = []
            tmp.unlink(missing_ok=True)
        filtered.append({"start": st, "end": en, "text": first["text"], "so_lan": len(reg), "ly_do": why,
                         "phien_am_lai": " ".join(r["text"] for r in redo) or None})
        if redo:
            final.extend(redo)
        elif (duration is None or st < duration):
            final.append({"start": st, "end": en, "text": "[không nghe rõ – nhạc nền/tạp âm]", "flag": "ao_giac"})
    final.sort(key=lambda x: x["start"])
    return final, filtered
