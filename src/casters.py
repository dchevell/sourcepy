import inspect
import json
import re
import sys
from collections.abc import Callable, Collection
from datetime import date, datetime, time
from io import IOBase, TextIOBase
from pathlib import Path
from re import Pattern
from typing import (IO, Any, Dict, List, Literal, Optional, Sequence, Set,
                    TextIO, Tuple, Type, TypeVar, Union)
from typing import _Final as TypingBase  # type: ignore[attr-defined]
from typing import get_args, get_origin



if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = object() # Dummy type



T = TypeVar('T')
StringUnion = Union[str, List[str]]
CollectionReturn = Optional[Collection[Any]]
DateTimeReturn = Union[date, datetime, time]
IOReturn = Union[IO[str], IO[bytes]]
JSONReturn = Optional[Union[Dict[str, Any], List[Any]]]
PatternReturn = Union[Pattern[str], Pattern[bytes]]

TypeHint = Union[Type[Any], TypingBase]
TypeHintTuple = Union[TypeHint, Tuple[TypeHint]]
TypeMap = Dict[Type[Any], Optional[Dict[Type[Any], Any]]]

IOMode = Literal['r', 'rb', 'w', 'wb']


class CastingError(Exception):
    """Custom exception for casters
    """


def cast_to_type(value: StringUnion, typehint: Optional[TypeHint] = None, *,
                 strict: bool = False) -> Any:
    typecaster = get_caster(typehint)
    name = get_typehint_name(typehint)
    try:
        typed_value = typecaster(value)
        if typed_value is None:
            raise ValueError
        return typed_value
    except (TypeError, ValueError) as e:
        if strict:
            err = f"invalid {name} value: {cast_to_shell(value)}"
            raise ValueError(err) from e
        return value



def get_caster(typehint: TypeHint) -> Callable[..., Any]:
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
    typecasters: Dict[TypeHintTuple, Callable[..., Any]] = {
        (bytes,):                   str.encode,
        (str,):                     str,
        (dict,):                    json_caster(typehint),
        (bool,):                    bool_caster,
        (Sequence, Set):            collection_caster(typehint),
        (date, time):               datetime_caster(typehint),
        (Pattern,):                 pattern_caster(typehint),
        (IO, IOBase):               io_caster(typehint),
        (Literal,):                 literal_caster(typehint),
    }
    for cls, caster in typecasters.items():
        if typehint in cls:
            return caster
        if origin in cls and origin is not None:
            return caster
        if issubtype(typehint, cls):
            return caster
    return generic_caster(typehint)


def union_caster(typehint: TypeHint) -> Callable[[StringUnion], Optional[T]]:
    def caster(value: StringUnion) -> Optional[T]:
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
            # prevent floats matching ints if both in Union
            if set(type_args).issuperset({int, float}):
                if value != str(typed_value):
                    continue
            return typed_value
        return None
    return caster


def generic_caster(typehint: TypeHint) -> Callable[[str], Union[T, str]]:
    """If we don't know how to handle a type, try calling it with a
    single argument constructor. If it fails, return the original string
    value rather than failing - we should fail with ValueErrors when the
    value is known not to match the expected type, not when we don't
    know how to handle a type. """
    def caster(value: str) -> Union[T, str]:
        try:
            return typehint(value)
        except TypeError:
            return value
    return caster


def bool_caster(value: str) -> Optional[bool]:
    if value in ('true', 'false'):
        return value == 'true'
    return None


def json_caster(typehint: TypeHint) -> Callable[[str], JSONReturn]:
    def caster(value: str) -> JSONReturn:
        try:
            json_value = json.loads(value)
            if istype(type(json_value), (typehint, get_origin(typehint))):
                return json_value
        except json.decoder.JSONDecodeError:
            pass
        return None
    return caster


def collection_caster(typehint: TypeHint) -> Callable[[StringUnion], CollectionReturn]:
    def caster(value: StringUnion) -> CollectionReturn:
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


