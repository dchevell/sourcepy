import inspect
import pathlib
import sys
import textwrap
from types import ModuleType
from typing import Any, Iterator, Optional, _SpecialForm

from loader import import_path



def isprimitive(obj: Any) -> bool:
    return type(obj) in (int, float, bool, str)


def iscollection(obj: Any) -> bool:
    return type(obj) in (tuple, list, set, dict)


def make_var(name: str, value: Any) -> None:
    var_def=f'{name}="{value}"'
    return var_def


def make_fn(name: str, runner_name: str) -> None:
    fn_def=textwrap.dedent(f"""
        {name}() {{
            local in
            if ! [[ -t 0 ]]; then
                in=$(cat)
            fi
            {runner_name} {name} $in $@
        }}
    """)
    return fn_def


def make_runner(module: ModuleType):
    runner_name = f'_sourcepy_run_{hash(module)}'
    module_path = module.__file__
    runner = textwrap.dedent(f"""\
        # stub for {module_path}

        {runner_name}() {{
            {sys.executable} $SOURCEPY_HOME/bin/run.py {module_path} $@
        }}
    """)
    return runner



def make_def(obj, runner_name, parent_ns=None):
    for name, value in inspect.getmembers(obj):
        if name.startswith('__') or isinstance(value, (type, ModuleType, _SpecialForm)):
            continue
        fullname = f"{parent_ns}.{name}" if parent_ns is not None else name
        if isprimitive(value) and '.' not in fullname:
            yield make_var(fullname, value)
        elif callable(value):
            yield make_fn(fullname, runner_name)
        else:
            yield from make_def(value, runner_name, parent_ns=fullname)


def get_definitions(obj: Any, parents: Optional[list] = None) -> Iterator[dict]:
    if parents is None:
        parents = []
    for name, value in inspect.getmembers(obj):
        if name.startswith('__') or isinstance(value, (type, ModuleType, _SpecialForm)):
            continue
        if isprimitive(value) or iscollection(value):
            yield {'type': 'variable', 'name': name, 'value': value, 'parents': parents}
        elif callable(value):
            yield {'type': 'function', 'name': name, 'parents': parents}
        else:
            yield from get_definitions(value, parents + [name])


def build_stub(module_path):
    stub_contents = []
    module = import_path(module_path)
    module_hash = f'_sourcepy_run_{hash(module)}'
    stub_contents.append(make_runner(module))
    make_def(module, runner_name)




if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("sourcepy: not enough arguments")
    module_path = pathlib.Path(sys.argv[1])
    build_stub(module_path)