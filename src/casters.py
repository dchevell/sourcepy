import json
import re
import sys

from collections.abc import Callable, Collection
from datetime import date, datetime, time
from io import TextIOWrapper
from pathlib import Path
from re import Pattern
from typing import (
    Any, Dict, List, Literal, Optional, TextIO, Tuple, Type, Union,
    get_args, get_origin
)
from typing import _Final as TypingBase # type: ignore[attr-defined]

if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = object() # Dummy obj



TypeHint = Union[Type, TypingBase]
TypeHintCollection = Union[TypeHint, Collection[TypeHint]]


def cast_to_type(value: Union[str, List], typehint: Optional[TypeHint] = None, *,
                 strict: bool = False) -> Any:
    typecaster = get_caster(typehint)
    try:
        typed_value = typecaster(value)
        if typed_value is None:
            raise ValueError(f"invalid literal for {typehint}: {value}")
        return typed_value
    except (TypeError, ValueError) as e:
        if strict:
            raise e
        return value


def get_caster(typehint: TypeHint) -> Callable:
    """Returns a conversion class most appropriate for the
    supplied type hint. Potential matches are checked in
    order from most to least specific to account for
    overlapping types (e.g. ABCs).
    """
    if typehint in (Any, None):
        return untyped_caster
    origin = get_origin(typehint)
    typecasters: Dict[TypeHintCollection, Callable] = {
        (Union, UnionType):        union_caster(typehint),
        (str, bytes):              generic_caster(typehint),
        (dict,):                   dict_caster,
        (bool,):                   bool_caster,
        (Collection,):             collection_caster(typehint),
        (date, time):              datetime_caster(typehint),
        (Pattern,):                pattern_caster,
        (TextIO, TextIOWrapper):   textio_caster,
        (Literal,):                literal_caster(typehint),
    }
    for cls, caster in typecasters.items():
        if typehint in cls:
            return caster
        if origin in cls and origin is not None:
            return caster
        if istypesubclass(typehint, cls):
            return caster
    return generic_caster(typehint)


def union_caster(typehint: TypeHint) -> Callable:
    def caster(value: Union[str, List]) -> Any:
        type_args = get_args(typehint)
        for _type in type_args:
            try:
                if (isinstance(value, list)
                    and not istypesubclass(_type, Collection)
                    and len(value) == 1):
                    typed_value = cast_to_type(value[0], _type, strict=True)
                else:
                    typed_value = cast_to_type(value, _type, strict=True)
            except (TypeError, ValueError):
                continue
            # prevent float matching ints if both in Union
            if set(type_args).issuperset({int, float}):
                if value != str(typed_value):
                    continue
            return typed_value
    return caster


def generic_caster(typehint: TypeHint) -> Callable:
    def caster(value: str) -> Any:
        return typehint(value)
    return caster


def dict_caster(value: str) -> Optional[dict]:
    try:
        json_value = json.loads(value)
        if isinstance(json_value, dict):
            return json_value
    except json.decoder.JSONDecodeError:
        pass
    return None


def bool_caster(value: str) -> Optional[bool]:
    if value in ('true', 'false'):
        return value == 'true'
    return None


def collection_caster(typehint: TypeHint) -> Callable:
    def caster(value: Union[str, List]) -> Optional[Collection]:
        base_type = get_origin(typehint) or typehint
        if isinstance(value, str):
            value = [value]
        if base_type is list and len(value) == 1:
            try:
                json_value = json.loads(*value)
                if isinstance(json_value, list):
                    return json_value
            except json.decoder.JSONDecodeError:
                pass
        if member_types := get_args(typehint):
            if not issubclass(base_type, tuple) or Ellipsis in member_types:
                member_types = (member_types[0],) * len(value)
            elif issubclass(base_type, tuple) and len(member_types) != len(value):
                return None
            member_values = []
            for m_value, m_type in zip(value, member_types):
                typed_value = cast_to_type(m_value, m_type, strict=True)
                member_values.append(typed_value)
            return base_type(member_values)
        return base_type(value)
    return caster


def datetime_caster(typehint: TypeHint) -> Callable:
    def caster(value: str) -> Union[date, datetime, time]:
        if value.isdecimal() and istypesubclass(typehint, date):
            return typehint.fromtimestamp(int(value))
        return typehint.fromisoformat(value)
    return caster


def pattern_caster(value: str) -> Any:
    return re.compile(value)


def textio_caster(value: str) -> Any:
    if not sys.stdin.isatty():
        return sys.stdin
    file = Path(value)
    if not file.exists():
        raise ValueError(f"no such file or directory: {value}")
    return file


def literal_caster(typehint: TypeHint) -> Callable:
    def caster(value: str) -> Any:
        type_literals = get_args(typehint)
        for lit in type_literals:
            try:
                typed_value = cast_to_type(value, type(lit), strict=True)
            except (TypeError, ValueError):
                continue
            if typed_value in type_literals:
                return typed_value
        return None
    return caster

def untyped_caster(value: str) -> Any:
    if value in ['true', 'false']:
        return value == 'true'
    if value.isdecimal():
        return int(value)
    return value


def unwrap_typehint(typehint: Any) -> List[Type]:
    origin = get_origin(typehint)
    if origin is None:
        return [typehint]
    if origin not in (Union, UnionType):
        return [origin]
    return [t for arg in get_args(typehint) for t in unwrap_typehint(arg)]


def istypeinstance(typehint: Type, comparetypes: Union[Type, Collection[Type]]) -> bool:
    if not isinstance(comparetypes, Collection):
        comparetypes = (comparetypes,)
    unwrapped = unwrap_typehint(typehint)
    for comparetype in comparetypes:
        if comparetype in unwrapped:
            return True
    return False


def istypesubclass(typehint: TypeHint, comparetypes: TypeHintCollection) -> bool:
    if not isinstance(comparetypes, Collection):
        comparetypes = (comparetypes,)
    unwrapped = list(unwrap_typehint(typehint))
    for comparetype in comparetypes:
        for _type in unwrapped:
            try:
                if issubclass(_type, comparetype):
                    return True
            except TypeError:
                pass
    return False


def get_typehint_name(typehint: Type) -> str:
    if isunion(typehint):
        names = []
        type_args = get_args(typehint)
        for _type in type_args:
            if _type == type(None):
                continue
            name = get_typehint_name(_type)
            names.append(name)
        return ' | '.join(names)
    origin = get_origin(typehint)
    if origin is Literal:
        return str(get_args(typehint))[1:-1]
    if origin is not None:
        return get_typehint_name(origin)
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


def isunion(typehint: Type) -> bool:
    origin = get_origin(typehint)
    return origin in (Union, UnionType)


def islist(typehint: Type) -> bool:
    origin = get_origin(typehint)
    if list in (typehint, origin):
        return True
    if isunion(typehint):
        return any(islist(a) for a in get_args(typehint))
    return False


def istextio(typehint: Type) -> bool:
    textio_types = {TextIO, TextIOWrapper}
    if typehint in textio_types:
        return True
    type_args = get_args(typehint)
    return islist(typehint) and len(textio_types.intersection(type_args)) > 0
