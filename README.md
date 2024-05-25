# CronDst

[![Test](https://github.com/lawcal/crondst/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/lawcal/crondst/actions/workflows/test.yml)

CronDst returns when the next job triggers given a cron expression. Supports time zones and daylight savings time (DST).

Features:
1. **Built according to [Vixie Cron](https://github.com/vixie/cron).** The popular cron scheduling logic that lives inside *nix systems like Debian, Ubuntu, RHEL and MacOS.
2. **Lightweight.** Single file, zero dependencies.
3. **Efficient.** Most expressions require just one constant-time step per iteration.

## Install
`pip install crondst`

## Usage
```
from datetime import datetime
from zoneinfo import ZoneInfo
from crondst import CronDst

# :00 and :01 at 2am and 3am in Pacific Time
tz = ZoneInfo('America/Los_Angeles')
it = CronDst('0-1 2,3 * * *').iter(datetime(2077, 12, 10, 2, 0, tzinfo=tz))

next(it) # datetime(2077, 12, 10, 2, 1)
next(it) # datetime(2077, 12, 10, 3, 0)
next(it) # datetime(2077, 12, 10, 3, 1)
next(it) # datetime(2077, 12, 11, 2, 0)
```

## Supported Cron Expressions

All valid Vixie Cron expressions are supported.

```
         field:
┌───────────── minute       (0–59)
│ ┌─────────── hour         (0–23)
│ │ ┌───────── day of month (1–31)
│ │ │ ┌─────── month        (1–12 or Jan-Dec)
│ │ │ │ ┌───── day of week  (0–6 or Sun-Sat, 7 or Sun)
│ │ │ │ │
* * * * *
```

| Syntax    | Name     | Applicable Field(s) |
| --------- | -------- | ------------------- |
| \<number> | number   | all                 |
| `*`       | wildcard | all                 |
| `-`       | range    | all                 |
| `,`       | list     | all                 |
| `/`       | step     | all                 |

## Daylight Savings Time (DST)

DST behavior follows Vixie Cron:
1. **Clock changes backwards.** Jobs triggered during ambiguous time are not repeated after the clock change.
2. **Clock changes forwards.** Jobs scheduled to trigger during missing time are triggered immediately after the clock change.
3. Above rules only apply to fixed-time (non-wildcard) jobs. Wildcard jobs are scheduled normally.

Wildcard jobs are where the hour or minute fields of a cron expression start with `*`.

CronDst iterates through each timestamp only once even if multiple jobs can be triggered for a timestamp.

## Day of Month and Day of Week

When the day of month or day of week fields start with `*`, the matching days are based on the intersection (AND) of both fields. Otherwise the union (OR) is taken.

This also aligns with Vixie Cron behavior.
