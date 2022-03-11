import re

from datetime import date, datetime, time
from re import Pattern
from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple, Union, get_args

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
    ('one two three', List, True, ['one', 'two', 'three']),
    ('one two three', tuple, True, ('one', 'two', 'three')),
    ('one two three', Tuple, True, ('one', 'two', 'three')),
    ('one "two three four" five', list, True, ['one', 'two three four', 'five']),
    ("one 'two three four' five", List, True, ['one', 'two three four', 'five']),

    # Support inner types for containers
    ('1 2 3', list[int], True, [1, 2, 3]),
    ('false 1 two 3', list[bool | int | str], True, [False, 1, 'two', 3]),
    ('1', tuple[int], True, (1,)),
    ('false 1 two 3', tuple[bool, int, str, int], True, (False, 1, 'two', 3)),
    ('1 2 3', tuple[int, ...], True, (1, 2, 3)),
    ('1 2 3', tuple[int], True, ValueError),
    ('1 2 3', tuple[int, int], True, ValueError),


    # Support Union types, including Optionals
    ('test', Union[int, str], True, 'test'),
    ('test', Union[int, list], True, ['test']),
    ('1', bool | int, True, 1),
    ('test', Optional[list], True, ['test']),
    ('1 2 3', Optional[tuple[int, ...]], True, (1, 2, 3)),

    # Support native datetime types: date, datetime, time
    ('1646803515', date, True, date.fromtimestamp(1646803515)),
    ('2022-03-09', date, True, date.fromisoformat('2022-03-09')),
    ('1646803515', None, False, 1646803515),
    ('2022-03-09', None, False, '2022-03-09'),
    ('1646803515', datetime, True, datetime.fromtimestamp(1646803515)),
    ('2022-03-09T00:05:23', datetime, True, datetime.fromisoformat('2022-03-09T00:05:23')),
    ('1646803515', None, False, 1646803515),
    ('2022-03-09T00:05:23', None, False, '2022-03-09T00:05:23'),
    ('04:23:01.000384', time, True, time.fromisoformat('04:23:01.000384')),
    ('04:23:01.000384', None, False, '04:23:01.000384'),

    # Support regex re.Pattern type
    ('^abc$', Pattern, True, re.compile('^abc$')),

    # Support json values for dict/list types
    ('{"one": 2, "three": [4, 5]}', dict, True, {"one": 2, "three": [4, 5]}),
    ('{"one": 2, "three": [4, 5]}', Dict, True, {"one": 2, "three": [4, 5]}),
    ('["one", {"two": 3, "four": 5}]', list, True, ["one", {"two": 3, "four": 5}]),
    ('["one", {"two": 3, "four": 5}]', List, True, ["one", {"two": 3, "four": 5}]),

))
def test_cast_from_shell(value, type_hint, strict, expected_result):
    if isinstance(expected_result, type) and issubclass(expected_result, Exception):
        with pytest.raises(expected_result, match='invalid literal'):
            cast_to_type(value, type_hint, strict=strict)
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
        (Dict,  'dict'),        (List,  'list'),
        (Set,   'set'),         (Tuple, 'tuple'),
        (DefaultDict, 'defaultdict'),

        # Union types
        (Optional[int], 'int'),
        (Optional[List], 'list'),
        (list | dict, 'list | dict'),
        (Union[int, str], 'int | str'),
        (dict | int | List, 'dict | int | list'),
        (Union[Set, list, DefaultDict], 'set | list | defaultdict'),
))
def test_get_type_hint_name(type_hint, name):
    assert get_type_hint_name(type_hint) == name
