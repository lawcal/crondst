# CronDst v1.0.3

# MIT License
#
# Copyright (c) 2023-2024 Calvin Law
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from __future__ import annotations
# from typing import Self # python >= 3.11

from collections.abc import Generator
import dataclasses as dc
import datetime as dt

__all__ = ['CronDst', 'CronDstError']

class CronDstError(Exception):
    pass

# internal structure
# ********************

MAX_EXPRESSION_LENGTH = 1000
MAX_YEARS_BETWEEN_MATCHES = 50

@dc.dataclass
class _CronField:
    name: str
    bound: tuple[int, int]
    text_map: dict[str, int] | None = None

FIELD_PROPS = [
    _CronField('minute', (0, 59)),
    _CronField('hour', (0, 23)),
    _CronField('day-of-month', (1, 31)),
    _CronField('month', (1, 12), {
        'jan': 1,
        'feb': 2,
        'mar': 3,
        'apr': 4,
        'may': 5,
        'jun': 6,
        'jul': 7,
        'aug': 8,
        'sep': 9,
        'oct': 10,
        'nov': 11,
        'dec': 12,
    }),
    _CronField('day-of-week', (0, 7), {
        'sun': 0,
        'mon': 1,
        'tue': 2,
        'wed': 3,
        'thu': 4,
        'fri': 5,
        'sat': 6,
    }),
]

def _number_from_item(item: str, text_map: dict[str, int] | None) -> int | None:
    number = None
    try:
        number = int(item)
    except ValueError:
        if text_map:
            number = text_map.get(item)
    return number

@dc.dataclass
class _CronEntry:
    minutes: list[int] = dc.field(default_factory=list)
    hours: list[int] = dc.field(default_factory=list)
    days: list[int] = dc.field(default_factory=list)
    months: list[int] = dc.field(default_factory=list)
    days_of_week: list[int] = dc.field(default_factory=list)
    minute_star: bool = False
    hour_star: bool = False
    day_star: bool = False
    day_of_week_star: bool = False

    @classmethod
    def from_expression(cls, expression: str) -> _CronEntry: # -> Self
        if len(expression) > MAX_EXPRESSION_LENGTH:
            raise CronDstError(f"Bad expression - length exceeds {MAX_EXPRESSION_LENGTH} characters")
        structure: list[set] = [set() for i in range(5)]
        minute_star = False
        hour_star = False
        day_star = False
        day_of_week_star = False
        fields = expression.strip().split()
        if len(fields) != 5:
            raise CronDstError('Bad expression - expect five (5) fields separated by whitespace')
        for idx, field in enumerate(fields):
            if field.startswith('*'):
                minute_star = minute_star or idx == 0
                hour_star = hour_star or idx == 1
                day_star = day_star or idx == 2
                day_of_week_star = day_of_week_star or idx == 4
            name = FIELD_PROPS[idx].name
            bound = FIELD_PROPS[idx].bound
            text_map = FIELD_PROPS[idx].text_map
            for token in field.split(','):
                # parse slash (ex. /)
                parts = token.split('/', maxsplit=1)
                is_step_specified = len(parts) > 1
                list_item = parts[0]
                try:
                    step = int(parts[1]) if is_step_specified else 1
                except ValueError:
                    raise CronDstError(f"Bad {name}") from None
                if step <= 0:
                    raise CronDstError(f"Bad {name}")

                # asterisk (ex. *)
                if list_item == '*':
                    structure[idx].update(range(bound[0], bound[1] + 1, step))
                    continue

                range_expression = list_item.split('-')
                if len(range_expression) == 1:
                    # number (ex. 3)
                    num = _number_from_item(list_item, text_map)
                    if num is None:
                        raise CronDstError(f"Bad {name}")
                    if num < bound[0] or num > bound[1]:
                        raise CronDstError(f"Bad {name}")
                    if is_step_specified:
                        # treat as range from number to max bounds
                        structure[idx].update(range(num, bound[1] + 1, step))
                    else:
                        structure[idx].add(num)
                    continue
                elif len(range_expression) != 2:
                    raise CronDstError(f"Bad {name}")
                # range expression (ex. 1-6)
                lower = _number_from_item(range_expression[0], text_map)
                upper = _number_from_item(range_expression[1], text_map)
                if lower is None or upper is None:
                    raise CronDstError(f"Bad {name}")
                if lower > upper:
                    raise CronDstError(f"Bad {name}")
                if lower < bound[0] or upper > bound[1]:
                    raise CronDstError(f"Bad {name}")
                structure[idx].update(range(lower, upper + 1, step))

        for s in structure:
            # general catch all, should never happen
            if not s:
                raise CronDstError('Bad expression')

        entry = cls(
            minutes=sorted(structure[0]),
            hours=sorted(structure[1]),
            days=sorted(structure[2]),
            months=sorted(structure[3]),
            days_of_week=sorted(structure[4]),
            minute_star=minute_star,
            hour_star=hour_star,
            day_star=day_star,
            day_of_week_star=day_of_week_star,
        )

        # check entry results in a schedule with triggers
        if not entry.has_triggers():
            raise CronDstError('Bad expression - results in no triggers')

        return entry

    def has_triggers(self) -> bool:
        max_day_of_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        days_of_month = self.days # already sorted in ascending order
        months = self.months
        if self.day_of_week_star:
            # when day of week is wildcard, only month and day of month specify days* so check impossible combinations
            # *except when day of week is wilcard with step, but then the critiera is even narrower because of ANDing
            if days_of_month[-1] > max(max_day_of_month[month - 1] for month in months):
                return False
        return True

    def is_wildcard(self) -> bool:
        return self.minute_star or self.hour_star

    def merge_days_and_days_of_week(self, datetime: dt.datetime, use_and_operator: bool | None = None) -> list[int]:
        if use_and_operator is None:
            use_and_operator = self.day_star or self.day_of_week_star
        days_set = set(self.days)
        # alias Sun=7 to Sun=0
        days_of_week_set = set([0, *self.days_of_week] if 7 in self.days_of_week else self.days_of_week)
        weekday = datetime.replace(day=1).weekday() # weekday() returns Mon=0 so var is pre-incremented in loop
        result = []
        for day in range(1, _days_in_month(datetime) + 1):
            weekday = (weekday + 1) % 7
            if use_and_operator and (day in days_set and weekday in days_of_week_set):
                result.append(day)
            if not use_and_operator and (day in days_set or weekday in days_of_week_set):
                result.append(day)
        return result

