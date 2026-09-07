import re


def normalize_predicate(value: str) -> str | None:
    canonical = re.sub(r"[^a-z0-9]+", "_", value.strip().casefold()).strip("_")
    return canonical or None
