"""A dependency-free, rule-based natural language date parser.

Input is normalized (case, punctuation, trailing times of day) and then offered
to a series of handlers. Each handler recognizes one family of expressions and
returns ``None`` if the text is not in that family. Expressions that are built
from other expressions, like "3 days after next Tuesday", recurse.
"""

import calendar
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class _Duration:
    months: int = 0
    days: int = 0
    business_days: int = 0

    def __add__(self, other: "_Duration") -> "_Duration":
        return _Duration(
            self.months + other.months,
            self.days + other.days,
            self.business_days + other.business_days,
        )

    def __mul__(self, n: int) -> "_Duration":
        return _Duration(self.months * n, self.days * n, self.business_days * n)


def _alternatives(options: Iterable[str]) -> str:
    """Build a regex alternation that tries the longest options first."""
    return "|".join(sorted(map(re.escape, options), key=len, reverse=True))


def _compounds(tens: str, ones: Iterable[str]) -> list[str]:
    return [f"{tens}{sep}{one}" for one in ones for sep in (" ", "-")]


_MONTHS = {
    name: number
    for number, names in enumerate(
        (
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sep", "sept"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        ),
        start=1,
    )
    for name in names
}

_WEEKDAYS = {
    name: number
    for number, names in enumerate(
        (
            ("monday", "mon"),
            ("tuesday", "tue", "tues"),
            ("wednesday", "wed", "weds"),
            ("thursday", "thu", "thur", "thurs"),
            ("friday", "fri"),
            ("saturday", "sat"),
            ("sunday", "sun"),
        )
    )
    for name in names
}

_ONES = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
_TEENS = [
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

_CARDINALS = {"zero": 0}
_CARDINALS.update({word: i for i, word in enumerate(_ONES + _TEENS, start=1)})
for _i, _tens in enumerate(_TENS):
    _CARDINALS[_tens] = 20 + 10 * _i
    for _j, _word in enumerate(_compounds(_tens, _ONES)):
        _CARDINALS[_word] = 20 + 10 * _i + _j // 2 + 1

_QUANTITIES = _CARDINALS | {
    "a": 1,
    "an": 1,
    "couple": 2,
    "couple of": 2,
    "a couple": 2,
    "a couple of": 2,
    "few": 3,
    "a few": 3,
}

_ORDINAL_ONES = [
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
    "eleventh",
    "twelfth",
    "thirteenth",
    "fourteenth",
    "fifteenth",
    "sixteenth",
    "seventeenth",
    "eighteenth",
    "nineteenth",
]
_ORDINALS = {word: i for i, word in enumerate(_ORDINAL_ONES, start=1)}
_ORDINALS |= {"twentieth": 20, "thirtieth": 30}
for _j, _word in enumerate(_compounds("twenty", _ORDINAL_ONES[:9])):
    _ORDINALS[_word] = 20 + _j // 2 + 1
_ORDINALS |= {"thirty first": 31, "thirty-first": 31}

_UNITS = {
    "day": _Duration(days=1),
    "week": _Duration(days=7),
    "wk": _Duration(days=7),
    "fortnight": _Duration(days=14),
    "month": _Duration(months=1),
    "year": _Duration(months=12),
    "yr": _Duration(months=12),
    "decade": _Duration(months=120),
    "business day": _Duration(business_days=1),
    "working day": _Duration(business_days=1),
    "weekday": _Duration(business_days=1),
}

_QUALIFIERS = {
    "next": "next",
    "following": "next",
    "coming": "next",
    "this coming": "next",
    "last": "last",
    "previous": "last",
    "past": "last",
    "this": "this",
}

# Fixed-date holidays only, as (month, day).
_HOLIDAYS = {
    "christmas": (12, 25),
    "christmas day": (12, 25),
    "xmas": (12, 25),
    "christmas eve": (12, 24),
    "new year": (1, 1),
    "new years": (1, 1),
    "new year's": (1, 1),
    "new year day": (1, 1),
    "new years day": (1, 1),
    "new year's day": (1, 1),
    "new years eve": (12, 31),
    "new year's eve": (12, 31),
    "valentines": (2, 14),
    "valentines day": (2, 14),
    "valentine's day": (2, 14),
    "halloween": (10, 31),
    "independence day": (7, 4),
    "fourth of july": (7, 4),
}

_KEYWORD_OFFSETS = {
    "today": 0,
    "now": 0,
    "tonight": 0,
    "this morning": 0,
    "this afternoon": 0,
    "this evening": 0,
    "tomorrow": 1,
    "tmrw": 1,
    "tmr": 1,
    "yesterday": -1,
    "last night": -1,
}

_MONTH = _alternatives(_MONTHS)
_WEEKDAY = _alternatives(_WEEKDAYS)
_ORDINAL_WORD = _alternatives(_ORDINALS)
_UNIT = _alternatives(_UNITS)
_QUALIFIER = _alternatives(_QUALIFIERS)
_HOLIDAY = _alternatives(_HOLIDAYS)
_QUANTITY = rf"\d+|{_alternatives(_QUANTITIES)}"
_DAY = rf"\d{{1,2}}(?:st|nd|rd|th)?|{_ORDINAL_WORD}"
_YEAR = r"'?(?:\d{4}|\d{2})"
_HOUR = r"(?:[01]?\d|2[0-3])"
_MINUTES = r"(?::[0-5]\d)"

_MERIDIEM_DOTS = re.compile(r"\b([ap])\.m\b\.?")
_ABBREVIATION_DOT = re.compile(r"(?<=[a-z])\.(?=\s|$)")
_ISO_TIME = re.compile(
    r"(?<=\d)t\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:z|[+-]\d{2}:?\d{2})?$"
)
_TRAILING_TIME = re.compile(
    rf"\s+(?:(?:at|@)\s+{_HOUR}{_MINUTES}{{0,2}}\s*(?:am|pm)?"
    rf"|{_HOUR}{_MINUTES}{{1,2}}\s*(?:am|pm)?"
    rf"|{_HOUR}\s*(?:am|pm)"
    r"|(?:at\s+)?(?:noon|midnight))$"
)
_TRAILING_DAY_PART = re.compile(
    r"(?<!this)(?<!last)\s+(?:in the\s+)?(?:morning|afternoon|evening|night)$"
)
_LEADING_WORDS = re.compile(r"^(?:on\s+)?(?:the\s+)?")
_DURATION_ITEM = re.compile(rf"(?:and\s+)?({_QUANTITY})\s+({_UNIT})s?\b\s*")


_YMD = re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})")
_MDY = re.compile(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})")
_MD = re.compile(r"(\d{1,2})/(\d{1,2})")
_MONTH_DAY = re.compile(rf"({_MONTH})[ -](?:the\s+)?({_DAY})(?:[ -]({_YEAR}))?")
_DAY_MONTH = re.compile(rf"({_DAY})[ -]({_MONTH})(?:[ -]({_YEAR}))?")
_YEAR_MONTH_DAY = re.compile(rf"(\d{{4}})\s+({_MONTH})\s+({_DAY})")
_MONTH_ONLY = re.compile(rf"({_MONTH})(?:\s+(?:of\s+)?(\d{{4}}))?")
_QUALIFIED_MONTH = re.compile(
    rf"({_QUALIFIER})\s+({_MONTH})(?:\s+(?:the\s+)?({_DAY}))?"
)
_QUALIFIED_HOLIDAY = re.compile(rf"(?:({_QUALIFIER})\s+)?({_HOLIDAY})(?:\s+(\d{{4}}))?")
_IN_DURATION = re.compile(r"in\s+(.+?)(?:'s?\s+time)?")
_DURATION_AGO = re.compile(r"(.+?)\s+(?:ago|earlier|back)")
_DURATION_AHEAD = re.compile(r"(.+?)\s+(?:from now|hence|later)")
_ANCHORED = re.compile(r"(.+?)\s+(before|prior to|after|from)\s+(.+)")
_WEEKDAY_AFTER_NEXT = re.compile(rf"({_WEEKDAY})\s+after\s+next")
_WEEKDAY_BEFORE_LAST = re.compile(rf"({_WEEKDAY})\s+before\s+last")
_WEEKDAY_ANCHORED = re.compile(rf"({_WEEKDAY})\s+(before|after)\s+(.+)")
_WEEKDAY_IN_WEEK = re.compile(
    rf"({_WEEKDAY})\s+(?:of\s+)?(?:the\s+)?({_QUALIFIER})\s+week"
)
_WEEK_THEN_WEEKDAY = re.compile(rf"({_QUALIFIER})\s+week\s+(?:on\s+)?({_WEEKDAY})")
_QUALIFIED_WEEKDAY = re.compile(rf"({_QUALIFIER})\s+({_WEEKDAY})")
_BARE_WEEKDAY = re.compile(rf"{_WEEKDAY}")
_UNIT_AFTER_NEXT = re.compile(rf"({_UNIT})\s+after\s+next")
_UNIT_BEFORE_LAST = re.compile(rf"({_UNIT})\s+before\s+last")
_QUALIFIED_UNIT = re.compile(rf"({_QUALIFIER})\s+({_UNIT})")
_PERIOD_EDGE = re.compile(r"(start|beginning|end)\s+of\s+(.+)")
_LAST_DAY_OF = re.compile(r"last\s+day\s+(?:of|in)\s+(.+)")
_NTH_WEEKDAY_OF = re.compile(rf"(last|{_DAY})\s+({_WEEKDAY})\s+(?:of|in)\s+(.+)")
_NTH_DAY_OF = re.compile(rf"({_DAY})\s+(?:day\s+)?(?:of|in)\s+(.+)")
_LEADING_WEEKDAY = re.compile(rf"({_WEEKDAY})\s+(.+)")
_PERIOD_YEAR = re.compile(r"\d{4}")
_PERIOD_THIS_UNIT = re.compile(r"week|month|year")
_PERIOD_QUALIFIED_UNIT = re.compile(rf"({_QUALIFIER})\s+(week|month|year)")
_PERIOD_QUALIFIED_MONTH = re.compile(rf"({_QUALIFIER})\s+({_MONTH})")


