import inspect

from collections.abc import Callable
from typing import Any, Iterator, Optional, Tuple, Union, _SpecialForm, get_args, get_origin



def uniontypes() -> Tuple:
    try:
        from types import UnionType # type: ignore[attr-defined] # Python < 3.10
        return (Union, UnionType)
    except ImportError:
        return (Union,)


def cast_from_shell(value: str, type_hint: Optional[type] = None, strict_typing: bool = False) -> Any:
    if type_hint not in (Any, inspect._empty, None):
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
    if type_hint == list:
        return value.split(' ')

    # Support typing module's generic collection types
    if origin_type := get_origin(type_hint):
        return cast_typed_from_shell(value, origin_type)

    # Handle Unions (including Optionals) by trying each type in order.
    if type_hint in uniontypes():
        for t in get_args(type_hint):
            try:
                return cast_typed_from_shell(value, t)
            except (TypeError, ValueError):
                pass
    # call all other type constructors directly
    return type_hint(value)


def cast_to_shell(value: Any) -> Tuple[str, str]:
    typedef = ""
    if isinstance(value, bool):
        value = str(value).lower()
    elif isinstance(value, int):
        typedef = "-i"
        value = str(value)
    elif isarray(value):
        shell_array = [cast_to_shell(v)[0] for v in value]
        value = f'({" ".join(shell_array)})'
        typedef = "-a"
    elif isinstance(value, dict):
        shell_array = [f'[{cast_to_shell(k)[0]}]={cast_to_shell(v)[0]}' for k, v in value.items()]
        value = f'({" ".join(shell_array)})'
        typedef = '-A'
    else:
        value = f'"{value}"'
    return value, typedef


def typecast_factory(param: inspect.Parameter) -> Optional[Callable]:
    if param.annotation != inspect._empty:
        type_hint = param.annotation
        strict_typing = True
    elif param.default != inspect._empty:
        type_hint = type(param.default)
        strict_typing = False
    else:
        return None

    def typecaster(value: str) -> Any:
        return cast_from_shell(value, type_hint, strict_typing)

    typecaster.__name__ = get_type_hint_name(type_hint)
    return typecaster


def get_type_hint_name(type_hint: type) -> str:
    if origin_type := get_origin(type_hint):
        type_hint = origin_type
    if hasattr(type_hint, '__name__'):
        return type_hint.__name__
    if get_origin(type_hint) in uniontypes():
        type_hint_names = []
        for t in get_args(type_hint):
            if t == type(None):
                continue
            name = get_type_hint_name(t)
            type_hint_names.append(name)
        return ' | '.join(type_hint_names)
    return str(type_hint)


def isprimitive(obj: Any) -> bool:
    return isinstance(obj, (int, float, bool, str))


def iscollection(obj: Any) -> bool:
    return isinstance(obj, (tuple, list, set, dict))


def isarray(obj: Any) -> bool:
    return isinstance(obj, (tuple, list, set))
