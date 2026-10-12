from ml_common.preprocessing.display import display_token


def test_placeholders_become_words():
    assert display_token("__url__") == "link"
    assert display_token("__num__") == "number"
    assert display_token("call __num__") == "call number"


def test_ordinary_tokens_are_unchanged():
    assert display_token("otp") == "otp"
    assert display_token("bank account") == "bank account"
