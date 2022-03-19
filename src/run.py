import contextlib
import pathlib
import sys

from typing import Any, Generator, Iterator, List

from loaders import get_callable, load_path
from parsers import FunctionParameterParser



def run_from_stub(module_path: pathlib.Path, fn_string: str, raw_args: List[str]) -> None:
    with contextlib.redirect_stdout(sys.stderr):
        module = load_path(module_path)
        fn = get_callable(module, fn_string)
        parser = FunctionParameterParser(fn)
        with parser.parse_fn_args(raw_args) as (args, kwargs):
            result = fn(*args, **kwargs)
            print_result(result)


def print_result(result: Any) -> None:
    with contextlib.redirect_stdout(sys.stdout):
        if result is None:
            return
        if isinstance(result, bool):
            print(str(result).lower())
        elif isinstance(result, (Generator, Iterator)):
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
    run_from_stub(module_path, fn_string, raw_args)
