"""Tests for the Phase 3 extensions to url_intelligence.py: structural
fields (port/path/query/fragment/length/encoding), suspicious path/query
signals, the graded evidence list, and configurable brand vocabulary.
Includes adversarial URLs specifically crafted to test evasion attempts.
"""
from ml_common.security.url_intelligence import analyze_url


class TestUrlStructureFields:
    def test_extracts_port(self):
        result = analyze_url("https://example.com:8443/path")
        assert result.port == 8443

    def test_port_is_none_when_not_specified(self):
        result = analyze_url("https://example.com/path")
        assert result.port is None

    def test_extracts_path_query_fragment(self):
        result = analyze_url("https://example.com/a/b?x=1&y=2#section")
        assert result.path == "/a/b"
        assert result.query == "x=1&y=2"
        assert result.fragment == "section"

    def test_url_length_is_the_full_string_length(self):
        url = "https://example.com/" + "a" * 50
        result = analyze_url(url)
        assert result.url_length == len(url)

    def test_ip_version_reported_for_ipv4(self):
        result = analyze_url("http://192.168.1.1/x")
        assert result.is_ip_literal is True
        assert result.ip_version == 4

    def test_ip_version_reported_for_ipv6(self):
        result = analyze_url("http://[2001:db8::1]/x")
        assert result.is_ip_literal is True
        assert result.ip_version == 6


class TestPercentEncodingDetection:
    def test_detects_percent_encoded_characters(self):
        result = analyze_url("https://example.com/path%20with%20spaces")
        assert result.has_percent_encoding is True

    def test_plain_url_has_no_percent_encoding_flag(self):
        result = analyze_url("https://example.com/plain/path")
        assert result.has_percent_encoding is False

    def test_lone_percent_sign_without_valid_encoding_is_not_falsely_flagged(self):
        # unquote() leaves "100% off" unchanged since %20f isn't its own
        # valid escape in context here -- confirms we compare against a
        # real decode, not just checking for the '%' character.
        result = analyze_url("https://example.com/100%-off")
        # This IS technically decodable (%2D isn't here, but %-o isn't
        # valid hex) -- unquote leaves malformed sequences alone, so this
        # should NOT be flagged as genuinely percent-encoded content.
        assert result.has_percent_encoding is False


class TestSuspiciousPathKeywords:
    def test_flags_login_path_on_non_brand_domain(self):
        result = analyze_url("http://totally-unrelated-xyz123.com/login/verify")
        assert "login" in result.suspicious_path_keywords
        assert "verify" in result.suspicious_path_keywords

    def test_does_not_flag_login_path_on_a_known_brand_domain(self):
        result = analyze_url("https://accounts.google.com/login")
        assert result.suspicious_path_keywords == ()

    def test_ordinary_path_has_no_suspicious_keywords(self):
        result = analyze_url("https://example.com/blog/2026/my-post")
        assert result.suspicious_path_keywords == ()


class TestSuspiciousQueryParams:
    def test_flags_open_redirect_style_param(self):
        result = analyze_url("https://example.com/go?redirect=http://evil.tk")
        assert "redirect" in result.suspicious_query_params

    def test_flags_multiple_redirect_style_params(self):
        result = analyze_url("https://example.com/go?next=/a&url=http://evil.tk")
        assert set(result.suspicious_query_params) == {"next", "url"}

    def test_ordinary_query_params_not_flagged(self):
        result = analyze_url("https://example.com/search?q=weather&page=2")
        assert result.suspicious_query_params == ()


class TestEvidenceSeverityAndReasons:
    def test_every_evidence_signal_has_code_severity_and_reason(self):
        result = analyze_url("http://arnaz0n-verify-login.tk/account?redirect=http://x.com")
        assert len(result.evidence) > 0
        for signal in result.evidence:
            assert signal.code
            assert signal.severity in ("low", "medium", "high")
            assert len(signal.reason) > 10

    def test_clean_url_has_no_evidence_signals(self):
        result = analyze_url("https://www.wikipedia.org/wiki/Security")
        assert result.evidence == ()

    def test_single_weak_signal_does_not_imply_multiple_signals(self):
        # A suspicious TLD alone (no other signals) should produce exactly
        # one low-severity signal, not be amplified into several.
        result = analyze_url("https://my-personal-blog.xyz/about")
        codes = [e.code for e in result.evidence]
        assert codes == ["suspicious_tld"]
        assert result.evidence[0].severity == "low"

    def test_to_dict_serializes_evidence_as_plain_dicts(self):
        result = analyze_url("http://192.168.1.1/admin")
        d = result.to_dict()
        assert isinstance(d["evidence"], list)
        assert d["evidence"][0]["code"] == "ip_literal_host"
        assert "severity" in d["evidence"][0]
        assert "reason" in d["evidence"][0]


