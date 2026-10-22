"""Shared helpers for the Bluemingo chemicals data generator. Everything is deterministic (seeded).

All dates are RELATIVE to the as-of day, which defaults to TODAY (override: --asof YYYY-MM-DD or env CHM_ASOF), so
re-running the generator before a demo makes the whole dataset current without changing any id or any story.
"""
import os
import random
import sys
from datetime import datetime, timedelta

from .config import SEED, HISTORY_DAYS, FORWARD_DAYS, SOP_MONTHS, ASOF_HOUR, ASOF_MIN


def _asof():
    v = None
    for i, a in enumerate(sys.argv):
        if a == "--asof" and i + 1 < len(sys.argv):
            v = sys.argv[i + 1]
        elif a.startswith("--asof="):
            v = a.split("=", 1)[1]
    v = v or os.environ.get("CHM_ASOF")
    d = datetime.strptime(v, "%Y-%m-%d") if v else datetime.now()
    return d.replace(hour=ASOF_HOUR, minute=ASOF_MIN, second=0, microsecond=0)


R = random.Random(SEED)
ASOF = _asof()
DAY0 = ASOF.replace(hour=0, minute=0)
BASE = DAY0 - timedelta(days=HISTORY_DAYS)              # history starts here (minute 0 of the engine)
END = DAY0 + timedelta(days=FORWARD_DAYS)               # the detailed plan ends here
ASOF_MINUTE = int((ASOF - BASE).total_seconds() // 60)
END_MINUTE = int((END - BASE).total_seconds() // 60)
SOP_END = DAY0 + timedelta(days=31 * SOP_MONTHS)


def at(days, hour=0, minute=0):
    """datetime at an offset in days from the as-of day (0 = the as-of day) with a time of day"""
    return DAY0 + timedelta(days=days, hours=hour, minutes=minute)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%S") if d else None


def dstr(d):
    return d.strftime("%Y-%m-%d")


def minute_of(d):
    return int((d - BASE).total_seconds() // 60)


def month_key(d):
    return "%04d-%02d" % (d.year, d.month)


def months_ahead(n):
    """the first day of the month n months after the as-of month (n = 0 is the as-of month)"""
    y, m = DAY0.year, DAY0.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return datetime(y, m, 1)


def pick(seq):
    return R.choice(seq)


def wpick(pairs):
    """weighted pick from [(item, weight), ...] or {item: weight}"""
    items = list(pairs.items()) if isinstance(pairs, dict) else list(pairs)
    tot = sum(w for _, w in items)
    x = R.random() * tot
    for it, w in items:
        x -= w
        if x <= 0:
            return it
    return items[-1][0]


def between(a, b):
    return a + (b - a) * R.random()


def rint(a, b):
    return R.randint(a, b)


def shift_of(d):
    hr = d.hour
    return "A" if 6 <= hr < 14 else "B" if 14 <= hr < 22 else "C"


def rnd(x, d=1):
    return round(x + 0.0, d)
