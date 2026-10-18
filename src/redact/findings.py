"""Findings and privacy-safe reporting."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class Finding:
    kind: str
    page: int
    bbox: tuple[float, float, float, float]
    confidence: float = 1.0
    source: str = "regex"
    text: str = field(default="", repr=False)

    def masked(self) -> str:
        """Return a preview that does not leak the value."""
        text = self.text
        if not text:
            return f"[{self.kind}]"
        if self.kind == "email" and "@" in text:
            local, domain = text.split("@", 1)
            return f"{local[:1]}***@{domain}"
        digits = re.sub(r"\D", "", text)
        if digits and len(digits) >= 4:
            return f"***{digits[-4:]}"
        if self.kind in {"name", "address", "labeled"}:
            return f"{text[:1]}***"
        return "***"

    def digest(self) -> str:
        return hashlib.sha256(f"{self.kind}:{self.text}".encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "page": self.page,
            "bbox": [round(value, 1) for value in self.bbox],
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "preview": self.masked(),
            "digest": self.digest(),
        }