def _normalize(text: str) -> str:
    text = text.lower().replace(",", " ").replace("’", "'")
    text = _MERIDIEM_DOTS.sub(r"\1m", text)
    text = _ABBREVIATION_DOT.sub("", text)
    text = " ".join(text.split()).rstrip(".!? ")
    text = _ISO_TIME.sub("", text)
    text = _TRAILING_TIME.sub("", text)
    return _TRAILING_DAY_PART.sub("", text)


def _parse_day(text: str) -> int:
    return _ORDINALS.get(text) or int(re.sub(r"\D", "", text))


def _parse_year(text: str) -> int:
    digits = text.lstrip("'")
    year = int(digits)
    if len(digits) == 2:
        # Same pivot as strptime's %y: 69-99 are 19xx, 00-68 are 20xx.
        return year + (1900 if year >= 69 else 2000)
    return year


def _parse_duration(text: str, allow_bare_unit: bool = False) -> _Duration | None:
    """Parse "2 weeks", "one year, 3 days" etc., or return None if not a duration."""
    if allow_bare_unit and text in _UNITS:
        return _UNITS[text]
    total = _Duration()
    position = 0
    while position < len(text):
        match = _DURATION_ITEM.match(text, position)
        if match is None:
            return None
        quantity, unit = match.groups()
        amount = int(quantity) if quantity.isdigit() else _QUANTITIES[quantity]
        total += _UNITS[unit] * amount
        position = match.end()
    return total if position else None


