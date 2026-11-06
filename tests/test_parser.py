from datetime import date, datetime

import pytest

from nldate import parse

# A Wednesday.
TODAY = date(2025, 11, 5)


def check(text: str, expected: date, today: date = TODAY) -> None:
    assert parse(text, today=today) == expected


@pytest.mark.parametrize(
    "text",
    [
        "December 1st, 2025",
        "December 1, 2025",
        "december 1 2025",
        "Dec 1, 2025",
        "Dec. 1st, 2025",
        "December first, 2025",
        "December the 1st, 2025",
        "1 December 2025",
        "1st December, 2025",
        "1st of December 2025",
        "the 1st of December, 2025",
        "on the first of December 2025",
        "1-Dec-2025",
        "Dec 1 '25",
        "2025 December 1",
        "2025-12-01",
        "2025-12-1",
        "2025/12/01",
        "2025-12-01T10:30:00Z",
        "12/01/2025",
        "12/1/2025",
        "12-01-2025",
        "12.01.2025",
        "12/1/25",
        "Monday, December 1, 2025",
    ],
)
def test_absolute_dates(text: str) -> None:
    check(text, date(2025, 12, 1))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("December 1", date(2025, 12, 1)),
        ("Jan 15", date(2025, 1, 15)),
        ("15th of March", date(2025, 3, 15)),
        ("12/25", date(2025, 12, 25)),
        ("March", date(2025, 3, 1)),
        ("March 2026", date(2026, 3, 1)),
        ("next March", date(2026, 3, 1)),
        ("last March", date(2025, 3, 1)),
        ("next December 1", date(2025, 12, 1)),
        ("next March 3rd", date(2026, 3, 3)),
    ],
)
def test_dates_without_year(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1/2/2025", date(2025, 1, 2)),
        ("25/12/2025", date(2025, 12, 25)),
        ("1/2/99", date(1999, 1, 2)),
        ("1/2/30", date(2030, 1, 2)),
    ],
)
def test_numeric_date_interpretation(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("today", date(2025, 11, 5)),
        ("now", date(2025, 11, 5)),
        ("tonight", date(2025, 11, 5)),
        ("this morning", date(2025, 11, 5)),
        ("tomorrow", date(2025, 11, 6)),
        ("yesterday", date(2025, 11, 4)),
        ("last night", date(2025, 11, 4)),
        ("the day after tomorrow", date(2025, 11, 7)),
        ("day before yesterday", date(2025, 11, 3)),
    ],
)
def test_keywords(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Friday", date(2025, 11, 7)),
        ("on Friday", date(2025, 11, 7)),
        ("fri", date(2025, 11, 7)),
        ("Wednesday", date(2025, 11, 5)),
        ("this Friday", date(2025, 11, 7)),
        ("this coming Friday", date(2025, 11, 7)),
        ("next Tuesday", date(2025, 11, 11)),
        ("next Wednesday", date(2025, 11, 12)),
        ("next Friday", date(2025, 11, 7)),
        ("last Tuesday", date(2025, 11, 4)),
        ("last Wednesday", date(2025, 10, 29)),
        ("previous Monday", date(2025, 11, 3)),
        ("Tuesday next week", date(2025, 11, 11)),
        ("next week Tuesday", date(2025, 11, 11)),
        ("Friday of last week", date(2025, 10, 31)),
        ("Monday this week", date(2025, 11, 3)),
        ("Tuesday after next", date(2025, 11, 18)),
        ("Tuesday before last", date(2025, 10, 28)),
        ("the Friday before Christmas", date(2025, 12, 19)),
        ("the Monday after December 1, 2025", date(2025, 12, 8)),
    ],
)
def test_weekdays(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("in 3 days", date(2025, 11, 8)),
        ("in three days", date(2025, 11, 8)),
        ("in a day", date(2025, 11, 6)),
        ("in a week", date(2025, 11, 12)),
        ("in a fortnight", date(2025, 11, 19)),
        ("in a couple of days", date(2025, 11, 7)),
        ("in 3 days' time", date(2025, 11, 8)),
        ("in a week's time", date(2025, 11, 12)),
        ("in 1 month", date(2025, 12, 5)),
        ("twenty-one days from now", date(2025, 11, 26)),
        ("twenty one days from now", date(2025, 11, 26)),
        ("2 years from now", date(2027, 11, 5)),
        ("two weeks ago", date(2025, 10, 22)),
        ("3 months ago", date(2025, 8, 5)),
        ("a year ago", date(2024, 11, 5)),
        ("1 year, 2 months and 3 days from now", date(2027, 1, 8)),
        ("next week", date(2025, 11, 12)),
        ("last week", date(2025, 10, 29)),
        ("next month", date(2025, 12, 5)),
        ("last year", date(2024, 11, 5)),
        ("next year", date(2026, 11, 5)),
        ("this month", date(2025, 11, 5)),
        ("the week after next", date(2025, 11, 19)),
    ],
)
def test_relative_to_today(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5 days before December 1st, 2025", date(2025, 11, 26)),
        ("5 days after December 1st, 2025", date(2025, 12, 6)),
        ("2 weeks prior to 2025-12-01", date(2025, 11, 17)),
        ("a week from tomorrow", date(2025, 11, 13)),
        ("a week from today", date(2025, 11, 12)),
        ("3 days after next Tuesday", date(2025, 11, 14)),
        ("a month from next Tuesday", date(2025, 12, 11)),
        ("the day after Christmas", date(2025, 12, 26)),
        ("2 weeks before Christmas", date(2025, 12, 11)),
        ("1 week after 2 days before December 10, 2025", date(2025, 12, 15)),
    ],
)
def test_offsets_from_other_dates(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a month after January 31, 2025", date(2025, 2, 28)),
        ("a month after January 31, 2024", date(2024, 2, 29)),
        ("a month before March 31, 2025", date(2025, 2, 28)),
        ("1 year after February 29, 2024", date(2025, 2, 28)),
        ("3 days after February 28, 2024", date(2024, 3, 2)),
        ("1 day after December 31, 2025", date(2026, 1, 1)),
    ],
)
def test_calendar_edge_cases(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("end of the month", date(2025, 11, 30)),
        ("start of next month", date(2025, 12, 1)),
        ("the beginning of this week", date(2025, 11, 3)),
        ("end of this week", date(2025, 11, 9)),
        ("end of next year", date(2026, 12, 31)),
        ("end of December 2025", date(2025, 12, 31)),
        ("start of 2026", date(2026, 1, 1)),
        ("last day of February 2024", date(2024, 2, 29)),
        ("first day of next month", date(2025, 12, 1)),
        ("the first of next month", date(2025, 12, 1)),
        ("the 15th of next month", date(2025, 12, 15)),
        ("first Monday of December 2025", date(2025, 12, 1)),
        ("the last Friday of next month", date(2025, 12, 26)),
        ("third Thursday in November 2025", date(2025, 11, 20)),
        ("2nd Tuesday of next month", date(2025, 12, 9)),
    ],
)
def test_positions_within_periods(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Christmas", date(2025, 12, 25)),
        ("Christmas Eve", date(2025, 12, 24)),
        ("next Christmas", date(2025, 12, 25)),
        ("last Christmas", date(2024, 12, 25)),
        ("Christmas 2030", date(2030, 12, 25)),
        ("New Year's Eve 2026", date(2026, 12, 31)),
        ("new years day", date(2025, 1, 1)),
        ("next New Year’s Day", date(2026, 1, 1)),
        ("Halloween", date(2025, 10, 31)),
        ("Valentine's Day", date(2025, 2, 14)),
        ("the Fourth of July", date(2025, 7, 4)),
    ],
)
def test_holidays(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("in 3 business days", date(2025, 11, 10)),
        ("2 business days ago", date(2025, 11, 3)),
        ("next business day", date(2025, 11, 6)),
        ("5 working days from now", date(2025, 11, 12)),
        ("1 business day before November 3, 2025", date(2025, 10, 31)),
        ("5 business days after Saturday", date(2025, 11, 14)),
        ("1 business day after Saturday", date(2025, 11, 10)),
        ("1 business day before Saturday", date(2025, 11, 7)),
    ],
)
def test_business_days(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("tomorrow at 5pm", date(2025, 11, 6)),
        ("tomorrow at 17:00", date(2025, 11, 6)),
        ("tomorrow morning", date(2025, 11, 6)),
        ("tomorrow morning at 9", date(2025, 11, 6)),
        ("next Tuesday at 10:30 a.m.", date(2025, 11, 11)),
        ("next Tuesday night", date(2025, 11, 11)),
        ("Dec 1 2025 at noon", date(2025, 12, 1)),
        ("December 1 5pm", date(2025, 12, 1)),
        ("2025-12-01 10:30:00", date(2025, 12, 1)),
    ],
)
def test_times_of_day_are_ignored(text: str, expected: date) -> None:
    check(text, expected)


