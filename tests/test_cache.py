"""
Tests for pipeline.cache.FileCache
Run with: pytest tests/test_cache.py -v
"""
import hashlib
import json

import pytest

from pipeline.cache import FileCache


def test_set_and_get(tmp_path):
    cache = FileCache(tmp_path / "cache")
    cache.set("hello", {"result": 42})
    assert cache.get("hello") == {"result": 42}


def test_get_miss(tmp_path):
    cache = FileCache(tmp_path / "cache")
    assert cache.get("nonexistent_key") is None


def test_exists(tmp_path):
    cache = FileCache(tmp_path / "cache")
    cache.set("present", {"x": 1})
    assert cache.exists("present") is True
    assert cache.exists("absent") is False


def test_len(tmp_path):
    cache = FileCache(tmp_path / "cache")
    assert len(cache) == 0
    cache.set("a", {"v": 1})
    cache.set("b", {"v": 2})
    cache.set("c", {"v": 3})
    assert len(cache) == 3


def test_clear(tmp_path):
    cache = FileCache(tmp_path / "cache")
    cache.set("x", {"v": 1})
    cache.set("y", {"v": 2})
    cache.clear()
    assert len(cache) == 0


def test_atomic_write(tmp_path):
    cache_dir = tmp_path / "cache"
    cache = FileCache(cache_dir)
    cache.set("atomic_test", {"data": "written"})
    key = hashlib.md5("atomic_test".encode("utf-8")).hexdigest()
    json_file = cache_dir / f"{key}.json"
    assert json_file.exists()
    assert json.loads(json_file.read_text()) == {"data": "written"}


def test_special_characters(tmp_path):
    cache = FileCache(tmp_path / "cache")
    query = '"Düsseldorf Königsallee GmbH & Co. KG" Düsseldorf'
    payload = {"name": query, "score": 99}
    cache.set(query, payload)
    assert cache.get(query) == payload


def test_overwrite(tmp_path):
    cache = FileCache(tmp_path / "cache")
    cache.set("key", {"version": 1})
    cache.set("key", {"version": 2})
    assert cache.get("key") == {"version": 2}
