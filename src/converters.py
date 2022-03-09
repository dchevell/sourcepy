import json
import inspect
import re
import shlex

from collections.abc import Callable
from datetime import date, datetime, time
from inspect import Parameter
from re import Pattern
from typing import (Any, Callable, Dict, List, Optional, Tuple,
    Union, get_args, get_origin)



def uniontypes() -> Tuple:
    try:
        from types import UnionType # type: ignore[attr-defined] # Python < 3.10
        return (Union, UnionType)
    except ImportError:
        return (Union,)


def cast_to_type(value: str, type_hint: Optional[type] = None, strict: bool = False) -> Any:
    if origin_type := get_origin(type_hint):
        return generics_caster(value, type_hint)
    typecaster = get_typecaster(type_hint) or type_hint
    if typecaster in (Any, Parameter.empty, None):
        typecaster = unknown_caster
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
        list: list_caster,
        tuple: tuple_caster,
        date: datetime_caster_factory(type_hint),
        datetime: datetime_caster_factory(type_hint),
        time: datetime_caster_factory(type_hint),
        Pattern: pattern_caster,
    }
    return typecast_map.get(type_hint)


def bool_caster(value: str) -> bool:
    if value in ('true', 'false'):
        return value == 'true'
    raise ValueError(f"invalid literal for boolean: {value}")


def dict_caster(value: str) -> Dict:
    return json.loads(value)


def list_caster(value: str) -> List:
    try:
        return json.loads(value)
    except json.decoder.JSONDecodeError:
        return shlex.split(value)


def tuple_caster(value: str) -> Tuple:
    return tuple(shlex.split(value))


def datetime_caster_factory(type_hint: Union[date, datetime, time]) -> Callable:
    def datetime_caster(value: str) -> type_hint:
        if value.isdecimal() and type_hint != time:
            return type_hint.fromtimestamp(int(value))
        return type_hint.fromisoformat(value)
    return datetime_caster


def pattern_caster(value: str) -> Pattern:
    return re.compile(value)


# Untyped coercion - allow casting to bools and ints only
def unknown_caster(value: str) -> Union[bool, int, str]:
    if value in ['true', 'false']:
        return value == 'true'
    if value.isdecimal():
        return int(value)
    return value


def cast_from_shell(value: str, type_hint: Optional[type] = None, strict_typing: bool = False) -> Any:
    if type_hint not in (Any, Parameter.empty, None):
        try:
            return cast_typed_from_shell(value, type_hint)
        except (TypeError, ValueError) as e:
            if strict_typing:
                raise e
    if value in ['true', 'false']:
        return value == 'true'
    if value.isdecimal():
        return int(value)
    return value


def cast_typed_from_shell(value: str, type_hint: Any) -> Any:
    # We can't just call `bool` on a string value, it will always return true
    if type_hint == bool:
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        raise ValueError(f"invalid literal for boolean: {value}")
    if type_hint in (dict, list):
        try:
            return json.loads(value)
        except json.decoder.JSONDecodeError:
            pass
    if type_hint in (list, tuple):
        return type_hint(shlex.split(value))
    if type_hint in (date, datetime, time):
        if value.isdecimal() and type_hint != time:
            return type_hint.fromtimestamp(int(value))
        return type_hint.fromisoformat(value)
    if type_hint == Pattern:
        return re.compile(value)

    origin_type = get_origin(type_hint)

    # Handle Unions (including Optionals) by trying each type in order.
    if origin_type in uniontypes():
        for t in get_args(type_hint):
            try:
                return cast_typed_from_shell(value, t)
            except (TypeError, ValueError):
                pass

    member_type_hint = get_args(type_hint)

    # Support typing module's generic collection types
    if origin_type is not None and member_type_hint == ():
        return cast_typed_from_shell(value, origin_type)

    # Handle containers with specified member types
    if origin_type == list:
        member_type_hint = get_args(type_hint)[0]
        return [cast_typed_from_shell(v, member_type_hint) for v in shlex.split(value)]

    # call all other type constructors directly
    return type_hint(value)


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


def typecast_factory(param: inspect.Parameter) -> Optional[Callable]:
    if param.annotation not in(param.empty, Any):
        type_hint = param.annotation
        strict_typing = True
    elif param.default is not param.empty:
        type_hint = type(param.default)
        strict_typing = False
    else:
        return None

    def typecaster(value: str) -> Any:
        return cast_from_shell(value, type_hint, strict_typing)

    typecaster.__name__ = get_type_hint_name(type_hint)
    return typecaster


def get_type_hint_name(type_hint: type) -> str:
    origin_type = get_origin(type_hint)
    if origin_type in uniontypes():
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


def isprimitive(obj: Any) -> bool:
    return isinstance(obj, (int, float, bool, str))


def iscollection(obj: Any) -> bool:
    return isinstance(obj, (tuple, list, set, dict))


def isarray(obj: Any) -> bool:
    return isinstance(obj, (tuple, list, set))
