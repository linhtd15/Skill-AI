"""Bước 2: tách giọng (diarization) + gán tên người nói CÓ CĂN CỨ.

Căn cứ được chấp nhận (ghi rõ vào speakers.json):
  - tu_gioi_thieu : người nói tự giới thiệu ("tôi là Hà", "em là Đức phòng kế toán")
  - duoc_goi_ten  : câu ngay trước do người khác nói có gọi tên ("mời anh Đức", "Hà ơi")
  - nhan_video    : nhãn tên hiển thị trên video Meet/Zoom/Teams (đọc bằng OCR của Windows)
  - nhan_transcript: tên người nói có sẵn trong file transcript (.vtt/.docx của Teams/Zoom)
Không đủ căn cứ hoặc mâu thuẫn → "Chưa xác định" để Claude hỏi người dùng.
"""
from __future__ import annotations

import asyncio
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from common import MODELS, nfc, norm_loose, run_ff

UNKNOWN = "Chưa xác định"
HONOR = r"(?i:anh|chị|chi|em|ông|bà|bạn|cô|chú|bác)"
CAP = r"[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]"
NAME = rf"({CAP}[\wÀ-ỹ]*(?:\s+{CAP}[\wÀ-ỹ]*){{0,3}})"


# ------------------------------------------------------------ diarization
def _embedder():
    import sherpa_onnx
    model = MODELS / "speaker-embedding.onnx"
    if not model.exists():
        return None
    cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(model), num_threads=4)
    return sherpa_onnx.SpeakerEmbeddingExtractor(cfg)


def _mfcc_embed(x, sr=16000):
    """Dự phòng khi thiếu mô hình: đặc trưng phổ log-mel trung bình + độ lệch."""
    n = 400
    hop = 160
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    bins = np.linspace(0, spec.shape[1], 41).astype(int)
    mel = np.stack([spec[:, a:b].mean(1) for a, b in zip(bins[:-1], bins[1:])], 1)
    mel = np.log(mel + 1e-9)
    mel -= mel.mean(0)
    return np.concatenate([mel.std(0), np.percentile(mel, 90, 0)])


def _cluster(emb: np.ndarray, thr: float, k: int | None):
    """Gộp cụm phân cấp (average linkage, cosine). Dừng khi khoảng cách > thr hoặc đủ k cụm."""
    e = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    clusters = [[i] for i in range(len(e))]
    cent = [e[i].copy() for i in range(len(e))]
    while len(clusters) > 1:
        C = np.stack(cent)
        C = C / (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)
        sim = C @ C.T
        np.fill_diagonal(sim, -9)
        i, j = np.unravel_index(np.argmax(sim), sim.shape)
        dist = 1 - sim[i, j]
        if k is not None and len(clusters) <= k:
            break
        if k is None and dist > thr:
            break
        clusters[i] += clusters[j]
        cent[i] = e[clusters[i]].mean(0)
        del clusters[j], cent[j]
    lab = np.zeros(len(e), int)
    for ci, idx in enumerate(clusters):
        lab[idx] = ci
    return lab


def diarize(wav: Path, segs: list, cfg, n_speakers: int | None = None, log=print):
    import soundfile as sf
    audio, sr = sf.read(str(wav), dtype="float32")
    ext = _embedder()
    log("  • Tách giọng bằng " + ("mô hình nhận dạng giọng nói (sherpa-onnx)" if ext else "đặc trưng phổ (dự phòng)"))
    min_len = cfg["nguoi_noi"]["thoi_luong_toi_thieu_giay"]
    idx, embs = [], []
    for i, s in enumerate(segs):
        if s.get("flag"):
            continue
        a, b = int(s["start"] * sr), int(s["end"] * sr)
        if (b - a) < min_len * sr:
            c = (a + b) // 2
            a, b = max(0, c - int(min_len * sr / 2)), c + int(min_len * sr / 2)
        x = audio[a:b]
        if len(x) < sr * 0.3:
            continue
        if ext:
            st = ext.create_stream()
            st.accept_waveform(sr, x)
            st.input_finished()
            v = np.array(ext.compute(st))
        else:
            v = _mfcc_embed(x, sr)
        idx.append(i)
        embs.append(v)
    if not embs:
        return segs
    lab = _cluster(np.stack(embs), cfg["nguoi_noi"]["nguong_cosine_gop_cum"], n_speakers)
    order = {}
    for i, l in zip(idx, lab):
        order.setdefault(l, f"S{len(order) + 1}")
        segs[i]["speaker"] = order[l]
    # đoạn ngắn không tính được: lấy theo đoạn liền trước
    last = None
    for s in segs:
        if s.get("speaker"):
            last = s["speaker"]
        elif not s.get("flag"):
            s["speaker"] = last or "S1"
    return segs


