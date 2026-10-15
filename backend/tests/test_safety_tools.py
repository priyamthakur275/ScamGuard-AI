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
    assert r["redundant"] is True  # several cues, each enough on its own
    plain = client.post("/api/v1/tools/what-if", json={"text": "See you at the station at 6, bring the tickets"}).json()
    assert plain["parts"] == [] and plain["baseline"] is None


def test_what_if_ignores_scan_annotation(client):
    text = "Share the OTP sent to your phone at http://sbi-kyc.xyz"
    a = client.post("/api/v1/tools/what-if", json={"text": text}).json()
    b = client.post("/api/v1/tools/what-if", json={"text": text + "\n\nDetected language/concepts (heuristic):\nDetected concepts: KYC, OTP."}).json()
    assert a == b
