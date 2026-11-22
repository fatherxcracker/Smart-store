"""Read-only queries against Phase 4's database and local-date/UTC boundaries."""
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import current_app, request
import db


def rows(conn, sql, args=()):
    return [dict(row) for row in conn.execute(sql, args).fetchall()]


@contextmanager
def snapshot():
    conn = db.get_connection()
    try:
        conn.execute("PRAGMA query_only = ON")
        conn.execute("BEGIN")
        yield conn
    finally:
        conn.close()


class Period:
    def __init__(self):
        self.zone = ZoneInfo(current_app.config["REPORT_TIMEZONE"])
        today = datetime.now(self.zone).date()
        self.start = self.parse(request.args.get("start", (today - timedelta(days=29)).isoformat()))
        self.end = self.parse(request.args.get("end", today.isoformat()))
        if self.end < self.start:
            raise ValueError("The end date must be on or after the start date.")
        if (self.end - self.start).days > 365:
            raise ValueError("Choose a period of at most 366 days.")
        try:
            following = self.end + timedelta(days=1)
        except OverflowError:
            raise ValueError("Choose an earlier end date.")
        self.bounds = tuple(datetime.combine(day, time.min, self.zone).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                            for day in (self.start, following))
        self.days = [(self.start + timedelta(days=i)).isoformat() for i in range((self.end - self.start).days + 1)]

    @staticmethod
    def parse(value):
        try:
            if len(value) != 10:
                raise ValueError()
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            raise ValueError("Enter a valid date in YYYY-MM-DD format.")

    def local_day(self, value):
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).astimezone(self.zone).date().isoformat()


def currency(value):
    return round(float(value or 0), 2)
