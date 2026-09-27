import time

from app_service.core.captcha import generate_challenge, verify_answer, CAPTCHA_TTL_SECONDS


SECRET = "test-secret-key-for-captcha-tests"


def _solve(question: str) -> int:
    # question is "What is A op B?"
    body = question.replace("What is", "").replace("?", "").strip()
    a_str, op, b_str = body.split(" ")
    a, b = int(a_str), int(b_str)
    return a + b if op == "+" else a - b


class TestCaptchaGeneration:
    def test_generates_a_question_and_token(self):
        challenge = generate_challenge(SECRET)
        assert challenge.question
        assert challenge.token

    def test_token_does_not_embed_the_answer_in_cleartext(self):
        # The token should decode to "<expiry>:<hmac signature>" only --
        # the answer itself must not appear as a separate cleartext field
        # (a crude substring check on the digit isn't meaningful since a
        # single digit is likely to appear coincidentally inside a hex
        # signature; instead check the decoded structure directly).
        import base64

        challenge = generate_challenge(SECRET)
        decoded = base64.urlsafe_b64decode(challenge.token.encode("utf-8")).decode("utf-8")
        parts = decoded.split(":")
        assert len(parts) == 2, "token should decode to exactly <expiry>:<signature>"
        expires_at_str, signature = parts
        assert expires_at_str.isdigit()
        assert len(signature) == 64  # hex-encoded sha256 digest


class TestCaptchaVerification:
    def test_correct_answer_is_accepted(self):
        challenge = generate_challenge(SECRET)
        answer = _solve(challenge.question)
        assert verify_answer(challenge.token, str(answer), SECRET) is True

    def test_incorrect_answer_is_rejected(self):
        challenge = generate_challenge(SECRET)
        answer = _solve(challenge.question)
        assert verify_answer(challenge.token, str(answer + 1), SECRET) is False

    def test_whitespace_around_answer_is_tolerated(self):
        challenge = generate_challenge(SECRET)
        answer = _solve(challenge.question)
        assert verify_answer(challenge.token, f"  {answer}  ", SECRET) is True

    def test_non_numeric_answer_is_rejected(self):
        challenge = generate_challenge(SECRET)
        assert verify_answer(challenge.token, "not a number", SECRET) is False

    def test_empty_token_is_rejected(self):
        assert verify_answer("", "5", SECRET) is False

    def test_garbage_token_is_rejected(self):
        assert verify_answer("not-a-real-token", "5", SECRET) is False

    def test_token_signed_with_a_different_secret_is_rejected(self):
        challenge = generate_challenge(SECRET)
        answer = _solve(challenge.question)
        assert verify_answer(challenge.token, str(answer), "a-completely-different-secret") is False

    def test_expired_token_is_rejected(self, monkeypatch):
        import app_service.core.captcha as captcha_module

        challenge = generate_challenge(SECRET)
        answer = _solve(challenge.question)

        # Simulate time passing beyond the TTL without sleeping in the test.
        real_time = time.time
        monkeypatch.setattr(captcha_module.time, "time", lambda: real_time() + CAPTCHA_TTL_SECONDS + 1)

        assert verify_answer(challenge.token, str(answer), SECRET) is False

    def test_a_token_cannot_be_reused_for_a_different_answer(self):
        # Tampering: take a valid token and try to pair it with an answer
        # from a DIFFERENT challenge -- must fail, since the signature is
        # bound to (answer, expiry), not just expiry. Retry a few times in
        # the rare case two independent random challenges land on the same
        # answer by coincidence (small answer space), which would make the
        # reuse legitimately succeed and isn't the case under test.
        for _ in range(10):
            challenge_1 = generate_challenge(SECRET)
            challenge_2 = generate_challenge(SECRET)
            answer_1 = _solve(challenge_1.question)
            answer_2 = _solve(challenge_2.question)
            if answer_1 != answer_2:
                break
        else:
            raise AssertionError("could not produce two challenges with different answers")

        assert verify_answer(challenge_1.token, str(answer_2), SECRET) is False
