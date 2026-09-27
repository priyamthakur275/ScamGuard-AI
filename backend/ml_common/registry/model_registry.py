"""Model registry.

Mirrors the `model_registry_meta` table from the approved database schema,
but lives as a lightweight, dependency-free JSON index alongside the
artifacts themselves -- this is what both the training pipeline (writer)
and the inference service (reader) depend on. Neither depends on the
other directly (Dependency Inversion), and neither depends on Postgres:
the app_service's `model_registry_meta` table can be kept in sync from
this registry's index as an optional, separate audit copy, but the
registry itself must never require a live database connection just to
serve a prediction.
"""
import json
import threading
from pathlib import Path

from ml_common.domain.value_objects import ModelMetrics, ModelVersionInfo
from ml_common.registry.artifact_store import ArtifactStore, LocalArtifactStore


class ModelNotFoundError(Exception):
    pass


class ModelRegistry:
    """Thread-safe registry of versioned (model, vectorizer) artifact pairs."""

    _INDEX_KEY = "registry_index.json"

    def __init__(self, artifact_store: ArtifactStore | None = None, root_dir: str = "artifacts"):
        self._store: ArtifactStore = artifact_store or LocalArtifactStore(root_dir)
        self._lock = threading.RLock()

    # -- internal index persistence -----------------------------------

    def _read_index(self) -> dict:
        if not self._store.exists(self._INDEX_KEY):
            return {"versions": []}
        path = self._store.load_path(self._INDEX_KEY)
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_index(self, index: dict) -> None:
        # LocalArtifactStore.save expects a source file on disk; write to
        # a temp location inside the store root and "save" it over itself.
        if isinstance(self._store, LocalArtifactStore):
            target = Path(self._store.root_dir) / self._INDEX_KEY
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(index, handle, indent=2)
        else:  # pragma: no cover - exercised once a remote store exists
            import tempfile

            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
                json.dump(index, tmp, indent=2)
                tmp_path = tmp.name
            self._store.save(tmp_path, self._INDEX_KEY)

    # -- public API ------------------------------------------------------

    def register(
        self,
        model_name: str,
        version: str,
        local_model_path: str,
        local_vectorizer_path: str,
        metrics: ModelMetrics,
        train_rows: int = 0,
        test_rows: int = 0,
    ) -> ModelVersionInfo:
        """Register a newly trained (model, vectorizer) pair.

        The artifacts are copied into the artifact store under a
        version-qualified key so multiple versions of the same model name
        can coexist -- this is what makes rollback and shadow evaluation
        possible.
        """
        from datetime import datetime, timezone

        with self._lock:
            model_key = f"{model_name}/{version}/model.joblib"
            vectorizer_key = f"{model_name}/{version}/vectorizer.joblib"

            stored_model_path = self._store.save(local_model_path, model_key)
            stored_vectorizer_path = self._store.save(local_vectorizer_path, vectorizer_key)

            info = ModelVersionInfo(
                model_name=model_name,
                version=version,
                metrics=metrics,
                is_production=False,
                trained_at=datetime.now(timezone.utc).isoformat(),
                artifact_path=stored_model_path,
                vectorizer_path=stored_vectorizer_path,
                train_rows=train_rows,
                test_rows=test_rows,
            )

            index = self._read_index()
            index["versions"] = [
                v
                for v in index["versions"]
                if not (v["model_name"] == model_name and v["version"] == version)
            ]
            index["versions"].append(info.to_dict())
            self._write_index(index)

            return info

    def promote(self, model_name: str, version: str) -> ModelVersionInfo:
        """Mark the given version as the single production version for
        `model_name`, demoting any previously promoted version. This is
        the only operation that changes what the inference service serves.
        """
        with self._lock:
            index = self._read_index()
            found: dict | None = None

            for entry in index["versions"]:
                if entry["model_name"] == model_name:
                    entry["is_production"] = entry["version"] == version
                    if entry["version"] == version:
                        found = entry

            if found is None:
                raise ModelNotFoundError(f"No version '{version}' registered for '{model_name}'")

            self._write_index(index)
            return ModelVersionInfo.from_dict(found)

    def get_production(self, model_name: str) -> ModelVersionInfo:
        index = self._read_index()
        for entry in index["versions"]:
            if entry["model_name"] == model_name and entry["is_production"]:
                return ModelVersionInfo.from_dict(entry)
        raise ModelNotFoundError(f"No production version registered for '{model_name}'")

    def get_version(self, model_name: str, version: str) -> ModelVersionInfo:
        index = self._read_index()
        for entry in index["versions"]:
            if entry["model_name"] == model_name and entry["version"] == version:
                return ModelVersionInfo.from_dict(entry)
        raise ModelNotFoundError(f"No version '{version}' registered for '{model_name}'")

    def list_versions(self, model_name: str) -> list[ModelVersionInfo]:
        index = self._read_index()
        return [
            ModelVersionInfo.from_dict(entry)
            for entry in index["versions"]
            if entry["model_name"] == model_name
        ]

    def list_all(self) -> list[ModelVersionInfo]:
        """Every registered version across all model names -- the real,
        complete set of what's actually in the registry. Used by the
        admin Model Evaluation view (Phase 15), which must never show
        anything the registry doesn't actually contain.
        """
        index = self._read_index()
        return [ModelVersionInfo.from_dict(entry) for entry in index["versions"]]

    def resolve_artifact_paths(self, info: ModelVersionInfo) -> tuple[str, str]:
        """Resolve a registered version's artifacts to local filesystem
        paths ready to be deserialized (downloading/caching first if the
        backing store is remote).
        """
        model_key = f"{info.model_name}/{info.version}/model.joblib"
        vectorizer_key = f"{info.model_name}/{info.version}/vectorizer.joblib"
        return self._store.load_path(model_key), self._store.load_path(vectorizer_key)
