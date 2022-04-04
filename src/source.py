import contextlib
import os
import sys
import textwrap
from pathlib import Path

from casters import cast_to_shell, get_typedef
from loaders import load_path, module_definitions



SOURCEPY_HOME = Path(os.environ.get('SOURCEPY_HOME', Path.home() / '.sourcepy'))
SOURCEPY_BIN = Path(__file__).resolve().parent


def make_var(name: str, value: object) -> str:
    typedef = get_typedef(value)
    value = cast_to_shell(value)
    var_def = textwrap.dedent(f"""\
        declare {('-g ' + typedef).strip()} {name}
        {name}={value}
    """)
    return var_def


def make_fn(name: str, runner_name: str) -> str:
    fn_def = textwrap.dedent(f"""\
        {name}() {{
            {runner_name} {name} "$@"
        }}
    """)
    return fn_def


def make_runner(runner_name: str, module_path: Path) -> str:
    runner = textwrap.dedent(f"""\
        {runner_name}() {{
            {sys.executable} {SOURCEPY_BIN}/run.py {module_path} "$@"
        }}
    """)
    return runner


def make_wrapper_name(path: Path) -> str:
    """Return an escaped filename to be used in source wrappers.
    Reverses the order of parts from the original filepath for
    easier readability
    """
    escaped = '_'.join(reversed(path.parts))
    for char in '. /':
        escaped = escaped.replace(char, '_')
    return escaped + '.sh'


def build_wrapper(module_path: Path) -> str:
    wrapper_contents = []

    module = load_path(module_path)
    wrapper_title = f'Sourcepy wrapper for {module.__name__} ({module_path})'
    wrapper_contents.append(textwrap.dedent(f"""\
        ######{"#" * len(wrapper_title)}######
        ##### {wrapper_title} #####
        ######{"#" * len(wrapper_title)}######
    """))

    runner_name = f'_sourcepy_run_{hash(module)}'
    runner = make_runner(runner_name, module_path)
    wrapper_contents.append('# Sourcepy runner')
    wrapper_contents.append(runner)

    wrapper_contents.append('\n# Definitions')
    for obj_definition in module_definitions(module):
        name = obj_definition['name']
        if obj_definition['type'] == 'function':
            fn_def = make_fn(name, runner_name)
            wrapper_contents.append(fn_def)
        elif obj_definition['type'] == 'variable':
            var_def = make_var(name, obj_definition['value'])
            wrapper_contents.append(var_def)
    wrapper = '\n'.join(wrapper_contents)
    return wrapper


def write_wrapper_file(wrapper_contents: str, wrapper_name: str) -> Path:
    wrapper_file = SOURCEPY_HOME / 'wrappers' / wrapper_name
    wrapper_file.parent.mkdir(parents=True, exist_ok=True)
    with open(wrapper_file, 'w', encoding='utf-8') as f:
        f.write(wrapper_contents)
    return wrapper_file


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("sourcepy: not enough arguments")
    with contextlib.redirect_stdout(sys.stderr):
        module_path = Path(sys.argv[1]).resolve()
        wrapper_contents = build_wrapper(module_path)
        wrapper_name = make_wrapper_name(module_path)
        wrapper_file = write_wrapper_file(wrapper_contents, wrapper_name)
    print(wrapper_file)


if __name__ == '__main__':
    main()
