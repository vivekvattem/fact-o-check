import re
from dataclasses import dataclass, field

AMBIGUOUS = {"company", "the company", "group", "the group", "we", "us", "it"}
SUFFIX = re.compile(
    r"(?:\s|,)+(?:limited|ltd\.?|private\s+limited|pvt\.?\s+ltd\.?|incorporated|inc\.?|corp(?:oration)?\.?)$",
    re.IGNORECASE,
)


@dataclass
class EntityNormalization:
    value: str | None
    rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_entity(value: str) -> EntityNormalization:
    canonical = re.sub(r"\s+", " ", value.strip()).casefold()
    canonical = canonical.strip(" \t\r\n.,;:")
    if not canonical or canonical in AMBIGUOUS:
        return EntityNormalization(None, warnings=["entity alias requires document context"])
    rules = ["case_whitespace_punctuation"]
    stripped = canonical
    while True:
        updated = SUFFIX.sub("", stripped).strip(" ,.")
        if updated == stripped:
            break
        stripped = updated
    if stripped != canonical:
        canonical = stripped
        rules.append("corporate_suffix_removed")
    return EntityNormalization(canonical or None, rules)
