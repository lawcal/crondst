# pylint: disable=too-many-lines, line-too-long
import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from crondst import CronDst, CronDstError

TZ_NY = ZoneInfo('America/New_York')
TZ_RIGA = ZoneInfo('Europe/Riga')
TZ_LH = ZoneInfo('Australia/Lord_Howe') # cool place with half hour clock change

def assert_expected_iter(expression, after, expected):
    it = CronDst(expression).iter(after)
    for datetime in expected:
        actual = next(it)
        assert actual.tzinfo == datetime.tzinfo
        assert actual == datetime

def assert_expected_expression(expression, expected_error):
    if expected_error is None:
        assert CronDst(expression)
    else:
        with pytest.raises(CronDstError, match=expected_error):
            CronDst(expression)

@pytest.mark.parametrize(
    'expression,expected',
    [
        # maximum length
        (f"* * * * * {' ' * 991}", 'Bad expression - length exceeds 1000 characters'),
        (f"* * * * * {' ' * 990}", None),

        # fields count
        ('', 'Bad expression - expect five \\(5\\) fields separated by whitespace'),
        ('         ', 'Bad expression - expect five \\(5\\) fields separated by whitespace'),
        ('* * * *', 'Bad expression - expect five \\(5\\) fields separated by whitespace'),
        ('* * * * * *', 'Bad expression - expect five \\(5\\) fields separated by whitespace'),
        (' *  *  *  *  * ', None),
    ],
)
def test_expression_validation(expression, expected):
    assert_expected_expression(expression, expected)

def create_validation_tests(field):
    field_data = {
        'minute': (0, 0, 59),
        'hour': (1, 0, 23),
        'day-of-month': (2, 1, 31),
        'month': (3, 1, 12),
        'day-of-week': (4, 0, 7),
    }
    index, lower, upper = field_data[field]
    test_cases = [
        # number
        ('a', f"Bad {field}"),
        ('jan', None if field == 'month' else f"Bad {field}"),
        ('1jan', f"Bad {field}"),
        ('mon', None if field == 'day-of-week' else f"Bad {field}"),
        ('1mon', f"Bad {field}"),
        (f"{lower - 1}", f"Bad {field}"),
        ('-', f"Bad {field}"),
        (f"{upper + 1}", f"Bad {field}"),
        (f"{lower}", None),
        (f"{upper}", None),

        # wildcard
        ('**', f"Bad {field}"),
        ('*-*', f"Bad {field}"),
        ('*,*', None),

        # range
        (f"{lower - 1}-{upper + 1}", f"Bad {field}"),
        (f"{lower}-{upper + 1}", f"Bad {field}"),
        (f"{lower - 1}-{upper}", f"Bad {field}"),
        (f"{lower}--{upper}", f"Bad {field}"),
        (f"{upper}-{lower}", f"Bad {field}"),
        (f"{lower}-{upper}", None),
        (f"{lower}-{lower}", None),
        (f"{upper}-{upper}", None),

        # list
        (',', f"Bad {field}"),
        (',,', f"Bad {field}"),
        (f"{lower},{upper}-{lower}", f"Bad {field}"),
        ('*,*', None),
        (f"{lower},{lower}", None),
        (f"{lower},{lower}-{upper},*/1", None),

        # step
        ('1/', f"Bad {field}"),
        ('1//1', f"Bad {field}"),
        ('1/jan', f"Bad {field}"),
        ('1/mon', f"Bad {field}"),
        ('1/a', f"Bad {field}"),
        ('1/-1', f"Bad {field}"),
        ('1/0', f"Bad {field}"),
        ('*/1', None),
        ('1/1', None),
        ('1/999', None),
        (f"{lower}-{upper}/1", None),
        (f"{lower}-{lower}/1", None),
        (f"{upper}-{upper}/1", None),
    ]
    # effectively substitutes one of * in * * * * * with token at index
    return [(f"{' *' * index} {token}{' *' * (4 - index)}", expected) for token, expected in test_cases]

@pytest.mark.parametrize(
    'expression,expected',
    [
        *create_validation_tests('minute'),
        *create_validation_tests('hour'),
        *create_validation_tests('day-of-month'),
        *create_validation_tests('month'),
        *create_validation_tests('day-of-week'),
    ],
)
def test_field_validation(expression, expected):
    assert_expected_expression(expression, expected)

