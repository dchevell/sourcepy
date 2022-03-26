import inspect
import json
import re
import sys

from collections.abc import Callable, Collection
from datetime import date, datetime, time
from io import TextIOBase
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
    UnionType = object() # Dummy type



RawStringList = Union[str, List[str]]
TypeHint = Union[Type[Any], TypingBase]
TypeHintTuple = Union[TypeHint, Tuple[TypeHint]]
TypeMap = Dict[Type[Any], Optional[Dict[Type[Any], Any]]]


def cast_to_type(value: RawStringList, typehint: Optional[TypeHint] = None, *,
                 strict: bool = False) -> Any:
    typecaster = get_caster(typehint)
    try:
        typed_value = typecaster(value)
        if typed_value is None:
            raise ValueError(f"invalid literal for {typehint}: {value}")
        return typed_value
    except (TypeError, ValueError) as e:
        if strict:
            raise ValueError(f"invalid literal for {typehint}: {value}") from e
        return value


def get_caster(typehint: TypeHint) -> Callable[[Any], Any]:
    """Returns a conversion class most appropriate for the
    supplied type hint. Potential matches are checked in
    order from most to least specific to account for
    overlapping types (e.g. ABCs).
    """
    if typehint in (Any, None):
        return untyped_caster
    origin = get_origin(typehint)
    if origin in (Union, UnionType):
        return union_caster(typehint)
    typecasters: Dict[TypeHintTuple, Callable[[Any], Any]] = {
        (str, bytes):              generic_caster(typehint),
        (dict,):                   json_caster(typehint),
        (bool,):                   bool_caster,
        (Collection,):             collection_caster(typehint),
        (date, time):              datetime_caster(typehint),
        (Pattern,):                pattern_caster,
        (TextIO, TextIOBase):   textio_caster,
        (Literal,):                literal_caster(typehint),
    }
    for cls, caster in typecasters.items():
        if typehint in cls:
            return caster
        if origin in cls and origin is not None:
            return caster
        if issubtype(typehint, cls):
            return caster
    return generic_caster(typehint)


def union_caster(typehint: TypeHint) -> Callable[[Any], Any]:
    def caster(value: RawStringList) -> Any:
        type_args = get_args(typehint)
        for _type in type_args:
            try:
                if (isinstance(value, list)
                    and not issubtype(_type, Collection)
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


def generic_caster(typehint: TypeHint) -> Callable[[Any], Any]:
    def caster(value: str) -> Any:
        try:
            return typehint(value)
        except TypeError:
            return value
    return caster


def bool_caster(value: str) -> Optional[bool]:
    if value in ('true', 'false'):
        return value == 'true'
    return None


def json_caster(typehint: TypeHint) -> Callable[[Any], Any]:
    def caster(value: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
        try:
            json_value = json.loads(value)
            if istype(type(json_value), (typehint, get_origin(typehint))):
                return json_value
        except json.decoder.JSONDecodeError:
            pass
        return None
    return caster


def collection_caster(typehint: TypeHint) -> Callable[[Any], Any]:
    def caster(value: RawStringList) -> Optional[Collection[Any]]:
        base_type = get_origin(typehint) or typehint
        if isinstance(value, str):
            value = [value]
        if base_type is list and len(value) == 1:
            typecaster = json_caster(typehint)
            json_value = typecaster(value[0])
            if json_value is not None:
                return json_value
        if member_types := get_args(typehint):
            if not issubclass(base_type, tuple) or Ellipsis in member_types:
                member_types = (member_types[0],) * len(value)
            elif issubclass(base_type, tuple) and len(member_types) != len(value):
                return None
            member_values = []
            for m_value, m_type in zip(value, member_types):
                typed_value = cast_to_type(m_value, m_type, strict=True)
                member_values.append(typed_value)
            value = member_values
        container_type = list if inspect.isabstract(base_type) else base_type
        return container_type(value)
    return caster


def datetime_caster(typehint: TypeHint) -> Callable[[Any], Any]:
    def caster(value: str) -> Union[date, datetime, time]:
        if value.isdecimal() and issubtype(typehint, date):
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


def literal_caster(typehint: TypeHint) -> Callable[[Any], Any]:
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


def map_typehint(typehint: TypeHint) -> TypeMap:
    typehint_map: TypeMap = {}
    origin = get_origin(typehint)
    type_args = get_args(typehint)
    if origin is None:
        typehint_map[typehint] = origin
    elif origin in (Union, UnionType):
        for arg in type_args:
            typehint_map.update(map_typehint(arg))
    else:
        child_map: TypeMap = {}
        for arg in get_args(typehint):
            child_map.update(map_typehint(arg))
        typehint_map[origin] = child_map or None
    return typehint_map


def istype(typehint: TypeHint, comparetypes: TypeHintTuple) -> bool:
    if not isinstance(comparetypes, Collection):
        comparetypes = (comparetypes,)
    type_map = map_typehint(typehint)
    primary_types = type_map.keys()
    if set(primary_types).intersection(comparetypes):
        return True
    return False


def issubtype(typehint: TypeHint, comparetypes: TypeHintTuple) -> bool:
    if not isinstance(comparetypes, tuple):
        comparetypes = (comparetypes,)
    type_map = map_typehint(typehint)
    primary_types = type_map.keys()
    for _type in primary_types:
        try:
            if issubclass(_type, comparetypes):
                return True
        except TypeError:
            pass
    return False


def containstype(typehint: TypeHint, comparetypes: TypeHintTuple) -> bool:
    def _containstype(type_map: TypeMap, comparetypes: TypeHintTuple) -> bool:
        for key, value in type_map.items():
            if issubtype(key, comparetypes):
                return True
            if value is None:
                continue
            if _containstype(value, comparetypes):
                return True
        return False
    if not isinstance(comparetypes, Collection):
        comparetypes = (comparetypes,)
    type_map = map_typehint(typehint)
    return _containstype(type_map, comparetypes)


def isunion(typehint: TypeHint) -> bool:
    type_map = map_typehint(typehint)
    return len(type_map) > 1


def istextio(typehint: TypeHint) -> bool:
    return containstype(typehint, (TextIO, TextIOBase))


def get_typehint_name(typehint: TypeHint) -> str:
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
    if istextio(typehint):
        name = 'file(s)' if issubtype(typehint, Collection) else 'file'
        return f'{name} / stdin'
    if origin is not None:
        return get_typehint_name(origin)
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
    elif isinstance(value, (tuple, list, set)):
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
