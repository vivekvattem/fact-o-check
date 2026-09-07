import re

REPORTING_MODIFIERS = {
    "at",
    "estimated",
    "expected",
    "is",
    "moderated",
    "reported",
    "to",
    "was",
}


def normalize_predicate(value: str) -> str | None:
    canonical = value.strip().casefold()
    canonical = re.sub(
        r"\bgross\s+domestic\s+product\b(?:\s*\(\s*gdp\s*\))?",
        "gdp",
        canonical,
    )
    tokens = re.findall(r"[a-z0-9]+", canonical)
    normalized = []
    for token in tokens:
        if re.fullmatch(r"fy\d{2,4}", token) or token in REPORTING_MODIFIERS:
            continue
        normalized.append("growth" if token in {"grew", "grow", "growing"} else token)
    return "_".join(normalized) or None
