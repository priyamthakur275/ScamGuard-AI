from ml_common.security.url_intelligence import analyze_url


class TestBasicParsing:
    def test_parses_scheme_and_hostname(self):
        result = analyze_url("https://www.example.com/path?x=1")
        assert result.scheme == "https"
        assert result.hostname == "www.example.com"

    def test_registrable_domain_for_simple_com(self):
        result = analyze_url("https://accounts.google.com/signin")
        assert result.registrable_domain == "google.com"

    def test_registrable_domain_for_multi_label_suffix(self):
        result = analyze_url("https://retail.sbi.co.in/login")
        assert result.registrable_domain == "sbi.co.in"


class TestIpLiteralDetection:
    def test_detects_ip_literal_host(self):
        result = analyze_url("http://192.168.1.1/admin")
        assert result.is_ip_literal is True

    def test_normal_hostname_is_not_ip_literal(self):
        result = analyze_url("http://example.com")
        assert result.is_ip_literal is False


class TestPunycodeDetection:
    def test_detects_punycode_hostname(self):
        # xn--80ak6aa92e.com is a real-world punycode IDN homograph example
        result = analyze_url("http://xn--80ak6aa92e.com/login")
        assert result.is_punycode is True

    def test_ordinary_hostname_is_not_punycode(self):
        result = analyze_url("http://example.com")
        assert result.is_punycode is False


class TestSuspiciousTld:
    def test_flags_known_abused_tld(self):
        result = analyze_url("http://free-prize-claim.tk")
        assert result.is_suspicious_tld is True

    def test_does_not_flag_common_tld(self):
        result = analyze_url("http://example.com")
        assert result.is_suspicious_tld is False


class TestShortenerDetection:
    def test_flags_known_shortener(self):
        result = analyze_url("https://bit.ly/3xample")
        assert result.is_shortened is True

    def test_does_not_flag_non_shortener(self):
        result = analyze_url("https://example.com/some/long/path")
        assert result.is_shortened is False


class TestUserinfoObfuscation:
    def test_flags_userinfo_in_url(self):
        # A classic obfuscation trick: the browser treats "evil.tk" as the
        # real host, with "paypal.com" appearing only as (ignored) userinfo.
        result = analyze_url("http://paypal.com@evil.tk/login")
        assert result.has_userinfo_obfuscation is True
        assert result.hostname == "evil.tk"

    def test_no_userinfo_is_not_flagged(self):
        result = analyze_url("https://example.com")
        assert result.has_userinfo_obfuscation is False


class TestLookalikeDetection:
    def test_flags_close_typosquat_of_known_brand(self):
        result = analyze_url("http://arnazon.com/deals")  # rn instead of m
        assert result.lookalike_of == "amazon.com"
        assert result.lookalike_distance is not None
        assert result.lookalike_distance <= 2

    def test_does_not_flag_the_real_brand_domain(self):
        result = analyze_url("https://www.amazon.com/orders")
        assert result.lookalike_of is None

    def test_does_not_flag_unrelated_domain(self):
        result = analyze_url("https://my-personal-blog.com")
        assert result.lookalike_of is None


class TestLexicalFeatures:
    def test_subdomain_depth_counts_extra_labels(self):
        result = analyze_url("http://secure.login.example.com")
        assert result.subdomain_depth == 2

    def test_digit_ratio_computed_over_hostname(self):
        result = analyze_url("http://192-168-1-1-verify.com")
        assert 0.0 < result.digit_ratio_in_hostname < 1.0

    def test_hyphen_count(self):
        result = analyze_url("http://secure-account-verify-now.com")
        assert result.hyphen_count_in_hostname == 3


class TestSerialization:
    def test_to_dict_round_trips_all_fields(self):
        result = analyze_url("https://example.com")
        d = result.to_dict()
        assert d["hostname"] == "example.com"
        assert "lookalike_of" in d
        assert "is_punycode" in d