# ------------------------------------------------------------ OCR nhãn tên trên video
async def _ocr_async(paths):
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage import FileAccessMode, StorageFile
    eng = OcrEngine.try_create_from_user_profile_languages()
    out = {}
    for p in paths:
        try:
            f = await StorageFile.get_file_from_path_async(str(Path(p).resolve()))
            stream = await f.open_async(FileAccessMode.READ)
            dec = await BitmapDecoder.create_async(stream)
            bmp = await dec.get_software_bitmap_async()
            res = await eng.recognize_async(bmp)
            out[p] = [ln.text for ln in res.lines]
        except Exception:  # noqa: BLE001
            out[p] = []
    return out


def ocr_images(paths):
    try:
        return asyncio.run(_ocr_async(paths))
    except Exception:  # noqa: BLE001
        return {}


def video_labels(video: Path, segs, work: Path, cfg, log=print, cap=160):
    """OCR nhãn tên người nói tại giữa MỖI đoạn (tối đa `cap` đoạn, lấy đều). → {seg_id: (t, văn bản OCR)}"""
    from PIL import Image
    x1, y1, x2, y2 = cfg["nguoi_noi"]["vung_nhan_ten_video"]
    d = work / "_ocr"
    d.mkdir(exist_ok=True)
    cand = [s for s in segs if s.get("speaker") and not s.get("flag")]
    if len(cand) > cap:
        step = len(cand) / cap
        cand = [cand[int(i * step)] for i in range(cap)]
    jobs = {}
    for s in cand:
        t = (s["start"] + s["end"]) / 2
        p = d / f"seg{s['id']:04d}.png"
        run_ff(["-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", p], check=False)
        if p.exists():
            im = Image.open(p)
            W, H = im.size
            crop = im.crop((int(x1 * W), int(y1 * H), int(x2 * W), int(y2 * H)))
            crop.resize((crop.width * 2, crop.height * 2)).save(p)
            jobs[str(p)] = (s["id"], t)
    if not jobs:
        return {}
    log(f"  • Đọc nhãn tên trên video ({len(jobs)} khung hình, OCR của Windows)")
    texts = ocr_images(list(jobs))
    out = {}
    for p, lines in texts.items():
        sid, t = jobs[p]
        txt = " ".join(lines).strip()
        if txt:
            out[sid] = (round(t, 1), txt)
    return out


def refine_by_labels(segs, labels, participants, log=print):
    """Một cụm giọng mà nhãn video cho thấy ≥2 người khác nhau (mỗi người ≥2 đoạn) → tách cụm theo nhãn."""
    seg_name = {}
    for sid, (t, txt) in labels.items():
        n = _match_participant(txt, participants) if participants else None
        if n:
            seg_name[sid] = n
    by_c = defaultdict(list)
    for s in segs:
        if s.get("speaker"):
            by_c[s["speaker"]].append(s)
    next_id = max([int(c[1:]) for c in by_c if c[1:].isdigit()] or [0]) + 1
    name_to_c = {}
    for c, lst in sorted(by_c.items()):
        cnt = Counter(seg_name[s["id"]] for s in lst if s["id"] in seg_name)
        if len([n for n, k in cnt.items() if k >= 2]) < 2:
            continue
        major = cnt.most_common(1)[0][0]
        for n, k in cnt.items():
            if n == major or k < 2:
                continue
            if n not in name_to_c:
                name_to_c[n] = f"S{next_id}"
                next_id += 1
            moved = [s for s in lst if seg_name.get(s["id"]) == n]
            for s in moved:
                s["speaker"] = name_to_c[n]
            log(f"  • Tách {len(moved)} đoạn khỏi cụm {c} sang {name_to_c[n]} theo nhãn tên video “{n}”")
    return seg_name


# ------------------------------------------------------------ căn cứ trong lời nói
def _match_participant(raw: str, participants):
    """Khớp tên thô (có thể không dấu, chỉ tên gọi) với danh sách người tham gia."""
    r = norm_loose(raw)
    if not r:
        return None
    hits = []
    for p in participants:
        full = norm_loose(p["ten"])
        if not full:
            continue
        given = full.split()[-1]
        if r == full or full in r or (len(r.split()) > 1 and r in full):
            hits.append(p["ten"])
        elif re.search(rf"\b{re.escape(given)}\b", r):
            hits.append(p["ten"])
    hits = list(dict.fromkeys(hits))
    return hits[0] if len(hits) == 1 else None


