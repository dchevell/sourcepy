import contextlib
import inspect
import pathlib
import sys

from loader import import_path



def get_callable(parent, method_str):
    attr_list = method_str.split('.')
    current = parent
    for attr in attr_list:
        current = getattr(current, attr)
    return current


def fn_kwarg_names(fn):
    params = inspect.signature(fn).parameters.items()
    kwarg_kinds = (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    kwarg_names = [name for name, param in params if param.kind in kwarg_kinds]
    return kwarg_names


def coerce_arg(arg):
    match result:
        case 'true' | 'false':
            if result == 'true':
                return True
            return False
        case _:
            return arg


def parse_args(fn, raw_args):
    args = list()
    kwargs = dict()
    for arg in raw_args:
        if '=' in arg:
            k, v = arg.split('=', 1)
            if k in fn_kwarg_names(fn):
                kwargs[k] = v
                continue
        args.append(arg)
    return args, kwargs


def coerce_result(result):
    match result:
        case bool():
            print(str(result).lower())
        case _:
            print(result)



@contextlib.contextmanager
def redirect_stdout():
    try:
        sys.stdout = sys.__stderr__ # shell interprets stdout as return values; redirect to stderr
        yield
    finally:
        sys.stdout = sys.__stdout__ # now we can print the return value to stdout



def run_from_stub(module_path, fn_string, raw_args):
    with redirect_stdout():
        module = import_path(module_path)
        fn = get_callable(module, fn_string)
        args, kwargs = parse_args(fn, raw_args)
        result = fn(*args, **kwargs)
    coerce_result(result)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit("sourcepy_run: not enough arguments")
    module_path = pathlib.Path(sys.argv[1])
    fn_string = sys.argv[2]
    raw_args = sys.argv[3:]
    run_from_stub(module_path, fn_string, raw_args)