import importlib.machinery
import importlib.util
import inspect
import sys

from collections.abc import Callable
from pathlib import Path
from typing import Optional



def import_path(module_path: Path):
    module_name = module_path.stem.replace('-', '_')
    spec = importlib.util.spec_from_loader(
        module_name,
        importlib.machinery.SourceFileLoader(module_name, str(module_path))
    )
    module = importlib.util.module_from_spec(spec) # type: ignore[arg-type] # spec_from_loader could be None only if loader was not supplied
    spec.loader.exec_module(module) # type: ignore [union-attr] # results from above implied Optional[ModuleSpec]
    sys.modules[module_name] = module
    return module


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
                arg = coerce_shell_arg(arg, kw_param.annotation)
                kwargs[kw] = arg
                kwargs_used = True
                continue
        # handle positional args, abort if kwargs have started
        if kwargs_used:
            raise SyntaxError('positional argument follows keyword argument')
        arg = coerce_shell_arg(raw_arg, param.annotation)
        args.append(arg)
    return args, kwargs


def coerce_shell_arg(arg: str, annotation: Optional[type]=None):
    if annotation not in (inspect._empty, None):
        try:
            return coerce_typed_arg(arg, annotation)
        except (TypeError, ValueError):
            pass # fall through to raw arg
    if arg in ['true', 'false']:
        return arg == 'true'
    if arg.isdecimal():
        return int(arg)
    return arg


def coerce_typed_arg(arg, annotation):
    if annotation == bool:
        if arg.lower() in ['true', 'false']:
            return arg == 'true'
        return arg
    if annotation == int:
        return int(arg)
    if annotation == float:
        return float(arg)
    return annotation(arg)