def _shift_business_days(base: date, count: int, sign: int) -> date:
    if count == 0:
        return base
    # Start from a weekday, so that counting never lands on or counts a weekend.
    if base.weekday() >= 5:
        offset = base.weekday() - 4 if sign > 0 else base.weekday() - 7
        base -= timedelta(days=offset)
    weeks, remainder = divmod(count, 5)
    result = base + timedelta(days=sign * weeks * 7)
    for _ in range(remainder):
        result += timedelta(days=sign)
        while result.weekday() >= 5:
            result += timedelta(days=sign)
    return result


def _shift(base: date, duration: _Duration, sign: int = 1) -> date:
    """Move a date by a duration. Months are clamped, so Jan 31 + 1 month is Feb 28."""
    months = base.year * 12 + base.month - 1 + sign * duration.months
    year, month_index = divmod(months, 12)
    month = month_index + 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    result = date(year, month, day) + timedelta(days=sign * duration.days)
    return _shift_business_days(result, duration.business_days, sign)


def _upcoming_weekday(today: date, weekday: int, include_today: bool) -> date:
    delta = (weekday - today.weekday()) % 7
    if delta == 0 and not include_today:
        delta = 7
    return today + timedelta(days=delta)


def _previous_weekday(today: date, weekday: int) -> date:
    return today - timedelta(days=(today.weekday() - weekday) % 7 or 7)


def _occurrence(month: int, day: int, qualifier: str | None, today: date) -> date:
    """Resolve a month and day without a year, relative to today."""
    candidate = date(today.year, month, day)
    kind = _QUALIFIERS.get(qualifier or "this")
    if kind == "next" and candidate <= today:
        return candidate.replace(year=today.year + 1)
    if kind == "last" and candidate >= today:
        return candidate.replace(year=today.year - 1)
    return candidate


