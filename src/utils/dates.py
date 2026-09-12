"""Date parsing, flooring, ranges and display formatting."""

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil import parser
from dateutil.relativedelta import relativedelta

from utils.errors import InvalidDate
from utils.strings import ordinal_number

# Constants

API_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%fZ"

_DATE_RE = re.compile(
    r"^\d{4}([-/\.]\d{1,2}([-/\.]\d{1,2})?)?$"
    r"|^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$"
    r"|^\d{1,2}[/-]\d{4}$",
    re.IGNORECASE
)
_DATE_KEYWORDS = {"now", "today", "yesterday", "yd"}


# Basic Date Utilities

def now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


def epoch() -> datetime:
    """Return the Unix epoch (January 1, 1970) as a UTC datetime."""
    return datetime(1970, 1, 1, tzinfo=UTC)


def current_utc_offset(tz: ZoneInfo) -> timedelta:
    """Return how far a timezone stands from UTC right now."""
    return now().astimezone(tz).utcoffset()


def format_utc_offset(offset: timedelta) -> str:
    """Return an offset from UTC for display, like UTC-5 or UTC+5:30."""
    total_minutes = round(offset.total_seconds() / 60)
    if total_minutes == 0:
        return "UTC"

    hours, minutes = divmod(abs(total_minutes), 60)
    sign = "+" if total_minutes > 0 else "-"

    return f"UTC{sign}{hours}" + (f":{minutes:02d}" if minutes else "")


# String & Date Conversion

def normalize_datetime(date_string: str) -> str:
    """Normalize an RFC-3339 'T' separator to the space-separated form the bot stores and parses."""
    if date_string and len(date_string) > 10 and date_string[10] == "T":
        return date_string[:10] + " " + date_string[11:]
    return date_string


def string_to_date(date_string: str, format: str = API_DATE_FORMAT) -> datetime:
    """Convert a date string to a datetime object using the specified format."""
    return datetime.strptime(normalize_datetime(date_string), format)


def date_to_string(date_object: datetime, format: str = API_DATE_FORMAT) -> str:
    """Convert a datetime object to a string using the specified format."""
    return datetime.strftime(date_object, format)


def to_timestamp_string(date: datetime | str | None) -> str | None:
    """Return a date as the string form the race tables store, passing strings and None through."""
    # Binding a datetime straight to SQLite uses an adapter deprecated in Python 3.12.
    return date_to_string(date) if isinstance(date, datetime) else date


def parse_date(date_string: str | None) -> datetime:
    """Parse a flexible date string (e.g., 'now', 'yesterday', ISO format) into a UTC datetime."""
    _now = now()
    if not date_string or date_string in ["now", "present", "today"]:
        date = _now
    elif date_string in ["yesterday", "yd"]:
        date = _now - timedelta(days=1)
    else:
        try:
            date = parser.parse(date_string).replace(tzinfo=UTC)
        except ValueError:
            raise InvalidDate

    return date


def is_date_like(arg) -> bool:
    """Return whether a date string is date-like, for parameter parsing."""
    return arg.lower() in _DATE_KEYWORDS or bool(_DATE_RE.match(arg))


def format_date(date) -> str:
    """Format a datetime as a readable string (e.g., 'October 1st, 2025')."""
    month = date.strftime("%B")
    year = date.strftime("%Y")
    day = int(date.strftime("%d"))

    return f"{month} {ordinal_number(day)}, {year}"


def get_timestamp_list(date_list) -> list[float]:
    """Convert a list of date strings to Unix timestamps."""
    return [
        datetime.strptime(normalize_datetime(date).rstrip("Z"), "%Y-%m-%d %H:%M:%S.%f").timestamp()
        for date in date_list
    ]


# Date Flooring Functions

def floor_day(date) -> datetime:
    """Round a datetime down to the start of the day."""
    return date.replace(hour=0, minute=0, second=0, microsecond=0)


def floor_week(date) -> datetime:
    """Round a datetime down to the start of the week (Monday)."""
    return (date - relativedelta(days=date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def floor_month(date) -> datetime:
    """Round a datetime down to the start of the month."""
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def floor_year(date) -> datetime:
    """Round a datetime down to the start of the year."""
    return date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


# Date Range Utilities

def get_start_end_dates(date: datetime, period: str, tz: ZoneInfo) -> tuple[datetime | None, datetime | None]:
    """Calculate start and end dates for a given period (day, week, month, or year)."""
    periods = {
        "day": (floor_day, relativedelta(days=1)),
        "week": (floor_week, relativedelta(weeks=1)),
        "month": (floor_month, relativedelta(months=1)),
        "year": (floor_year, relativedelta(years=1)),
    }

    if period in periods:
        floor_function, relative_delta = periods[period]
        start_local = floor_function(date.astimezone(tz))
        # Adding the period in local time keeps a DST day 23 or 25 hours long.
        end_local = start_local + relative_delta

        return start_local.astimezone(UTC), end_local.astimezone(UTC)

    return None, None


def local_midnight(date: datetime, tz: ZoneInfo) -> datetime:
    """Return the calendar date a user typed as midnight in their own timezone."""
    # parse_date reads a typed date as UTC midnight, which lands on the day before west of UTC.
    return datetime(date.year, date.month, date.day, tzinfo=tz)


def resolve_date_range(flags, tz: ZoneInfo, stored=(None, None)) -> tuple[datetime, datetime] | None:
    """Return the half-open UTC range a command should filter by, or None for all time."""
    if flags.period == "alltime":
        return None

    if flags.period:
        anchor = local_midnight(flags.date, tz) if flags.dates else flags.date
        return get_start_end_dates(anchor, flags.period, tz)

    if len(flags.dates) > 1:
        start, end = (local_midnight(date, tz) for date in flags.dates)
        # Adding the day in local time rather than UTC keeps the end inclusive across a DST change.
        return start.astimezone(UTC), (end + relativedelta(days=1)).astimezone(UTC)

    start, end = stored
    if start is None and end is None:
        return None

    return (
        datetime.fromtimestamp(start, UTC) if start else epoch(),
        datetime.fromtimestamp(end, UTC) if end else now(),
    )


def count_unique_dates(start, end) -> int:
    """Count the number of unique days between two date strings (inclusive)."""
    start_date = parse_date(start)
    end_date = parse_date(end)

    unique_dates = set()

    while start_date <= end_date:
        unique_dates.add(start_date.strftime("%m-%d-%Y"))
        start_date += relativedelta(days=1)

    return len(unique_dates)


def discord_date(date_string: str, style: str | None = "R") -> str:
    """Convert a date string or timestamp to Discord's date format tag."""
    try:
        timestamp = int(date_string)
    except ValueError:
        timestamp = int(parser.parse(date_string).timestamp())
    return f"<t:{timestamp}:{style}>"
