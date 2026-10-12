import shutil
from pathlib import Path

import pytest
from PIL import Image

from app_service.services.chat_ocr import read_screenshot

pytestmark = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
FIXTURE = Path(__file__).parent / "fixtures" / "whatsapp_dark_scam.png"


def test_dark_whatsapp_screenshot_is_split_into_sender_and_user():
    result = read_screenshot(Image.open(FIXTURE))
    assert result.is_chat
    incoming = " ".join(result.incoming).lower()
    assert "otp" in incoming and "blocked" in incoming
    assert any("who is this" in line.lower() for line in result.outgoing)
    assert "who is this" not in result.text.lower()  # only the sender's side is scored
    assert "10:42" not in result.text and "type a message" not in result.text.lower()
