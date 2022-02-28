import inspect
import pathlib
import sys
import textwrap
import types

from loader import import_path


def isprimitive(obj: any) -> bool:
    return type(obj) in (int, float, bool, str)


def iscollection(obj: any) -> bool:
    return type(obj) in (tuple, list, set, dict)


def make_var(name, value):
    var_def=f'{name}="{value}"'
    print(var_def)


def make_fn(name, value, runner_name):
    fn_def=textwrap.dedent(f"""
        {name}() {{
            local in
            read -t 0 in
            {runner_name} {name} $in $@
        }}
    """)
    print(fn_def)


def make_runner(module):
    runner_name = f'_sourcepy_run_{hash(module)}'
    module_path = module.__file__
    runner = textwrap.dedent(f"""\
        # stub for {module_path}

        {runner_name}() {{
            {sys.executable} $SOURCEPY_HOME/bin/run.py {module_path} $@
        }}
    """)
    print(runner)
    return runner_name


def make_def(obj, runner_name, parent_ns=None):
    for name, value in inspect.getmembers(obj):
        if name.startswith('__') or isinstance(value, (types.ModuleType, type)):
            continue

        fullname = f"{parent_ns}.{name}" if parent_ns is not None else name
        if isprimitive(value) and '.' not in fullname:
            make_var(fullname, value)
        elif callable(value):
            make_fn(fullname, value, runner_name)
        else:
            make_def(value, runner_name, parent_ns=fullname)


def build_stub(module_path):
    module = import_path(module_path)
    runner_name = make_runner(module)
    make_def(module, runner_name)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("sourcepy: not enough arguments")
    module_path = pathlib.Path(sys.argv[1])
    build_stub(module_path)