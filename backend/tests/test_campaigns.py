from app_service.services import campaigns
from tests.conftest import register_and_login


def test_known_campaigns_are_named():
    assert campaigns.match("Your SBI YONO account will be blocked today, update KYC")[0] == "kyc_block"
    assert campaigns.match("This is Mumbai cyber crime, you are under digital arrest")[0] == "digital_arrest"
    assert campaigns.match("Earn Rs 3000 daily by liking YouTube videos, pay registration fee")[0] == "task_job"
    assert campaigns.match("http://paypa1-secure-login.verify-account.top/signin")[0] == "fake_login_link"


def test_genuine_messages_do_not_match():
    assert campaigns.match("Rs 2,450 debited from A/c XX4821. Never share your OTP.") is None
    assert campaigns.match("Your Amazon order has been delivered.") is None


def test_scan_result_carries_campaign_with_count(client):
    auth_headers = {"Authorization": f"Bearer {register_and_login(client, 'camp@example.com')}"}
    text = "Dear customer, your SBI YONO account will be blocked today. Update KYC and share the OTP at http://sbi-kyc.xyz"
    campaigns._CACHE.clear()
    client.post("/api/v1/messages/analyze", json={"text": text, "input_type": "TEXT"}, headers=auth_headers)
    campaigns._CACHE.clear()
    body = client.post("/api/v1/messages/analyze", json={"text": text, "input_type": "TEXT"}, headers=auth_headers).json()
    camp = body["metadata"]["campaign"]
    assert camp["id"] == "kyc_block" and camp["seen_30d"] >= 1