@pytest.mark.parametrize(
    "text",
    [
        "NEXT TUESDAY",
        "  next   tuesday  ",
        "Next Tuesday.",
        "next tues",
        "Next\tTuesday",
    ],
)
def test_formatting_is_flexible(text: str) -> None:
    check(text, date(2025, 11, 11))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        ".",
        "hello",
        "not a date",
        "next",
        "next blursday",
        "in days",
        "banana days ago",
        "5 days before",
        "before December 1",
        "5 bananas before December 1",
        "5 days before banana",
        "2025",
        "5",
        "at 5pm",
        "February 30, 2025",
        "February 29, 2025",
        "December 32",
        "13/13/2025",
        "2025-13-01",
        "0/1/2025",
        "Monday, December 2, 2025",
        "fifth Monday of February 2025",
        "31st of next month of next month",
        "in 99999999 years",
        "in 99999999999999999999 days",
        "in 99999999999999999999 business days",
        "a day after " * 5000 + "today",
    ],
)
def test_unrecognized_input_raises_value_error(text: str) -> None:
    with pytest.raises(ValueError):
        parse(text, today=TODAY)


def test_today_defaults_to_current_date() -> None:
    before = date.today()
    result = parse("today")
    assert before <= result <= date.today()


def test_datetime_reference_still_returns_a_plain_date() -> None:
    result = parse("tomorrow", today=datetime(2025, 11, 5, 23, 59))
    assert type(result) is date
    assert result == date(2025, 11, 6)


def test_relative_expressions_cross_year_boundaries() -> None:
    check("next week", date(2026, 1, 3), today=date(2025, 12, 27))
    check("next Monday", date(2026, 1, 5), today=date(2025, 12, 31))
    check("next month", date(2026, 1, 15), today=date(2025, 12, 15))