def speech_evidence(segs, participants):
    ev = defaultdict(list)
    for i, s in enumerate(segs):
        if s.get("flag") or not s.get("speaker"):
            continue
        t = nfc(s["text"])
        for m in re.finditer(rf"\b(?i:tôi|em|mình|tớ)\s+(?i:là|tên là)\s+{NAME}", t):
            ev[s["speaker"]].append(("tu_gioi_thieu", m[1], s["id"], m[0]))
        m = re.search(rf"(?i:mời|xin mời|nhờ|cảm ơn)\s+{HONOR}\s+{NAME}", t)
        m2 = re.search(rf"{NAME}\s+(?:ơi|nhé)\b", t)
        for mm in (m, m2):
            if not mm:
                continue
            # người được gọi tên = người nói KHÁC tiếp theo
            for nx in segs[i + 1:i + 3]:
                if nx.get("speaker") and nx["speaker"] != s["speaker"] and not nx.get("flag"):
                    ev[nx["speaker"]].append(("duoc_goi_ten", mm[1], s["id"], mm[0]))
                    break
    out = defaultdict(list)
    for spk, items in ev.items():
        for kind, raw, sid, quote in items:
            name = _match_participant(raw, participants) if participants else None
            if not participants:
                name = raw.strip()
            if name:
                out[spk].append({"loai": kind, "ten": name, "seg": sid, "trich": quote})
    return out


def assign_names(segs, participants, video: Path | None, work: Path, cfg, log=print):
    speakers = sorted({s["speaker"] for s in segs if s.get("speaker")}, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
    talk = Counter()
    for s in segs:
        if s.get("speaker") and not s.get("flag"):
            talk[s["speaker"]] += s["end"] - s["start"]
    labels = {}
    if video is not None:
        labels = video_labels(video, segs, work, cfg, log)
        refine_by_labels(segs, labels, participants, log)
        speakers = sorted({s["speaker"] for s in segs if s.get("speaker")}, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
        talk = Counter()
        for s in segs:
            if s.get("speaker") and not s.get("flag"):
                talk[s["speaker"]] += s["end"] - s["start"]
    evid = speech_evidence(segs, participants)
    spk_of = {s["id"]: s.get("speaker") for s in segs}
    for sid, (t, txt) in labels.items():
        name = _match_participant(txt, participants) if participants else None
        if name and spk_of.get(sid):
            evid[spk_of[sid]].append({"loai": "nhan_video", "ten": name, "seg": sid, "trich": f"OCR “{txt}” lúc {t}s"})
    weight = {"tu_gioi_thieu": 3, "nhan_video": 2, "duoc_goi_ten": 1, "nhan_transcript": 3}
    result = {}
    for spk in speakers:
        sc = Counter()
        for e in evid.get(spk, []):
            sc[e["ten"]] += weight[e["loai"]]
        name, conf = UNKNOWN, "thap"
        if sc:
            (top, v), *rest = sc.most_common()
            second = rest[0][1] if rest else 0
            if v >= 2 and v >= 2 * second:
                name, conf = top, ("cao" if v >= 3 else "trung_binh")
        result[spk] = {"ten": name, "do_tin": conf, "can_cu": evid.get(spk, []),
                       "thoi_luong_noi": round(talk[spk], 1)}
    # một tên không được gán cho 2 cụm: giữ cụm có điểm cao nhất
    by_name = defaultdict(list)
    for spk, r in result.items():
        if r["ten"] != UNKNOWN:
            by_name[r["ten"]].append(spk)
    for name, spks in by_name.items():
        if len(spks) > 1:
            for spk in spks:
                result[spk]["ghi_chu"] = f"Nhiều cụm giọng cùng khớp tên {name} – có thể tách giọng nhầm, cần xác nhận."
                result[spk]["do_tin"] = "thap"
    return result


def from_labels(segs, participants):
    """Transcript đã có tên người nói: ánh xạ nhãn → S1.., căn cứ = nhãn transcript."""
    labels = {}
    for s in segs:
        lb = s.get("speaker_label")
        if lb:
            labels.setdefault(lb, f"S{len(labels) + 1}")
            s["speaker"] = labels[lb]
    res = {}
    for lb, spk in labels.items():
        name = (_match_participant(lb, participants) if participants else None) or lb
        dur = sum((s["end"] or 0) - (s["start"] or 0) for s in segs if s.get("speaker") == spk and s.get("start") is not None)
        res[spk] = {"ten": name, "do_tin": "cao", "thoi_luong_noi": round(dur, 1),
                    "can_cu": [{"loai": "nhan_transcript", "ten": name, "seg": None, "trich": f"Nhãn “{lb}” trong file transcript"}]}
    return res
