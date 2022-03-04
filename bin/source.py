import inspect
import sys
import textwrap
from collections import namedtuple
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator, Optional, _SpecialForm

from converters import cast_to_shell, isprimitive, iscollection
from loaders import load_path, get_definitions



def make_var(name: str, value: Any) -> None:
    value, typedef = cast_to_shell(value)
    var_def = textwrap.dedent(f"""\
            declare {('-g ' + typedef).strip()} {name}
            {name}={value}
    """)
    return var_def


def make_fn(name: str, runner_name: str, helpdoc: Optional[str] = '') -> str:
    fn_def = textwrap.dedent(f"""\
        {name}() {{
            local helpdoc="{helpdoc or ""}"
            {runner_name} {name} "$@"
        }}
    """)
    return fn_def


def make_runner(runner_name: str, module_path: Path) -> str:
    runner = textwrap.dedent(f"""\
        {runner_name}() {{
            local in
            if ! [[ -t 0 ]]; then
                in=$(cat)
            fi
            {sys.executable} $SOURCEPY_HOME/bin/run.py {module_path} "$1" $in "${{@:2}}"
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



def build_stub(module_path: Path) -> str:
    stub_contents = []

    module = load_path(module_path)
    stub_title = f"SourcePy stub for {module.__name__} ({module_path})"
    stub_contents.append(textwrap.dedent(f"""\
        ######{"#" * len(stub_title)}######
        ##### {stub_title} #####
        ######{"#" * len(stub_title)}######
    """))

    runner_name = f'_sourcepy_run_{hash(module)}'
    runner = make_runner(runner_name, module_path)
    stub_contents.append('# SourcePy runner')
    stub_contents.append(runner)

    stub_contents.append('\n# Definitions')
    for d in get_definitions(module):
        full_name = d['parents'] + [d['name']]
        full_name = '.'.join(full_name)
        if d['type'] == 'function':
            helpdoc = inspect.getdoc(d['value'])
            fn_def = make_fn(full_name, runner_name, helpdoc)
            stub_contents.append(fn_def)
        elif d['type'] == 'variable':
            var_def = make_var(full_name, d['value'])
            stub_contents.append(var_def)
    stub = '\n'.join(stub_contents)
    return stub

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("sourcepy: not enough arguments")
    module_path = Path(sys.argv[1])
    stub = build_stub(module_path)
    print(stub)
