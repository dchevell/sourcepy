import collections.abc as abc
import io
import re
import datetime as dt
import pathlib as p
import typing as t

import pytest

from casters import cast_to_type, get_typehint_name



@pytest.mark.parametrize(
    'value, type_hint, strict, expected_result', (
    ('1', int, True, 1),
    ('1.0', float, True, 1.0),
    ('1', None, False, 1),
    ('true', bool, True, True),
    ('false', bool, False, False),
    ('true', None, False, True),

    # Support containers
    (['a', 'b', 'c'], list, True, ['a', 'b', 'c']),
    (['a', 'b', 'c'], tuple, True, ('a', 'b', 'c')),
    (['a', 'b', 'c'], set, True, {'a', 'b', 'c'}),
    (['a', 'b', 'c'], abc.Sequence, True, ['a', 'b', 'c']),
    (['a', 'b', 'c'], abc.Collection, True, ['a', 'b', 'c']),

    # Support inner types for containers
    (['1', '2', '3'], list[int], True, [1, 2, 3]),
    (['false', '1', 'two', '3'], list[bool | int | str], True, [False, 1, 'two', 3]),
    (['1'], tuple[int], True, (1,)),
    (['false', '1', 'two', '3'], tuple[bool, int, str, int], True, (False, 1, 'two', 3)),
    (['1', '2', '3'], tuple[int, ...], True, (1, 2, 3)),
    (['1', '2', '3'], tuple[int], True, ValueError),
    (['1', '2', '3'], tuple[int, int], True, ValueError),

    # Support t.Union types, including Optionals
    ('test', t.Union[int, str], True, 'test'),
    (['test'], t.Union[int, list], True, ['test']),
    (['1'], t.Union[int, list], True, 1),
    ('1.0', t.Union[int, float], True, 1.0),
    ('1.0', t.Union[float, int], True, 1.0),
    ('1', t.Union[int, float], True, 1),
    ('1', t.Union[float, int], True, 1),
    ('1.0', int | float, True, 1.0),
    ('1', float | int, True, 1),
    ('1', bool | int, True, 1),
    (['test'], t.Optional[list], True, ['test']),
    (['1', '2', '3'], t.Optional[tuple[int, ...]], True, (1, 2, 3)),

    # Support literals
    ('1', t.Literal['2', 1], True, 1),
    ('1', t.Literal['2', '1', 1], True, '1'),
    ('get', t.Literal['get', 'set', 'has'], True, 'get'),
    ('del', t.Literal['get', 'set', 'has'], True, ValueError),
    ('false', t.Literal[True, False], True, False),
    ('1.1', t.Literal[1, 1.1, '1.1'], True, 1.1),

    # Support regex re.Pattern / typing.Pattern type
    ('^abc$', t.Pattern, True, re.compile('^abc$')),
    ('^abc$', re.Pattern, True, re.compile('^abc$')),

    # Support json values for dict/list types
    ('{"one": 2, "three": [4, 5]}', dict, True, {"one": 2, "three": [4, 5]}),
    ('{"one": 2, "three": [4, 5]}', t.Dict, True, {"one": 2, "three": [4, 5]}),
    (['["one", {"two": 3, "four": 5}]'], list, True, ["one", {"two": 3, "four": 5}]),
    (['["one", {"two": 3, "four": 5}]'], t.List, True, ["one", {"two": 3, "four": 5}]),

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
    ('/dev/null', t.TextIO, True, p.Path),
    ('/dev/null', io.TextIOWrapper, True, p.Path),
))
def test_cast_to_type(monkeypatch, value, type_hint, strict, expected_result):
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    if isinstance(expected_result, type) and issubclass(expected_result, Exception):
        with pytest.raises(expected_result, match='invalid literal'):
            cast_to_type(value, type_hint, strict=strict)
    elif isinstance(expected_result, type):
        result = cast_to_type(value, type_hint, strict=strict)
        assert type(result) in (p.Path, p.PosixPath)
    else:
        result = cast_to_type(value, type_hint, strict=strict)
        assert result == expected_result
        assert type(result) is type(expected_result)



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

        # file / stdin
        (t.TextIO, 'file / stdin'),
        (io.TextIOWrapper, 'file / stdin'),
        (t.List[t.TextIO], 'file(s) / stdin'),
        (tuple[io.TextIOWrapper], 'file(s) / stdin'),
        (list[io.TextIOBase], 'file(s) / stdin'),

        # Union types
        (t.Optional[int], 'int'),
        (t.Optional[t.List], 'list'),
        (list | dict, 'list | dict'),
        (t.Union[int, str], 'int | str'),
        (dict | int | t.List, 'dict | int | list'),
        (t.Union[t.Set, list, t.DefaultDict], 'set | list | defaultdict'),
))
def test_get_typehint_name(type_hint, name):
    assert get_typehint_name(type_hint) == name