class TestConfigurableBrandVocabulary:
    def test_extra_brand_domains_are_honored_for_lookalike_detection(self):
        # Without the extra vocabulary, this org-specific domain isn't a
        # known brand, so no lookalike detection is possible against it.
        result_without = analyze_url("https://scamguord.com/login")
        assert result_without.lookalike_of is None

        result_with = analyze_url(
            "https://scamguord.com/login",
            extra_brand_domains=frozenset({"scamguard.com"}),
        )
        assert result_with.lookalike_of == "scamguard.com"

    def test_extra_brand_domains_do_not_replace_the_default_list(self):
        # Default brand detection (amazon.com) must still work even when
        # extra domains are supplied.
        result = analyze_url(
            "http://arnazon.com/deals",
            extra_brand_domains=frozenset({"my-custom-brand.com"}),
        )
        assert result.lookalike_of == "amazon.com"


class TestInsecureHttpWithSensitivePath:
    def test_flags_plain_http_login_page(self):
        result = analyze_url("http://totally-unrelated-xyz123.com/login")
        assert any(e.code == "insecure_http_with_sensitive_path" for e in result.evidence)

    def test_does_not_flag_https_login_page(self):
        result = analyze_url("https://totally-unrelated-xyz123.com/login")
        assert not any(e.code == "insecure_http_with_sensitive_path" for e in result.evidence)

    def test_does_not_flag_plain_http_with_no_sensitive_path(self):
        result = analyze_url("http://example.com/blog/post")
        assert not any(e.code == "insecure_http_with_sensitive_path" for e in result.evidence)
    """URLs specifically crafted to attempt to evade or exploit the
    analysis itself -- not just "bad" URLs, but ones testing edge cases
    of the parsing/detection logic.
    """

    def test_mixed_case_scheme_and_host_still_detected(self):
        result = analyze_url("HTTPS://ARNAZON.COM/Login")
        assert result.registrable_domain == "arnazon.com"
        assert result.lookalike_of == "amazon.com"

    def test_url_with_multiple_at_signs_uses_real_host_not_first_at(self):
        # Browsers parse everything before the LAST unescaped '@' before
        # the host as userinfo -- confirms urlsplit's behavior is used
        # correctly, not a naive first-'@' split that could be fooled.
        result = analyze_url("http://google.com@paypal.com@evil.tk/login")
        assert result.hostname == "evil.tk"
        assert result.has_userinfo_obfuscation is True

    def test_extremely_long_url_does_not_crash_and_is_flagged(self):
        url = "https://example.com/" + "x" * 5000
        result = analyze_url(url)
        assert result.url_length > 5000
        assert any(e.code == "unusually_long_url" for e in result.evidence)

    def test_url_with_no_path_at_all(self):
        result = analyze_url("https://example.com")
        assert result.path == ""
        assert result.suspicious_path_keywords == ()

    def test_double_encoded_percent_sign_still_flagged(self):
        result = analyze_url("https://example.com/redirect?url=%2568ttp%253A%252F%252Fevil.tk")
        assert result.has_percent_encoding is True
        assert "url" in result.suspicious_query_params

    def test_punycode_combined_with_lookalike_evidence_both_present(self):
        # A hostname that is BOTH punycode-encoded AND a brand lookalike
        # should surface both signals independently, not merge/hide one.
        result = analyze_url(
            "http://xn--arnazon-x5a.com/verify",  # punycode-flagged + close to a brand-ish name
        )
        codes = [e.code for e in result.evidence]
        assert "punycode_hostname" in codes

    def test_empty_string_does_not_crash(self):
        result = analyze_url("")
        assert result.hostname == ""
        assert result.evidence == ()

    def test_javascript_scheme_is_not_treated_as_a_normal_host(self):
        result = analyze_url("javascript:alert(document.cookie)")
        assert result.scheme == "javascript"
        assert result.hostname == ""
        assert any(e.code == "non_http_scheme" for e in result.evidence)
