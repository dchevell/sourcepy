import inspect
import re
import sys

from pathlib import Path
from re import Pattern
from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple, Union

import pytest

from data_funcdefs import typed_fn
from data_typedefs import type_hints

src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from converters import cast_from_shell, get_type_hint_name



@pytest.mark.parametrize(
    'value, type_hint, strict_typing, expected_type, expected_value', (
    ('1', int, True, int, 1),
    ('1.1', float, True, float, 1.1),
    ('1', None, False, int, 1),
    ('true', bool, True, bool, True),
    ('false', bool, False, bool, False),
    ('true', None, False, bool, True),
    ('one two three', list, True, list, ['one', 'two', 'three']),
    ('one two three', List, True, list, ['one', 'two', 'three']),
    ('one two three', tuple, True, tuple, ('one', 'two', 'three')),
    ('one two three', Tuple, True, tuple, ('one', 'two', 'three')),

    # Support Union types, including Optionals
    ('test', Union[int, str], True, str, 'test'),
    ('test', Union[int, list], True, list, ['test']),
    ('1', bool | int, True, int, 1),
    ('test', Optional[list], True, list, ['test']),

    # Support regex re.Pattern type
    ('^abc$', Pattern, True, Pattern, re.compile('^abc$')),

    # Support json values for dict/list types
    ('{"one": 2, "three": [4, 5]}', dict, True, dict, {"one": 2, "three": [4, 5]}),
    ('{"one": 2, "three": [4, 5]}', Dict, True, dict, {"one": 2, "three": [4, 5]}),
    ('["one", {"two": 3, "four": 5}]', list, True, list, ["one", {"two": 3, "four": 5}]),
    ('["one", {"two": 3, "four": 5}]', List, True, list, ["one", {"two": 3, "four": 5}]),

))
def test_cast_from_shell(value, type_hint, strict_typing, expected_type, expected_value):
    result = cast_from_shell(value, type_hint, strict_typing)
    assert type(result) == expected_type
    assert result == expected_value


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
