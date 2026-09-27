import pandas as pd
import pytest

from ml_training.data.validator import DatasetValidationError, DatasetValidator, ValidationConfig


def make_df(rows: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["text", "label"])


class TestDatasetValidator:
    def test_valid_dataset_passes(self):
        df = make_df(
            [("Urgent verify now", "scam"), ("Hi there", "legitimate")] * 10
        )
        validator = DatasetValidator(ValidationConfig(min_rows=5))
        report = validator.validate(df)
        assert report.row_count == 20

    def test_missing_columns_raises(self):
        df = pd.DataFrame({"foo": [1, 2]})
        validator = DatasetValidator()
        with pytest.raises(DatasetValidationError):
            validator.validate(df)

    def test_too_few_rows_raises(self):
        df = make_df([("Hi", "legitimate")])
        validator = DatasetValidator(ValidationConfig(min_rows=10))
        with pytest.raises(DatasetValidationError):
            validator.validate(df)

    def test_null_values_raise(self):
        df = make_df([("Hi there", "legitimate")] * 5)
        df.loc[0, "text"] = None
        validator = DatasetValidator(ValidationConfig(min_rows=1))
        with pytest.raises(DatasetValidationError):
            validator.validate(df)

    def test_unexpected_label_raises(self):
        df = make_df([("Hi there", "not_a_real_label")] * 5)
        validator = DatasetValidator(ValidationConfig(min_rows=1))
        with pytest.raises(DatasetValidationError):
            validator.validate(df)

    def test_text_too_short_raises(self):
        df = make_df([("Hi", "legitimate")] * 5)
        validator = DatasetValidator(ValidationConfig(min_rows=1, min_text_length=10))
        with pytest.raises(DatasetValidationError):
            validator.validate(df)

    def test_class_imbalance_produces_warning_not_error(self):
        rows = [("Legit message here", "legitimate")] * 50 + [("Urgent scam now", "scam")] * 1
        df = make_df(rows)
        validator = DatasetValidator(ValidationConfig(min_rows=1, max_class_imbalance_ratio=5.0))

        report = validator.validate(df)  # must not raise

        assert any("imbalance" in warning.lower() for warning in report.warnings)

    def test_balanced_dataset_has_no_imbalance_warning(self):
        rows = [("Legit message here", "legitimate")] * 10 + [("Urgent scam now", "scam")] * 10
        df = make_df(rows)
        validator = DatasetValidator(ValidationConfig(min_rows=1))

        report = validator.validate(df)

        assert report.warnings == []

    def test_label_distribution_is_reported(self):
        rows = [("Legit message here", "legitimate")] * 3 + [("Urgent scam now", "scam")] * 2
        df = make_df(rows)
        validator = DatasetValidator(ValidationConfig(min_rows=1))

        report = validator.validate(df)

        assert report.label_distribution == {"legitimate": 3, "scam": 2}
