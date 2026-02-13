from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from dateutil import parser
from dateutil.relativedelta import relativedelta

from utils.errors import InvalidDate
from utils.strings import ordinal_number

# Constants

API_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%fZ"


# Basic Date Utilities

def now():
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def epoch():
    """Return the Unix epoch (January 1, 1970) as a UTC datetime."""
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


# String & Date Conversion

def string_to_date(date_string: str, format: str = API_DATE_FORMAT):
    """Convert a date string to a datetime object using the specified format."""
    return datetime.strptime(date_string, format)


def date_to_string(date_object: datetime, format: str = API_DATE_FORMAT):
    """Convert a datetime object to a string using the specified format."""
    return datetime.strftime(date_object, format)


def parse_date(date_string):
    """Parse a flexible date string (e.g., 'now', 'yesterday', ISO format) into a UTC datetime."""
    _now = now()
    if not date_string or date_string in ["now", "present", "today"]:
        date = _now
    elif date_string in ["yesterday", "yd"]:
        date = _now - timedelta(days=1)
    else:
        try:
            date = parser.parse(date_string).replace(tzinfo=timezone.utc)
        except ValueError:
            raise InvalidDate

    return date


def format_date(date):
    """Format a datetime as a readable string (e.g., 'October 1st, 2025')."""
    month = date.strftime("%B")
    year = date.strftime("%Y")
    day = int(date.strftime("%d"))

    return f"{month} {ordinal_number(day)}, {year}"


def format_timestamp(date: datetime):
    """Format a datetime as an ISO-like timestamp string (YYYY-MM-DD HH:MM:SSZ)."""
    return date.strftime("%Y-%m-%d %H:%M:%SZ")


def get_timestamp_list(date_list):
    """Convert a list of date strings to Unix timestamps."""
    return [datetime.strptime(date.rstrip("Z"), "%Y-%m-%d %H:%M:%S.%f").timestamp() for date in date_list]


# Date Flooring Functions

def floor_day(date):
    """Round a datetime down to the start of the day."""
    return date.replace(hour=0, minute=0, second=0, microsecond=0)


def floor_week(date):
    """Round a datetime down to the start of the week (Monday)."""
    return (date - relativedelta(days=date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def floor_month(date):
    """Round a datetime down to the start of the month."""
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def floor_year(date):
    """Round a datetime down to the start of the year."""
    return date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


# Date Range Utilities

def get_start_end_dates(date: datetime, period: str, tz: ZoneInfo):
    """Calculate start and end dates for a given period (day, week, month, or year)."""
    periods = {
        "day": (floor_day, relativedelta(days=1)),
        "week": (floor_week, relativedelta(weeks=1)),
        "month": (floor_month, relativedelta(months=1)),
        "year": (floor_year, relativedelta(years=1)),
    }

    if period in periods:
        floor_function, relative_delta = periods[period]
        local_date = date.astimezone(tz)
        start_local = floor_function(local_date)
        start = start_local.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        end = start + relative_delta

        return start, end

    return None, None


def count_unique_dates(start, end):
    """Count the number of unique days between two date strings (inclusive)."""
    start_date = parse_date(start)
    end_date = parse_date(end)

    unique_dates = set()

    while start_date <= end_date:
        unique_dates.add(start_date.strftime("%m-%d-%Y"))
        start_date += relativedelta(days=1)

    return len(unique_dates)
