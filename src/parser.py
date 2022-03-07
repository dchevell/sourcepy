import argparse
import inspect

from argparse import Action
from collections import defaultdict
from collections.abc import Callable
from inspect import _ParameterKind as ParameterKind, Parameter
from typing import Any, DefaultDict, Dict, List, Union, Tuple, Type

# Fall back on regular boolean action < Python 3.9
try:
    from argparse import BooleanOptionalAction # type: ignore[attr-defined] # Python < 3.9
except ImportError:
    BooleanOptionalAction = 'store_true' # type: ignore[misc, assignment] # Python > 3.9

from converters import typecast_factory



POSITIONAL_ONLY = ParameterKind.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = ParameterKind.POSITIONAL_OR_KEYWORD
KEYWORD_ONLY = ParameterKind.KEYWORD_ONLY
REQUIRED = 'REQUIRED'



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
        for name, param in self.param_signatures.items():
            kind = param.kind
            self.param_sig_map[kind].append(param)
            if param.default == inspect._empty:
                self.param_sig_map[REQUIRED].append(param)
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
            options = self.generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_positional_or_keyword_args(self) -> None:
        group = self.add_argument_group('positional or keyword args')
        group.add_argument('_positional_or_kw', nargs='*', default=[], help=argparse.SUPPRESS)
        for param in self.param_sig_map[POSITIONAL_OR_KEYWORD]:
            name = '--' + param.name.replace('_', '-')
            options = self.generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_keyword_only_args(self) -> None:
        group = self.add_argument_group('keyword only args')
        for param in self.param_sig_map[KEYWORD_ONLY]:
            name = '--' + param.name.replace('_', '-')
            options = self.generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_arg_options(self, param: Parameter) -> Dict[str, Any]:
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

        if param.default is not inspect._empty:
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

    def parse_fn_args(self, *raw_args: List[str]) -> Tuple[List[Any], Dict[str, Any]]:
        cmd_args = vars(super().parse_args(*raw_args))
        args = []
        kwargs = {}
        for param in self.param_sig_map[POSITIONAL_ONLY]:
            value = cmd_args[param.name]
            args.append(value)
        for param in self.param_sig_map[POSITIONAL_OR_KEYWORD]:
            if param.name in cmd_args:
                kwargs[param.name] = cmd_args[param.name]
            else:
                try: # no idea if this is sane
                    value = cmd_args['_positional_or_kw'].pop(0)
                    typecast = typecast_factory(param)
                    if typecast is not None:
                        value = typecast(value)
                    kwargs[param.name] = value
                    cmd_args[param.name] = value
                except IndexError:
                    pass
        for param in self.param_sig_map[KEYWORD_ONLY]:
            if param.name in cmd_args:
                kwargs[param.name] = cmd_args[param.name]

        for param in self.param_sig_map[REQUIRED]:
            if param.name not in cmd_args:
                self.error(f"the following arguments are required: {param.name}")

        return args, kwargs
