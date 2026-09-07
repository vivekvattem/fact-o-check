import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

SCALES = {
    "thousand": Decimal("1000"),
    "lakh": Decimal("100000"),
    "lac": Decimal("100000"),
    "million": Decimal("1000000"),
    "crore": Decimal("10000000"),
    "billion": Decimal("1000000000"),
}


@dataclass(frozen=True)
class ParsedNumber:
    value: Decimal
    scale: str | None
    suffix: str | None
    negative_style: str | None


def parse_number(text: str) -> ParsedNumber | None:
    value = text.strip()
    negative_style = None
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1].strip()
        negative_style = "parentheses"
    match = re.fullmatch(
        r"(?:₹|\$|INR\b|USD\b)?\s*([+-]?\d[\d,]*(?:\.\d+)?)"
        r"\s*(thousands?|lakhs?|lacs?|millions?|crores?|billions?)?\s*"
        r"(percent|per\s+cent|%|[A-Za-z][A-Za-z0-9_./-]*)?",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    number, scale, suffix = match.groups()
    if not valid_commas(number):
        return None
    try:
        parsed = Decimal(number.replace(",", ""))
    except InvalidOperation:
        return None
    if negative_style:
        parsed = -parsed
    scale = scale.lower().removesuffix("s") if scale else None
    return ParsedNumber(
        value=parsed * SCALES.get(scale, Decimal(1)),
        scale=scale,
        suffix=suffix.lower() if suffix else None,
        negative_style=negative_style,
    )


def valid_commas(value: str) -> bool:
    unsigned = value.lstrip("+-")
    integer = unsigned.split(".", 1)[0]
    if "," not in integer:
        return True
    return bool(
        re.fullmatch(r"\d{1,3}(?:,\d{3})+", integer)
        or re.fullmatch(r"\d{1,2}(?:,\d{2})*,\d{3}", integer)
    )


def json_number(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    return int(integral) if value == integral else float(value)
