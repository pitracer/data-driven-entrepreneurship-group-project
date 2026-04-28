"""
Reusable API key pool classes.

ExhaustPool  — use one key until it fails/exhausts, then rotate to the next.
               Best for Serper: burn free credits on one account before opening another.

RoundRobinPool — spread calls evenly across all keys.
                 Best for Groq: stay under per-key RPM limits by distributing load.
"""
from __future__ import annotations


class ExhaustPool:
    """
    Exhaust one key fully before rotating to the next.

    Usage:
        pool = ExhaustPool(["key1", "key2", "key3"])
        key = pool.current()
        if key is None:
            # all keys exhausted
            ...
        # on rate-limit / quota error:
        if not pool.rotate():
            # no more keys available
            ...
    """

    def __init__(self, keys: list[str]) -> None:
        self._keys = list(keys)
        self._idx = 0

    def current(self) -> str | None:
        """Return the active key, or None if all keys are exhausted."""
        if self._idx < len(self._keys):
            return self._keys[self._idx]
        return None

    def rotate(self) -> bool:
        """
        Advance to the next key.

        Returns True if a new key is available, False if all keys are exhausted.
        """
        self._idx += 1
        return self._idx < len(self._keys)

    def is_exhausted(self) -> bool:
        return self._idx >= len(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def remaining(self) -> int:
        return max(0, len(self._keys) - self._idx)


class RoundRobinPool:
    """
    Spread calls evenly across all keys.

    Usage:
        pool = RoundRobinPool(["key1", "key2", "key3"])
        key = pool.next()   # returns keys in rotation
    """

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise ValueError("RoundRobinPool requires at least one key")
        self._keys = list(keys)
        self._idx = 0

    def next(self) -> str:
        """Return the next key in rotation."""
        key = self._keys[self._idx % len(self._keys)]
        self._idx += 1
        return key

    def __len__(self) -> int:
        return len(self._keys)
