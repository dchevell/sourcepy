import importlib.machinery
import importlib.util
import inspect
import sys

from collections.abc import Callable
from pathlib import Path

from converters import cast_from_shell


def load_path(module_path: Path):
    module_name = module_path.stem.replace('-', '_')
    spec = importlib.util.spec_from_loader(
        module_name,
        importlib.machinery.SourceFileLoader(module_name, str(module_path))
    )
    module = importlib.util.module_from_spec(spec) # type: ignore[arg-type] # spec_from_loader could be None only if loader was not supplied
    spec.loader.exec_module(module) # type: ignore [union-attr] # results from above implied Optional[ModuleSpec]
    sys.modules[module_name] = module
    return module



def get_definitions(obj: Any, parents: Optional[list] = None) -> Iterator[dict]:
    if parents is None:
        parents = []
    for name, value in inspect.getmembers(obj):
        if name.startswith('__') or isinstance(value, (type, ModuleType, _SpecialForm)):
            continue
        if isprimitive(value) or iscollection(value):
            yield {'type': 'variable', 'name': name, 'value': value, 'parents': parents}
        elif callable(value):
            yield {'type': 'function', 'name': name, 'value': value, 'parents': parents}
        else:
            yield from get_definitions(value, parents + [name])


def get_callable(parent: Callable, method_str: str) -> Callable:
    attr_list = method_str.split('.')
    current = parent
    for attr in attr_list:
        current = getattr(current, attr)
    return current


def load_shell_args(fn: Callable, shell_args: list[str]) -> tuple[list, dict]:
    args = list()
    kwargs = dict()
    param_signatures = inspect.signature(fn).parameters
    kwargs_used = False
    for raw_arg, param in zip(shell_args, param_signatures.values()):
        # handle keyword args
        if '=' in raw_arg:
            kw, arg = raw_arg.split('=', 1)
            kw_names = [name for name, param in param_signatures.items() if param.kind > 0]
            if kw in kw_names:
                kw_param = param_signatures[kw]
                arg = cast_from_shell(arg, kw_param.annotation)
                kwargs[kw] = arg
                kwargs_used = True
                continue
        # handle positional args, abort if kwargs have started
        if kwargs_used:
            raise SyntaxError('positional argument follows keyword argument')
        arg = cast_from_shell(raw_arg, param.annotation)
        args.append(arg)
    return args, kwargs


def parse_shell_args(fn: Callable, shell_args: list[str]) -> tuple[list, dict]:
    args = list()
    kwargs = dict()
    param_signatures = inspect.signature(fn).parameters
    import argparse
    parser = argparse.ArgumentParser(description=inspect.getdoc(fn), prog=fn.__name__)
    parser.add_argument('_positional_args', nargs="*")
    for name, param in param_signatures.items():
        arg_name = name.replace('_', '-')
        arg_settings = dict()

        # type behaviour
        if isinstance(param.default, bool) or param.annotation == bool:
            arg_settings['action'] = 'store_true'
        else:
            arg_settings['type'] = param.annotation



        # create arg
        if param.kind == inspect.Parameter.POSITIONAL_ONLY:
            parser.add_argument(arg_name, **arg_settings)
        else:
            if param.default == inspect._empty:
                arg_settings['required'] = True
            parser.add_argument(f'--{arg_name}', **arg_settings)

    cmdargs = parser.parse_args(sys.argv[3:])
    print(cmdargs)
    for i, (name, param) in enumerate(param_signatures.items()):
        if param.kind == inspect.Parameter.POSITIONAL_ONLY:
            args.append(getattr(cmdargs, name))
        else:
            kwargs[name] = getattr(cmdargs, name)
    return args, kwargs