@pytest.mark.parametrize(
    'expression,expected',
    [
        # all months
        ('* * 30 1 *', None),
        ('* * 31 1 *', None),
        ('* * 28 2 *', None),
        ('* * 29 2 *', None),
        ('* * 30 2 *', 'Bad expression - results in no triggers'),
        ('* * 31 2 *', 'Bad expression - results in no triggers'),
        ('* * 30 3 *', None),
        ('* * 31 3 *', None),
        ('* * 30 4 *', None),
        ('* * 31 4 *', 'Bad expression - results in no triggers'),
        ('* * 30 5 *', None),
        ('* * 31 5 *', None),
        ('* * 30 6 *', None),
        ('* * 31 6 *', 'Bad expression - results in no triggers'),
        ('* * 30 7 *', None),
        ('* * 31 7 *', None),
        ('* * 30 8 *', None),
        ('* * 31 8 *', None),
        ('* * 30 9 *', None),
        ('* * 31 9 *', 'Bad expression - results in no triggers'),
        ('* * 30 10 *', None),
        ('* * 31 10 *', None),
        ('* * 30 11 *', None),
        ('* * 31 11 *', 'Bad expression - results in no triggers'),
        ('* * 30 12 *', None),
        ('* * 31 12 *', None),

        # wildcard week field with step
        ('* * 30 2 */1', 'Bad expression - results in no triggers'),
        ('* * 31 2 */1', 'Bad expression - results in no triggers'),
        ('* * 1-30 2 */1', 'Bad expression - results in no triggers'),
        ('* * 1-31 2 */1', 'Bad expression - results in no triggers'),
        ('* * 1,30 2 */1', 'Bad expression - results in no triggers'),
        ('* * 1,31 2 */1', 'Bad expression - results in no triggers'),

        # non-wildcard week field, causing OR
        ('* * 30 2 6,*/1', None),
        ('* * 31 2 6,*/1', None),

        # another month with greater maximum day
        ('* * 1-29 2,4 *', None),
        ('* * 1-30 2,4 *', None),
        ('* * 1-31 2,4 *', 'Bad expression - results in no triggers'),
        ('* * 1-29 2,3 *', None),
        ('* * 1-30 2,3 *', None),
        ('* * 1-31 2,3 *', None),
    ],
)
def test_expression_without_triggers(expression, expected):
    assert_expected_expression(expression, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        # wildcard
        (('*/20 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 20, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 40, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 20, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 40, tzinfo=TZ_NY),
        ]),

        # wildcard, not divisible
        (('*/21 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 21, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 42, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 21, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 42, tzinfo=TZ_NY),
        ]),

        # wildcard, exceeds range
        (('*/60 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 0, tzinfo=TZ_NY),
        ]),

        # smallest step
        (('2-3/1 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 3, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 3, tzinfo=TZ_NY),
        ]),

        # medium step, divisible
        (('2-10/4 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 10, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 2, tzinfo=TZ_NY),
        ]),

        # medium step, not divisible
        (('2-10/5 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 7, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 7, tzinfo=TZ_NY),
        ]),

        # large step
        (('2-10/8 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 10, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 10, tzinfo=TZ_NY),
        ]),

        # large step, exceeds range
        (('2-10/9 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 2, tzinfo=TZ_NY),
        ]),

        # range shorthand starting from smallest
        (('0/15 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 0, tzinfo=TZ_NY),
        ]),

        # range shorthand starting somewhere in middle
        (('3/1 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 23, 58, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 3, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 4, tzinfo=TZ_NY),
        ]),

        # range shorthand starting from largest
        (('59/1 * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 59, tzinfo=TZ_NY),
        ]),
    ],
)
def test_step(params, expected):
    assert_expected_iter(*params, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        (('* * * * *', dt.datetime(2022, 12, 31, 23, 57, 59, 99999, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 23, 58, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 59, tzinfo=TZ_NY),
        ]),
        (('* * * * *', dt.datetime(2022, 12, 31, 23, 58, 0, 1, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
        ]),
    ],
)
def test_seconds(params, expected):
    assert_expected_iter(*params, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        # minute column only
        # ********************

        # every minute
        (('* * * * *', dt.datetime(2022, 12, 31, 23, 57, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 23, 58, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 1, tzinfo=TZ_NY),
        ]),

        # minute 17
        (('17 * * * *', dt.datetime(2022, 12, 31, 22, 17, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 17, tzinfo=TZ_NY),
        ]),

        # minute 5-6
        (('5-6 * * * *', dt.datetime(2022, 12, 31, 22, 6, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 23, 5, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 6, tzinfo=TZ_NY),
        ]),

        # minute 5-6, 17
        (('5-6,17 * * * *', dt.datetime(2022, 12, 31, 22, 6, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 22, 17, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 5, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 6, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 17, tzinfo=TZ_NY),
        ]),

        # hour column only
        # ********************

        # every minute at 1am
        (('* 1 * * *', dt.datetime(2022, 12, 31, 0, 58, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 1, 1, tzinfo=TZ_NY),
        ]),
        (('* 1 * * *', dt.datetime(2022, 12, 31, 1, 58, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 0, tzinfo=TZ_NY),
        ]),

        # every minute at 10-11am
        (('* 10-11 * * *', dt.datetime(2022, 12, 31, 0, 58, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 10, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11 * * *', dt.datetime(2022, 12, 31, 10, 58, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 10, 59, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 11, 0, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 11, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11 * * *', dt.datetime(2022, 12, 31, 11, 58, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 11, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 10, 1, tzinfo=TZ_NY),
        ]),

        # every minute at 10-11am, 11pm
        (('* 10-11,23 * * *', dt.datetime(2022, 12, 31, 0, 58, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 10, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 * * *', dt.datetime(2022, 12, 31, 11, 58, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 11, 59, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 0, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 1, tzinfo=TZ_NY),
        ]),

        # hour and minute column
        # --------------------

        # minute 5-6, 17 at 10-11am, 11pm
        (('5-6,17 10-11,23 * * *', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2022, 12, 31, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 10, 17, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 11, 5, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 11, 6, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 11, 17, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 5, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 6, tzinfo=TZ_NY),
            dt.datetime(2022, 12, 31, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 10, 5, tzinfo=TZ_NY),
        ]),

        # day column only
        # ********************

        # every minute on 1st day
        (('* * 1 * *', dt.datetime(2022, 12, 31, 20, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1 * *', dt.datetime(2023, 1, 1, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 0, 1, tzinfo=TZ_NY),
        ]),

        # every minute on 5-6th day
        (('* * 5-6 * *', dt.datetime(2022, 12, 31, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 5-6 * *', dt.datetime(2023, 1, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 5, 0, 1, tzinfo=TZ_NY),
        ]),

        # every minute on 1st, 5-6th day
        (('* * 1,5-6 * *', dt.datetime(2022, 12, 31, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 * *', dt.datetime(2023, 1, 1, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 * *', dt.datetime(2023, 1, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 0, 1, tzinfo=TZ_NY),
        ]),

        # day and minute column
        # --------------------

        # minute 5-6, 17 on 1st, 5-6th day
        (('5-6,17 * 1,5-6 * *', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 17, tzinfo=TZ_NY),
        ]),
        (('5-6,17 * 1,5-6 * *', dt.datetime(2023, 1, 1, 23, 17, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 5, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 1, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 1, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 1, 17, tzinfo=TZ_NY),
        ]),
        (('5-6,17 * 1,5-6 * *', dt.datetime(2023, 1, 6, 23, 17, tzinfo=TZ_NY)), [
            dt.datetime(2023, 2, 1, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 1, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 1, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 1, 17, tzinfo=TZ_NY),
        ]),

        # day and hour column
        # --------------------

        # every minute at 10-11am, 11pm on 1st, 5-6th day
        (('* 10-11,23 1,5-6 * *', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 10, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 1,5-6 * *', dt.datetime(2023, 1, 1, 11, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 23, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 23, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 1,5-6 * *', dt.datetime(2023, 1, 1, 23, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 5, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 10, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 1,5-6 * *', dt.datetime(2023, 1, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 10, 1, tzinfo=TZ_NY),
        ]),

        # day, hour and minute column
        # --------------------

        # minute 5-6, 17 at 10-11am, 11pm on 1st, 5-6th day
        (('5-6,17 10-11,23 1,5-6 * *', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 10, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 11, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 11, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 11, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 23, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 23, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 10, 5, tzinfo=TZ_NY),
        ]),
        (('5-6,17 10-11,23 1,5-6 * *', dt.datetime(2023, 1, 5, 23, 17, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 6, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 6, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 6, 10, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 6, 11, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 6, 11, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 6, 11, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 6, 23, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 6, 23, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 6, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 10, 17, tzinfo=TZ_NY),
        ]),

        # month column only
        # ********************

        # every minute in Mar
        (('* * * 3 *', dt.datetime(2022, 12, 31, 20, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * 3 *', dt.datetime(2023, 3, 31, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 31, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 1, tzinfo=TZ_NY),
        ]),

        # every minute in Jul-Nov
        (('* * * 7-11 *', dt.datetime(2022, 12, 31, 20, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 7, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * 7-11 *', dt.datetime(2023, 11, 30, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 30, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2024, 7, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2024, 7, 1, 0, 1, tzinfo=TZ_NY),
        ]),

        # every minute in Mar, Jul-Nov
        (('* * * 3,7-11 *', dt.datetime(2023, 3, 31, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 31, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * 3,7-11 *', dt.datetime(2023, 11, 30, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 30, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 1, tzinfo=TZ_NY),
        ]),

        # month and minute column
        # --------------------

        # minute 5-6, 17 in Mar, Jul-Nov
        (('5-6,17 * * 3,7-11 *', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 1, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 1, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 1, 17, tzinfo=TZ_NY),
        ]),
        (('5-6,17 * * 3,7-11 *', dt.datetime(2023, 3, 31, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 31, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 1, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 1, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 1, 17, tzinfo=TZ_NY),
        ]),
        (('5-6,17 * * 3,7-11 *', dt.datetime(2023, 11, 30, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 30, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 1, 5, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 1, 6, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 1, 17, tzinfo=TZ_NY),
        ]),

        # month and hour column
        # --------------------

        # every minute at 10-11am, 11pm in Mar, Jul-Nov
        (('* 10-11,23 * 3,7-11 *', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 10, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 * 3,7-11 *', dt.datetime(2023, 3, 1, 11, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 11, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 23, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 23, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 * 3,7-11 *', dt.datetime(2023, 3, 1, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 2, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 2, 10, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 * 3,7-11 *', dt.datetime(2023, 3, 31, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 31, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 10, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 * 3,7-11 *', dt.datetime(2023, 11, 30, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 30, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 10, 1, tzinfo=TZ_NY),
        ]),

        # month and day column
        # --------------------

        # every minute on 1st, 5-6th day in Mar, Jul-Nov
        (('* * 1,5-6 3,7-11 *', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 3,7-11 *', dt.datetime(2023, 3, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 3,7-11 *', dt.datetime(2023, 7, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 7, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 8, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 8, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 3,7-11 *', dt.datetime(2023, 11, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 1, tzinfo=TZ_NY),
        ]),

        # month, day, hour and minute column
        # --------------------

        # minute 5-6, 17 at 10-11am, 11pm on 1st, 5-6th day in Mar, Jul-Nov
        (('5-6,17 10-11,23 1,5-6 3,7-11 *', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 10, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 11, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 11, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 11, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 23, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 23, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 5, 10, 5, tzinfo=TZ_NY),
        ]),
        (('5-6,17 10-11,23 1,5-6 3,7-11 *', dt.datetime(2023, 3, 6, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 6, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 10, 17, tzinfo=TZ_NY),
        ]),
        (('5-6,17 10-11,23 1,5-6 3,7-11 *', dt.datetime(2023, 11, 6, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 6, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 10, 17, tzinfo=TZ_NY),
        ]),

        # day of week column only
        # ********************

        # every minute on Wed
        (('* * * * 3', dt.datetime(2022, 12, 31, 20, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 4, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * * 3', dt.datetime(2023, 1, 4, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 4, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 11, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 11, 0, 1, tzinfo=TZ_NY),
        ]),

        # every minute on Wed-Fri
        (('* * * * 3-5', dt.datetime(2022, 12, 31, 20, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 4, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * * 3-5', dt.datetime(2023, 1, 4, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 4, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 5, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * * 3-5', dt.datetime(2023, 1, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 11, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 11, 0, 1, tzinfo=TZ_NY),
        ]),

        # every minute on Wed-Fri, Sun
        (('* * * * 3-5,0', dt.datetime(2022, 12, 31, 20, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * * 3-5,0', dt.datetime(2023, 1, 1, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * * 3-5,0', dt.datetime(2023, 1, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 0, 1, tzinfo=TZ_NY),
        ]),

        # every minute on Wed-Fri, Sun (alias)
        (('* * * * 3-5,7', dt.datetime(2022, 12, 31, 20, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * * 3-5,7', dt.datetime(2023, 1, 1, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * * 3-5,7', dt.datetime(2023, 1, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 0, 1, tzinfo=TZ_NY),
        ]),

        # day of week and minute column
        # --------------------

        # minute 5-6, 17 on Wed-Fri, Sun
        (('5-6,17 * * * 3-5,0', dt.datetime(2022, 12, 31, 20, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 1, 5, tzinfo=TZ_NY),
        ]),
        (('5-6,17 * * * 3-5,0', dt.datetime(2023, 1, 1, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 1, 5, tzinfo=TZ_NY),
        ]),
        (('5-6,17 * * * 3-5,0', dt.datetime(2023, 1, 6, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 6, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 0, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 0, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 0, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 1, 5, tzinfo=TZ_NY),
        ]),

        # day of week and hour column
        # --------------------

        # every minute at 10-11am, 11pm on Wed-Fri, Sun
        (('* 10-11,23 * * 3-5,0', dt.datetime(2022, 12, 31, 20, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 10, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 * * 3-5,0', dt.datetime(2023, 1, 1, 10, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 10, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 11, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 11, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 * * 3-5,0', dt.datetime(2023, 1, 1, 11, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 11, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 23, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 1, 23, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 * * 3-5,0', dt.datetime(2023, 1, 1, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 1, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 4, 10, 1, tzinfo=TZ_NY),
        ]),
        (('* 10-11,23 * * 3-5,0', dt.datetime(2023, 1, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 10, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 1, 8, 10, 1, tzinfo=TZ_NY),
        ]),

        # day of week and day column
        # --------------------

        # every minute on (1st, 5-6th day OR Wed-Fri, Sun)
        (('* * 1,5-6 * 3-5,0', dt.datetime(2023, 1, 31, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 2, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 * 3-5,0', dt.datetime(2023, 2, 1, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 2, 1, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 2, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 2, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 * 3-5,0', dt.datetime(2023, 2, 5, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 2, 5, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 6, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 6, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 * 3-5,0', dt.datetime(2023, 2, 6, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 2, 6, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 8, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 8, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 * 3-5,0', dt.datetime(2023, 2, 10, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 2, 10, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 12, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 12, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * 1,5-6 * 3-5,0', dt.datetime(2023, 2, 12, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 2, 12, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 15, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 2, 15, 0, 1, tzinfo=TZ_NY),
        ]),

        # day of week and month column
        # --------------------

        # every minute on Wed-Fri, Sun in Mar, Jul-Nov
        (('* * * 3,7-11 3-5,0', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * 3,7-11 3-5,0', dt.datetime(2023, 3, 1, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 2, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 2, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * 3,7-11 3-5,0', dt.datetime(2023, 3, 3, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 3, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 5, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * 3,7-11 3-5,0', dt.datetime(2023, 3, 3, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 3, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 5, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * 3,7-11 3-5,0', dt.datetime(2023, 3, 5, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 5, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 8, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 8, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * 3,7-11 3-5,0', dt.datetime(2023, 3, 31, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 31, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 2, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 2, 0, 1, tzinfo=TZ_NY),
        ]),
        (('* * * 3,7-11 3-5,0', dt.datetime(2023, 11, 30, 23, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 30, 23, 59, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 0, 1, tzinfo=TZ_NY),
        ]),

        # day of week, month, day, hour and minute column
        # --------------------

        # minute 5-6, 17 at 10-11am, 11pm on (1st, 5-6th day OR Wed-Fri, Sun) in Mar, Jul-Nov
        (('5-6,17 10-11,23 1,5-6 3,7-11 3-5,0', dt.datetime(2022, 12, 31, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 1, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 10, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 11, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 11, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 11, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 23, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 23, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 1, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 2, 10, 5, tzinfo=TZ_NY),
        ]),
        (('5-6,17 10-11,23 1,5-6 3,7-11 3-5,0', dt.datetime(2023, 3, 5, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 5, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 6, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 6, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 6, 10, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 6, 11, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 6, 11, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 6, 11, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 6, 23, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 6, 23, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 6, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 8, 10, 5, tzinfo=TZ_NY),
        ]),
        (('5-6,17 10-11,23 1,5-6 3,7-11 3-5,0', dt.datetime(2023, 3, 10, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 10, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 10, 17, tzinfo=TZ_NY),
        ]),
        (('5-6,17 10-11,23 1,5-6 3,7-11 3-5,0', dt.datetime(2023, 3, 31, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 31, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 1, 10, 17, tzinfo=TZ_NY),
        ]),
        (('5-6,17 10-11,23 1,5-6 3,7-11 3-5,0', dt.datetime(2023, 11, 30, 23, 6, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 30, 23, 17, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 10, 5, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 10, 6, tzinfo=TZ_NY),
            dt.datetime(2024, 3, 1, 10, 17, tzinfo=TZ_NY),
        ]),
    ],
)
def test_valid_expression(params, expected):
    assert_expected_iter(*params, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        # America/New_York time zone clock change:
        # 2023-03-12 right before 2:00am -> 3:00am (clock change forwards)

        # wilcard job
        # ********************

        # minute wildcard job - every minute
        # --------------------

        # before missing time
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 1, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 2, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 3, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 2, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 1, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 2, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 3, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 2, 58, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('* 0-23 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 2, tzinfo=TZ_NY),
        ]),

        # minute wildcard job - every 30m
        # --------------------

        # before missing time
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 1, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 29, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 29, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('*/30 0-23 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),

        # minute wildcard job - every hour
        # --------------------

        # before missing time
        (('*/999 0-23 * * *', dt.datetime(2023, 3, 12, 0, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('*/999 0-23 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('*/999 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 0, tzinfo=TZ_NY),
        ]),
        (('*/999 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('*/999 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('*/999 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('*/999 0-23 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 0, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every minute
        # --------------------

        # before missing time
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 1, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 2, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 2, 1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 3, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 2, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 1, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 2, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 2, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 3, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 2, 58, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0-59/1 * * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 2, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every 30m
        # --------------------

        # before missing time
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 1, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 2, 1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 2, 29, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 2, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 2, 29, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0,30 * * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every 30m with offset
        # --------------------

        # before missing time
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 1, 15, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 2, 1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 2, 44, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 45, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 2, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 2, 29, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('15,45 * * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every hour
        # --------------------

        # before missing time
        (('0 * * * *', dt.datetime(2023, 3, 12, 0, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0 * * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0 * * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 0, tzinfo=TZ_NY),
        ]),
        (('0 * * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0 * * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0 * * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0 * * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 0, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every 2h (hitting 2am)
        # --------------------

        # before missing time
        (('0 */2 * * *', dt.datetime(2023, 3, 11, 22, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0 */2 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0 */2 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),
        (('0 */2 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0 */2 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),
        (('0 */2 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0 */2 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every 3h (hitting 3am)
        # --------------------

        # before missing time
        (('0 */3 * * *', dt.datetime(2023, 3, 11, 22, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0 */3 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0 */3 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 9, 0, tzinfo=TZ_NY),
        ]),
        (('0 */3 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 9, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0 */3 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),
        (('0 */3 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0 */3 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 9, 0, tzinfo=TZ_NY),
        ]),

        # non-wilcard (fixed-time) job
        # ********************

        # every minute
        # --------------------

        # before missing time
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 1, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 2, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 3, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 2, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 1, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 2, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 2, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 3, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 2, 58, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0-59 0-23 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 2, tzinfo=TZ_NY),
        ]),

        # every 30m
        # --------------------

        # before missing time
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 1, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 29, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 29, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0,30 0-23 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),

        # every 30m with offset
        # --------------------

        # before missing time
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 1, 15, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 2, 44, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 45, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 2, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 2, 44, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('15,45 0-23 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 45, tzinfo=TZ_NY),
        ]),

        # every hour
        # --------------------

        # before missing time
        (('0 0-23 * * *', dt.datetime(2023, 3, 12, 0, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0 0-23 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 0, tzinfo=TZ_NY),
        ]),

        # every hour with offset
        # --------------------

        # before missing time
        (('30 0-23 * * *', dt.datetime(2023, 3, 12, 0, 30, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
        ]),
        (('30 0-23 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
        ]),
        (('30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 5, 30, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
        ]),
        (('30 0-23 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('30 0-23 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 30, tzinfo=TZ_NY),
        ]),

        # every 2h (hitting 2am)
        # --------------------

        # before missing time
        (('0 0-23/2 * * *', dt.datetime(2023, 3, 11, 22, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23/2 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0 0-23/2 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23/2 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0 0-23/2 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23/2 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0 0-23/2 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # every 3h (hitting 3am)
        # --------------------

        # before missing time
        (('0 0-23/3 * * *', dt.datetime(2023, 3, 11, 22, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23/3 * * *', dt.datetime(2023, 3, 12, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=0
        (('0 0-23/3 * * *', dt.datetime(2023, 3, 12, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 9, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23/3 * * *', dt.datetime(2023, 3, 12, 2, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 9, 0, tzinfo=TZ_NY),
        ]),

        # missing time fold=1
        (('0 0-23/3 * * *', dt.datetime(2023, 3, 12, 2, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23/3 * * *', dt.datetime(2023, 3, 12, 2, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
        ]),

        # after missing time
        (('0 0-23/3 * * *', dt.datetime(2023, 3, 12, 3, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 12, 6, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 12, 9, 0, tzinfo=TZ_NY),
        ]),
    ],
)
def test_clock_change_forwards_america(params, expected):
    assert_expected_iter(*params, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        # America/New_York time zone clock change:
        # 2023-11-05 right before 2:00am -> 1:00am (clock change backwards)

        # wilcard job
        # ********************

        # minute wildcard job - every minute
        # --------------------

        # before ambiguous time
        (('* 0-23 * * *', dt.datetime(2023, 11, 5, 1, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('* 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 2, fold=1, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 2, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 3, fold=1, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 11, 5, 1, 58, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('* 0-23 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 2, tzinfo=TZ_NY),
        ]),

        # minute wildcard job - every 30m
        # --------------------

        # before ambiguous time
        (('*/30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('*/30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 29, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('*/30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('*/30 0-23 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),

        # minute wildcard job - every hour
        # --------------------

        # before ambiguous time
        (('*/999 0-23 * * *', dt.datetime(2023, 11, 5, 0, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('*/999 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('*/999 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),
        (('*/999 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('*/999 0-23 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every minute
        # --------------------

        # before ambiguous time
        (('0-59/1 * * * *', dt.datetime(2023, 11, 5, 1, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0-59/1 * * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 2, fold=1, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 2, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 3, fold=1, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 11, 5, 1, 58, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('0-59/1 * * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0-59/1 * * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 2, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every 30m
        # --------------------

        # before ambiguous time
        (('0,30 * * * *', dt.datetime(2023, 11, 5, 1, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0,30 * * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 11, 5, 1, 29, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0,30 * * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every 30m with offset
        # --------------------

        # before ambiguous time
        (('15,45 * * * *', dt.datetime(2023, 11, 5, 1, 15, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 15, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 45, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 15, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 45, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('15,45 * * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 15, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 45, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 15, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 45, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 11, 5, 1, 44, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 45, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 * * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 45, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('15,45 * * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 45, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every hour
        # --------------------

        # before ambiguous time
        (('0 * * * *', dt.datetime(2023, 11, 5, 0, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('0 * * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0 * * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0 * * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0 * * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every 2h (hitting 2am)
        # --------------------

        # before ambiguous time
        (('0 */2 * * *', dt.datetime(2023, 11, 4, 22, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0 */2 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0 */2 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0 */2 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0 */2 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 6, 0, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - midnight and 1am only
        # --------------------

        # before ambiguous time
        (('0 */999,1 * * *', dt.datetime(2023, 11, 4, 22, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
        ]),
        (('0 */999,1 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0 */999,1 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 1, 0, tzinfo=TZ_NY),
        ]),
        (('0 */999,1 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 1, 0, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0 */999,1 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 1, 0, tzinfo=TZ_NY),
        ]),

        # non-wilcard (fixed-time) job
        # ********************

        # every minute
        # --------------------

        # before ambiguous time
        (('0-59 0-23 * * *', dt.datetime(2023, 11, 5, 1, 58, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0-59 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 11, 5, 1, 58, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0-59 0-23 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 2, tzinfo=TZ_NY),
        ]),

        # every 30m
        # --------------------

        # before ambiguous time
        (('0,30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0,30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
        ]),
        (('0,30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0,30 0-23 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),

        # every 30m with offset
        # --------------------

        # before ambiguous time
        (('15,45 0-23 * * *', dt.datetime(2023, 11, 5, 1, 15, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 45, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('15,45 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 45, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 11, 5, 1, 1, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 45, tzinfo=TZ_NY),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 45, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('15,45 0-23 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 45, tzinfo=TZ_NY),
        ]),

        # every hour
        # --------------------

        # before ambiguous time
        (('0 0-23 * * *', dt.datetime(2023, 11, 5, 0, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0 0-23 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),

        # every hour with offset
        # --------------------

        # before ambiguous time
        (('30 0-23 * * *', dt.datetime(2023, 11, 5, 0, 30, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 1, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 30, tzinfo=TZ_NY),
        ]),
        (('30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 30, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 30, tzinfo=TZ_NY),
        ]),
        (('30 0-23 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 30, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('30 0-23 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 3, 30, tzinfo=TZ_NY),
        ]),

        # every 2h (hitting 2am)
        # --------------------

        # before ambiguous time
        (('0 0-23/2 * * *', dt.datetime(2023, 11, 4, 22, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23/2 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0 0-23/2 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),
        (('0 0-23/2 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0 0-23/2 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 4, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 6, 0, tzinfo=TZ_NY),
        ]),

        # midnight and 1am only
        # --------------------

        # before ambiguous time
        (('0 0,1 * * *', dt.datetime(2023, 11, 4, 22, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 5, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 5, 1, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
        ]),
        (('0 0,1 * * *', dt.datetime(2023, 11, 5, 1, 59, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 1, 0, tzinfo=TZ_NY),
        ]),

        # ambiguous time fold=1
        (('0 0,1 * * *', dt.datetime(2023, 11, 5, 1, 0, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 1, 0, tzinfo=TZ_NY),
        ]),
        (('0 0,1 * * *', dt.datetime(2023, 11, 5, 1, 59, fold=1, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 1, 0, tzinfo=TZ_NY),
        ]),

        # after ambiguous time
        (('0 0,1 * * *', dt.datetime(2023, 11, 5, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 11, 6, 0, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 6, 1, 0, tzinfo=TZ_NY),
        ]),
    ],
)
def test_clock_change_backwards_america(params, expected):
    assert_expected_iter(*params, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        # Australia/Lord_Howe time zone clock change:
        # 2023-10-01 right before 2:00am -> 2:30am (clock change forwards)

        # wilcard job
        # ********************

        # minute wildcard job - every minute
        # --------------------

        # before missing time
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 1, 58, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 59, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 1, 59, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_LH),
        ]),

        # missing time fold=0
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 2, 0, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 32, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 2, 1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 32, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 33, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 2, 28, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 59, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 2, 29, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 1, tzinfo=TZ_LH),
        ]),

        # missing time fold=1
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 2, 0, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 31, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 1, 32, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 2, 1, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 32, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 1, 33, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 2, 28, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 59, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 2, 29, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_LH),
        ]),

        # after ambiguous time
        (('* 0-23 * * *', dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_NY)), [
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_NY),
            dt.datetime(2023, 10, 1, 2, 32, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every 30m
        # --------------------

        # before missing time
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 1, 0, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 1, 59, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
        ]),

        # missing time fold=0
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 2, 0, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 30, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 2, 1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 30, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 2, 28, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 30, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 2, 29, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 30, tzinfo=TZ_LH),
        ]),

        # missing time fold=1
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 2, 0, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 2, 1, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 2, 28, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 2, 29, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
        ]),

        # after ambiguous time
        (('0,30 * * * *', dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_NY)), [
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 10, 1, 3, 30, tzinfo=TZ_NY),
        ]),

        # non-wilcard (fixed-time) job
        # ********************

        # every minute
        # --------------------

        # before missing time
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 1, 58, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 59, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 1, 59, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_LH),
        ]),

        # missing time fold=0
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 2, 0, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 32, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 2, 1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 32, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 33, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 2, 28, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 59, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 2, 29, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 3, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 1, tzinfo=TZ_LH),
        ]),

        # missing time fold=1
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 2, 0, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 31, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 1, 32, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 2, 1, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 32, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 1, 33, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 2, 28, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 59, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 2, 29, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_LH),
        ]),

        # after ambiguous time
        (('0-59 0-23 * * *', dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_NY)), [
            dt.datetime(2023, 10, 1, 2, 31, tzinfo=TZ_NY),
            dt.datetime(2023, 10, 1, 2, 32, tzinfo=TZ_NY),
        ]),

        # every 30m with offset
        # --------------------

        # before missing time
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 1, 44, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 45, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 45, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 1, 59, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 45, tzinfo=TZ_LH),
        ]),

        # missing time fold=0
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 2, 0, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 45, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 15, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 2, 1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 45, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 15, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 2, 16, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 3, 15, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 45, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 2, 29, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 3, 15, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 3, 45, tzinfo=TZ_LH),
        ]),

        # missing time fold=1
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 2, 0, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 45, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 45, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 2, 1, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 45, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 45, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 2, 14, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 1, 45, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 45, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 2, 29, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 10, 1, 2, 45, tzinfo=TZ_LH),
        ]),

        # after ambiguous time
        (('15,45 0-23 * * *', dt.datetime(2023, 10, 1, 2, 30, tzinfo=TZ_NY)), [
            dt.datetime(2023, 10, 1, 2, 45, tzinfo=TZ_NY),
            dt.datetime(2023, 10, 1, 3, 15, tzinfo=TZ_NY),
        ]),
    ],
)
def test_clock_change_forwards_australia(params, expected):
    assert_expected_iter(*params, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        # Australia/Lord_Howe time zone clock change:
        # 2023-04-02 right before 2:00am -> 1:30am (clock change backwards)

        # wilcard job
        # ********************

        # minute wildcard job - every minute
        # --------------------

        # before missing time
        (('* 0-23 * * *', dt.datetime(2023, 4, 2, 1, 58, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 1, 59, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 1, 30, fold=1, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 1, 31, fold=1, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 4, 2, 1, 59, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 1, 30, fold=1, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 1, 31, fold=1, tzinfo=TZ_LH),
        ]),

        # missing time fold=1
        (('* 0-23 * * *', dt.datetime(2023, 4, 2, 1, 30, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 1, 31, fold=1, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 1, 32, fold=1, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 4, 2, 1, 31, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 1, 32, fold=1, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 1, 33, fold=1, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 4, 2, 1, 58, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 1, 59, fold=1, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
        ]),
        (('* 0-23 * * *', dt.datetime(2023, 4, 2, 1, 59, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 1, tzinfo=TZ_LH),
        ]),

        # after ambiguous time
        (('* 0-23 * * *', dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 4, 2, 2, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 4, 2, 2, 2, tzinfo=TZ_NY),
        ]),

        # hour wildcard job - every 30m
        # --------------------

        # before missing time
        (('0,30 * * * *', dt.datetime(2023, 4, 2, 1, 0, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 1, 30, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 1, 30, fold=1, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 4, 2, 1, 59, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 1, 30, fold=1, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
        ]),

        # missing time fold=1
        (('0,30 * * * *', dt.datetime(2023, 4, 2, 1, 30, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 30, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 4, 2, 1, 31, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 30, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 4, 2, 1, 58, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 30, tzinfo=TZ_LH),
        ]),
        (('0,30 * * * *', dt.datetime(2023, 4, 2, 1, 59, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 30, tzinfo=TZ_LH),
        ]),

        # after ambiguous time
        (('0,30 * * * *', dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 4, 2, 2, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 4, 2, 3, 0, tzinfo=TZ_NY),
        ]),

        # non-wilcard (fixed-time) job
        # ********************

        # every minute
        # --------------------

        # before missing time
        (('0-59 0-23 * * *', dt.datetime(2023, 4, 2, 1, 58, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 1, 59, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 1, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 4, 2, 1, 59, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 1, tzinfo=TZ_LH),
        ]),

        # missing time fold=1
        (('0-59 0-23 * * *', dt.datetime(2023, 4, 2, 1, 30, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 1, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 4, 2, 1, 31, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 1, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 4, 2, 1, 58, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 1, tzinfo=TZ_LH),
        ]),
        (('0-59 0-23 * * *', dt.datetime(2023, 4, 2, 1, 59, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 1, tzinfo=TZ_LH),
        ]),

        # after ambiguous time
        (('0-59 0-23 * * *', dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 4, 2, 2, 1, tzinfo=TZ_NY),
            dt.datetime(2023, 4, 2, 2, 2, tzinfo=TZ_NY),
        ]),

        # every 30m with offset
        # --------------------

        # before missing time
        (('15,45 0-23 * * *', dt.datetime(2023, 4, 2, 1, 44, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 1, 45, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 15, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 45, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 4, 2, 1, 59, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 15, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 45, tzinfo=TZ_LH),
        ]),

        # missing time fold=1
        (('15,45 0-23 * * *', dt.datetime(2023, 4, 2, 1, 30, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 15, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 45, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 4, 2, 1, 31, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 15, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 45, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 4, 2, 1, 44, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 15, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 45, tzinfo=TZ_LH),
        ]),
        (('15,45 0-23 * * *', dt.datetime(2023, 4, 2, 1, 59, fold=1, tzinfo=TZ_LH)), [
            dt.datetime(2023, 4, 2, 2, 15, tzinfo=TZ_LH),
            dt.datetime(2023, 4, 2, 2, 45, tzinfo=TZ_LH),
        ]),

        # after ambiguous time
        (('15,45 0-23 * * *', dt.datetime(2023, 4, 2, 2, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 4, 2, 2, 15, tzinfo=TZ_NY),
            dt.datetime(2023, 4, 2, 2, 45, tzinfo=TZ_NY),
        ]),
    ],
)
def test_clock_change_backwards_australia(params, expected):
    assert_expected_iter(*params, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        # Sourced from cronsim:
        # https://github.com/cuu508/cronsim/blob/main/tests/test_cronsim.py

        # Europe/Riga time zone clock change:
        # 2021-03-28 right before 3:00am -> 4:00am (clock change forwards)
        # 2021-10-31 right before 4:00am -> 3:00am (clock change backwards)

        # test_001_every_hour_mar
        (('0 * * * *', dt.datetime(2021, 3, 28, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_001_every_hour_oct
        (('0 * * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_002_every_30_minutes_mar
        (('*/30 * * * *', dt.datetime(2021, 3, 28, 2, 10, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 30, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 30, tzinfo=TZ_RIGA),
        ]),

        # test_002_every_30_minutes_oct
        (('*/30 * * * *', dt.datetime(2021, 10, 31, 2, 10, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 30, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 30, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 30, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_003_every_15_minutes_mar
        (('*/15 * * * *', dt.datetime(2021, 3, 28, 2, 40, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 45, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_003_every_15_minutes_oct
        (('*/15 * * * *', dt.datetime(2021, 10, 31, 2, 40, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 45, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 15, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 30, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 45, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 15, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 30, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 45, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_004_every_2_hours_mar
       (('0 */2 * * *', dt.datetime(2021, 3, 28, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 6, 0, tzinfo=TZ_RIGA),
        ]),

        # test_004_every_2_hours_oct
        (('0 */2 * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 6, 0, tzinfo=TZ_RIGA),
        ]),

        # test_005_30_minutes_past_every_2_hours_mar
       (('30 */2 * * *', dt.datetime(2021, 3, 28, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 30, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 30, tzinfo=TZ_RIGA),
        ]),

        # test_005_30_minutes_past_every_2_hours_oct
        (('30 */2 * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 30, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 30, tzinfo=TZ_RIGA),
        ]),

        # test_006_every_3_hours_oct
        (('0 */3 * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 6, 0, tzinfo=TZ_RIGA),
        ]),

        # test_008_at_1_2_3_4_5_mar
        (('0 1,2,3,4,5 * * *', dt.datetime(2021, 3, 28, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 5, 0, tzinfo=TZ_RIGA),
        ]),

        # test_008_at_1_2_3_4_5_oct
        (('0 1,2,3,4,5 * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_009_30_past_at_1_2_3_4_5_mar
        (('30 1,2,3,4,5 * * *', dt.datetime(2021, 3, 28, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 30, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 30, tzinfo=TZ_RIGA),
        ]),

        # test_009_30_past_at_1_2_3_4_5_oct
        (('30 1,2,3,4,5 * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 30, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 30, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 30, tzinfo=TZ_RIGA),
        ]),

        # test_010_at_2_mar
        (('0 2 * * *', dt.datetime(2021, 3, 28, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 29, 2, 0, tzinfo=TZ_RIGA),
        ]),

        # test_010_at_2_oct
        (('0 2 * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 11, 1, 2, 0, tzinfo=TZ_RIGA),
        ]),

        # test_011_at_3_mar
        (('0 3 * * *', dt.datetime(2021, 3, 27, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 27, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 29, 3, 0, tzinfo=TZ_RIGA),
        ]),

        # test_011_at_3_oct
        (('0 3 * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 11, 1, 3, 0, tzinfo=TZ_RIGA),
        ]),

        # test_012_at_4_mar
        (('0 4 * * *', dt.datetime(2021, 3, 27, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 27, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 29, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_012_at_4_oct
        (('0 4 * * *', dt.datetime(2021, 10, 30, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 30, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 11, 1, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_014_every_hour_enumerated_mar
        (('0 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23 * * *', dt.datetime(2021, 3, 28, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 5, 0, tzinfo=TZ_RIGA),
        ]),

        # test_014_every_hour_enumerated_oct
        (('0 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23 * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_015_every_other_hour_enumerated_mar
        (('0 1,3,5,7,9,11,13,15,17,19,21,23 * * *', dt.datetime(2021, 3, 28, 0, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 1, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 5, 0, tzinfo=TZ_RIGA),
        ]),

        # test_015_every_other_hour_enumerated_oct
        (('0 1,3,5,7,9,11,13,15,17,19,21,23 * * *', dt.datetime(2021, 10, 31, 0, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 1, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 5, 0, tzinfo=TZ_RIGA),
        ]),

        # test_016_at_1_to_5_mar
        (('0 1-5 * * *', dt.datetime(2021, 3, 28, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 5, 0, tzinfo=TZ_RIGA),
        ]),

        # test_016_at_1_to_5_oct
        (('0 1-5 * * *', dt.datetime(2021, 10, 31, 1, 30, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 2, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_at_3_15_mar
        (('15 3 * * *', dt.datetime(2021, 3, 27, 0, 0, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 27, 3, 15, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 29, 3, 15, tzinfo=TZ_RIGA),
        ]),

        # test_at_3_15_oct
        (('15 3 * * *', dt.datetime(2021, 10, 30, 0, 0, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 30, 3, 15, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 15, tzinfo=TZ_RIGA),
            dt.datetime(2021, 11, 1, 3, 15, tzinfo=TZ_RIGA),
        ]),

        # test_every_minute_mar
        (('* * * * *', dt.datetime(2021, 3, 28, 2, 58, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 59, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_every_minute_oct
        (('* * * * *', dt.datetime(2021, 10, 31, 3, 58, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 3, 59, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 1, fold=1, tzinfo=TZ_RIGA),
        ]),

        # test_every_minute_from_1_to_6_mar
        (('* 1-6 * * *', dt.datetime(2021, 3, 28, 2, 58, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 3, 28, 2, 59, tzinfo=TZ_RIGA),
            dt.datetime(2021, 3, 28, 4, 0, tzinfo=TZ_RIGA),
        ]),

        # test_every_minute_from_1_to_6_oct
        (('* 1-6 * * *', dt.datetime(2021, 10, 31, 3, 58, tzinfo=TZ_RIGA)), [
            dt.datetime(2021, 10, 31, 3, 59, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 0, fold=1, tzinfo=TZ_RIGA),
            dt.datetime(2021, 10, 31, 3, 1, fold=1, tzinfo=TZ_RIGA),
        ]),
    ],
)
def test_clock_change_europe(params, expected):
    assert_expected_iter(*params, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        # leap years, starting from non leap-year
        (('0 12 29 2 *', dt.datetime(2023, 2, 28, 12, 0, tzinfo=TZ_NY)), [
            dt.datetime(2024, 2, 29, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2028, 2, 29, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2032, 2, 29, 12, 0, tzinfo=TZ_NY),
        ]),

        # leap years, starting from leap-year
        (('0 12 29 2 *', dt.datetime(2024, 2, 29, 12, 0, tzinfo=TZ_NY)), [
            dt.datetime(2028, 2, 29, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2032, 2, 29, 12, 0, tzinfo=TZ_NY),
        ]),

        # leap years with minute frequency, starting from non leap-year
        (('2,4 12 29 2 *', dt.datetime(2023, 2, 28, 12, 0, tzinfo=TZ_NY)), [
            dt.datetime(2024, 2, 29, 12, 2, tzinfo=TZ_NY),
            dt.datetime(2024, 2, 29, 12, 4, tzinfo=TZ_NY),
            dt.datetime(2028, 2, 29, 12, 2, tzinfo=TZ_NY),
            dt.datetime(2028, 2, 29, 12, 4, tzinfo=TZ_NY),
            dt.datetime(2032, 2, 29, 12, 2, tzinfo=TZ_NY),
            dt.datetime(2032, 2, 29, 12, 4, tzinfo=TZ_NY),
        ]),

        # leap years with minute frequency, starting from leap-year
        (('2,4 12 29 2 *', dt.datetime(2024, 2, 29, 12, 2, tzinfo=TZ_NY)), [
            dt.datetime(2024, 2, 29, 12, 4, tzinfo=TZ_NY),
            dt.datetime(2028, 2, 29, 12, 2, tzinfo=TZ_NY),
            dt.datetime(2028, 2, 29, 12, 4, tzinfo=TZ_NY),
            dt.datetime(2032, 2, 29, 12, 2, tzinfo=TZ_NY),
        ]),

        # 31st of every month
        (('0 12 31 * *', dt.datetime(2023, 1, 1, 12, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 31, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 31, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 5, 31, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 31, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 8, 31, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 10, 31, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 12, 31, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2024, 1, 31, 12, 0, tzinfo=TZ_NY),
        ]),

        # 30th of every month
        (('0 12 30 * *', dt.datetime(2023, 1, 1, 12, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 1, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 3, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 4, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 5, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 6, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 8, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 9, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 10, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 11, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2023, 12, 30, 12, 0, tzinfo=TZ_NY),
            dt.datetime(2024, 1, 30, 12, 0, tzinfo=TZ_NY),
        ]),
    ]
)
def test_leap_years(params, expected):
    assert_expected_iter(*params, expected)

@pytest.mark.parametrize(
    'params,expected',
    [
        # Vixie Cron hack using day wildcard and oversized step to cause day, day of week critiera to be ANDed

        # 1:00pm on the 1st that must be a Wed in Jan,Apr,Jul,Oct
        (('0 13 */999 1,4,7,10 3', dt.datetime(2020, 9, 24, tzinfo=TZ_NY)), [
            dt.datetime(2025, 1, 1, 13, 0, tzinfo=TZ_NY),
        ]),

        # 3:30am on the first Mon of every month
        (('30 3 */999,1-7 * 1', dt.datetime(2023, 2, 28, 12, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 3, 6, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 4, 3, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 5, 1, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 6, 5, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2023, 7, 3, 3, 30, tzinfo=TZ_NY)
        ]),

        # 3:30am on the 1st that must be a Mon of every month
        (('30 3 */999 * 1', dt.datetime(2023, 2, 28, 12, 0, tzinfo=TZ_NY)), [
            dt.datetime(2023, 5, 1, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2024, 1, 1, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2024, 4, 1, 3, 30, tzinfo=TZ_NY),
            dt.datetime(2024, 7, 1, 3, 30, tzinfo=TZ_NY),
        ]),
    ]
)
def test_vixie_cron_hack(params, expected):
    assert_expected_iter(*params, expected)
