import importlib.machinery
import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterator, List, Optional, Tuple, TypedDict



class _MemberDef(TypedDict):
    name: str
    type: str
    value: object


MemberDefinitions = Iterator[_MemberDef]
Members = List[Tuple[str, object]]


def load_path(module_path: Path) -> ModuleType:
    module_name = module_path.stem.replace('-', '_')
    spec = importlib.util.spec_from_loader(
        module_name,
        importlib.machinery.SourceFileLoader(module_name, str(module_path))
    )
    # spec_from_loader could be None only if loader was not supplied
    module = importlib.util.module_from_spec(spec) # type: ignore[arg-type]
    # results from above implied Optional[ModuleSpec]
    spec.loader.exec_module(module) # type: ignore [union-attr]
    sys.modules[module_name] = module
    return module


def module_definitions(module: ModuleType) -> MemberDefinitions:
    module_exports = getattr(module, '__all__', None)
    valid_members = []
    for name, value in inspect.getmembers(module):
        if module_exports is not None:
            if name in module_exports:
                valid_members.append((name, value))
            continue
        if name.startswith('_'):
            continue
        if inspect.getmodule(value) in (module, None):
            valid_members.append((name, value))
    yield from member_definitions(valid_members)


def member_definitions(members: Members, parent: Optional[str] = None) -> MemberDefinitions:
    for name, value in members:
        if name.startswith('__') or isinstance(value, type):
            continue
        if inspect.isroutine(value):
            if parent is not None:
                name = f'{parent}.{name}'
            yield {'type': 'function', 'name': name, 'value': value}
        elif isprimitive(value) or iscollection(value):
            yield {'type': 'variable', 'name': name, 'value': value}
        elif getattr(value, '__dict__', {}):
            yield from member_definitions([(name, vars(value))])
        if methods := inspect.getmembers(value, inspect.ismethod):
            yield from member_definitions(methods, parent=name)


def get_callable(parent: ModuleType, method_str: str) -> Callable[..., object]:
    attr_list = method_str.split('.')
    current = parent
    for attr in attr_list:
        current = getattr(current, attr)
    if not callable(current):
        raise ValueError(f'{method_str} does not point to a valid callable')
    return current


def isprimitive(obj: object) -> bool:
    return isinstance(obj, (int, float, bool, str))


def iscollection(obj: object) -> bool:
    return isinstance(obj, (tuple, list, set, dict))
