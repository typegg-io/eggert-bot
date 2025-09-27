from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc)


def get_timestamp_list(date_list):
    return [datetime.strptime(date[:-1], "%Y-%m-%d %H:%M:%S.%f").timestamp() for date in date_list]
