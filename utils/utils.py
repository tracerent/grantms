from datetime import datetime, date
from calendar import monthrange
import re


class Utils:

    @staticmethod
    def current_year_quarter():
        """Return (year, quarter) for current date. Quarter is 1-4."""
        now = datetime.now()
        return (now.year, (now.month - 1) // 3 + 1)

    @staticmethod
    def parse_quarter_string(quarter_str):
        """Parse '2026 Q2' to (year, quarter). Quarter 1-4. Returns (None, None) if invalid."""
        if not quarter_str or not isinstance(quarter_str, str):
            return (None, None)
        s = quarter_str.strip()
        m = re.match(r"(\d{4})\s*[Qq]\s*([1-4])$", s)
        if m:
            return (int(m.group(1)), int(m.group(2)))
        return (None, None)

    @staticmethod
    def quarter_start_date(year, quarter):
        """Return the first day of the given quarter (Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct)."""
        if not year or not quarter or quarter not in (1, 2, 3, 4):
            return None
        month = (quarter - 1) * 3 + 1
        return date(year, month, 1)

    @staticmethod
    def date_plus_months(d, months):
        """Return a date that is `months` months after date `d`. Uses same day of month when valid."""
        if not d or not months:
            return d
        m, y = d.month + months, d.year
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        last = monthrange(y, m)[1]
        day = min(d.day, last)
        return date(y, m, day)

    @staticmethod
    def is_quarter_in_next_6_months(year, quarter):
        """True if the start of the given (year, quarter) falls within the next 6 months from today."""
        start = Utils.quarter_start_date(year, quarter)
        if not start:
            return False
        today = date.today()
        cutoff = Utils.date_plus_months(today, 6)
        return start <= cutoff

    @staticmethod
    def get_user_display_name(user):
        """Return display name: first_name + last_name, or email if both empty. No DB access."""
        if not user:
            return ""
        fn = (user.get("first_name") or "").strip()
        ln = (user.get("last_name") or "").strip()
        if fn or ln:
            return " ".join([fn, ln]).strip()
        return user.get("email") or ""

