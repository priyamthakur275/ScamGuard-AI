import re
import dataclasses

class ThreatLevelClassifier:
    def classify(self, threat_score: float, verdict: str = "scam") -> str:
        if verdict == "legitimate":
            if threat_score < 0.20:
                return "very_low"
            elif threat_score < 0.40:
                return "low"
            return "medium"
        if threat_score < 0.35:
            return "low"
        elif threat_score < 0.65:
            return "medium"
        elif threat_score < 0.80:
            return "high"
        else:
            return "critical"

class EntityHighlighter:
    """Real, deterministic entity extraction via regex/known-vocabulary
    matching only -- no NER model, no guessing. Person names are
    deliberately NOT extracted: a reliable heuristic (e.g. "capitalized
    word sequences") produces far too many false positives (any
    capitalized phrase, sentence starts, brand names already covered
    elsewhere) to responsibly present as "detected names" -- that would
    be fabricating entities under a plausible-sounding label. Every field
    below is either a well-defined format (IFSC codes, dates, crypto
    addresses) or an explicit, small, known vocabulary (organizations) --
    not a guess.
    """

    _ORG_NAMES = (
        "State Bank of India", "SBI", "HDFC Bank", "HDFC", "ICICI Bank", "ICICI",
        "Axis Bank", "Punjab National Bank", "PNB", "Bank of Baroda",
        "Paytm", "PhonePe", "Google Pay", "Amazon", "Flipkart", "Myntra",
        "Income Tax Department", "Reserve Bank of India", "RBI",
        "UIDAI", "Aadhaar", "IRCTC", "India Post", "Indian Post",
        "Cyber Crime Cell", "Cyber Cell", "TRAI", "Microsoft", "Apple",
        "Netflix", "WhatsApp", "Instagram", "Facebook", "PayPal",
    )

    # IFSC: a real, well-defined 11-character Indian bank branch code
    # format (4 letters, a literal '0', 6 alphanumeric) -- not a guess.
    _IFSC_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
    _BANK_ACCOUNT_LABELED_PATTERN = re.compile(
        r"(?:a/?c\.?\s*(?:no\.?)?|account\s*(?:number|no\.?)?)\s*[:\-]?\s*(\d{6,18})",
        re.IGNORECASE,
    )
    _PAYMENT_AMOUNT_PATTERN = re.compile(
        r"(?:₹|rs\.?|inr)\s?[\d,]+(?:\.\d{1,2})?|[\d,]+(?:\.\d{1,2})?\s?(?:rupees|rs\.?|inr)\b",
        re.IGNORECASE,
    )
    _DATE_PATTERN = re.compile(
        r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b"
        r"|\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        """Order-preserving dedup -- plain set() would discard the order
        entities first appeared in, which matters for evidence display.
        """
        return list(dict.fromkeys(items))

    @staticmethod
    def _normalize_phone(raw: str) -> str:
        digits = re.sub(r"[^\d]", "", raw)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return f"+91{digits}" if len(digits) == 10 else digits

    def extract(self, text: str) -> dict:
        urls = self._dedupe(re.findall(r'https?://[^\s]+', text))
        emails = self._dedupe([value.rstrip(".,;:!?)") for value in re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)])
        raw_phones = re.findall(r'(?:\+91|91)?[-\s]?[6-9]\d{9}', text)
        phones = self._dedupe([self._normalize_phone(p) for p in raw_phones])
        payment_candidates = re.findall(r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z0-9.\-]+', text)
        upi_ids = self._dedupe([candidate.rstrip('.,;:!?)') for candidate in payment_candidates
                               if '.' not in candidate.rstrip('.,;:!?)').split('@')[-1]])
        shortened_links = self._dedupe(re.findall(
            r'https?://(?:bit\.ly|t\.co|goo\.gl|tinyurl\.com|ow\.ly)[^\s]+', text
        ))

        btc = re.findall(r'\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b', text)
        eth = re.findall(r'\b0x[a-fA-F0-9]{40}\b', text)
        crypto_wallets = self._dedupe(btc + eth)

        payment_amounts = self._dedupe([m.strip() for m in self._PAYMENT_AMOUNT_PATTERN.findall(text)])
        bank_references = self._dedupe(
            self._IFSC_PATTERN.findall(text) + self._BANK_ACCOUNT_LABELED_PATTERN.findall(text)
        )
        dates = self._dedupe(self._DATE_PATTERN.findall(text))
        organizations = self._dedupe([org for org in self._ORG_NAMES if org.lower() in text.lower()])

        return {
            "urls": urls,
            "emails": emails,
            "phones": phones,
            "upi_ids": upi_ids,
            "shortened_links": shortened_links,
            "crypto_wallets": crypto_wallets,
            "payment_amounts": payment_amounts,
            "bank_references": bank_references,
            "dates": dates,
            "organizations": organizations,
        }

class RiskBreakdownCalculator:
    def __init__(self):
        self.keywords = {
            "urgency": {"urgent", "immediately", "expire", "now", "hurry", "deadline", "last chance", "final warning", "act now", "limited time"},
            "financial_risk": {"payment", "money", "transfer", "bank", "account", "fund", "withdraw", "deposit", "transaction", "credit"},
            "credential_theft": {"password", "login", "otp", "verify", "confirm", "credentials", "pin", "security code", "cvv"},
            "identity_risk": {"aadhaar", "pan", "ssn", "passport", "identity", "kyc", "verification", "document"},
            "social_engineering": {"urgent", "help", "friend", "family", "emergency", "trust", "believe", "promise", "guarantee"},
            "malicious_tone": {"suspend", "block", "legal", "police", "arrest", "court", "penalty", "fine", "terminate"}
        }

    def calculate(self, tokens: list, scam_probability: float, text: str) -> dict:
        text_lower = text.lower()
        breakdown = {}
        
        for dimension, kw_set in self.keywords.items():
            matched = sum(1 for kw in kw_set if kw in text_lower)
            score = (matched / len(kw_set)) * scam_probability
            breakdown[dimension] = min(max(score, 0.0), 1.0)
            
        breakdown["emotional_manipulation"] = min(max(breakdown.get("urgency", 0) * 0.8 + breakdown.get("social_engineering", 0) * 0.5, 0.0), 1.0)
        breakdown["financial_pressure"] = min(max(breakdown.get("financial_risk", 0) * 0.9, 0.0), 1.0)
        breakdown["identity_impersonation"] = min(max(breakdown.get("identity_risk", 0) * 0.9, 0.0), 1.0)
            
        # suspicious_links
        urls = re.findall(r'https?://[^\s]+', text)
        shortened = re.findall(r'https?://(?:bit\.ly|t\.co|goo\.gl|tinyurl\.com)[^\s]+', text)
        link_count = len(urls) + len(shortened)
        if link_count > 0:
            breakdown["suspicious_links"] = 1.0
        else:
            breakdown["suspicious_links"] = 0.0
            
        return breakdown

class ExplanationGenerator:
    def generate(self, verdict: str, probability: float, scam_category: str, top_tokens: list, entities: dict, breakdown: dict, input_type: str = "TEXT", metadata: dict = None) -> tuple[str, str]:
        if verdict in ("safe", "legitimate"):
            return (
                "The input appears to be safe and legitimate.",
                "No significant scam or phishing indicators were detected. The message exhibits standard, genuine communication patterns and is safe to interact with.",
            )
            
        executive_summary = f"The input exhibits characteristics of a {scam_category} scam." if scam_category else f"The input has been classified as {verdict}."
            
        metadata_context = ""
        if input_type == "URL":
            metadata_context = "This URL directs to a potentially malicious domain. "
        elif input_type == "EMAIL":
            metadata_context = "This email exhibits common phishing indicators. "
        elif input_type == "QR":
            metadata_context = "The QR code points to suspicious content. "
        elif input_type == "IMAGE":
            metadata_context = "Text extracted from this image shows scam characteristics. "
        elif input_type == "PDF":
            metadata_context = "This document contains deceptive patterns. "
            
        technical_explanation = f"{metadata_context}This {input_type.lower()} has been classified as {verdict} with a {round(probability * 100)}% model scam probability. "
        
        if scam_category:
            technical_explanation += f"It exhibits characteristics consistent with {scam_category} patterns. "
            
        if top_tokens:
            technical_explanation += f"Key suspicious indicators include: {', '.join(top_tokens[:3])}. "
            
        entity_count = sum(len(v) for v in entities.values())
        if entity_count > 0:
            technical_explanation += f"The message contains {entity_count} suspicious entity(s) that may be used for deception. "
            
        if breakdown.get("urgency", 0) > 0.5:
            technical_explanation += "The use of urgent language is a common pressure tactic employed by scammers."
            
        return executive_summary, technical_explanation.strip()

class RecommendationEngine:
    def generate(self, threat_level: str, category: str) -> list:
        if threat_level in ["critical", "high"]:
            actions = [
                "Do not click any links or download attachments in this message.",
                "Block the sender immediately and report this message as spam.",
                "Never share OTP, PIN, or passwords — no legitimate organization will ask for these."
            ]
            if category == "banking_fraud":
                actions.append("Contact your bank directly using the official number on your card.")
            elif category == "upi_scam":
                actions.append("Do not scan any QR codes or approve any UPI requests.")
            actions.append("Report this message to the Cyber Crime portal (cybercrime.gov.in) or call 1930.")
            return actions
        elif threat_level == "medium":
            return [
                "Exercise caution before responding to this message.",
                "Verify the sender's identity through an independent, trusted channel.",
                "Do not share personal or financial information.",
                "If this claims to be from a company, contact them directly via their official website."
            ]
        else:
            return [
                "This message appears safe, but always stay vigilant.",
                "Be cautious of follow-up messages that may escalate pressure tactics.",
                "When in doubt, verify the sender through official channels."
            ]

class PatternMatcher:
    def match(self, category: str) -> list:
        patterns = {
            "phishing": [
                {"title": "Credential Phishing", "description": "Attackers impersonate trusted services and create fake login pages to harvest your credentials. They often use urgent language about account suspension to pressure immediate action."},
                {"title": "Account Recovery Fraud", "description": "Scammers claim your account was hacked or needs verification. They provide a link to a fake portal to steal your login details."}
            ],
            "banking_fraud": [
                {"title": "Bank Impersonation Fraud", "description": "Scammers pose as bank officials claiming suspicious activity on your account. They request sensitive information like OTPs or card details to 'verify' your identity."},
                {"title": "KYC Update Scam", "description": "Fraudsters claim your banking KYC is pending and your account will be blocked. They trick you into sharing details or downloading malicious apps."}
            ],
            "lottery_scam": [
                {"title": "Prize/Lottery Scam", "description": "Victims are told they have won a prize or lottery and must pay a fee or provide personal details to claim it. No legitimate lottery requires upfront payment."},
                {"title": "Surprise Gift Fraud", "description": "Scammers claim a valuable parcel or gift is waiting for you, but requires customs clearance fees or taxes to be paid."}
            ],
            "upi_scam": [
                {"title": "UPI Payment Fraud", "description": "Fraudsters send collect requests or fake payment links. They may pose as buyers on marketplace platforms, asking you to 'receive' money through a collect request that actually debits your account."},
                {"title": "Refund Offer Scam", "description": "Scammers pretend to offer a refund for a failed transaction, tricking victims into approving a UPI PIN to 'receive' the refund."}
            ],
            "investment_scam": [
                {"title": "High-Yield Investment Program", "description": "Scammers promise unrealistically high returns on investments with little or no risk."},
                {"title": "Ponzi Scheme", "description": "Early investors are paid with funds from new investors, creating an illusion of a profitable enterprise."}
            ],
            "job_scam": [
                {"title": "Work-From-Home Scam", "description": "Fraudsters offer easy remote jobs but require an upfront payment for training or equipment."},
                {"title": "Fake Recruitment", "description": "Scammers pose as recruiters from top companies, conducting fake interviews and charging for background checks."}
            ],
            "identity_theft": [
                {"title": "Document Verification Fraud", "description": "Scammers trick victims into sharing copies of identity documents like Aadhaar or PAN card."},
                {"title": "Social Security Impersonation", "description": "Fraudsters claim your identity has been compromised and demand details to 'protect' you."}
            ],
            "romance_scam": [
                {"title": "Catfishing", "description": "Scammers create fake online profiles to build a romantic relationship and eventually ask for money."},
                {"title": "Emergency Help Scam", "description": "An online romance prospect suddenly encounters an 'emergency' and needs urgent financial assistance."}
            ],
            "crypto_scam": [
                {"title": "Fake Crypto Exchange", "description": "Scammers create a realistic-looking crypto trading platform to steal deposited funds."},
                {"title": "Rug Pull", "description": "Developers of a new cryptocurrency abandon the project and run away with investors' funds."}
            ],
            "fake_delivery": [
                {"title": "Missed Parcel Scam", "description": "You receive a message about a missed delivery with a link to reschedule, which leads to a phishing site."},
                {"title": "Customs Fee Fraud", "description": "Scammers claim your package is held at customs and requires a small fee to be released."}
            ],
            "subscription_scam": [
                {"title": "Unexpected Renewal", "description": "You receive a fake invoice for an expensive subscription renewal, with a number to call to 'cancel' it."},
                {"title": "Free Trial Trap", "description": "A 'free' trial requires a credit card and makes it nearly impossible to cancel before being charged."}
            ],
            "government_scam": [
                {"title": "Tax Refund Fraud", "description": "Scammers claim you are owed a tax refund and ask for bank details to deposit it."},
                {"title": "Official Impersonation", "description": "Fraudsters pose as law enforcement or government officials threatening arrest if a fine is not paid immediately."}
            ],
            "loan_scam": [
                {"title": "Advance-Fee Loan", "description": "Scammers guarantee a loan regardless of credit history but require an upfront fee for 'processing'."},
                {"title": "Fake App Loan", "description": "Malicious loan apps steal your contacts and photos, then use them to extort repayment at exorbitant interest rates."}
            ]
        }
        
        default_patterns = [
            {"title": "Generic Social Engineering", "description": "Scammers manipulate victims into performing actions or divulging confidential information."},
            {"title": "Urgency Tactic", "description": "Fraudsters create a false sense of urgency to bypass critical thinking and force immediate compliance."}
        ]
        
        return patterns.get(category, default_patterns)

class ExplainableAIService:
    def __init__(self):
        self.threat_classifier = ThreatLevelClassifier()
        self.entity_highlighter = EntityHighlighter()
        self.risk_calculator = RiskBreakdownCalculator()
        self.explanation_generator = ExplanationGenerator()
        self.recommendation_engine = RecommendationEngine()
        self.pattern_matcher = PatternMatcher()

    def enrich(self, prediction_result, raw_text: str, input_type: str = "TEXT", metadata: dict | None = None):
        metadata = metadata or {}
        threat_level = self.threat_classifier.classify(prediction_result.threat_score, prediction_result.verdict)
        entities = self.entity_highlighter.extract(raw_text)
        
        tokens = []
        if prediction_result.top_contributing_tokens:
            tokens = [t.token for t in prediction_result.top_contributing_tokens]
            
        breakdown = self.risk_calculator.calculate(tokens, prediction_result.scam_probability, raw_text)
        
        executive_summary, technical_explanation = self.explanation_generator.generate(
            verdict=prediction_result.verdict,
            probability=prediction_result.scam_probability,
            scam_category=prediction_result.scam_category,
            top_tokens=tokens,
            entities=entities,
            breakdown=breakdown,
            input_type=input_type,
            metadata=metadata
        )
        
        actions = self.recommendation_engine.generate(threat_level, prediction_result.scam_category)
        patterns = self.pattern_matcher.match(prediction_result.scam_category)
        
        return dataclasses.replace(
            prediction_result,
            ai_explanation=technical_explanation,
            executive_summary=executive_summary,
            technical_explanation=technical_explanation,
            threat_level=threat_level,
            risk_breakdown=breakdown,
            recommended_actions=actions,
            highlighted_entities=entities,
            similar_patterns=patterns
        )