def _period(text: str, today: date) -> tuple[date, date] | None:
    """Resolve a span such as "next month" to its first and last days."""
    text = _LEADING_WORDS.sub("", text)
    if _PERIOD_YEAR.fullmatch(text):
        return date(int(text), 1, 1), date(int(text), 12, 31)

    month: int | None = None
    year = today.year
    if match := _MONTH_ONLY.fullmatch(text):
        month = _MONTHS[match[1]]
        year = int(match[2]) if match[2] else year
    elif match := _PERIOD_QUALIFIED_MONTH.fullmatch(text):
        month = _MONTHS[match[2]]
        year = _occurrence(month, 1, match[1], today).year
    if month is not None:
        return date(year, month, 1), date(
            year, month, calendar.monthrange(year, month)[1]
        )

    if _PERIOD_THIS_UNIT.fullmatch(text):
        unit, reference = text, today
    elif match := _PERIOD_QUALIFIED_UNIT.fullmatch(text):
        unit = match[2]
        sign = {"next": 1, "last": -1, "this": 0}[_QUALIFIERS[match[1]]]
        reference = _shift(today, _UNITS[unit], sign)
    else:
        return None

    if unit == "week":
        start = reference - timedelta(days=reference.weekday())
        return start, start + timedelta(days=6)
    if unit == "month":
        last_day = calendar.monthrange(reference.year, reference.month)[1]
        return reference.replace(day=1), reference.replace(day=last_day)
    return date(reference.year, 1, 1), date(reference.year, 12, 31)


def _month_first(month: int, day: int, year: int) -> date:
    """Build a numeric date, as month/day unless only day/month could be valid."""
    if month > 12 and day <= 12:
        month, day = day, month
    return date(year, month, day)


def _from_keyword(text: str, today: date) -> date | None:
    offset = _KEYWORD_OFFSETS.get(text)
    return None if offset is None else today + timedelta(days=offset)


def _from_holiday(text: str, today: date) -> date | None:
    match = _QUALIFIED_HOLIDAY.fullmatch(text)
    if match is None:
        return None
    month, day = _HOLIDAYS[match[2]]
    if match[3]:
        return date(int(match[3]), month, day)
    return _occurrence(month, day, match[1], today)


def _from_numeric(text: str, today: date) -> date | None:
    if match := _YMD.fullmatch(text):
        return date(int(match[1]), int(match[2]), int(match[3]))
    if match := _MDY.fullmatch(text):
        return _month_first(int(match[1]), int(match[2]), _parse_year(match[3]))
    if match := _MD.fullmatch(text):
        return _month_first(int(match[1]), int(match[2]), today.year)
    return None


def _from_month_name(text: str, today: date) -> date | None:
    if match := _MONTH_DAY.fullmatch(text):
        month, day, year = match[1], match[2], match[3]
    elif match := _DAY_MONTH.fullmatch(text):
        day, month, year = match[1], match[2], match[3]
    elif match := _YEAR_MONTH_DAY.fullmatch(text):
        year, month, day = match[1], match[2], match[3]
    elif match := _MONTH_ONLY.fullmatch(text):
        return date(int(match[2] or today.year), _MONTHS[match[1]], 1)
    elif match := _QUALIFIED_MONTH.fullmatch(text):
        day_number = _parse_day(match[3]) if match[3] else 1
        return _occurrence(_MONTHS[match[2]], day_number, match[1], today)
    else:
        return None
    full_year = _parse_year(year) if year else today.year
    return date(full_year, _MONTHS[month], _parse_day(day))


def _from_relative(text: str, today: date) -> date | None:
    for pattern, sign in (
        (_IN_DURATION, 1),
        (_DURATION_AHEAD, 1),
        (_DURATION_AGO, -1),
    ):
        if match := pattern.fullmatch(text):
            duration = _parse_duration(match[1])
            if duration is not None:
                return _shift(today, duration, sign)
    return None


def _from_weekday(text: str, today: date) -> date | None:
    if match := _WEEKDAY_AFTER_NEXT.fullmatch(text):
        upcoming = _upcoming_weekday(today, _WEEKDAYS[match[1]], include_today=False)
        return upcoming + timedelta(days=7)
    if match := _WEEKDAY_BEFORE_LAST.fullmatch(text):
        return _previous_weekday(today, _WEEKDAYS[match[1]]) - timedelta(days=7)
    if match := _WEEKDAY_ANCHORED.fullmatch(text):
        anchor = _resolve(match[3], today)
        weekday = _WEEKDAYS[match[1]]
        if match[2] == "after":
            return _upcoming_weekday(anchor, weekday, include_today=False)
        return _previous_weekday(anchor, weekday)
    if match := _WEEKDAY_IN_WEEK.fullmatch(text):
        weekday_name, qualifier = match[1], match[2]
    elif match := _WEEK_THEN_WEEKDAY.fullmatch(text):
        qualifier, weekday_name = match[1], match[2]
    else:
        return _from_simple_weekday(text, today)
    week = _period(f"{qualifier} week", today)
    assert week is not None
    return week[0] + timedelta(days=_WEEKDAYS[weekday_name])


