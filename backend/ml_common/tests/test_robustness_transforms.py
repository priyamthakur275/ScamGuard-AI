from ml_common.testing.robustness_transforms import apply_all_transforms, TRANSFORM_CATALOG


class TestTransformCatalogCompleteness:
    def test_catalog_covers_all_requested_transformation_types(self):
        codes = {code for code, _, _ in TRANSFORM_CATALOG}
        assert codes == {
            "case_change", "whitespace", "punctuation", "spelling_variation",
            "inserted_symbols", "homoglyph_domain", "url_obfuscation",
        }

    def test_apply_all_transforms_returns_one_result_per_catalog_entry(self):
        results = apply_all_transforms("Verify your account now")
        assert len(results) == len(TRANSFORM_CATALOG)


class TestDeterminism:
    def test_same_input_always_produces_same_output(self):
        text = "URGENT: verify your account at http://example.com/login"
        first = apply_all_transforms(text)
        second = apply_all_transforms(text)
        assert [t.transformed_text for t in first] == [t.transformed_text for t in second]


class TestCaseChange:
    def test_uppercases_the_text(self):
        results = apply_all_transforms("verify now")
        case_result = next(r for r in results if r.code == "case_change")
        assert case_result.transformed_text == "VERIFY NOW"


class TestWhitespaceVariation:
    def test_introduces_irregular_whitespace(self):
        results = apply_all_transforms("verify your account")
        ws_result = next(r for r in results if r.code == "whitespace")
        assert ws_result.transformed_text != "verify your account"
        assert "\t" in ws_result.transformed_text


class TestPunctuationVariation:
    def test_doubles_exclamation_marks(self):
        results = apply_all_transforms("Act now!")
        punct_result = next(r for r in results if r.code == "punctuation")
        assert "!!!" in punct_result.transformed_text

    def test_adds_ellipsis_after_urgency_words(self):
        results = apply_all_transforms("Verify immediately")
        punct_result = next(r for r in results if r.code == "punctuation")
        assert "immediately..." in punct_result.transformed_text


class TestSpellingVariation:
    def test_applies_leetspeak_substitutions(self):
        results = apply_all_transforms("verify account online")
        spelling_result = next(r for r in results if r.code == "spelling_variation")
        assert "0" in spelling_result.transformed_text
        assert "3" in spelling_result.transformed_text


class TestInsertedSymbols:
    def test_spreads_letters_in_longer_words_with_dots(self):
        results = apply_all_transforms("verify")
        symbols_result = next(r for r in results if r.code == "inserted_symbols")
        assert symbols_result.transformed_text == "v.e.r.i.f.y"

    def test_leaves_short_words_untouched(self):
        results = apply_all_transforms("to us")
        symbols_result = next(r for r in results if r.code == "inserted_symbols")
        assert symbols_result.transformed_text == "to us"


class TestHomoglyphDomain:
    def test_replaces_latin_letters_in_hostname_with_homoglyphs(self):
        results = apply_all_transforms("Visit http://paypal.com/login now")
        homoglyph_result = next(r for r in results if r.code == "homoglyph_domain")
        assert "http://paypal.com" not in homoglyph_result.transformed_text
        assert "/login now" in homoglyph_result.transformed_text

    def test_text_with_no_url_is_unaffected(self):
        results = apply_all_transforms("Call me later")
        homoglyph_result = next(r for r in results if r.code == "homoglyph_domain")
        assert homoglyph_result.transformed_text == "Call me later"


class TestUrlObfuscation:
    def test_percent_encodes_the_url_path(self):
        results = apply_all_transforms("Click http://example.com/verify/account")
        url_result = next(r for r in results if r.code == "url_obfuscation")
        assert "%2F" in url_result.transformed_text
        assert url_result.transformed_text.startswith("Click http://")

    def test_text_with_no_url_is_unaffected(self):
        results = apply_all_transforms("No links here")
        url_result = next(r for r in results if r.code == "url_obfuscation")
        assert url_result.transformed_text == "No links here"
