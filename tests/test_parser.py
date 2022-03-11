from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple, Union

import pytest

from parser import FunctionSignatureParser

@pytest.mark.parametrize(
    'in_args, expected_result', (
    (['test', '1', 'true', 'a "b c" d'], (('test', 1, True, ['a', 'b c', 'd']), {})),
    (['test', '1', '--three', 'a b c'], (('test', 1, ['a', 'b', 'c']), {'three': True})),
    (['--four', 'a b c', 'test', '1', '--no-three'], (('test', 1), {'three': False, 'four': ['a', 'b', 'c']})),
    (['test', '1', 'true', 'a "b c" d', '1'], SystemExit),
    (['test', '1', '--three', 'true', 'a "b c" d'], SystemExit),
    (['test', 'test', 'test', 'test'], SystemExit),
))
def test_function_signature_parser(typed_fn, in_args, expected_result):
    parser = FunctionSignatureParser(typed_fn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(in_args)
    else:
        assert expected_result == parser.parse_fn_args(in_args)
