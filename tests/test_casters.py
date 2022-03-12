import io
import re
import datetime as dt
import typing as t

import pytest

from casters import cast_to_type, get_type_hint_name



@pytest.mark.parametrize(
    'value, type_hint, strict, expected_result', (
    ('1', int, True, 1),
    ('1.1', float, True, 1.1),
    ('1', None, False, 1),
    ('true', bool, True, True),
    ('false', bool, False, False),
    ('true', None, False, True),

    # Support shell lists (space separated values)
    ('one two three', list, True, ['one', 'two', 'three']),
    ('one two three', t.List, True, ['one', 'two', 'three']),
    ('one two three', tuple, True, ('one', 'two', 'three')),
    ('one two three', t.Tuple, True, ('one', 'two', 'three')),
    ('one "two three four" five', list, True, ['one', 'two three four', 'five']),
    ("one 'two three four' five", t.List, True, ['one', 'two three four', 'five']),

    # Support inner types for containers
    ('1 2 3', list[int], True, [1, 2, 3]),
    ('false 1 two 3', list[bool | int | str], True, [False, 1, 'two', 3]),
    ('1', tuple[int], True, (1,)),
    ('false 1 two 3', tuple[bool, int, str, int], True, (False, 1, 'two', 3)),
    ('1 2 3', tuple[int, ...], True, (1, 2, 3)),
    ('1 2 3', tuple[int], True, ValueError),
    ('1 2 3', tuple[int, int], True, ValueError),


    # Support t.Union types, including Optionals
    ('test', t.Union[int, str], True, 'test'),
    ('test', t.Union[int, list], True, ['test']),
    ('1', bool | int, True, 1),
    ('test', t.Optional[list], True, ['test']),
    ('1 2 3', t.Optional[tuple[int, ...]], True, (1, 2, 3)),


    # Support regex re.Pattern / typing.Pattern type
    ('^abc$', t.Pattern, True, re.compile('^abc$')),
    ('^abc$', re.Pattern, True, re.compile('^abc$')),

    # Support json values for dict/list types
    ('{"one": 2, "three": [4, 5]}', dict, True, {"one": 2, "three": [4, 5]}),
    ('{"one": 2, "three": [4, 5]}', t.Dict, True, {"one": 2, "three": [4, 5]}),
    ('["one", {"two": 3, "four": 5}]', list, True, ["one", {"two": 3, "four": 5}]),
    ('["one", {"two": 3, "four": 5}]', t.List, True, ["one", {"two": 3, "four": 5}]),

    # Support native dt.datetime types: dt.date, dt.datetime, time
    ('1646803515', dt.date, True, dt.date.fromtimestamp(1646803515)),
    ('2022-03-09', dt.date, True, dt.date.fromisoformat('2022-03-09')),
    ('1646803515', None, False, 1646803515),
    ('2022-03-09', None, False, '2022-03-09'),
    ('1646803515', dt.datetime, True, dt.datetime.fromtimestamp(1646803515)),
    ('2022-03-09T00:05:23', dt.datetime, True, dt.datetime.fromisoformat('2022-03-09T00:05:23')),
    ('1646803515', None, False, 1646803515),
    ('2022-03-09T00:05:23', None, False, '2022-03-09T00:05:23'),
    ('04:23:01.000384', dt.time, True, dt.time.fromisoformat('04:23:01.000384')),
    ('04:23:01.000384', None, False, '04:23:01.000384'),

    # TextIO stream from file
    ('/dev/null', t.TextIO, True, io.TextIOWrapper),
    ('/dev/null', io.TextIOWrapper, True, io.TextIOWrapper),
))
def test_cast_from_shell(value, type_hint, strict, expected_result, monkeypatch):
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    if isinstance(expected_result, type) and issubclass(expected_result, Exception):
        with pytest.raises(expected_result, match='invalid literal'):
            cast_to_type(value, type_hint, strict=strict)
    elif isinstance(expected_result, type):
        result = cast_to_type(value, type_hint, strict=strict)
        assert type(result) is io.TextIOWrapper
    else:
        result = cast_to_type(value, type_hint, strict=strict)
        assert result == expected_result



@pytest.mark.parametrize(
    'type_hint, name', (
        # Native types
        (int,   'int'),         (bool,  'bool'),
        (float, 'float'),       (str,   'str'),
        (tuple, 'tuple'),       (list,  'list'),
        (set,   'set'),         (dict,  'dict'),

        # typing module built in generics
        (t.Dict,  'dict'),        (t.List,  'list'),
        (t.Set,   'set'),         (t.Tuple, 'tuple'),
        (t.DefaultDict, 'defaultdict'),

        # Union types
        (t.Optional[int], 'int'),
        (t.Optional[t.List], 'list'),
        (list | dict, 'list | dict'),
        (t.Union[int, str], 'int | str'),
        (dict | int | t.List, 'dict | int | list'),
        (t.Union[t.Set, list, t.DefaultDict], 'set | list | defaultdict'),
))
def test_get_type_hint_name(type_hint, name):
    assert get_type_hint_name(type_hint) == name
