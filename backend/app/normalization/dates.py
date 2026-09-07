import calendar
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

MONTHS = {name.casefold(): number for number, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.casefold(): number for number, name in enumerate(calendar.month_abbr) if name})
DATE_PATTERN = r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"


@dataclass
class TemporalNormalization:
    period_start: date | None = None
    period_end: date | None = None
    as_of_date: date | None = None
    normalized_date: date | None = None
    rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_date_literal(value: str) -> date | None:
    text = value.strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    match = re.fullmatch(DATE_PATTERN, text, re.IGNORECASE)
    if not match:
        return None
    month, day, year = match.groups()
    month_number = MONTHS.get(month.casefold())
    if not month_number:
        return None
    try:
        return date(int(year), month_number, int(day))
    except ValueError:
        return None


def normalize_temporal(text: str, *, india_fy_context: bool) -> TemporalNormalization:
    result = TemporalNormalization()
    as_of = re.search(rf"\bas\s+of\s*:?[ \t]*{DATE_PATTERN}", text, re.IGNORECASE)
    if as_of:
        parsed = parse_date_literal(" ".join(as_of.groups()))
        if parsed:
            result.as_of_date = parsed
            result.rules.append("as_of_date")

    year_ended = re.search(rf"\byear\s+ended\s*:?[ \t]*{DATE_PATTERN}", text, re.IGNORECASE)
    if year_ended:
        end = parse_date_literal(" ".join(year_ended.groups()))
        if end:
            result.period_end = end
            try:
                prior_anniversary = end.replace(year=end.year - 1)
            except ValueError:
                prior_anniversary = date(end.year - 1, 2, 28)
            result.period_start = prior_anniversary + timedelta(days=1)
            result.rules.append("year_ended_period")

    fy = re.search(
        r"\b(?:FY\s*)?(?:(\d{4})\s*[-/]\s*(\d{2,4})|FY\s*(\d{2})|FY\s*(\d{4}))\b",
        text,
        re.IGNORECASE,
    )
    if fy:
        if not india_fy_context:
            result.warnings.append("FY notation lacks deterministic India fiscal-year context")
        else:
            start_full, end_part, short_year, full_year = fy.groups()
            if start_full and end_part:
                start_year = int(start_full)
                end_year = (
                    int(end_part) if len(end_part) == 4 else start_year // 100 * 100 + int(end_part)
                )
                if end_year != start_year + 1:
                    result.warnings.append("fiscal-year range is not consecutive")
                else:
                    result.period_start = date(start_year, 4, 1)
                    result.period_end = date(end_year, 3, 31)
                    result.rules.append("india_fiscal_year_range")
            else:
                if short_year and int(short_year) >= 70:
                    result.warnings.append("two-digit fiscal year has an ambiguous century")
                else:
                    end_year = int(full_year) if full_year else 2000 + int(short_year)
                    result.period_start = date(end_year - 1, 4, 1)
                    result.period_end = date(end_year, 3, 31)
                    result.rules.append("india_fiscal_year_end")

            quarter = re.search(r"\bQ([1-4])\b", text, re.IGNORECASE)
            if quarter and result.period_start:
                number = int(quarter.group(1))
                month = 4 + (number - 1) * 3
                year = result.period_start.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                start = date(year, month, 1)
                end_month = (month - 1 + 3) % 12 + 1
                end_year = year + (month - 1 + 3) // 12
                result.period_start = start
                result.period_end = date(end_year, end_month, 1) - timedelta(days=1)
                result.rules.append(f"india_fiscal_quarter_q{number}")
    return result
