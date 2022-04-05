import datetime as dt
import decimal as d
import enum
import io
import pathlib as p
import re
import typing as t
from collections import abc

import pytest

from casters import CastingError, cast_to_type, get_typehint_name



class Colour(enum.Enum):
    RED = 'red'
    GREEN = 'green'
    BLUE = 'blue'


@pytest.mark.parametrize(
    'value, typehint, strict, expected_result', (
    ('1', int, True, 1),
    ('1.0', float, True, 1.0),
    ('1', None, False, 1),
    ('true', bool, True, True),
    ('false', bool, False, False),
    ('true', None, False, True),

    # Support containers
    (['a', 'rb', 'c'], list, True, ['a', 'rb', 'c']),
    (['a', 'rb', 'c'], tuple, True, ('a', 'rb', 'c')),
    (['a', 'rb', 'c'], set, True, {'a', 'rb', 'c'}),
    (['a', 'rb', 'c'], abc.Sequence, True, ['a', 'rb', 'c']),
    (['a', 'rb', 'c'], abc.Collection, True, ['a', 'rb', 'c']),

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
    ('false', t.Literal[True, False], True, False),
    ('1.1', t.Literal[1, 1.1, '1.1'], True, 1.1),
    ('del', t.Optional[t.Literal['get', 'set', 'has']], True, CastingError),

    # Support enums
    ('RED', Colour, True, Colour.RED),
    ('YELLOW', Colour, True, CastingError),

    # Support regex re.Pattern / typing.Pattern type
    ('^abc$', t.Pattern, True, re.compile('^abc$')),
    ('^abc$', re.Pattern, True, re.compile('^abc$')),
    ('^abc$', t.Pattern[str], True, re.compile('^abc$')),
    ('^abc$', re.Pattern[str], True, re.compile('^abc$')),
    ('^abc$', t.Pattern[bytes], True, re.compile(b'^abc$')),
    ('^abc$', re.Pattern[bytes], True, re.compile(b'^abc$')),

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
    ('/dev/null', t.TextIO, True, io.TextIOBase),
    ('/dev/null', t.BinaryIO, True, io.BufferedIOBase),

    # Support single-arg types Sourcepy does not know about
    ('1.1', d.Decimal, True, d.Decimal('1.1')),
    ('/dev/null', p.Path, True, p.Path('/dev/null')),
))
def test_cast_to_type(monkeypatch, value, typehint, strict, expected_result):
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    if isinstance(expected_result, type) and issubclass(expected_result, Exception):
        with pytest.raises(expected_result, match='invalid'):
            cast_to_type(value, typehint, strict=strict)
    elif isinstance(expected_result, type):
        result = cast_to_type(value, typehint, strict=strict)
        assert issubclass(type(result), expected_result)
    else:
        result = cast_to_type(value, typehint, strict=strict)
        assert result == expected_result
        assert type(result) is type(expected_result)


@pytest.mark.parametrize(
    'value, typehint, expected_result', (
    # IO stream from stdin
    (io.BytesIO(b'a b'),    t.BinaryIO,         b'a b'),
    (io.BytesIO(b'a b'),    t.TextIO,           'a b'),
    (io.BytesIO(b'a b'),    t.IO[bytes],        b'a b'),
    (io.BytesIO(b'a b'),    t.IO[str],          'a b'),
    (io.BytesIO(b'a b'),    io.BufferedIOBase,  b'a b'),
    (io.BytesIO(b'a b'),    io.TextIOBase,      'a b'),
    (io.BytesIO(b'a b'),    io.BytesIO,         b'a b'),
    (io.BytesIO(b'a b'),    io.TextIOWrapper,   'a b'),
))
def test_cast_to_type_stdin(monkeypatch, value, typehint, expected_result):
    monkeypatch.setattr('sys.stdin', io.TextIOWrapper(value))
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)

    result = cast_to_type(value, typehint, strict=True)
    print('@@@', result)
    result = result.read()

    assert result == expected_result
    assert type(result) is type(expected_result)


@pytest.mark.parametrize(
    'typehint, name', (
        # Native types
        (int,   'int'),         (bool,  'bool'),
        (float, 'float'),       (str,   'str'),
        (tuple, '[...]'),       (list,  '[...]'),
        (set,   '[...]'),         (dict,  'dict'),

        # typing module built in generics
        (t.Dict,  'dict'),        (t.List,  '[...]'),
        (t.Set,   '[...]'),         (t.Tuple, '[...]'),
        (t.DefaultDict, 'defaultdict'),

        # file / stdin
        (t.BinaryIO, 'file/stdin'),
        (t.TextIO, 'file/stdin'),
        (t.IO[bytes], 'file/stdin'),
        (t.IO[str], 'file/stdin'),
        (io.BufferedIOBase, 'file/stdin'),
        (io.TextIOBase, 'file/stdin'),
        (io.BytesIO, 'file/stdin'),
        (io.TextIOWrapper, 'file/stdin'),

        # Union types
        (t.Optional[int],                       'int'),
        (t.Optional[t.List],                    '[...]'),
        (list | dict,                           ['[...]', 'dict']),
        (t.Union[int, str],                     ['int', 'str']),
        (dict | int | t.List,                   ['dict', 'int', '[...]']),
        (t.Union[t.Set, list, t.DefaultDict],   ['[...]', 'defaultdict']),

        # Inner types for containers
        (t.List[int], '[int ...]'),
        (t.Tuple[int, int], '[int, int]'),
        (t.List[int], '[int ...]'),
        (t.Tuple[int, int], '[int, int]'),
        (t.List[t.TextIO], '[file/stdin ...]'),
        (tuple[io.TextIOWrapper], '[file/stdin]'),
        (list[io.BytesIO], '[file/stdin ...]'),
        (tuple[t.IO[bytes], t.IO[str]], '[file/stdin, file/stdin]'),

        # Literals
        (t.Literal['get', 'set', 'del'], "{'get', 'set', 'del'}"),
        (t.Literal[0, 1, True, False], '{0, 1, true, false}'),

        # Enums
        (Colour, "{'RED', 'GREEN', 'BLUE'}"),

))
def test_get_typehint_name(typehint, name):
    if isinstance(name, list):
        assert get_typehint_name(typehint) == ' | '.join(set(name))
    else:
        assert get_typehint_name(typehint) == name
