"""Artifact storage abstraction (Dependency Inversion Principle).

The approved architecture specifies object storage (S3/GCS) for model
artifacts in production, while local development and this environment use
the filesystem. Every caller in this codebase depends on the `ArtifactStore`
protocol below, never on `LocalArtifactStore` directly, so adding an
`S3ArtifactStore` later is a pure addition -- no existing code changes.
"""
import shutil
from pathlib import Path
from typing import Protocol


class ArtifactStore(Protocol):
    """Minimal contract any artifact backend must satisfy."""

    def save(self, source_path: str, destination_key: str) -> str:
        """Persist the file at `source_path` under `destination_key`.
        Returns the final, canonical path/URI of the stored artifact.
        """
        ...

    def load_path(self, key: str) -> str:
        """Return a local filesystem path from which `key` can be read.
        For remote backends this would download-and-cache; for the local
        backend it is a no-op passthrough.
        """
        ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...


class LocalArtifactStore:
    """Filesystem-backed artifact store rooted at a configurable directory."""

    def __init__(self, root_dir: str):
        # NOTE: this used to silently redirect a fresh/empty root_dir to
        # whichever of a few hardcoded candidate paths already contained a
        # populated production registry_index.json. That "self-healing"
        # was actually dangerous: any caller that legitimately wanted an
        # isolated or brand-new registry (the test suite's tmp_path, a
        # first-time local checkout, a second worker process) would
        # instead transparently read from and write into the real
        # production artifacts directory, corrupting it with test/dev
        # entries. root_dir must always mean exactly what the caller
        # passed; callers that want the shared production registry should
        # pass its real path explicitly.
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, source_path: str, destination_key: str) -> str:
        destination = self._root / destination_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        if str(Path(source_path).resolve()) != str(destination.resolve()):
            shutil.copyfile(source_path, destination)
        return str(destination)

    def load_path(self, key: str) -> str:
        path = self._root / key
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found in store: {key}")
        return str(path)

    def exists(self, key: str) -> bool:
        return (self._root / key).exists()

    def delete(self, key: str) -> None:
        path = self._root / key
        if path.exists():
            path.unlink()

    @property
    def root_dir(self) -> str:
        return str(self._root)
