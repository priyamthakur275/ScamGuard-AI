import io
import zipfile

import pytest

from app_service.services import safety_tools as st


def _qr_png(data: str) -> bytes:
    qrcode = pytest.importorskip("qrcode")
    buf = io.BytesIO()
    qrcode.make(data).save(buf, format="PNG")
    return buf.getvalue()


def _apk() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("AndroidManifest.xml", "x")
        z.writestr("classes.dex", "x")
    return buf.getvalue()


def test_parse_upi_uri():
    u = st.parse_upi_uri("upi://pay?pa=refund.desk@ybl&pn=SBI%20Refund&am=4999&tn=Receive%20refund")
    assert u == {"vpa": "refund.desk@ybl", "payee_name": "SBI Refund", "amount": "4999", "note": "Receive refund", "mode": "pay"}
    assert st.parse_upi_uri("https://example.com") is None


def test_receive_money_qr_is_high_risk():
    r = st.analyze_upi("refund.desk@ybl", "SBI Refund", "4999", "Receive refund", source="qr")
    titles = [f.title for f in r.flags]
    assert r.risk == "high" and "QR code says you will receive money" in titles and "Bait word in the UPI ID" in titles


def test_normal_shop_payment_is_low_risk():
    r = st.analyze_upi("ramesh.kirana@okaxis", "Ramesh Kirana Store", "250", reason="shop")
    assert r.risk == "low"


def test_name_mismatch_and_reasons():
    assert st.analyze_upi("abc123@ybl", "Sunil Kumar", expected_name="Ramesh Kirana", reason="shop").risk == "high"
    for reason in ("receive", "kyc", "job", "customs", "police", "electricity"):
        assert st.analyze_upi(reason=reason).risk == "high"
    assert st.analyze_upi(reason="investment").risk == "medium"


