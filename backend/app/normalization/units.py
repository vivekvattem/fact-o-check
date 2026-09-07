import re
from dataclasses import dataclass, field

from app.normalization.numbers import SCALES, json_number, parse_number


@dataclass
class ValueNormalization:
    value: int | float | str | bool | None = None
    unit: str | None = None
    rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_value(
    raw_value: object, value_type: str | None, raw_unit: str | None
) -> ValueNormalization:
    if not isinstance(raw_value, (str, int, float)) or isinstance(raw_value, bool):
        return ValueNormalization(warnings=["raw_value is not a supported scalar"])
    text = str(raw_value).strip()
    kind = (value_type or "").upper()
    if kind == "CURRENCY":
        return normalize_currency(text, raw_unit)
    if kind == "PERCENTAGE":
        return normalize_percentage(text, raw_unit)
    if kind in {"NUMBER", "QUANTITY"}:
        return normalize_numeric(text, raw_unit, quantity=kind == "QUANTITY")
    if kind == "BOOLEAN":
        lowered = text.casefold()
        if lowered in {"true", "yes"}:
            return ValueNormalization(True, "BOOLEAN", ["boolean_literal"])
        if lowered in {"false", "no"}:
            return ValueNormalization(False, "BOOLEAN", ["boolean_literal"])
        return ValueNormalization(warnings=["ambiguous boolean"])
    return ValueNormalization(
        warnings=[f"value type {kind or 'UNKNOWN'} is not numerically normalized"]
    )


def normalize_currency(text: str, raw_unit: str | None) -> ValueNormalization:
    currencies = set()
    combined = f"{text} {raw_unit or ''}"
    if "₹" in combined or re.search(r"\bINR\b", combined, re.IGNORECASE):
        currencies.add("INR")
    if "$" in combined or re.search(r"\bUSD\b", combined, re.IGNORECASE):
        currencies.add("USD")
    if len(currencies) != 1:
        reason = "currency is missing" if not currencies else "multiple currencies are present"
        return ValueNormalization(warnings=[reason])
    parsed = parse_number(text)
    if not parsed:
        return ValueNormalization(warnings=["currency amount could not be parsed"])
    currency = currencies.pop()
    if parsed.suffix and parsed.suffix.upper() not in {currency}:
        return ValueNormalization(warnings=["currency suffix is not supported"])
    unit_scale = _unit_scale(raw_unit) if not parsed.scale else None
    normalized = parsed.value * SCALES.get(unit_scale, 1)
    rules = ["currency_to_base_unit"]
    scale = parsed.scale or unit_scale
    if scale:
        rules.append(f"{scale}_to_{currency.lower()}")
    if parsed.negative_style:
        rules.append("parentheses_as_negative")
    return ValueNormalization(json_number(normalized), currency, rules)


def normalize_percentage(text: str, raw_unit: str | None) -> ValueNormalization:
    combined = f"{text} {raw_unit or ''}"
    if not re.search(r"(?:%|\bpercent\b|\bper\s+cent\b)", combined, re.IGNORECASE):
        return ValueNormalization(warnings=["percentage marker is missing"])
    parsed = parse_number(text) or parse_number(combined)
    if not parsed or parsed.scale:
        return ValueNormalization(warnings=["percentage could not be parsed unambiguously"])
    rules = ["percentage_points"]
    if parsed.negative_style:
        rules.append("parentheses_as_negative")
    return ValueNormalization(json_number(parsed.value), "PERCENT", rules)


def normalize_numeric(text: str, raw_unit: str | None, *, quantity: bool) -> ValueNormalization:
    parsed = parse_number(text)
    if not parsed:
        return ValueNormalization(warnings=["number could not be parsed"])
    unit_scale = _unit_scale(raw_unit) if not parsed.scale else None
    normalized = parsed.value * SCALES.get(unit_scale, 1)
    suffix = parsed.suffix
    unit = _base_unit(raw_unit) or suffix or ("COUNT" if not quantity else None)
    if quantity and not unit:
        return ValueNormalization(warnings=["quantity unit is missing"])
    rules = ["numeric_parser"]
    scale = parsed.scale or unit_scale
    if scale:
        rules.append(f"{scale}_scale")
    if parsed.negative_style:
        rules.append("parentheses_as_negative")
    return ValueNormalization(json_number(normalized), unit.upper() if unit else None, rules)


def _unit_scale(raw_unit: str | None) -> str | None:
    if not raw_unit:
        return None
    match = re.search(rf"\b({'|'.join(SCALES)})s?\b", raw_unit, re.IGNORECASE)
    return match.group(1).casefold() if match else None


def _base_unit(raw_unit: str | None) -> str | None:
    if not raw_unit:
        return None
    value = re.sub(rf"\b({'|'.join(SCALES)})s?\b", "", raw_unit, flags=re.IGNORECASE)
    value = re.sub(r"\b(?:INR|USD)\b|[₹$]", "", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip() or None
