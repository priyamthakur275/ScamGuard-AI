import io

import pytest

from app_service.services.extraction import (
    ExtractionService,
    UnsafeUrlError,
    MAX_UPLOAD_BYTES,
    _assert_public_host,
)


class FakeUploadFile:
    """Minimal stand-in for fastapi.UploadFile.file (a SpooledTemporaryFile)."""

    def __init__(self, data: bytes, filename: str = "test.bin"):
        self.file = io.BytesIO(data)
        self.filename = filename


class TestPrivateHostBlocking:
    @pytest.mark.parametrize(
        "hostname",
        [
            "localhost",
            "127.0.0.1",
            "127.0.0.53",
            "169.254.169.254",  # cloud metadata endpoint
            "10.0.0.5",
            "192.168.1.1",
            "172.16.0.1",
            "0.0.0.0",
        ],
    )
    def test_rejects_private_and_loopback_hosts(self, hostname):
        with pytest.raises(UnsafeUrlError):
            _assert_public_host(hostname)

    def test_allows_public_ip(self):
        # 8.8.8.8 is a real public address (Google DNS) -- should not raise.
        _assert_public_host("8.8.8.8")

    def test_unresolvable_host_raises_plain_value_error_not_unsafe_url_error(self):
        # An unresolvable/nonexistent hostname is an ordinary broken link,
        # not a blocked-attack situation -- it must NOT be reported as
        # UnsafeUrlError (which implies "we found this and blocked it").
        with pytest.raises(ValueError):
            _assert_public_host("this-host-does-not-exist.invalid")
        with pytest.raises(UnsafeUrlError):
            # Confirm the distinction actually holds: this specific
            # exception type is reserved for resolved-but-unsafe hosts.
            _assert_public_host("127.0.0.1")


class TestUrlExtractionBlocksSSRF:
    def test_url_targeting_localhost_is_blocked_not_silently_fetched(self):
        extracted, metadata = ExtractionService.extract(None, "http://127.0.0.1:8000/admin", "URL")
        assert metadata["fetch_status"] == "blocked_unsafe_target"
        assert "fetch blocked" in extracted.lower()

    def test_url_targeting_metadata_endpoint_is_blocked(self):
        extracted, metadata = ExtractionService.extract(None, "http://169.254.169.254/latest/meta-data/", "URL")
        assert metadata["fetch_status"] == "blocked_unsafe_target"


class TestUploadSizeLimit:
    def test_oversized_image_upload_is_rejected(self):
        oversized = FakeUploadFile(b"x" * (MAX_UPLOAD_BYTES + 1), filename="big.png")
        with pytest.raises(ValueError, match="exceeds"):
            ExtractionService.extract(oversized, None, "IMAGE")

    def test_upload_within_limit_is_not_rejected_for_size(self):
        # Not a real image, so OCR itself will fail -- but it must fail with
        # an OCR error, not the size-limit error, proving the limit isn't
        # firing on legitimately-sized files.
        small = FakeUploadFile(b"not a real image", filename="small.png")
        with pytest.raises(ValueError) as exc_info:
            ExtractionService.extract(small, None, "IMAGE")
        assert "exceeds" not in str(exc_info.value)


class TestTlsCertificateInfoFailsafe:
    """_get_tls_certificate_info must NEVER raise or block the main
    fetch, even for blocked/unresolvable hosts. It's tested here only for
    this safe-failure behavior -- see its docstring for why a live
    successful-fetch test isn't possible in this environment.
    """

    def test_returns_none_for_blocked_private_host(self):
        from app_service.services.extraction import _get_tls_certificate_info
        assert _get_tls_certificate_info("127.0.0.1", 443) is None

    def test_returns_none_for_unresolvable_host(self):
        from app_service.services.extraction import _get_tls_certificate_info
        assert _get_tls_certificate_info("this-host-does-not-exist.invalid", 443) is None

    def test_never_raises_regardless_of_input(self):
        from app_service.services.extraction import _get_tls_certificate_info
        # Must not raise even for a completely malformed hostname.
        result = _get_tls_certificate_info("not a valid hostname at all !!", 443)
        assert result is None


class TestNetworkIntelligenceInMetadata:
    def test_blocked_url_still_returns_url_intelligence_with_new_fields(self):
        text, metadata = ExtractionService.extract(None, "http://169.254.169.254/", "URL")
        intel = metadata["url_intelligence"]
        # Structural fields from Phase 3 must be present even on a
        # blocked target (they're computed from the URL string alone).
        assert "port" in intel
        assert "path" in intel
        assert "evidence" in intel
        assert isinstance(intel["evidence"], list)

    def test_resolved_ips_and_redirect_chain_default_safely_when_fetch_fails(self):
        text, metadata = ExtractionService.extract(
            None, "http://this-domain-does-not-exist-xyz987.invalid/", "URL"
        )
        intel = metadata["url_intelligence"]
        assert intel["resolved_ips"] == []
        assert intel["redirect_chain"] == []
        assert intel["tls"] is None


