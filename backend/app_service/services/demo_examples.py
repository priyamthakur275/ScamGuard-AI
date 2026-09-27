"""Demo Mode example catalog (Phase 13).

CRITICAL: this file contains only example INPUT text. It does not, and
must never, contain a precomputed verdict, probability, or any other
analysis output -- every demo example is run through the exact same real
pipeline (MessageService.analyze_ephemeral, which calls the same ML/XAI
code as a genuine scan) at request time. If the model's output for one of
these examples changes because the model changed, the demo reflects that
change automatically -- there is nothing here to keep in sync or that
could silently drift from reality.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DemoExample:
    id: str
    label: str
    category: str
    input_type: str
    text: str


DEMO_EXAMPLES: tuple[DemoExample, ...] = (
    DemoExample(
        id="bank_otp_scam",
        label="Bank / OTP scam",
        category="banking_fraud",
        input_type="TEXT",
        text=(
            "URGENT: Your bank account will be suspended within 24 hours due to "
            "suspicious activity. Please share the OTP sent to your registered "
            "mobile number immediately to verify your identity and avoid "
            "permanent account closure."
        ),
    ),
    DemoExample(
        id="job_scam",
        label="Fake job offer scam",
        category="job_scam",
        input_type="TEXT",
        text=(
            "Congratulations! You have been selected for a work-from-home data "
            "entry job paying Rs. 45,000 per month. To confirm your position, "
            "pay a refundable registration fee of Rs. 1500 via UPI within the "
            "next 2 hours or the offer will be given to the next candidate."
        ),
    ),
    DemoExample(
        id="investment_scam",
        label="Investment / trading scam",
        category="investment_scam",
        input_type="TEXT",
        text=(
            "Double your money in 7 days! Join our exclusive stock trading group "
            "with guaranteed 300% returns. Our AI trading bot has never lost a "
            "trade. Limited slots available, invest now before the offer closes "
            "tonight."
        ),
    ),
    DemoExample(
        id="delivery_scam",
        label="Delivery / courier scam",
        category="delivery_scam",
        input_type="TEXT",
        text=(
            "Your parcel is held at customs due to an unpaid duty of Rs. 350. "
            "Click the link below to pay the fee and schedule redelivery within "
            "24 hours, or the package will be returned to sender: "
            "http://indiapost-redelivery.xyz/pay"
        ),
    ),
    DemoExample(
        id="phishing_url",
        label="Phishing URL",
        category="phishing",
        input_type="URL",
        text="http://arnaz0n-account-verify.tk/login",
    ),
    DemoExample(
        id="legitimate_message",
        label="Legitimate message",
        category=None,
        input_type="TEXT",
        text="Hi, are you still free to grab lunch tomorrow around 1pm?",
    ),
)

_EXAMPLES_BY_ID = {e.id: e for e in DEMO_EXAMPLES}


def get_demo_example(example_id: str) -> DemoExample | None:
    return _EXAMPLES_BY_ID.get(example_id)
