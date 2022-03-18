from io import BytesIO, TextIOWrapper
from typing import Any, DefaultDict, Dict, List, Optional, Set, TextIO, Tuple, Union

import pytest

from parsers import FunctionParameterParser



@pytest.mark.parametrize(
    'cmd_args, expected_result', (
    (['test', '1', 'true', 'a "b c" d'], ((), {'one': 'test', 'two': 1, 'three': True, 'four': ['a', 'b c', 'd']}
        )
    ),
    (['test', '1', '--three', 'a b c'],  ((), {'one': 'test', 'two': 1, 'three': True, 'four': ['a', 'b', 'c']}
        )
    ),
    (['test', '1', '--no-three'], ((), {'one': 'test', 'two': 1, 'three': False}
        )
    ),
    (['test', '1', 'a b c'], SystemExit),
    (['test', 'test', 'test', 'test'], SystemExit),
))
def test_parser_typed(cmd_args, expected_result, monkeypatch):

    def myfn(one: str, two: int, three: bool = False, four: Optional[list] = None):
        return one, two, three, four

    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    parser = FunctionParameterParser(myfn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'cmd_args, expected_result', (
    (['test', '1', 'true', '--four', 'a "b c" d'], (('test', 1), {'three': True, 'four': ['a', 'b c', 'd']}
        )
    ),
    (['test', '1', '--three', '--four', 'a b c'],  (('test', 1), {'three': True, 'four': ['a', 'b', 'c']}
        )
    ),
    (['test', '1', '--no-three'], (('test', 1), {'three': False}
        )
    ),
    (['test', '1'], (('test', 1), {}
        )
    ),
    (['test', '1', 'a b c'], SystemExit),
    (['test', '1', 'true', 'a "b c" d', '1'], SystemExit),
    (['test', '1', '--three', 'true', 'a "b c" d'], SystemExit),
    (['test', 'test', 'test', 'test'], SystemExit),
    (['--four', 'a b c', 'test', '1', '--no-three'], SystemExit),
))
def test_parser_param_kinds(cmd_args, expected_result, monkeypatch):

    def myfn(one: str, two: int, /, three: bool = False, *, four: Optional[list] = None):
        return one, two, three, four

    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    parser = FunctionParameterParser(myfn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'stdin_arg, cmd_args, expected_result', (
    (TextIOWrapper(BytesIO(b'test')), ['1', 'true', 'a "b c" d'], ((), {'one': 'test', 'two': 1, 'three': True, 'four': ['a', 'b c', 'd']}
        )
    ),
    (TextIOWrapper(BytesIO(b'test')), ['1', '--three', 'a b c'], ((), {'one': 'test', 'two': 1, 'three': True, 'four': ['a', 'b', 'c']}
        )
    ),

))
def test_parser_implicit_stdin_str(stdin_arg, cmd_args, expected_result, monkeypatch):

    def myfn(one: str, two: int, three: bool = False, four: Optional[list] = None):
        return one, two, three, four

    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('sys.stdin.read', stdin_arg.read)
    parser = FunctionParameterParser(myfn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'stdin_arg, cmd_args, expected_result', (
    (TextIOWrapper(BytesIO(b'1')), ['test', 'true', 'a "b c" d'], ((), {'one': 1, 'two': 'test', 'three': True, 'four': ['a', 'b c', 'd']}
        )
    ),
    (TextIOWrapper(BytesIO(b'1')), ['test', '--three', 'a b c'], ((), {'one': 1, 'two': 'test', 'three': True, 'four': ['a', 'b', 'c']}
        )
    ),

))
def test_parser_implicit_stdin_int(stdin_arg, cmd_args, expected_result, monkeypatch):

    def myfn(one: int, two: str, three: bool, four: list):
        return one, two, three, four

    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('sys.stdin.read', stdin_arg.read)
    parser = FunctionParameterParser(myfn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'stdin_arg, cmd_args, expected_result', (
    (TextIOWrapper(BytesIO(b'test')), ['1', 'true', 'a "b c" d'], (1, 'test', True, ['a', 'b c', 'd'])),
    (TextIOWrapper(BytesIO(b'test')), ['1', '--three', 'a b c'], (1, 'test', True, ['a', 'b', 'c'])),
    (TextIOWrapper(BytesIO(b'test')), ['--one', '1', 'true', 'a "b c" d'], (1, 'test', True, ['a', 'b c', 'd'])),
    (TextIOWrapper(BytesIO(b'test')), ['--no-three', '--one', '1', 'a "b c" d'], (1, 'test', False, ['a', 'b c', 'd'])),
    (TextIOWrapper(BytesIO(b'test')), ['--no-three', '--one', '1'], (1, 'test', False, None)),

))
def test_parser_explicit_stdin_int(stdin_arg, cmd_args, expected_result, monkeypatch):

    def myfn(one: int, two: TextIO, three: bool, four: Optional[list] = None):
        return one, two.read().rstrip(), three, four

    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('sys.stdin.read', stdin_arg.read)
    parser = FunctionParameterParser(myfn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        args, kwargs = parser.parse_fn_args(cmd_args)
        assert expected_result == myfn(*args, **kwargs)


@pytest.mark.parametrize(
    'stdin_arg, cmd_args, expected_result', (
    (TextIOWrapper(BytesIO(b'test')), ['1', 'true', '--four', 'a "b c" d'], (('test', 1), {'three': True, 'four': ['a', 'b c', 'd']}
        )
    ),
    (TextIOWrapper(BytesIO(b'test')), ['1', '--three', '--four', 'a b c'], (('test', 1), {'three': True, 'four': ['a', 'b', 'c']}
        )
    ),

))
def test_parser_pos_kw_implicit_stdin_str(stdin_arg, cmd_args, expected_result, monkeypatch):

    def myfn(one: str, two: int, /, three: bool = False, *, four: Optional[list] = None):
        return one, two, three, four

    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('sys.stdin.read', stdin_arg.read)
    parser = FunctionParameterParser(myfn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'cmd_args, expected_result', (
    (
        ['a', '--two', '1'], (
            (['a'],),
            {'two': True, 'three': [1]}
        )
    ),
    (
        ['a', 'b', '--two', '1', '2'], (
            (['a', 'b'],),
            {'two': True, 'three': [1,2]}
        )
    ),
    (
        ['a', '--no-two', '1', '2', '3'], (
            (['a'],),
            {'two': False, 'three': [1, 2, 3]}
        )
    ),
    (
        ['a', 'b', '--two', '--three', '1', '2'], (
            (['a', 'b'],),
            {'two': True, 'three': [1, 2]}
        )
    ),
    (
        ['--three', '1', '2', '--two', 'a', 'b'], (
            (['a', 'b'],),
            {'two': True, 'three': [1,2]}
        )
    ),
))
def test_parser_nargs_list(cmd_args, expected_result, monkeypatch):

    def myfn(one: list, /, two: bool, three: Optional[List[int]]):
        return one, two, three

    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    parser = FunctionParameterParser(myfn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'stdin_arg, cmd_args, expected_result', (
    (
        (TextIOWrapper(BytesIO(b'a b'))),
        ['test'],
        ('test', 'a b'),
    ),

))
def test_parser_nargs_list(stdin_arg, cmd_args, expected_result, monkeypatch):

    def myfn(one: str, two: List[TextIO]):
        data = []
        for f in two:
            for line in f:
                data.append(line)
        return one, ' '.join(data)

    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('sys.stdin', stdin_arg)
    parser = FunctionParameterParser(myfn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        args, kwargs = parser.parse_fn_args(cmd_args)
        assert expected_result == myfn(*args, **kwargs)