def datetime_caster(typehint: TypeHint) -> Callable[[str], DateTimeReturn]:
    def caster(value: str) -> DateTimeReturn:
        if value.isdecimal() and issubtype(typehint, date):
            return typehint.fromtimestamp(int(value))
        return typehint.fromisoformat(value)
    return caster


def pattern_caster(typehint: TypeHint) -> Callable[[str], PatternReturn]:
    def caster(value: str) -> PatternReturn:
        if member_types := get_args(typehint):
            value = cast_to_type(value, member_types[0], strict=True)
        return re.compile(value)
    return caster


def io_caster(typehint: TypeHint) -> Callable[[str], IOReturn]:
    def caster(value: str) -> IOReturn:
        if not sys.stdin.isatty():
            if containstextio(typehint):
                return sys.stdin
            return sys.stdin.buffer
        file = Path(value)
        if not file.exists():
            raise CastingError(f"no such file or directory: {value}")
        mode: IOMode = 'r' if containstextio(typehint) else 'rb'
        return file.open(mode=mode)
    return caster


def literal_caster(typehint: TypeHint) -> Callable[[str], Optional[T]]:
    def caster(value: str) -> Optional[T]:
        type_literals = get_args(typehint)
        for lit in type_literals:
            try:
                typed_value = cast_to_type(value, type(lit), strict=True)
            except (TypeError, ValueError):
                continue
            if typed_value in type_literals:
                return typed_value
        raise CastingError(
            f'invalid choice: {cast_to_shell(value)} '
            f'(choose from {get_typehint_name(typehint)[1:-1]})')
    return caster


def untyped_caster(value: str) -> Union[bool, int, str]:
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


def isio(typehint: TypeHint) -> bool:
    return issubtype(typehint, (IO, IOBase))


def containsio(typehint: TypeHint) -> bool:
    return containstype(typehint, (IO, IOBase))


def containstextio(typehint: TypeHint) -> bool:
    if not containsio(typehint):
        return False
    return containstype(typehint, (TextIO, TextIOBase, str))


def iscontainer(typehint: TypeHint) -> bool:
    if issubtype(typehint, (bytes, str)):
        return False
    return issubtype(typehint, (Sequence, Set))


def get_typehint_name(typehint: TypeHint) -> str:
    origin = get_origin(typehint)
    if isunion(typehint):
        names = set()
        type_args = get_args(typehint)
        for _type in type_args:
            if _type == type(None):
                continue
            name = get_typehint_name(_type)
            names.add(name)
        return ' | '.join(names)
    if iscontainer(typehint):
        base_type = origin or typehint
        if member_types := get_args(typehint):
            if issubclass(base_type, tuple) and Ellipsis not in member_types:
                member_names = [get_typehint_name(t) for t in member_types]
                name = f'[{", ".join(member_names)}]'
            else:
                member_name = get_typehint_name(member_types[0])
                name = f'[{member_name} ...]'
            return name
        return '[...]'
    if origin is Literal:
        choices = [cast_to_shell(a) for a in get_args(typehint)]
        return '{' + ', '.join(choices) + '}'
    if origin is not None:
        return get_typehint_name(origin)

    if isio(typehint):
        name = 'file/stdin'
    elif hasattr(typehint, '__name__'):
        name = typehint.__name__
    else:
        name = str(typehint)
    return name


def cast_to_shell(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (tuple, list, set)):
        shell_array = [cast_to_shell(v) for v in value]
        return f"({' '.join(shell_array)})"
    if isinstance(value, dict):
        shell_array = [f'[{cast_to_shell(k)}]={cast_to_shell(v)}'
                       for k, v in value.items()]
        return f"({' '.join(shell_array)})"
    if value is None:
        return ''
    return f"'{value}'"


def get_typedef(value: object) -> str:
    if isinstance(value, int):
        return '-i'
    if isinstance(value, (tuple, list, set)):
        return '-a'
    if isinstance(value, dict):
        return '-A'
    return ''