# helpers
# --------------------

def _days_in_month(datetime: dt.datetime) -> int:
    return (datetime.replace(month=(datetime.month % 12) + 1, day=1) - dt.timedelta(days=1)).day

def _index_of_nearest_number(numbers: list[int], target: int) -> int:
    # binary searches insertion point of target given a list of ascending numbers
    # returns i (0 <= i <= len(numbers)) such that numbers[i-1] < target <= numbers[i]
    low = -1
    high = len(numbers)
    while low + 1 < high:
        mid = low + (high - low) // 2
        if target <= numbers[mid]:
            high = mid
        else:
            low = mid
    return high

def _next_wallclock_datetime(
    start: dt.datetime,
    entry: _CronEntry,
    max_years_between_matches: int
) -> dt.datetime | None:
    # finds next wallclock time without considering DST, as in fold truncated to 0 and may return in missing time
    minutes = entry.minutes
    hours = entry.hours
    months = entry.months

    next_minute = start.minute + 1
    next_hour = start.hour
    next_day = start.day
    next_month = start.month
    next_year = start.year

    is_placeholder_day = False

    # minutes
    idx = _index_of_nearest_number(minutes, next_minute)
    if idx < len(minutes):
        next_minute = minutes[idx]
    else:
        next_minute = minutes[0]
        next_hour += 1

    # hours
    idx = _index_of_nearest_number(hours, next_hour)
    if idx < len(hours):
        next_hour = hours[idx]
        if next_hour != start.hour:
            next_minute = minutes[0]
    else:
        next_minute = minutes[0]
        next_hour = hours[0]
        next_day += 1

    # days, days of week
    # days_and_days_of_week may be calculated from wrong month or return an empty list,
    # but this is fine since later month section handles it
    days_and_days_of_week = entry.merge_days_and_days_of_week(start)
    idx = _index_of_nearest_number(days_and_days_of_week, next_day)
    if idx < len(days_and_days_of_week):
        next_day = days_and_days_of_week[idx]
        if next_day != start.day:
            next_minute = minutes[0]
            next_hour = hours[0]
    else:
        next_minute = minutes[0]
        next_hour = hours[0]
        next_day = 1 # placeholder
        next_month += 1
        is_placeholder_day = True

    # months
    next_timestamp = None
    for _ in range(max(max_years_between_matches, 0) * 12):
        idx = _index_of_nearest_number(months, next_month)
        if idx < len(months):
            next_month = months[idx]
            if next_month != start.month:
                next_minute = minutes[0]
                next_hour = hours[0]
                next_day = 1 # placeholder
                is_placeholder_day = True
        else:
            next_minute = minutes[0]
            next_hour = hours[0]
            next_day = 1 # placeholder
            next_month = months[0]
            next_year += 1
            is_placeholder_day = True

        timestamp = dt.datetime(next_year, next_month, next_day, next_hour, next_minute, tzinfo=start.tzinfo)
        if is_placeholder_day:
            days_and_days_of_week = entry.merge_days_and_days_of_week(timestamp)
            if days_and_days_of_week:
                # found month and year
                next_timestamp = timestamp.replace(day=days_and_days_of_week[0], month=next_month, year=next_year)
                break
            # no days to match in current month, try next
            next_month += 1
        else:
            # already found month and year
            next_timestamp = timestamp
            break
    return next_timestamp

