import json
import re
import shlex
import sys

from collections.abc import Callable
from datetime import date, datetime, time
from inspect import Parameter
from io import TextIOWrapper
from re import Pattern
from typing import (
    Any, Dict, List, Literal, Optional, TextIO, Tuple, Type,
    Union, get_args, get_origin
)

if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = object() # Dummy obj



def cast_to_type(value: str, typehint: Optional[type] = None, *, strict: bool = False) -> Any:
    typecaster = get_typecaster(typehint) or typehint
    try:
        return typecaster(value)
    except (TypeError, ValueError) as e:
        if strict:
            raise e
        return value


def get_typecaster(typehint: Any) -> Callable:
    typecast_map = {
        bool: bool_caster,
        dict: dict_caster,
        list: list_caster_factory(typehint),
        tuple: tuple_caster_factory(typehint),
        date: datetime_caster_factory(typehint),
        datetime: datetime_caster_factory(typehint),
        time: datetime_caster_factory(typehint),
        Pattern: pattern_caster,
        TextIO: textio_caster,
        TextIOWrapper: textio_caster,
        Union: union_caster_factory(typehint),
        UnionType: union_caster_factory(typehint),
        Literal: literal_caster_factory(typehint),
    }

    typecaster = (
        typecast_map.get(typehint) or
        typecast_map.get(get_origin(typehint)) or
        typehint or # int, float, other classes with single-arg constructors
        unknown_caster # typehint is Any or None
    )
    if callable(typecaster):
        return typecaster
    raise TypeError("invalid typecaster return value")


def bool_caster(value: str) -> bool:
    if value in ('true', 'false'):
        return value == 'true'
    raise ValueError(f"invalid literal for boolean: {value}")


def dict_caster(value: str) -> Dict:
    return json.loads(value)


def list_caster_factory(typehint: Type[List]) -> Callable:
    def list_caster(value: str) -> List:
        try:
            return json.loads(value)
        except json.decoder.JSONDecodeError:
            pass
        values = shlex.split(value)
        if member_type := get_args(typehint):
            return [cast_to_type(v, member_type[0], strict=True) for v in values]
        return shlex.split(value)
    return list_caster


def tuple_caster_factory(typehint: Type[Tuple]) -> Callable:
    def tuple_caster(value: str) -> Tuple:
        values = shlex.split(value)
        if member_types := get_args(typehint):
            if len(values) != len(member_types):
                if Ellipsis not in member_types:
                    raise ValueError(f"invalid literal for {typehint}: {value}")
                member_types = (member_types[0],) * len(values)
            return tuple(
                (cast_to_type(v, t, strict=True) for v, t in zip(values, member_types))
            )
        return tuple(values)
    return tuple_caster


def datetime_caster_factory(typehint: Type[Union[date, datetime, time]]) -> Callable:
    def datetime_caster(value: str) -> Union[date, datetime, time]:
        if value.isdecimal() and not issubclass(typehint, time):
            return typehint.fromtimestamp(int(value))
        return typehint.fromisoformat(value)
    return datetime_caster


def pattern_caster(value: str) -> Pattern:
    return re.compile(value)


# Return an open TextIO stream from a file or stdin
def textio_caster(value: str) -> TextIO:
    if not sys.stdin.isatty():
        return sys.stdin
    try:
        file = open(value)
        return file
    except FileNotFoundError as e:
        raise ValueError(f"no such file or directory: {value}") from e


def union_caster_factory(typehint: Type[Union[Any]]) -> Callable:
    def union_caster(value: str) -> Any:
        types = get_args(typehint)
        for t in types:
            try:
                typed_value = cast_to_type(value, t, strict=True)
            except (TypeError, ValueError):
                continue
            # prevent float matching ints if both in Union
            if set(types).issuperset({int, float}):
                if value != str(typed_value):
                    continue
            return typed_value
        raise ValueError(f"invalid literal for {typehint}: {value}")
    return union_caster


def literal_caster_factory(typehint: Type) -> Callable:
    def literal_caster(value: str) -> Any:
        choices = get_args(typehint)
        for c in choices:
            try:
                choice = cast_to_type(value, type(c), strict=True)
            except (TypeError, ValueError):
                continue
            if choice in choices:
                return choice
        raise ValueError(f"invalid literal for {typehint}: {value}")
    return literal_caster


# Untyped coercion - allow casting to bools and ints only
def unknown_caster(value: str) -> Union[bool, int, str]:
    if value in ['true', 'false']:
        return value == 'true'
    if value.isdecimal():
        return int(value)
    return value


def typecast_factory(param: Parameter, is_stdin: bool = False) -> Optional[Callable]:
    if param.annotation not in(param.empty, Any):
        typehint = param.annotation
        strict = True
    elif param.default is not param.empty:
        typehint = type(param.default)
        strict = False
    else:
        typehint = None

    # if implicit stdin, read the value inside closure so we can
    # call it multiple times without getting an empty buffer
    implicit_stdin = None
    if is_stdin and param.annotation not in (TextIO, TextIOWrapper):
        implicit_stdin = sys.stdin.read().rstrip()

    def typecaster(value: str) -> Any:
        if implicit_stdin is not None:
            value = implicit_stdin
        return cast_to_type(value, typehint, strict=strict)

    typecaster.__name__ = get_typehint_name(typehint)
    return typecaster


def get_typehint_name(typehint: Type) -> str:
    origin_type = get_origin(typehint)
    if origin_type in (Union, UnionType):
        typehint_names = []
        for t in get_args(typehint):
            if t == type(None):
                continue
            name = get_typehint_name(t)
            typehint_names.append(name)
        return ' | '.join(typehint_names)
    if origin_type is Literal:
        return str(get_args(typehint))[1:-1]
    if origin_type is not None:
        return get_typehint_name(origin_type)
    if typehint in (TextIO, TextIOWrapper):
        return 'file / stdin'
    if hasattr(typehint, '__name__'):
        return typehint.__name__
    return str(typehint)


def cast_to_shell(value: Any) -> Tuple[str, str]:
    typedef = ''
    if isinstance(value, bool):
        value = str(value).lower()
    elif isinstance(value, int):
        typedef = "-i"
        value = str(value)
    elif isarray(value):
        shell_array = [cast_to_shell(v)[0] for v in value]
        value = f'({" ".join(shell_array)})'
        typedef = '-a'
    elif isinstance(value, dict):
        shell_array = [f'[{cast_to_shell(k)[0]}]={cast_to_shell(v)[0]}' for k, v in value.items()]
        value = f'({" ".join(shell_array)})'
        typedef = '-A'
    elif value is None:
        value = ''
    else:
        value = f'"{value}"'
    return value, typedef


def isprimitive(obj: Any) -> bool:
    return isinstance(obj, (int, float, bool, str))


def iscollection(obj: Any) -> bool:
    return isinstance(obj, (tuple, list, set, dict))


def isarray(obj: Any) -> bool:
    return isinstance(obj, (tuple, list, set))
