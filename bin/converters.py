from inspect import _empty
from typing import Any, Optional



def cast_from_shell(value: str, annotation: Optional[type]=None) -> Any:
    if annotation not in (_empty, None):
        try:
            return cast_typed_from_shell(value, annotation)
        except (TypeError, ValueError):
            pass # fall through to raw value
    if value in ['true', 'false']:
        return value == 'true'
    if value.isdecimal():
        return int(value)
    return value


def cast_typed_from_shell(value: str, annotation: Any) -> Any:
    if annotation == bool:
        if value.lower() in ['true', 'false']:
            return value == 'true'
        return value
    if annotation == int:
        return int(value)
    if annotation == float:
        return float(value)
    return annotation(value)


def cast_to_shell(value: Any) -> tuple[str, Optional[str]]:
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


def isprimitive(obj: Any) -> bool:
    return isinstance(obj, (int, float, bool, str))


def iscollection(obj: Any) -> bool:
    return isinstance(obj, (tuple, list, set, dict))


def isarray(obj: Any) -> bool:
    return isinstance(obj, (tuple, list, set))