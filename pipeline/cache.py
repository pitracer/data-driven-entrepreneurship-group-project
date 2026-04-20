"""
Generic JSON file cache with MD5-based keys and atomic writes.

Usage:
    cache = FileCache(Path("data/cache/serp"))
    result = cache.get("some query")
    if result is None:
        result = expensive_api_call("some query")
        cache.set("some query", result)
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


class FileCache:
    """Thread-safe, file-system-backed JSON cache keyed by MD5 of the query."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _key(self, query: str) -> str:
        """Derive a filesystem-safe key from an arbitrary query string."""
        return hashlib.md5(query.encode("utf-8")).hexdigest()

    def _path(self, query: str) -> Path:
        return self.cache_dir / f"{self._key(query)}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, query: str) -> Any | None:
        """Return cached data for *query*, or None on cache miss."""
        path = self._path(query)
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def set(self, query: str, data: Any) -> None:
        """Persist *data* for *query* atomically (write-then-rename)."""
        path = self._path(query)
        # Write to a temp file in the same directory, then atomically rename.
        # Prevents partial reads if another process reads concurrently.
        fd, tmp_path = tempfile.mkstemp(dir=str(self.cache_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp_path, str(path))  # atomic on POSIX
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def exists(self, query: str) -> bool:
        """Check if a cached entry exists without loading it."""
        return self._path(query).exists()

    def clear(self) -> None:
        """Remove all cached entries."""
        for p in self.cache_dir.glob("*.json"):
            p.unlink()

    def __len__(self) -> int:
        """Return the number of cached entries."""
        return sum(1 for _ in self.cache_dir.glob("*.json"))

    def __repr__(self) -> str:
        return f"FileCache(dir={self.cache_dir!r}, entries={len(self)})"
