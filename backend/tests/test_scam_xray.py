from ml_service.inference.scam_xray import xray


def test_xray_marks_each_stage_in_the_users_own_words():
    text = "Congratulations! You won Rs 25 lakh in the KBC lucky draw. Pay processing fee Rs 12,500 today and share the OTP."
    r = xray(text)
    found = {s["stage"] for s in r["spans"]}
    assert {"hook", "pressure", "ask", "cashout"} <= found
    for s in r["spans"]:
        assert text[s["start"]:s["end"]].strip()  # spans point into the original text
    starts = [s["start"] for s in r["spans"]]
    assert starts == sorted(starts)
    assert all(a["end"] <= b["start"] for a, b in zip(r["spans"], r["spans"][1:]))  # no overlaps


def test_genuine_otp_message_is_reassuring_not_flagged():
    r = xray("482913 is your OTP for the HDFC txn. Do not share it with anyone.")
    assert not any(s["stage"] == "ask" for s in r["spans"])
    assert r["reassuring"]


def test_quick_check_returns_xray(client):
    body = client.post("/api/v1/public/quick-check", json={"text": "Your SBI account will be blocked today, share the OTP now"}).json()
    xr = body["metadata"]["xray"]
    assert xr["text"].startswith("Your SBI account") and xr["spans"]
