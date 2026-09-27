from ml_service.services.explainable_ai import EntityHighlighter

highlighter = EntityHighlighter()


class TestExistingEntityTypesStillWork:
    """Confirms extending the class didn't regress the entity types that
    were already there before this phase.
    """

    def test_url_extraction_still_works(self):
        result = highlighter.extract("Click here: http://arnaz0n-verify.tk/login")
        assert "http://arnaz0n-verify.tk/login" in result["urls"]

    def test_email_extraction_still_works(self):
        result = highlighter.extract("Contact us at support@example.com")
        assert "support@example.com" in result["emails"]

    def test_crypto_wallet_extraction_still_works(self):
        result = highlighter.extract("Send BTC to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
        assert len(result["crypto_wallets"]) == 1


class TestDeduplicationAndNormalization:
    def test_repeated_phone_number_is_deduplicated(self):
        text = "Call 9876543210 now, again 9876543210 for confirmation, ext. 9876543210"
        result = highlighter.extract(text)
        assert result["phones"].count("+919876543210") == 1

    def test_phone_number_normalized_to_consistent_format_regardless_of_input_style(self):
        text = "Call +91 98765 43210 or 9876543210 or 91-9876543210"
        result = highlighter.extract(text)
        assert result["phones"] == ["+919876543210"]

    def test_repeated_url_is_deduplicated(self):
        text = "Visit http://evil.tk/pay and again http://evil.tk/pay for details"
        result = highlighter.extract(text)
        assert result["urls"].count("http://evil.tk/pay") == 1

    def test_entity_order_is_preserved_after_dedup(self):
        text = "First 9876543210 then 8765432109 then 9876543210 again"
        result = highlighter.extract(text)
        assert result["phones"] == ["+919876543210", "+918765432109"]


class TestPaymentAmountExtraction:
    def test_rupee_symbol_amount_detected(self):
        result = highlighter.extract("Pay ₹5,000 immediately to avoid penalty")
        assert any("5,000" in a for a in result["payment_amounts"])

    def test_rs_prefix_amount_detected(self):
        result = highlighter.extract("A fine of Rs. 2000 is pending")
        assert any("2000" in a for a in result["payment_amounts"])

    def test_rupees_suffix_amount_detected(self):
        result = highlighter.extract("Transfer 15000 rupees to this account")
        assert any("15000" in a for a in result["payment_amounts"])

    def test_no_amount_in_ordinary_text(self):
        result = highlighter.extract("Let's catch up soon")
        assert result["payment_amounts"] == []


class TestBankReferenceExtraction:
    def test_ifsc_code_detected(self):
        result = highlighter.extract("Transfer to IFSC code SBIN0001234 for processing")
        assert "SBIN0001234" in result["bank_references"]

    def test_labeled_account_number_detected(self):
        result = highlighter.extract("Please deposit to Account Number: 123456789012")
        assert "123456789012" in result["bank_references"]

    def test_ac_no_abbreviation_detected(self):
        result = highlighter.extract("A/C No 987654321012 is required")
        assert "987654321012" in result["bank_references"]

    def test_unlabeled_random_digits_are_not_treated_as_bank_reference(self):
        result = highlighter.extract("Call 9876543210 for support")
        assert result["bank_references"] == []


class TestDateExtraction:
    def test_slash_format_date_detected(self):
        result = highlighter.extract("Your KYC expires on 15/03/2026")
        assert "15/03/2026" in result["dates"]

    def test_month_name_format_date_detected(self):
        result = highlighter.extract("Deadline is 15 Mar 2026 for verification")
        assert any("15" in d and "2026" in d for d in result["dates"])

    def test_no_date_in_ordinary_text(self):
        result = highlighter.extract("Please call back later")
        assert result["dates"] == []


class TestOrganizationExtraction:
    def test_detects_bank_name(self):
        result = highlighter.extract("This message is from State Bank of India regarding your account")
        assert "State Bank of India" in result["organizations"]

    def test_detects_government_authority(self):
        result = highlighter.extract("Income Tax Department has issued a notice against your PAN")
        assert "Income Tax Department" in result["organizations"]

    def test_detects_payment_app_brand(self):
        result = highlighter.extract("Your PhonePe KYC is incomplete, update now")
        assert "PhonePe" in result["organizations"]

    def test_no_organization_in_ordinary_text(self):
        result = highlighter.extract("Let's meet for lunch tomorrow")
        assert result["organizations"] == []

    def test_does_not_fabricate_person_names(self):
        result = highlighter.extract("Hi Rahul, this is Priya calling from the bank")
        assert "names" not in result
        assert "people" not in result


class TestRealisticIndianScamExamples:
    def test_banking_kyc_scam_message(self):
        text = (
            "Dear Customer, your HDFC Bank account KYC will expire on 20/03/2026. "
            "Pay Rs. 500 processing fee to IFSC HDFC0001234, Account Number 445566778899, "
            "or call 9876543210 immediately."
        )
        result = highlighter.extract(text)
        assert "HDFC Bank" in result["organizations"]
        assert "HDFC0001234" in result["bank_references"]
        assert "445566778899" in result["bank_references"]
        assert "+919876543210" in result["phones"]
        assert "20/03/2026" in result["dates"]
        assert any("500" in a for a in result["payment_amounts"])

    def test_upi_lottery_scam_message(self):
        text = (
            "Congratulations! You have won ₹50,000 in the Paytm lottery. "
            "Share your UPI ID winner123@paytm to claim before 31/12/2026. "
            "Contact support@paytm-rewards.tk or call 8765432109."
        )
        result = highlighter.extract(text)
        assert "Paytm" in result["organizations"]
        assert any("50,000" in a for a in result["payment_amounts"])
        assert "31/12/2026" in result["dates"]
        assert "+918765432109" in result["phones"]

    def test_courier_customs_scam_message(self):
        text = (
            "Your parcel is held by India Post customs. Pay Rs 1200 to release it. "
            "Visit http://indiapost-release.xyz/pay to complete payment by 05 Apr 2026."
        )
        result = highlighter.extract(text)
        assert "India Post" in result["organizations"]
        assert any("1200" in a for a in result["payment_amounts"])
        assert "http://indiapost-release.xyz/pay" in result["urls"]
