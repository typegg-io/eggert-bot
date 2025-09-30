from datetime import datetime, timezone, timedelta

from dateutil import parser

from utils.errors import InvalidDate


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
