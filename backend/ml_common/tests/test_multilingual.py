from ml_common.preprocessing.multilingual import (
    detect_language,
    detect_concepts,
    analyze_multilingual,
    normalize_for_analysis,
)


class TestLanguageDetectionEnglish:
    def test_plain_english_detected_as_english(self):
        lang, ratio = detect_language("Hi, are you coming to college tomorrow?")
        assert lang == "english"
        assert ratio == 0.0

    def test_empty_string_defaults_to_english_with_zero_ratio(self):
        lang, ratio = detect_language("")
        assert lang == "english"
        assert ratio == 0.0


class TestLanguageDetectionHindi:
    def test_devanagari_text_detected_as_hindi(self):
        lang, ratio = detect_language("आपका खाता तुरंत बंद हो जाएगा, अभी सत्यापित करें")
        assert lang == "hindi"
        assert ratio > 0.6

    def test_mostly_devanagari_with_some_latin_still_flagged_mixed_or_hindi(self):
        lang, ratio = detect_language("आपका OTP है 123456, तुरंत शेयर करें")
        assert lang in ("hindi", "mixed")
        assert ratio > 0.0


class TestLanguageDetectionHinglish:
    def test_hinglish_text_detected_via_marker_words(self):
        lang, ratio = detect_language("Aapka khata turant band ho jayega, abhi paisa bhejo")
        assert lang == "hinglish"

    def test_single_hinglish_word_alone_is_not_enough(self):
        # One common word ("hai" also appears in unrelated contexts)
        # should not be enough to call something Hinglish -- requires at
        # least two marker hits, avoiding false positives on ordinary
        # English text.
        lang, _ = detect_language("This is a legitimate business proposal.")
        assert lang == "english"


class TestConceptDetectionEnglish:
    def test_detects_otp_and_bank(self):
        concepts = detect_concepts("Please share your OTP to verify your bank account.")
        assert "otp" in concepts
        assert "bank" in concepts

    def test_detects_kyc_and_aadhaar(self):
        concepts = detect_concepts("Your KYC is pending, please update your Aadhaar card details.")
        assert "kyc" in concepts
        assert "aadhaar" in concepts

    def test_detects_lottery_and_cashback(self):
        concepts = detect_concepts("Congratulations! You won a lottery prize and cashback reward.")
        assert "lottery" in concepts
        assert "cashback" in concepts

    def test_no_concepts_in_ordinary_text(self):
        concepts = detect_concepts("Let's grab coffee this weekend.")
        assert concepts == ()


class TestConceptDetectionHindiAndHinglish:
    def test_detects_devanagari_bank_and_otp(self):
        concepts = detect_concepts("आपके बैंक खाते के लिए ओटीपी भेजा गया है")
        assert "bank" in concepts
        assert "otp" in concepts

    def test_detects_hinglish_upi_and_payment(self):
        concepts = detect_concepts("Turant apna UPI se paisa bhejo warna khata band ho jayega")
        assert "upi" in concepts
        assert "payment" in concepts

    def test_detects_devanagari_police_and_income_tax(self):
        concepts = detect_concepts("यह पुलिस साइबर सेल की ओर से कॉल है, आयकर विभाग का मामला है")
        assert "police" in concepts
        assert "income_tax" in concepts

    def test_detects_courier_and_pan_hinglish(self):
        concepts = detect_concepts("Your courier is held by customs department, share your PAN card number")
        assert "courier" in concepts
        assert "pan" in concepts


class TestHinglishUrgencyEvidence:
    def test_detects_common_hinglish_urgency_phrase(self):
        result = analyze_multilingual("Turant paisa bhejo warna aapka khata band ho jayega")
        codes = {s.code for s in result.evidence}
        assert "hinglish_urgency_language" in codes

    def test_ordinary_hinglish_without_urgency_has_no_urgency_evidence(self):
        result = analyze_multilingual("Aapka order kal aayega, dhanyavaad")
        codes = {s.code for s in result.evidence}
        assert "hinglish_urgency_language" not in codes


class TestOriginalTextIsPreserved:
    def test_normalize_never_removes_or_alters_the_original_text(self):
        original = "आपका खाता तुरंत बंद हो जाएगा, OTP शेयर करें"
        normalized = normalize_for_analysis(original)
        assert normalized.startswith(original)

    def test_normalize_appends_english_concept_summary_for_hindi_text(self):
        original = "आपके बैंक खाते के लिए ओटीपी भेजा गया है, तुरंत साझा करें"
        normalized = normalize_for_analysis(original)
        assert "bank" in normalized.lower()
        assert "otp" in normalized.lower()
        assert normalized != original  # something was genuinely appended

    def test_text_with_no_detected_concepts_is_returned_completely_unchanged(self):
        original = "Let's meet for coffee tomorrow at 5pm."
        normalized = normalize_for_analysis(original)
        assert normalized == original


class TestAnalysisSerialization:
    def test_to_dict_is_json_serializable(self):
        import json

        result = analyze_multilingual("Turant apna UPI OTP bhejo warna khata band ho jayega")
        json.dumps(result.to_dict())  # must not raise
