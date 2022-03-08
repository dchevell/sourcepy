import inspect
import sys

from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple, Union

import pytest

from data_funcdefs import typed_fn
from data_typedefs import type_hints

src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from converters import get_type_hint_name, typecast_factory



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


@pytest.mark.parametrize(
    'fn, test_values, expected_types', (
        (typed_fn,  {'one': 'true', 'two': 'true', 'three': '4', 'four':  '4'},
                    {'one': bool,   'two': str,  'three': str,  'four': int}),
        (typed_fn,  {'one': 'false', 'two': 'cheese', 'three': 'false', 'four':  '4'},
                    {'one': bool,   'two': str,  'three': str,  'four': int}),
))
def test_typecast_factory(fn, test_values, expected_types):
    param_sig = inspect.signature(typed_fn).parameters
    for name, param in param_sig.items():
        value = test_values[name]
        typecast = typecast_factory(param)
        if typecast is not None:
            value = typecast(test_values[name])
        assert type(value) == expected_types[name]
