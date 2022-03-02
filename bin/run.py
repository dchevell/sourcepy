import contextlib
import inspect
import pathlib
import sys
from typing import Any, Generator

from loader import get_callable, import_path, load_shell_args



def run_from_stub(module_path: pathlib.Path, fn_string: str, raw_args: list[str]) -> None:
    with redirect_stdout():
        module = import_path(module_path)
        fn = get_callable(module, fn_string)
        args, kwargs = load_shell_args(fn, raw_args)
        result = fn(*args, **kwargs)
    print_result(result)


@contextlib.contextmanager
def redirect_stdout() -> Generator:
    try:
        sys.stdout = sys.__stderr__ # shell interprets stdout as return values; redirect to stderr
        yield
    finally:
        sys.stdout = sys.__stdout__ # now we can print the return value to stdout


def print_result(result: Any) -> None:
    if isinstance(result, bool):
        print(str(result).lower())
    else:
        print(result)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit("sourcepy_run: not enough arguments")
    module_path = pathlib.Path(sys.argv[1])
    fn_string = sys.argv[2]
    raw_args = sys.argv[3:]
    run_from_stub(module_path, fn_string, raw_args)