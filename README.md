# nldate

Parse natural language dates into `datetime.date` objects. No runtime dependencies.

```python
from datetime import date
from nldate import parse

parse("5 days before December 1st, 2025")  # date(2025, 11, 26)
parse("next Tuesday", today=date(2025, 11, 5))  # date(2025, 11, 11)
parse("not a date")  # raises ValueError
```

`today` is the reference point for relative expressions, and defaults to the
current date. Anything unrecognized, including the empty string or an impossible
date like "February 30, 2025", raises `ValueError`.

## Supported input

Matching ignores case and extra whitespace.

| Kind | Examples |
| --- | --- |
| Month names | `December 1st, 2025`, `Dec 1 2025`, `1 December 2025`, `the first of December`, `March 2026` |
| Numeric | `2025-12-01`, `2025-12-01T10:30:00Z`, `12/01/2025`, `12/1/25`, `12.01.2025`, `12/25` |
| Keywords | `today`, `tomorrow`, `yesterday`, `tonight`, `last night`, `the day after tomorrow` |
| Weekdays | `Friday`, `this Friday`, `next Tuesday`, `last Tuesday`, `Tuesday next week`, `Tuesday after next` |
| Relative | `in 3 days`, `in a week`, `two weeks ago`, `2 years from now`, `1 year, 2 months and 3 days from now` |
| Units | `next week`, `last month`, `next year`, `the week after next` |
| Offsets | `5 days before December 1st, 2025`, `a week from tomorrow`, `3 days after next Tuesday` |
| Periods | `end of the month`, `start of next year`, `last day of February 2024`, `the 15th of next month` |
| Nth weekday | `first Monday of December 2025`, `the last Friday of next month` |
| Holidays | `Christmas`, `next Christmas`, `New Year's Eve 2026`, `Halloween`, `the Friday before Christmas` |
| Business days | `in 3 business days`, `next business day`, `5 working days after December 1` |

Times of day are accepted and ignored: `tomorrow at 5pm`, `next Tuesday morning`.

## How ambiguous input is interpreted

| Input | Interpretation |
| --- | --- |
| `next Tuesday` | The first Tuesday strictly after today, which may be this calendar week |
| `last Tuesday` | The most recent Tuesday strictly before today |
| `Tuesday`, `this Tuesday` | The first Tuesday on or after today |
| `Tuesday next week` | The Tuesday of the following Monday-to-Sunday calendar week |
| `December 1`, `Christmas` | That date in today's year, even if it has passed |
| `next December 1`, `next Christmas` | The first such date strictly after today |
| `March`, `March 2026` | The first of that month |
| `01/02/2025` | Month first (January 2), unless only day-first is valid (`25/12/2025`) |
| `1/2/25` | Two-digit years: 00-68 are 20xx, and 69-99 are 19xx |
| `a month after January 31, 2025` | Clamped to the end of the month (February 28) |
| `Monday, December 2, 2025` | `ValueError`, because that date is a Tuesday |

Business days skip weekends but not holidays.

## Not supported yet

Hours and minutes as offsets (`in 48 hours`), weekends (`next weekend`), holidays
that move from year to year (`Thanksgiving`, `Easter`), and a bare day of the month
(`the 15th`).

## Development

```sh
uv run pytest
uv run mypy src/
uv run ruff check
uv run ruff format --check
```
