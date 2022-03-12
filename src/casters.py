import json
import re
import shlex
import sys

from collections.abc import Callable
from datetime import date, datetime, time
from inspect import Parameter
from re import Pattern
from typing import (Any, Dict, List, Optional, Tuple, Type,
    Union, get_args, get_origin)

if sys.version_info >= (3, 10):
    from types import UnionType
else:
    class UnionType: pass


def cast_to_type(value: str, type_hint: Optional[type] = None, *, strict: bool = False) -> Any:
    typecaster = get_typecaster(type_hint) or type_hint
    try:
        return typecaster(value)
    except (TypeError, ValueError) as e:
        if strict:
            raise e
        return value


def get_typecaster(type_hint: Any) -> Callable:
    typecast_map = {
        bool: bool_caster,
        dict: dict_caster,
        list: list_caster_factory(type_hint),
        tuple: tuple_caster_factory(type_hint),
        date: datetime_caster_factory(type_hint),
        datetime: datetime_caster_factory(type_hint),
        time: datetime_caster_factory(type_hint),
        Pattern: pattern_caster,
        Union: union_caster_factory(type_hint),
        UnionType: union_caster_factory(type_hint),
    }

    typecaster = (
        typecast_map.get(type_hint) or
        typecast_map.get(get_origin(type_hint)) or
        type_hint or # int, float, other classes with single-arg constructors
        unknown_caster # type_hint is Any or None
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


def list_caster_factory(type_hint: Type[List]) -> Callable:
    def list_caster(value: str) -> List:
        try:
            return json.loads(value)
        except json.decoder.JSONDecodeError:
            pass
        values = shlex.split(value)
        if member_type := get_args(type_hint):
            return [cast_to_type(v, member_type[0], strict=True) for v in values]
        return shlex.split(value)
    return list_caster


def tuple_caster_factory(type_hint: Type[Tuple]) -> Callable:
    def tuple_caster(value: str) -> Tuple:
        values = shlex.split(value)
        if member_types := get_args(type_hint):
            if len(values) != len(member_types):
                if Ellipsis not in member_types:
                    raise ValueError(f"invalid literal for {type_hint}: {value}")
                member_types = (member_types[0],) * len(values)
            return tuple(
                (cast_to_type(v, t, strict=True) for v, t in zip(values, member_types))
            )
        return tuple(values)
    return tuple_caster


def datetime_caster_factory(type_hint: Type[Union[date, datetime, time]]) -> Callable:
    def datetime_caster(value: str) -> Union[date, datetime, time]:
        if value.isdecimal() and not issubclass(type_hint, time):
            return type_hint.fromtimestamp(int(value))
        return type_hint.fromisoformat(value)
    return datetime_caster


def pattern_caster(value: str) -> Pattern:
    return re.compile(value)


def union_caster_factory(type_hint: Type[Union[Any]]) -> Callable:
    def union_caster(value: str) -> Any:
        for t in get_args(type_hint):
            try:
                return cast_to_type(value, t, strict=True)
            except (TypeError, ValueError):
                pass
        raise ValueError(f"invalid literal for {type_hint}: {value}")
    return union_caster


# Untyped coercion - allow casting to bools and ints only
def unknown_caster(value: str) -> Union[bool, int, str]:
    if value in ['true', 'false']:
        return value == 'true'
    if value.isdecimal():
        return int(value)
    return value


def typecast_factory(param: Parameter) -> Optional[Callable]:
    if param.annotation not in(param.empty, Any):
        type_hint = param.annotation
        strict = True
    elif param.default is not param.empty:
        type_hint = type(param.default)
        strict = False
    else:
        return None

    def typecaster(value: str) -> Any:
        return cast_to_type(value, type_hint, strict=strict)

    typecaster.__name__ = get_type_hint_name(type_hint)
    return typecaster


def get_type_hint_name(type_hint: Type) -> str:
    origin_type = get_origin(type_hint)
    if origin_type in (Union, UnionType):
        type_hint_names = []
        for t in get_args(type_hint):
            if t == type(None):
                continue
            name = get_type_hint_name(t)
            type_hint_names.append(name)
        return ' | '.join(type_hint_names)
    if origin_type is not None:
        return get_type_hint_name(origin_type)
    if hasattr(type_hint, '__name__'):
        return type_hint.__name__
    return str(type_hint)


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
