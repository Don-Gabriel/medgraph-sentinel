"""ID formatting per docs/INTERFACES.md section 2: prefixed, zero-padded."""

_WIDTHS = {"CLM": 7}  # claims dominate; everything else uses 6 digits


def make_id(prefix: str, n: int) -> str:
    return f"{prefix}_{n:0{_WIDTHS.get(prefix, 6)}d}"


class IdSeq:
    """Sequential ID source for one prefix (deterministic by construction)."""

    def __init__(self, prefix: str, start: int = 1):
        self.prefix = prefix
        self._next = start

    def take(self) -> str:
        out = make_id(self.prefix, self._next)
        self._next += 1
        return out
