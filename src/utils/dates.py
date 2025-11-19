from datetime import datetime, timezone, timedelta

from dateutil import parser
from dateutil.relativedelta import relativedelta

from utils.errors import InvalidDate
from utils.strings import ordinal_number


def now():
    return datetime.now(timezone.utc)


def get_timestamp_list(date_list):
    return [datetime.strptime(date[:-1], "%Y-%m-%d %H:%M:%S.%f").timestamp() for date in date_list]


def parse_date(date_string):
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
    """Returns a date formatted as 'October 1st, 2025'."""
    month = date.strftime("%B")
    year = date.strftime("%Y")
    day = int(date.strftime("%d"))

    return f"{month} {ordinal_number(day)}, {year}"


def count_unique_dates(start, end):
    """Returns the number of unique days within a start and end date range."""
    start_date = parse_date(start)
    end_date = parse_date(end)

    unique_dates = set()

    while start_date <= end_date:
        unique_dates.add(start_date.strftime("%m-%d-%Y"))
        start_date += relativedelta(days=1)

    return len(unique_dates)


def floor_day(date):
    return date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def floor_week(date):
    return ((date - relativedelta(days=date.weekday()))
            .replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc))


def floor_month(date):
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def floor_year(date):
    return date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def get_start_end_dates(date: datetime, period: str):
    """Returns start and end dates (UTC) given a date and period (day, week, month, or year)."""
    periods = {
        "day": (floor_day, relativedelta(days=1)),
        "week": (floor_week, relativedelta(weeks=1)),
        "month": (floor_month, relativedelta(months=1)),
        "year": (floor_year, relativedelta(years=1))
    }

    if period in periods:
        floor_function, relative_delta = periods[period]
        start = floor_function(date)
        end = start + relative_delta

        return start, end

    return None, None
