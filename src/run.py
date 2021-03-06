import asyncio
import contextlib
import sys
from pathlib import Path
from typing import (Any, Awaitable, Callable, Dict, Generator, Iterator, List,
                    TypeVar, Union)

from loaders import get_callable, load_path
from parsers import FunctionParameterParser



T = TypeVar('T')
Caller = Union[Callable[..., T], Callable[..., Awaitable[T]]]


def run_from_wrapper(module_path: Path, fn_string: str, raw_args: List[str]) -> None:
    with contextlib.redirect_stdout(sys.stderr):
        module = load_path(module_path)
        fn = get_callable(module, fn_string)
        parser = FunctionParameterParser(fn, fn_string)
        with parser.parse_fn_args(raw_args) as (args, kwargs):
            result = caller(fn, *args, **kwargs)
            print_result(result)


def caller(fn: Caller[T], *args: List[Any], **kwargs: Dict[str, Any]) -> T:
    result = fn(*args, **kwargs)
    if isinstance(result, Awaitable):
        async_result: T = asyncio.run(result)
        return async_result
    return result


def print_result(result: object) -> None:
    if result is None:
        return
    if isinstance(result, (Generator, Iterator)):
        for line in result:
            print_result(line)
        return

    stdout = sys.__stdout__
    out = str(result)
    if isinstance(result, bool):
        out = out.lower()
    if not out.endswith('\n'):
        out += '\n'
    stdout.write(out)
    stdout.flush()


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("sourcepy_run: not enough arguments")
    module_path = Path(sys.argv[1])
    fn_string = sys.argv[2]
    raw_args = sys.argv[3:]
    run_from_wrapper(module_path, fn_string, raw_args)


if __name__ == '__main__':
    main()
