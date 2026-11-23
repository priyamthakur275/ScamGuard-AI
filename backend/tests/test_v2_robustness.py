"""v2: evasion-trick removal, Hindi/Hinglish intents, and the serving path."""

import pytest

from ml_common.preprocessing.robust import deobfuscate
from ml_service.inference.threat_scorer import ThreatScorer


@pytest.mark.parametrize("raw, plain", [
    ("Update your KYС now", "Update your KYC now"),                  # Cyrillic С
    ("ac​count blo​cked", "account blocked"),               # zero-width spaces
    ("c l i c k now", "click now"),                                   # spaced letters
    ("Dear H.D.F.C customer", "Dear HDFC customer"),                  # dotted acronym
    ("upd4te your acc0unt", "update your account"),                   # leetspeak
    ("hxxps://sbi-kyc[.]xyz", "https://sbi-kyc.xyz"),                 # defanged link
    ("visit sbi dot xyz", "visit sbi.xyz"),
    ("ＳＢＩ ＫＹＣ", "SBI KYC"),                                        # full-width letters
])
def test_deobfuscate_undoes_tricks(raw, plain):
    assert deobfuscate(raw) == plain


@pytest.mark.parametrize("text", [
    "Rs.500 debited from XX1234 at 10:30am on 2nd Dec, 4G pack",
    "I am a good boy",
    "e.g. this, i.e. that",
    "आपका खाता बंद",
    "covid19 vaccine slot booked",
])
def test_deobfuscate_leaves_normal_text_alone(text):
    assert deobfuscate(text) == text


def _intents(text):
    return set(ThreatScorer.intents(text)[0])


def test_hinglish_and_hindi_intents():
    assert "asks_for_secret" in _intents("jo OTP aaya hai wo batayein abhi")
    assert "legal_threat" in _intents("आपके नाम पर ड्रग्स का पार्सल पकड़ा गया है। गिरफ्तारी से बचने के लिए संपर्क करें")
    assert "pay_to_receive" in _intents("loan approve hai, processing fee bhejiye")
    assert "new_number_emergency" in _intents("bhai mera naya number hai, phone kho gaya")
    assert "move_money" in _intents("Rs 5000 PhonePe kar do is number pe")


def test_private_number_alone_is_weak_and_english_contact_lines_do_not_trigger_it():
    assert "call_private_number" not in _intents("Cust id: 9876543210 Amt Recvd: Rs.100, call 9876543210 for help")
    assert "call_private_number" in _intents("turant sampark karein 9876543210")


def test_hindi_protective_phrasing_counts_against():
    _, protective = ThreatScorer.intents("अपना OTP किसी को न बताएं। बैंक कभी नहीं मांगता।")
    assert "warns_not_to_share" in protective


def test_obfuscated_scam_scores_like_the_plain_one():
    s = ThreatScorer()
    plain = "Your account will be blocked today. Share the OTP to update KYC"
    tricky = "Your acc0unt will be bl​ocked today. Sh4re the 0TP to upd4te KYС"
    a = s.assess(0.5, [], deobfuscate(plain)).threat_score
    b = s.assess(0.5, [], deobfuscate(tricky)).threat_score
    assert a == b and a >= 0.5


def test_pipeline_stores_the_users_own_text(db_session):
    from app_service.services.message_service import MessageService
    text = "Your acc0unt is bl​ocked, upd4te KYС at hxxp://kyc-help[.]xyz"
    result = MessageService(db_session).analyze(None, text)
    assert result.text == text
    assert "Detected concepts" not in result.text
    assert result.verdict == "scam"


def test_review_band_matches_frontend():
    import re
    from pathlib import Path
    from ml_service.inference.threat_scorer import REVIEW_BAND, needs_review
    ts = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "utils.ts"
    if ts.exists():
        m = re.search(r"REVIEW_BAND = \{ low: ([\d.]+), high: ([\d.]+) \}", ts.read_text())
        assert m and (float(m.group(1)), float(m.group(2))) == REVIEW_BAND
    assert needs_review(0.3) and needs_review(0.69) and not needs_review(0.7) and not needs_review(0.29)
