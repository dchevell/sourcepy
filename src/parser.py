import argparse
import inspect
import sys

from argparse import Action
from collections import defaultdict
from collections.abc import Callable
from inspect import _ParameterKind as ParameterKind, Parameter
from io import TextIOWrapper
from typing import Any, DefaultDict, Dict, List, Union, Tuple, Type

# Fall back on regular boolean action < Python 3.9
try:
    from argparse import BooleanOptionalAction # type: ignore[attr-defined] # Python < 3.9
except ImportError:
    BooleanOptionalAction = 'store_true' # type: ignore[misc, assignment] # Python > 3.9

from casters import typecast_factory



POSITIONAL_ONLY = ParameterKind.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = ParameterKind.POSITIONAL_OR_KEYWORD
KEYWORD_ONLY = ParameterKind.KEYWORD_ONLY
REQUIRED = 'REQUIRED'
STDIN = 'STDIN'


KeyedParamDict = DefaultDict[Union[ParameterKind, str], List[Parameter]]
ArgOptions = Dict[str, Union[str, Type[Action], Callable, List]]


class FunctionSignatureParser(argparse.ArgumentParser):

    def __init__(self, fn: Callable, /, *args: Any, **kwargs: Any) -> None:
        if 'prog' not in kwargs:
            kwargs['prog'] = fn.__name__
        if 'description' not in kwargs:
            kwargs['description'] = inspect.getdoc(fn)
        super().__init__(*args, **kwargs)
        self.param_signatures = inspect.signature(fn).parameters
        self.param_sig_map: KeyedParamDict = defaultdict(list)
        for _, param in self.param_signatures.items():
            kind = param.kind
            self.param_sig_map[kind].append(param)
            if param.default is param.empty:
                self.param_sig_map[REQUIRED].append(param)
            if not self.param_sig_map[STDIN]:
                if param.kind is TextIOWrapper:
                    self.param_sig_map[STDIN] = param
        self.generate_args()

    def generate_args(self) -> None:
        if self.param_sig_map[POSITIONAL_ONLY]:
            self.generate_positional_only_args()

        if self.param_sig_map[POSITIONAL_OR_KEYWORD]:
            self.generate_positional_or_keyword_args()

        if self.param_sig_map[KEYWORD_ONLY]:
            self.generate_keyword_only_args()

    def generate_positional_only_args(self) -> None:
        group = self.add_argument_group('positional only args')
        for param in self.param_sig_map[POSITIONAL_ONLY]:
            name = param.name
            options = generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_positional_or_keyword_args(self) -> None:
        group = self.add_argument_group('positional or keyword args')
        for param in self.param_sig_map[POSITIONAL_OR_KEYWORD]:
            name = '--' + param.name.replace('_', '-')
            options = generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_keyword_only_args(self) -> None:
        group = self.add_argument_group('keyword only args')
        for param in self.param_sig_map[KEYWORD_ONLY]:
            name = '--' + param.name.replace('_', '-')
            options = generate_arg_options(param)
            group.add_argument(name, **options)

    def parse_fn_args(self, raw_args: List[str]) -> Tuple[Tuple, Dict[str, Any]]:
        # load stdin to first arg with type TextIOWrapper
        # or else first positional(only/-or-kw)
        if not sys.stdin.isatty():
            if param is self.param_sig_map[STDIN]:
                options[default] = sys.stdin
            if not self.param_sig_map[STDIN]:
                if param.kind in (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD):
                    options[default] = sys.stdin

        known_args, unknown_args = super().parse_known_args(raw_args)
        cmd_args = vars(known_args)
        args = []
        kwargs = {}

        # Parser will have already failed if these are missing
        for param in self.param_sig_map[POSITIONAL_ONLY]:
            value = cmd_args[param.name]
            args.append(value)

        # Reconcile which args are kw and which are positional
        for param in self.param_sig_map[POSITIONAL_OR_KEYWORD]:
            if param.name in cmd_args and cmd_args[param.name] is not None:
                kwargs[param.name] = cmd_args[param.name]
            else:
                try: # No idea if this is sane
                    value = unknown_args.pop(0)
                    typecast = typecast_factory(param)
                    if typecast is not None:
                        try:
                            value = typecast(value)
                        except (ValueError, TypeError):
                            self.error(
                                f"argument {param.name}: invalid {typecast.__name__} value: '{value}'"
                            )
                    args.append(value)
                    # Map back to cmd_args for easier REQUIRED checks later
                    cmd_args[param.name] = value
                except IndexError:
                    pass
        # Fail if unused positional args remain
        if unknown_args:
            self.error(f"unrecognized arguments: {', '.join(unknown_args)}")

        for param in self.param_sig_map[KEYWORD_ONLY]:
            if param.name in cmd_args:
                kwargs[param.name] = cmd_args[param.name]

        for param in self.param_sig_map[REQUIRED]:
            if param.name not in cmd_args:
                self.error(f"the following arguments are required: {param.name}")
        return tuple(args), kwargs


def generate_arg_options(param: Parameter) -> Dict[str, Any]:
    options: ArgOptions = {}
    helptext = []

    typecast = typecast_factory(param)
    if typecast is not None:
        helptext.append(typecast.__name__)

    # Boolean actions are incompatible with type options
    if param.annotation == bool or isinstance(param.default, bool):
        if param.kind == POSITIONAL_ONLY:
            options['choices'] = ['true', 'false']
            options['metavar'] = param.name
        else:
            # this nicer --option / --no-option helper
            # can only be usedwith kwargs
            options['action'] = BooleanOptionalAction
    elif typecast is not None:
        options['type'] = typecast

    if param.default is not param.empty:
        helptext.append(f'(default: {param.default})')
    else:
        helptext.append('(required)')

    if options.get('action') != BooleanOptionalAction:
        options['default'] = argparse.SUPPRESS

    if options.get('action') == BooleanOptionalAction:
        pass # Don't set metavar for bools
    elif param.kind == POSITIONAL_OR_KEYWORD:
        # Try to make it more obvious these can also be positional
        options['metavar'] = f'/ {param.name}'
    elif param.kind == KEYWORD_ONLY:
        options['metavar'] = ''

    options['help'] = ' '.join(helptext)
    return options
