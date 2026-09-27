"""Regression coverage: extraction failures must never become fabricated evidence."""
import io
from unittest.mock import patch
import pytest
from fastapi import UploadFile
from PIL import Image
from reportlab.pdfgen import canvas
from app_service.services.extraction import ExtractionService


def image_upload():
    data = io.BytesIO()
    Image.new('RGB', (100, 100), 'white').save(data, format='PNG')
    data.seek(0)
    return UploadFile(filename='blank.png', file=data)


def test_empty_ocr_does_not_produce_a_prediction_payload():
    with patch('pytesseract.image_to_string', return_value=''):
        with pytest.raises(ValueError, match='extraction failed'):
            ExtractionService.extract(image_upload(), None, 'IMAGE')


def test_missing_ocr_does_not_analyze_a_filename():
    with patch('pytesseract.image_to_string', side_effect=RuntimeError('tesseract not installed')):
        with pytest.raises(ValueError, match='OCR is unavailable'):
            ExtractionService.extract(image_upload(), None, 'IMAGE')


def test_blank_pdf_is_not_analyzed():
    data = io.BytesIO()
    document = canvas.Canvas(data)
    document.showPage()
    document.save()
    data.seek(0)
    with pytest.raises(ValueError, match='no extractable text'):
        ExtractionService.extract(UploadFile(filename='blank.pdf', file=data), None, 'PDF')


@pytest.mark.parametrize('url', ['not a url', 'file:///etc/passwd', 'https://example.com:bad'])
def test_malformed_url_rejected(url):
    with pytest.raises(ValueError):
        ExtractionService.extract(None, url, 'URL')


def test_header_only_email_rejected():
    with pytest.raises(ValueError, match='no subject or readable'):
        ExtractionService.extract(None, 'From: sender@example.com\n\n', 'EMAIL')