class TestRedirectChainValidation:
    """The single most important untested claim in the SSRF protection:
    that a redirect MID-CHAIN to a blocked target is actually caught, not
    just a directly-blocked initial URL. Uses httpx.MockTransport to
    simulate a real multi-hop redirect without needing network access to
    an actual external attacker-controlled server, and mocks DNS
    resolution for the fictional test hostnames used below so these tests
    don't depend on real DNS being reachable/consistent in CI -- IP
    literals (127.0.0.1, 169.254.169.254, 192.168.1.1) still resolve
    normally since getaddrinfo never does real network I/O for those.
    """

    @staticmethod
    def _mock_public_dns(monkeypatch, hostname_to_ip: dict[str, str]):
        import socket as socket_module

        real_getaddrinfo = socket_module.getaddrinfo

        def fake_getaddrinfo(host, *args, **kwargs):
            if host in hostname_to_ip:
                ip = hostname_to_ip[host]
                return [(socket_module.AF_INET, socket_module.SOCK_STREAM, 6, "", (ip, 0))]
            return real_getaddrinfo(host, *args, **kwargs)

        monkeypatch.setattr(socket_module, "getaddrinfo", fake_getaddrinfo)

    def test_redirect_to_private_ip_is_blocked_not_silently_followed(self, monkeypatch):
        import httpx
        from app_service.services.extraction import _fetch_url_safely, UnsafeUrlError

        self._mock_public_dns(monkeypatch, {"public-looking-site.example.com": "93.184.216.34"})
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            if request.url.host == "public-looking-site.example.com":
                # First hop looks completely safe -- redirects to an
                # internal address on the second hop.
                return httpx.Response(302, headers={"Location": "http://127.0.0.1:8000/admin"})
            # This must NEVER actually be reached.
            return httpx.Response(200, text="You should never see this -- internal admin panel")

        transport = httpx.MockTransport(handler)

        with pytest.raises(UnsafeUrlError, match="non-public address"):
            _fetch_url_safely("http://public-looking-site.example.com/start", transport=transport)

        # Only the first hop should have been attempted -- the second
        # (blocked) request must never actually be sent.
        assert call_count["n"] == 1

    def test_redirect_to_metadata_endpoint_mid_chain_is_blocked(self, monkeypatch):
        import httpx
        from app_service.services.extraction import _fetch_url_safely, UnsafeUrlError

        self._mock_public_dns(monkeypatch, {"public-looking-site.example.com": "93.184.216.34"})

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "public-looking-site.example.com":
                return httpx.Response(302, headers={"Location": "http://169.254.169.254/latest/meta-data/"})
            return httpx.Response(200, text="unreachable")

        transport = httpx.MockTransport(handler)
        with pytest.raises(UnsafeUrlError):
            _fetch_url_safely("http://public-looking-site.example.com/start", transport=transport)

    def test_chain_of_safe_redirects_all_get_validated_and_succeeds(self, monkeypatch):
        import httpx
        from app_service.services.extraction import _fetch_url_safely

        self._mock_public_dns(monkeypatch, {
            "hop1.example.com": "93.184.216.34",
            "hop2.example.com": "93.184.216.35",
        })

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "hop1.example.com":
                return httpx.Response(302, headers={"Location": "http://hop2.example.com/next"})
            if request.url.host == "hop2.example.com":
                return httpx.Response(200, text="Final safe destination")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        resp, resolved_ips, redirect_chain = _fetch_url_safely("http://hop1.example.com/start", transport=transport)

        assert resp.status_code == 200
        assert len(redirect_chain) == 1
        assert redirect_chain[0]["status_code"] == 302

    def test_redirect_loop_exceeding_max_redirects_fails_gracefully(self, monkeypatch):
        import httpx
        from app_service.services.extraction import _fetch_url_safely

        self._mock_public_dns(monkeypatch, {
            "loop-a.example.com": "93.184.216.34",
            "loop-b.example.com": "93.184.216.35",
        })

        def handler(request: httpx.Request) -> httpx.Response:
            # Infinite redirect loop between two safe-looking hosts.
            if request.url.host == "loop-a.example.com":
                return httpx.Response(302, headers={"Location": "http://loop-b.example.com/"})
            return httpx.Response(302, headers={"Location": "http://loop-a.example.com/"})

        transport = httpx.MockTransport(handler)
        with pytest.raises(httpx.TooManyRedirects):
            _fetch_url_safely("http://loop-a.example.com/", transport=transport)

    def test_later_hop_in_a_longer_chain_is_still_validated(self, monkeypatch):
        # Confirms validation isn't only checked on hop 1 and hop 2 --
        # every hop in a longer chain must be checked.
        import httpx
        from app_service.services.extraction import _fetch_url_safely, UnsafeUrlError

        self._mock_public_dns(monkeypatch, {
            "a.example.com": "93.184.216.34",
            "b.example.com": "93.184.216.35",
            "c.example.com": "93.184.216.36",
        })

        def handler(request: httpx.Request) -> httpx.Response:
            host = request.url.host
            if host == "a.example.com":
                return httpx.Response(302, headers={"Location": "http://b.example.com/"})
            if host == "b.example.com":
                return httpx.Response(302, headers={"Location": "http://c.example.com/"})
            if host == "c.example.com":
                # Third hop redirects to a blocked target.
                return httpx.Response(302, headers={"Location": "http://192.168.1.1/internal"})
            return httpx.Response(200, text="unreachable")

        transport = httpx.MockTransport(handler)
        with pytest.raises(UnsafeUrlError):
            _fetch_url_safely("http://a.example.com/", transport=transport)
