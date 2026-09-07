import re
from dataclasses import dataclass, field

AMBIGUOUS = {"company", "the company", "group", "the group", "we", "us", "it"}
SUFFIX = re.compile(
    r"(?:\s|,)+(?:limited|ltd\.?|private\s+limited|pvt\.?\s+ltd\.?|incorporated|inc\.?|corp(?:oration)?\.?)$",
    re.IGNORECASE,
)
FISCAL_PREFIX = re.compile(r"^(?:(?:q[1-4]\s+)?fy\s*\d{2,4})\s+", re.IGNORECASE)
FISCAL_SUFFIX = re.compile(
    r"\s+(?:in|for|during)\s+(?:(?:q[1-4]\s+)?fy\s*\d{2,4})$",
    re.IGNORECASE,
)
UNIT_QUALIFIER = re.compile(
    r"\s*\((?:[₹$]\s*)?(?:k|mn|cr|bn|thousand|million|crore|billion|%)\)\s*$",
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
    without_period = FISCAL_PREFIX.sub("", canonical)
    without_period = FISCAL_SUFFIX.sub("", without_period)
    if without_period != canonical:
        canonical = without_period.strip()
        rules.append("fiscal_label_removed")
    without_unit = UNIT_QUALIFIER.sub("", canonical)
    if without_unit != canonical:
        canonical = without_unit.strip()
        rules.append("unit_qualifier_removed")
    return EntityNormalization(canonical or None, rules)
