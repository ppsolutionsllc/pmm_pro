from __future__ import annotations

import base64
import hashlib
import io
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from app.core.time import utcnow

_CODE39 = {
    "0": "nnnwwnwnn",
    "1": "wnnwnnnnw",
    "2": "nnwwnnnnw",
    "3": "wnwwnnnnn",
    "4": "nnnwwnnnw",
    "5": "wnnwwnnnn",
    "6": "nnwwwnnnn",
    "7": "nnnwnnwnw",
    "8": "wnnwnnwnn",
    "9": "nnwwnnwnn",
    "A": "wnnnnwnnw",
    "B": "nnwnnwnnw",
    "C": "wnwnnwnnn",
    "D": "nnnnwwnnw",
    "E": "wnnnwwnnn",
    "F": "nnwnwwnnn",
    "G": "nnnnnwwnw",
    "H": "wnnnnwwnn",
    "I": "nnwnnwwnn",
    "J": "nnnnwwwnn",
    "K": "wnnnnnnww",
    "L": "nnwnnnnww",
    "M": "wnwnnnnwn",
    "N": "nnnnwnnww",
    "O": "wnnnwnnwn",
    "P": "nnwnwnnwn",
    "Q": "nnnnnnwww",
    "R": "wnnnnnwwn",
    "S": "nnwnnnwwn",
    "T": "nnnnwnwwn",
    "U": "wwnnnnnnw",
    "V": "nwwnnnnnw",
    "W": "wwwnnnnnn",
    "X": "nwnnwnnnw",
    "Y": "wwnnwnnnn",
    "Z": "nwwnwnnnn",
    "-": "nwnnnnwnw",
    ".": "wwnnnnwnn",
    " ": "nwwnnnwnn",
    "$": "nwnwnwnnn",
    "/": "nwnwnnnwn",
    "+": "nwnnnwnwn",
    "%": "nnnwnwnwn",
    "*": "nwnnwnwnn",
}

_ALLOWED = set(_CODE39.keys()) - {"*"}


def normalize_code39_value(value: str | None, *, max_len: int = 64) -> str:
    src = str(value or "").upper().strip()
    out = "".join(ch if ch in _ALLOWED else "-" for ch in src)
    out = out.strip("- ").strip()
    if not out:
        out = "PMM"
    return out[:max_len]


def build_unique_barcode_value(parts: Iterable[str | int | None]) -> str:
    ts = utcnow().strftime("%Y%m%d%H%M%S%f")
    base = "-".join(str(p) for p in parts if p is not None and str(p).strip())
    base = normalize_code39_value(base, max_len=46)
    nonce = hashlib.sha1(f"{base}|{ts}".encode("utf-8")).hexdigest()[:10].upper()
    return normalize_code39_value(f"{base}-{nonce}", max_len=60)


def build_code39_png_b64(value: str, *, narrow: int = 2, wide: int = 5, bar_height: int = 52) -> str:
    text = normalize_code39_value(value, max_len=60)
    encoded = f"*{text}*"

    inter_char_gap = narrow
    quiet = narrow * 10
    text_h = 14
    total_w = quiet * 2
    for idx, ch in enumerate(encoded):
        pattern = _CODE39[ch]
        total_w += sum(wide if unit == "w" else narrow for unit in pattern)
        if idx < len(encoded) - 1:
            total_w += inter_char_gap

    img = Image.new("RGB", (total_w, bar_height + text_h + 3), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    x = quiet
    for idx, ch in enumerate(encoded):
        pattern = _CODE39[ch]
        for unit_idx, unit in enumerate(pattern):
            width = wide if unit == "w" else narrow
            is_bar = (unit_idx % 2 == 0)
            if is_bar:
                draw.rectangle((x, 0, x + width - 1, bar_height), fill="black")
            x += width
        if idx < len(encoded) - 1:
            x += inter_char_gap

    draw.text((quiet, bar_height + 2), text, fill="black", font=font)

    out = io.BytesIO()
    img.save(out, format="PNG")
    return base64.b64encode(out.getvalue()).decode("ascii")
