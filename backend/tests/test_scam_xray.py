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


def test_genuine_message_gets_no_red_flags_only_reassurance():
    from ml_service.inference.scam_xray import xray
    out = xray("Rs 2,450 debited. Not you? Call the official helpline. Never share your OTP with anyone.", is_scam=False)
    assert out["spans"] == []
    assert out["reassuring"]


def test_never_share_warning_is_not_underlined_as_an_ask():
    from ml_service.inference.scam_xray import xray
    out = xray("Never share your OTP. Your account will be blocked today, pay the fee to unlock it.")
    assert "asks_for_secret" not in {s["intent"] for s in out["spans"]}
