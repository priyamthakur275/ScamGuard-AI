"""OCR tuned for chat screenshots (WhatsApp, Telegram, SMS apps).

Most Indian scams arrive on WhatsApp and people share them as screenshots.
Plain OCR of those images mixes in timestamps, ticks, "online"/"last seen",
the status bar and the encryption banner, and dark-mode screenshots read
poorly. This module:

1. prepares the image (dark-mode inversion, upscaling small images),
2. reads it line by line with positions (pytesseract image_to_data),
3. drops chat UI noise,
4. if it looks like a chat, splits lines into incoming (left-aligned, the
   other person) and outgoing (right-aligned, you) by horizontal position.

The scam check then scores the incoming side, i.e. what the sender wrote.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from PIL import Image, ImageOps, ImageStat

_NOISE = re.compile(
    r"^(\d{1,2}[:.]\d{2}\s*(am|pm)?\s*[✓✔vV/]*|today|yesterday|online|typing\.*|last seen.*|type a message|message|"
    r"messages and calls are end-to-end encrypted.*|tap to learn more|.*\b\d{1,3}%\s*$|[✓✔]+|\W{1,3})$",
    re.I,
)
_TRAILING_TIME = re.compile(r"\s+\d{1,2}[:.]\d{2}\s*(am|pm)?\s*[✓✔/vV]*\s*$", re.I)
_CHAT_HINTS = re.compile(r"last seen|online|type a message|end-to-end encrypted|whatsapp|\btyping\b", re.I)
_TIME = re.compile(r"\b\d{1,2}[:.]\d{2}\s*(am|pm)\b", re.I)


@dataclass
class ChatOcrResult:
    text: str
    is_chat: bool
    incoming: list[str] = field(default_factory=list)
    outgoing: list[str] = field(default_factory=list)
    header: str | None = None

    def metadata(self) -> dict:
        if not self.is_chat:
            return {"ocr_detected": True}
        return {
            "ocr_detected": True,
            "chat": {"incoming": self.incoming[:40], "outgoing": self.outgoing[:40], "header": self.header},
        }


def prepare(img: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(img.convert("RGB"))
    if ImageStat.Stat(gray).mean[0] < 110:  # dark-mode screenshot
        gray = ImageOps.invert(gray)
    if gray.width < 1000:
        scale = 1000 / gray.width
        gray = gray.resize((int(gray.width * scale), int(gray.height * scale)), Image.LANCZOS)
    return gray


def _lines(img: Image.Image) -> list[tuple[str, int, int, int]]:
    """Returns (text, left, right, top) per OCR line."""
    import pytesseract

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, timeout=25)
    groups: dict[tuple[int, int, int], list[int]] = {}
    for i, word in enumerate(data["text"]):
        if word and word.strip() and float(data["conf"][i]) > 30:
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            groups.setdefault(key, []).append(i)
    out = []
    for idxs in groups.values():
        words = " ".join(data["text"][i] for i in idxs).strip()
        left = min(data["left"][i] for i in idxs)
        right = max(data["left"][i] + data["width"][i] for i in idxs)
        top = min(data["top"][i] for i in idxs)
        out.append((words, left, right, top))
    return sorted(out, key=lambda r: r[3])


def read_screenshot(img: Image.Image) -> ChatOcrResult:
    prepared = prepare(img)
    width = prepared.width
    raw = _lines(prepared)
    all_text = "\n".join(t for t, *_ in raw)
    is_chat = bool(_CHAT_HINTS.search(all_text)) or len(_TIME.findall(all_text)) >= 2

    if not is_chat:
        return ChatOcrResult(text=all_text.strip(), is_chat=False)

    # Ignore the status bar / contact header band at the very top.
    header_cut = prepared.height * 0.09
    header_lines = [t for t, _, _, top in raw if top < header_cut * 1.6 and not _NOISE.match(t.strip())]
    incoming: list[str] = []
    outgoing: list[str] = []
    for text, left, right, top in raw:
        if top < header_cut:
            continue
        cleaned = _TRAILING_TIME.sub("", text).strip()
        if not cleaned or _NOISE.match(cleaned):
            continue
        centre = (left + right) / 2
        # Outgoing bubbles hug the right edge; incoming ones the left.
        if left > width * 0.30 and centre > width * 0.55:
            outgoing.append(cleaned)
        else:
            incoming.append(cleaned)

    analysed = "\n".join(incoming) if incoming else "\n".join(outgoing)
    return ChatOcrResult(
        text=analysed.strip(),
        is_chat=True,
        incoming=incoming,
        outgoing=outgoing,
        header=header_lines[0] if header_lines else None,
    )
