import pytest

from ml_training.data.loader import DatasetLoader, DatasetLoadError, DatasetSource, LoaderConfig


@pytest.fixture()
def csv_file(tmp_path):
    def _write(name: str, content: str) -> str:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    return _write


class TestDatasetLoader:
    def test_loads_a_single_source(self, csv_file):
        path = csv_file(
            "a.csv",
            "text,label\n"
            "\"Urgent verify now\",scam\n"
            "\"Hi how are you\",legitimate\n",
        )
        loader = DatasetLoader(LoaderConfig(sources=[DatasetSource(path=path)]))
        df = loader.load()

        assert len(df) == 2
        assert set(df.columns) == {"text", "label"}

    def test_merges_multiple_sources(self, csv_file):
        path_a = csv_file("a.csv", "text,label\n\"Urgent verify now\",scam\n")
        path_b = csv_file("b.csv", "text,label\n\"Hi how are you\",legitimate\n")

        loader = DatasetLoader(
            LoaderConfig(sources=[DatasetSource(path=path_a), DatasetSource(path=path_b)])
        )
        df = loader.load()

        assert len(df) == 2

    def test_maps_custom_column_names(self, csv_file):
        path = csv_file(
            "custom.csv",
            "message,category\n\"Urgent verify now\",scam\n",
        )
        loader = DatasetLoader(
            LoaderConfig(
                sources=[DatasetSource(path=path, text_column="message", label_column="category")]
            )
        )
        df = loader.load()

        assert list(df.columns) == ["text", "label"]
        assert df.iloc[0]["label"] == "scam"

    def test_normalizes_label_case_and_whitespace(self, csv_file):
        path = csv_file("a.csv", "text,label\n\"Urgent verify now\", ScaM \n")
        loader = DatasetLoader(LoaderConfig(sources=[DatasetSource(path=path)]))
        df = loader.load()
        assert df.iloc[0]["label"] == "scam"

    def test_drops_duplicate_text_rows(self, csv_file):
        path = csv_file(
            "a.csv",
            "text,label\n\"Same message\",scam\n\"Same message\",scam\n\"Different\",legitimate\n",
        )
        loader = DatasetLoader(LoaderConfig(sources=[DatasetSource(path=path)]))
        df = loader.load()
        assert len(df) == 2

    def test_drops_empty_text_rows(self, csv_file):
        path = csv_file("a.csv", "text,label\n\"\",scam\n\"Valid message\",legitimate\n")
        loader = DatasetLoader(LoaderConfig(sources=[DatasetSource(path=path)]))
        df = loader.load()
        assert len(df) == 1

    def test_missing_file_raises_dataset_load_error(self):
        loader = DatasetLoader(LoaderConfig(sources=[DatasetSource(path="/no/such/file.csv")]))
        with pytest.raises(DatasetLoadError):
            loader.load()

    def test_missing_required_column_raises(self, csv_file):
        path = csv_file("bad.csv", "foo,bar\n1,2\n")
        loader = DatasetLoader(LoaderConfig(sources=[DatasetSource(path=path)]))
        with pytest.raises(DatasetLoadError):
            loader.load()

    def test_empty_sources_list_raises_value_error(self):
        with pytest.raises(ValueError):
            DatasetLoader(LoaderConfig(sources=[]))
