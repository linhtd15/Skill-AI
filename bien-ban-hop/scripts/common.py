"""Hàm dùng chung cho Agent biên bản họp."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "BienBanHop"
MODELS = RUNTIME / "models"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


class BBError(Exception):
    """Lỗi hiển thị cho người dùng (tiếng Việt, không traceback)."""


def load_config() -> dict:
    return json.loads((SKILL_DIR / "config.json").read_text(encoding="utf-8"))


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, data):
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------- văn bản ----------
def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def strip_accents(s: str) -> str:
    """Bỏ dấu tiếng Việt, giữ nguyên độ dài từng ký tự (đ→d)."""
    out = []
    for ch in nfc(s):
        if ch in "đĐ":
            out.append("d" if ch == "đ" else "D")
            continue
        base = unicodedata.normalize("NFD", ch)[0]
        out.append(base)
    return "".join(out)


def norm(s: str) -> str:
    """Chuẩn hoá để so khớp: thường, bỏ dấu câu, gộp khoảng trắng (GIỮ dấu thanh)."""
    s = nfc(s).lower()
    s = re.sub(r"[^\w\s/]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_loose(s: str) -> str:
    """Chuẩn hoá lỏng: bỏ cả dấu thanh (dùng cho tên người, từ khoá)."""
    return norm(strip_accents(s))


def contains(hay: str, needle: str) -> bool:
    return norm(needle) in norm(hay)


# ---------- thời gian ----------
def fmt_t(sec) -> str:
    if sec is None:
        return "--:--"
    sec = int(round(float(sec)))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_t(s) -> float | None:
    if s is None or s == "":
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip().replace(",", ".")
    parts = s.split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None
    v = 0.0
    for p in parts:
        v = v * 60 + p
    return v


def clock(meta: dict, sec) -> str | None:
    """Đổi mốc ghi âm (giây) sang giờ đồng hồ nếu biết giờ bắt đầu."""
    g = (meta or {}).get("gio_bat_dau")
    if not g or sec is None:
        return None
    try:
        h, m = [int(x) for x in g.split(":")[:2]]
    except ValueError:
        return None
    t = dt.datetime(2000, 1, 1, h, m) + dt.timedelta(seconds=float(sec))
    return t.strftime("%H:%M")


def vn_date(d: dt.date | str | None) -> str:
    if not d:
        return "[CHƯA RÕ]"
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def vn_date_long(d) -> str:
    if not d:
        return "ngày [CHƯA RÕ]"
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    m = f"{d.month:02d}" if d.month < 3 else str(d.month)
    return f"ngày {d.day:02d} tháng {m} năm {d.year}"


# ---------- ffmpeg ----------
def ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ff(args, check=True):
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostdin", "-y", "-loglevel", "error", *map(str, args)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise BBError("ffmpeg lỗi: " + (r.stderr.strip().splitlines() or ["không rõ"])[-1])
    return r


def probe(path) -> dict:
    """Đọc thông tin media bằng ffmpeg -i (không cần ffprobe)."""
    r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostdin", "-i", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    err = r.stderr
    info = {"duration": None, "has_video": False, "has_audio": False, "w": None, "h": None, "raw": err}
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", err)
    if m:
        info["duration"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    for line in err.splitlines():
        if "Stream #" in line and "Video:" in line and "attached pic" not in line:
            info["has_video"] = True
            mm = re.search(r"(\d{2,5})x(\d{2,5})", line)
            if mm:
                info["w"], info["h"] = int(mm[1]), int(mm[2])
        if "Stream #" in line and "Audio:" in line:
            info["has_audio"] = True
    return info


def open_file(p):
    try:
        os.startfile(str(p))  # type: ignore[attr-defined]
    except Exception:
        pass


def slug(s: str, n=40) -> str:
    s = norm_loose(s).replace(" ", "-")
    s = re.sub(r"[^a-z0-9\-]", "", s)
    return s[:n].strip("-") or "cuoc-hop"


def initials(name: str) -> str:
    parts = [p for p in nfc(name).split() if p]
    if not parts:
        return "?"
    return parts[-1][0].upper()
