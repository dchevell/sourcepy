import contextlib
import pathlib
import sys

from typing import Any, Generator, List

from loaders import get_callable, load_path
from parser import FunctionSignatureParser



def run_from_stub(module_path: pathlib.Path, fn_string: str, raw_args: List[str]) -> None:
    with redirect_stdout():
        module = load_path(module_path)
        fn = get_callable(module, fn_string)
        parser = FunctionSignatureParser(fn)
        args, kwargs = parser.parse_fn_args(raw_args)
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
    if result is None:
        return
    if isinstance(result, bool):
        print(str(result).lower())
    elif isinstance(result, Generator):
        for y in result:
            print_result(y)
    else:
        print(result)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit("sourcepy_run: not enough arguments")
    module_path = pathlib.Path(sys.argv[1])
    fn_string = sys.argv[2]
    raw_args = sys.argv[3:]
    if not sys.stdin.isatty():
        stdin_arg = sys.stdin.read().rstrip()
        raw_args.insert(0, stdin_arg)
    run_from_stub(module_path, fn_string, raw_args)