def _delta_seconds_between_fold(datetime: dt.datetime) -> int:
    return round(
        datetime.replace(microsecond=0, fold=0).timestamp() - datetime.replace(microsecond=0, fold=1).timestamp()
    )

# public api
# ********************

class CronDst:
    def __init__(self, expression: str):
        self.entry = _CronEntry.from_expression(expression)

    def iter(
        self,
        start: dt.datetime | None = None,
        max_years_between_matches: int = MAX_YEARS_BETWEEN_MATCHES
    ) -> Generator[dt.datetime, None, None]:
        """Iterate over a sequence of job triggers.

        Args:
            start (dt.datetime | None, optional): Iteration starting point. Matches exclude the starting point itself.
              Defaults to the current datetime in UTC.
            max_years_between_matches (int, optional): Limit the number of years to search after each match.
              Defaults to 50.

        Yields:
            datetime: The next job trigger of the sequence.
        """
        # wildcard jobs are handled differently than fixed-time jobs during DST clock change
        is_wildcard_job = self.entry.is_wildcard()

        start = start if start else dt.datetime.now(dt.timezone.utc)
        # normalize input to convert missing time to realizable time (can still be in ambiguous time with fold=0/1)
        start = dt.datetime.fromtimestamp(start.timestamp(), tz=start.tzinfo).replace(second=0, microsecond=0)
        monotonic_datetime = start
        goto_datetime: dt.datetime | None = None

        while True:
            # handle starting or landing in ambiguous time
            delta_seconds = _delta_seconds_between_fold(start)
            if delta_seconds < 0:
                if not is_wildcard_job and start.fold > 0:
                    # fast forward to next hour because jobs would have triggered during fold=0
                    # shifting to next closest hour works because all countries' ambiguous times end on :00
                    # https://en.wikipedia.org/wiki/Daylight_saving_time_by_country
                    # -1us to include start point itself
                    start = start.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1, microseconds=-1)
                if is_wildcard_job and start.fold <= 0 and goto_datetime is None:
                    # schedule wallclock jump back to start of ambiguous time but this time with fold=1
                    goto_datetime = (
                        start.replace(minute=0, second=0, microsecond=0) +
                        dt.timedelta(hours=1, seconds=delta_seconds)
                    ).replace(fold=1)

            # increment wallclock datetime
            result = _next_wallclock_datetime(start, self.entry, max_years_between_matches)
            if result is None:
                # no matches
                return
            if result.timestamp() <= monotonic_datetime.timestamp():
                # happens when:
                # - start has fold=1 and _next_wallclock_datetime() truncated it
                # - looped back to iterate overlapping ambiguous time
                result = result.replace(fold=1)

            # handle landing in missing time
            delta_seconds = _delta_seconds_between_fold(result)
            if delta_seconds > 0:
                # per Vixie cron, trigger in missing time is run immediately after forward clock change
                result = result.replace(minute=0, second=0, microsecond=0) + dt.timedelta(seconds=delta_seconds)
                if is_wildcard_job:
                    # skip to just before end of missing time because result may or may not be a trigger point
                    start = result + dt.timedelta(microseconds=-1)
                    continue

            if goto_datetime and result.timestamp() >= goto_datetime.timestamp():
                # handle earlier prepared jump back
                start = goto_datetime + dt.timedelta(microseconds=-1) # -1us to include start point itself
                goto_datetime = None
                continue

            yield result
            start = result
            monotonic_datetime = result
