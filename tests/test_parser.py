from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple, Union

import pytest

from parser import FunctionSignatureParser

@pytest.mark.parametrize(
    'cmd_args, expected_result', (
    (['test', '1', 'true', 'a "b c" d'], ((), {'one': 'test', 'two': 1, 'three': True, 'four': ['a', 'b c', 'd']})),
    (['test', '1', '--three', 'a b c'],  ((), {'one': 'test', 'two': 1, 'three': True, 'four': ['a', 'b', 'c']})),
    (['--four', 'a b c', 'test', '1', '--no-three'], ((), {'one': 'test', 'two': 1, 'three': False, 'four': ['a', 'b', 'c']})),
    (['test', '1', '--no-three'], ((), {'one': 'test', 'two': 1, 'three': False})),
    (['test', '1', 'a b c'], SystemExit),
    (['test', '1', 'true', 'a "b c" d', '1'], SystemExit),
    (['test', '1', '--three', 'true', 'a "b c" d'], SystemExit),
    (['test', 'test', 'test', 'test'], SystemExit),
))
def test_parser(typed_fn, cmd_args, expected_result, monkeypatch):
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    parser = FunctionSignatureParser(typed_fn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'cmd_args, expected_result', (
    (['test', '1', 'true', '--four', 'a "b c" d'], (('test', 1), {'three': True, 'four': ['a', 'b c', 'd']})),
    (['test', '1', '--three', '--four', 'a b c'],  (('test', 1), {'three': True, 'four': ['a', 'b', 'c']})),
    (['--four', 'a b c', 'test', '1', '--no-three'], (('test', 1), {'three': False, 'four': ['a', 'b', 'c']})),
    (['test', '1', '--no-three'], (('test', 1), {'three': False})),
    (['test', '1'], (('test', 1), {})),
    (['test', '1', 'a b c'], SystemExit),
    (['test', '1', 'true', 'a "b c" d', '1'], SystemExit),
    (['test', '1', '--three', 'true', 'a "b c" d'], SystemExit),
    (['test', 'test', 'test', 'test'], SystemExit),
))
def test_parser_pos_kw(pos_kw_fn, cmd_args, expected_result, monkeypatch):
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    parser = FunctionSignatureParser(pos_kw_fn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'stdin_arg, cmd_args, expected_result', (
    ('test', ['1', 'true', 'a "b c" d'], ((), {'one': 'test', 'two': 1, 'three': True, 'four': ['a', 'b c', 'd']})),
    ('test', ['1', '--three', 'a b c'], ((), {'one': 'test', 'two': 1, 'three': True, 'four': ['a', 'b', 'c']})),

))
def test_parser_implicit_stdin_str(typed_fn, stdin_arg, cmd_args, expected_result, monkeypatch):
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('sys.stdin.read', lambda: stdin_arg)
    parser = FunctionSignatureParser(typed_fn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'stdin_arg, cmd_args, expected_result', (
    ('1', ['test', 'true', 'a "b c" d'], ((), {'one': 1, 'two': 'test', 'three': True, 'four': ['a', 'b c', 'd']})),
    ('1', ['test', '--three', 'a b c'], ((), {'one': 1, 'two': 'test', 'three': True, 'four': ['a', 'b', 'c']})),

))
def test_parser_implicit_stdin_int(stdin_implicit_int_fn, stdin_arg, cmd_args, expected_result, monkeypatch):
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('sys.stdin.read', lambda: stdin_arg)
    parser = FunctionSignatureParser(stdin_implicit_int_fn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)


@pytest.mark.parametrize(
    'stdin_arg, cmd_args, expected_result', (
    ('test', ['1', 'true', 'a "b c" d'], (1, 'test', True, ['a', 'b c', 'd'])),
    ('test', ['1', '--three', 'a b c'], (1, 'test', True, ['a', 'b', 'c'])),
    ('test', ['--one', '1', 'true', 'a "b c" d'], (1, 'test', True, ['a', 'b c', 'd'])),
    ('test', ['--no-three', '--one', '1', 'a "b c" d'], (1, 'test', False, ['a', 'b c', 'd'])),
    ('test', ['--no-three', '--one', '1'], (1, 'test', False, None)),

))
def test_parser_explicit_stdin_int(stdin_explicit_fn, stdin_arg, cmd_args, expected_result, monkeypatch):
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('sys.stdin.read', lambda: stdin_arg)
    parser = FunctionSignatureParser(stdin_explicit_fn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        args, kwargs = parser.parse_fn_args(cmd_args)
        assert expected_result == stdin_explicit_fn(*args, **kwargs)


@pytest.mark.parametrize(
    'stdin_arg, cmd_args, expected_result', (
    ('test', ['1', 'true', '--four', 'a "b c" d'], (('test', 1), {'three': True, 'four': ['a', 'b c', 'd']})),
    ('test', ['1', '--three', '--four', 'a b c'], (('test', 1), {'three': True, 'four': ['a', 'b', 'c']})),

))
def test_parser_pos_kw_implicit_stdin_str(pos_kw_fn, stdin_arg, cmd_args, expected_result, monkeypatch):
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('sys.stdin.read', lambda: stdin_arg)
    parser = FunctionSignatureParser(pos_kw_fn)
    if isinstance(expected_result, type) and issubclass(expected_result, BaseException):
        with pytest.raises(expected_result):
            parser.parse_fn_args(cmd_args)
    else:
        assert expected_result == parser.parse_fn_args(cmd_args)