def test_file_checks():
    assert st.check_file("SBI_Rewards.apk", _apk()).risk == "high"
    disguised = st.check_file("invoice.pdf", _apk())
    assert {"The name lies about the file type"} <= {f.title for f in disguised.flags}
    assert st.check_file("setup.pdf.exe", b"MZ" + b"\0" * 100).risk == "high"
    assert st.check_file("bill.pdf", b"%PDF-1.4 /OpenAction /JavaScript").risk == "medium"
    ok = st.check_file("photo.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
    assert ok.risk == "low" and ok.facts["sha256"] and ok.facts["virustotal_url"].endswith(ok.facts["sha256"])


def test_qr_endpoint_upi(client):
    png = _qr_png("upi://pay?pa=cashback.reward@ybl&pn=Paytm%20Cashback&am=1&tn=Claim%20cashback")
    res = client.post("/api/v1/tools/qr", files={"file": ("qr.png", png, "image/png")})
    body = res.json()
    assert res.status_code == 200 and body["kind"] == "upi" and body["risk"] == "high"
    assert body["facts"]["upi_id"] == "cashback.reward@ybl"


def test_qr_endpoint_link_runs_scan(client):
    res = client.post("/api/v1/tools/qr", files={"file": ("qr.png", _qr_png("http://sbi-kyc-update.xyz/login"), "image/png")})
    body = res.json()
    assert body["kind"] == "url" and body["analysis"]["verdict"]


def test_qr_endpoint_no_code(client):
    buf = io.BytesIO()
    from PIL import Image

    Image.new("RGB", (60, 60), "white").save(buf, format="PNG")
    assert client.post("/api/v1/tools/qr", files={"file": ("x.png", buf.getvalue(), "image/png")}).status_code == 422


def test_pay_check_and_file_endpoints(client):
    r = client.post("/api/v1/tools/pay-check", json={"upi_id": "kyc.update@ybl", "reason": "kyc"}).json()
    assert r["risk"] == "high"
    assert any(x["id"] == "receive" for x in client.get("/api/v1/tools/pay-reasons").json())
    f = client.post("/api/v1/tools/file", files={"file": ("wedding_card.apk", _apk(), "application/octet-stream")}).json()
    assert f["risk"] == "high" and f["facts"]["detected_type"] == "android-app"


def test_what_if_explains_the_score(client):
    text = "Dear customer your SBI account will be blocked today. Share the OTP sent to your phone at http://sbi-kyc.xyz immediately"
    r = client.post("/api/v1/tools/what-if", json={"text": text}).json()
    assert r["score"] > 0.5 and r["parts"]
    assert all(set(p) == {"label", "phrase", "score_alone", "lift", "drop"} for p in r["parts"])
    assert r["parts"] == sorted(r["parts"], key=lambda p: p["lift"], reverse=True)
    assert r["baseline"] < r["score"] and r["parts"][0]["lift"] > 0
    assert isinstance(r["redundant"], bool)  # whether one cue alone is enough depends on the model version
    plain = client.post("/api/v1/tools/what-if", json={"text": "See you at the station at 6, bring the tickets"}).json()
    assert plain["parts"] == [] and plain["baseline"] is None


def test_what_if_ignores_scan_annotation(client):
    text = "Share the OTP sent to your phone at http://sbi-kyc.xyz"
    a = client.post("/api/v1/tools/what-if", json={"text": text}).json()
    b = client.post("/api/v1/tools/what-if", json={"text": text + "\n\nDetected language/concepts (heuristic):\nDetected concepts: KYC, OTP."}).json()
    assert a == b


WA_CHAT = """14/10/26, 9:01 pm - Messages and calls are end-to-end encrypted.
14/10/26, 9:02 pm - Rahul: Sir your SBI account KYC is pending, it will be blocked today
14/10/26, 9:03 pm - Me: what should I do
14/10/26, 9:05 pm - Rahul: Share the OTP sent to your number to verify
it is urgent
14/10/26, 9:06 pm - Me: <Media omitted>
14/10/26, 9:07 pm - Rahul: Also transfer Rs 5000 to this account to keep it safe"""


def test_split_chat_formats():
    msgs = st.split_chat(WA_CHAT)
    assert [m["sender"] for m in msgs] == ["Rahul", "Me", "Rahul", "Rahul"]   # system lines and media dropped
    assert msgs[2]["text"].endswith("it is urgent")                         # continuation line joined
    assert [m["sender"] for m in st.split_chat("Asha: hi\nRavi: hello there")] == ["Asha", "Ravi"]
    assert len(st.split_chat("first message\n\nsecond message\nstill second")) == 2
    assert len(st.split_chat("one\ntwo\nthree")) == 3


def test_timeline_finds_the_turning_point(client):
    r = client.post("/api/v1/tools/timeline", json={"text": WA_CHAT}).json()
    assert len(r["messages"]) == 4
    assert all(0 <= m["risk_score"] <= 1 and m["verdict"] for m in r["messages"])
    seen = r["stage_first_seen"]
    if seen["ask"] is not None or seen["cashout"] is not None:
        expected = min(i for i in (seen["ask"], seen["cashout"]) if i is not None)
        assert r["turning_point"] == expected and "message" in r["summary"]
    for m in r["messages"]:
        assert set(m["stages"]) <= {"hook", "pressure", "ask", "cashout"}
    assert r["overall"]["verdict"] and r["note"]


def test_timeline_harmless_chat_and_validation(client):
    r = client.post("/api/v1/tools/timeline", json={"text": "Asha: are we meeting at 6?\nRavi: yes, see you at the cafe"}).json()
    assert r["turning_point"] is None and r["stages_reached"] == []
    assert client.post("/api/v1/tools/timeline", json={"text": "just one single line here"}).status_code == 422
    assert client.post("/api/v1/tools/timeline", json={"text": "x"}).status_code == 422



def test_model_xray_parts_add_up_to_the_model_output(client):
    import math

    scam = client.post("/api/v1/tools/model-xray", json={"text": "Your SBI account will be blocked today. Update KYC now at http://sbi-kyc.xyz"}).json()
    total = scam["bias"] + scam["words_up_total"] + scam["words_down_total"] + scam["char_total"]
    assert abs(total - scam["logit"]) < 1e-3
    assert abs(1 / (1 + math.exp(-scam["logit"])) - scam["probability"]) < 1e-3
    assert scam["probability"] > 0.9 and scam["words_up"] and scam["words_up"][0]["push"] > 0
    assert all(w["push"] < 0 for w in scam["words_down"])
    assert scam["vocabulary"] > 1000 and scam["active_features"] > 0

    genuine = client.post("/api/v1/tools/model-xray", json={"text": "Report spam calls and SMS to 1909. Never share your OTP with anyone. -Airtel"}).json()
    assert genuine["probability"] < 0.1 and genuine["words_down_total"] < 0


def test_payment_screenshot_rules():
    from datetime import date

    today = date(2026, 10, 29)
    good = st.payment_screenshot_text_check("Google Pay  ₹2,500 Payment successful  29 Oct 2026, 10:42 am  UPI transaction ID 430219876543", today)
    assert good["risk"] == "low" and good["facts"]["utr"] == "430219876543" and good["facts"]["amount"] == "₹2,500"
    fake = st.payment_screenshot_text_check("PhonePe ₹15,000 Payment Successful 12 Nov 2026 UTR: 12345678", today)
    titles = [f["title"] for f in fake["flags"]]
    assert fake["risk"] == "high" and "UTR is not 12 digits" in titles and "Date is in the future" in titles
    pend = st.payment_screenshot_text_check("Paytm Rs 999 Payment Pending 29/10/2026 UTR 430219876543", today)
    assert pend["risk"] == "high"
    assert st.payment_screenshot_text_check("hello how are you", today)["flags"][0]["title"] == "No payment details found"


def test_payment_screenshot_endpoint(client):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (900, 400), "white")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 34)
    except OSError:
        pytest.skip("font not available")
    for i, line in enumerate(["PhonePe", "Payment Pending", "Rs 15000", "UTR: 12345678"]):
        d.text((40, 30 + 85 * i), line, fill="black", font=f)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    r = client.post("/api/v1/tools/payment-screenshot", files={"file": ("pay.png", buf.getvalue(), "image/png")})
    if r.status_code == 422 and "OCR" in r.text:
        pytest.skip("tesseract not installed")
    assert r.status_code == 200 and r.json()["risk"] == "high"


def test_scam_to_genuine_path_lowers_the_score(client):
    r = client.post("/api/v1/tools/scam-to-genuine", json={"text": "URGENT: Your SBI account will be blocked today. Update KYC immediately at http://sbi-kyc-verify.xyz and share the OTP sent to your phone."}).json()
    assert r["score"] > 0.9 and len(r["cues"]) >= 3
    assert r["steps"] and r["steps"][-1]["score"] < 0.5
    assert all(a["score"] >= b["score"] - 0.05 for a, b in zip(r["steps"], r["steps"][1:]))