def _from_simple_weekday(text: str, today: date) -> date | None:
    if _BARE_WEEKDAY.fullmatch(text):
        return _upcoming_weekday(today, _WEEKDAYS[text], include_today=True)
    match = _QUALIFIED_WEEKDAY.fullmatch(text)
    if match is None:
        return None
    weekday = _WEEKDAYS[match[2]]
    kind = _QUALIFIERS[match[1]]
    if kind == "last":
        return _previous_weekday(today, weekday)
    return _upcoming_weekday(today, weekday, include_today=kind == "this")


def _from_anchor(text: str, today: date) -> date | None:
    match = _ANCHORED.fullmatch(text)
    if match is None:
        return None
    duration = _parse_duration(match[1], allow_bare_unit=True)
    if duration is None:
        return None
    sign = -1 if match[2] in ("before", "prior to") else 1
    return _shift(_resolve(match[3], today), duration, sign)


def _from_unit(text: str, today: date) -> date | None:
    if match := _UNIT_AFTER_NEXT.fullmatch(text):
        return _shift(today, _UNITS[match[1]] * 2)
    if match := _UNIT_BEFORE_LAST.fullmatch(text):
        return _shift(today, _UNITS[match[1]] * 2, -1)
    if match := _QUALIFIED_UNIT.fullmatch(text):
        sign = {"next": 1, "last": -1, "this": 0}[_QUALIFIERS[match[1]]]
        return _shift(today, _UNITS[match[2]], sign)
    return None


def _from_period(text: str, today: date) -> date | None:
    if match := _PERIOD_EDGE.fullmatch(text):
        span = _period(match[2], today)
        if span is None:
            return None
        return span[1] if match[1] == "end" else span[0]

    if match := _LAST_DAY_OF.fullmatch(text):
        span = _period(match[1], today)
        return None if span is None else span[1]

    if match := _NTH_WEEKDAY_OF.fullmatch(text):
        span = _period(match[3], today)
        if span is None:
            return None
        weekday = _WEEKDAYS[match[2]]
        if match[1] == "last":
            return _previous_weekday(span[1] + timedelta(days=1), weekday)
        first = _upcoming_weekday(span[0], weekday, include_today=True)
        result = first + timedelta(days=7 * (_parse_day(match[1]) - 1))
        if result > span[1]:
            raise ValueError("no such weekday in that period")
        return result

    if match := _NTH_DAY_OF.fullmatch(text):
        span = _period(match[2], today)
        if span is None:
            return None
        result = span[0] + timedelta(days=_parse_day(match[1]) - 1)
        if result > span[1]:
            raise ValueError("no such day in that period")
        return result
    return None


def _from_leading_weekday(text: str, today: date) -> date | None:
    """Handle a redundant weekday, as in "Tuesday, December 2, 2025"."""
    match = _LEADING_WEEKDAY.fullmatch(text)
    if match is None:
        return None
    result = _resolve(match[2], today)
    if result.weekday() != _WEEKDAYS[match[1]]:
        raise ValueError(f"{result} is not a {match[1]}")
    return result


_HANDLERS: tuple[Callable[[str, date], date | None], ...] = (
    _from_keyword,
    _from_holiday,
    _from_numeric,
    _from_month_name,
    _from_relative,
    _from_weekday,
    _from_unit,
    _from_anchor,
    _from_period,
    _from_leading_weekday,
)


def _resolve(text: str, today: date) -> date:
    text = _LEADING_WORDS.sub("", text.strip())
    for handler in _HANDLERS:
        result = handler(text, today)
        if result is not None:
            return result
    raise ValueError(f"unrecognized expression: {text!r}")


def parse(s: str, today: date | None = None) -> date:
    """Convert a natural language date into a ``datetime.date``.

    Args:
        s: The expression, such as "5 days before December 1st, 2025" or
            "next Tuesday". Matching ignores case and extra whitespace.
        today: The reference point for relative expressions. Defaults to the
            current date.

    Returns:
        The date that the expression refers to.

    Raises:
        ValueError: If the expression is not recognized, or is not a real date.
    """
    if today is None:
        today = date.today()
    elif isinstance(today, datetime):
        today = today.date()

    try:
        return _resolve(_normalize(s), today)
    except (ValueError, OverflowError, RecursionError) as error:
        raise ValueError(f"Could not parse date: {s!r}") from error
