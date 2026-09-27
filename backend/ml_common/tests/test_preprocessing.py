from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_common.preprocessing.text_cleaner import CleaningConfig, TextCleaner
from ml_common.preprocessing.tokenizer import Tokenizer, TokenizerConfig


class TestTextCleaner:
    def test_lowercases_text(self):
        cleaner = TextCleaner()
        assert cleaner.clean("HELLO World") == "hello world"

    def test_replaces_urls_with_placeholder(self):
        cleaner = TextCleaner()
        result = cleaner.clean("Click http://scam.link now")
        assert "__url__" in result
        assert "scam.link" not in result

    def test_replaces_emails_with_placeholder(self):
        cleaner = TextCleaner()
        result = cleaner.clean("Contact us at fraud@bad-domain.com")
        assert "__email__" in result
        assert "fraud@bad-domain.com" not in result

    def test_replaces_numbers_with_placeholder(self):
        cleaner = TextCleaner()
        result = cleaner.clean("Your code is 483920")
        assert "__num__" in result
        assert "483920" not in result

    def test_collapses_whitespace(self):
        cleaner = TextCleaner()
        assert cleaner.clean("too    many     spaces") == "too many spaces"

    def test_handles_none_input(self):
        cleaner = TextCleaner()
        assert cleaner.clean(None) == ""

    def test_clean_batch(self):
        cleaner = TextCleaner()
        results = cleaner.clean_batch(["HELLO", "WORLD"])
        assert results == ["hello", "world"]

    def test_config_can_disable_lowercasing(self):
        cleaner = TextCleaner(CleaningConfig(lowercase=False, remove_punctuation=False))
        assert cleaner.clean("HELLO") == "HELLO"


class TestTokenizer:
    def test_removes_stopwords(self):
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize("this is a test message")
        assert "this" not in tokens
        assert "test" in tokens

    def test_preserves_urgency_signal_words(self):
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize("urgent action needed now")
        assert "urgent" in tokens
        assert "now" in tokens

    def test_applies_stemming(self):
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize("running runners immediately")
        # "running"/"runners" should collapse toward a shared stem
        assert any(t.startswith("runn") for t in tokens)

    def test_filters_short_tokens(self):
        config = TokenizerConfig(min_token_length=3)
        tokenizer = Tokenizer(config)
        tokens = tokenizer.tokenize("a an ok verification")
        assert "a" not in tokens
        assert "an" not in tokens

    def test_tokenize_to_string_joins_with_spaces(self):
        tokenizer = Tokenizer()
        result = tokenizer.tokenize_to_string("urgent verification needed")
        assert isinstance(result, str)
        assert " " in result

    def test_empty_input_returns_empty_list(self):
        tokenizer = Tokenizer()
        assert tokenizer.tokenize("") == []


class TestTextPreprocessingPipeline:
    def test_process_returns_space_joined_tokens(self):
        pipeline = TextPreprocessingPipeline()
        result = pipeline.process("URGENT! Verify your account now at http://bad.link")
        assert "__url__" in result
        assert "urgent" in result
        assert result == result.lower()

    def test_process_batch(self):
        pipeline = TextPreprocessingPipeline()
        results = pipeline.process_batch(["Hello there", "URGENT now"])
        assert len(results) == 2

    def test_process_to_tokens_returns_list(self):
        pipeline = TextPreprocessingPipeline()
        tokens = pipeline.process_to_tokens("Urgent payment required now")
        assert isinstance(tokens, list)
        assert "urgent" in tokens

    def test_identical_input_produces_identical_output(self):
        """Determinism is a hard requirement: the same message must
        preprocess identically every time, since training and serving
        both depend on this pipeline being a pure function.
        """
        pipeline = TextPreprocessingPipeline()
        text = "Your OTP is 483920, verify immediately."
        assert pipeline.process(text) == pipeline.process(text)
