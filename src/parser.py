import argparse
import inspect
import sys

from argparse import Action
from collections import defaultdict
from collections.abc import Callable
from inspect import _ParameterKind as ParameterKind, Parameter
from io import TextIOWrapper
from types import MappingProxyType
from typing import Any, DefaultDict, Dict, List, Union, TextIO, Tuple, Type

# Fall back on regular boolean action < Python 3.9
try:
    from argparse import BooleanOptionalAction # type: ignore[attr-defined] # Python < 3.9
except ImportError:
    BooleanOptionalAction = 'store_true' # type: ignore[misc, assignment] # Python > 3.9

from casters import typecast_factory



STDIN = '==STDIN==' # placeholder for stdin


ArgOptions = Dict[str, Union[str, Type[Action], Callable, List]]


class FunctionSignatureParser(argparse.ArgumentParser):

    def __init__(self, fn: Callable, /, *args: Any, **kwargs: Any) -> None:
        if 'prog' not in kwargs:
            kwargs['prog'] = fn.__name__
        if 'description' not in kwargs:
            kwargs['description'] = inspect.getdoc(fn)
        super().__init__(*args, **kwargs)
        self.params = ParamSigMap(fn)
        self.generate_args()

    def generate_args(self) -> None:
        if self.params.positional_only:
            self.generate_positional_only_args()

        if self.params.positional_or_keyword:
            self.generate_positional_or_keyword_args()

        if self.params.keyword_only:
            self.generate_keyword_only_args()

    def generate_positional_only_args(self) -> None:
        group = self.add_argument_group('positional only args')
        for param in self.params.positional_only:
            name = param.name
            options = self.generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_positional_or_keyword_args(self) -> None:
        group = self.add_argument_group('positional or keyword args')
        for param in self.params.positional_or_keyword:
            name = '--' + param.name.replace('_', '-')
            options = self.generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_keyword_only_args(self) -> None:
        group = self.add_argument_group('keyword only args')
        for param in self.params.keyword_only:
            name = '--' + param.name.replace('_', '-')
            options = self.generate_arg_options(param)
            group.add_argument(name, **options)

    def parse_fn_args(self, raw_args: List[str]) -> Tuple[Tuple, Dict[str, Any]]:
        # load stdin to first arg with type TextIO or else first positional-[only/or-kw]
        raw_args = insert_stdin(raw_args, self.params)
        print('raw args', raw_args)
        known_args, pos_or_kw_args = super().parse_known_args(raw_args)
        print('parse fn args', known_args, pos_or_kw_args)
        cmd_args = vars(known_args)
        args = []
        kwargs = {}

        # Parser will have already failed if these are missing
        for param in self.params.positional_only:
            value = cmd_args[param.name]
            args.append(value)

        # Reconcile which args are kw and which are positional
        for param in self.params.positional_or_keyword:
            print('loop unknown pargs', param, pos_or_kw_args)
            if param.name in cmd_args and cmd_args[param.name] is not None:
                kwargs[param.name] = cmd_args[param.name]
            else:
                try: # No idea if this is sane
                    value = pos_or_kw_args.pop(0)
                    if value == STDIN:
                        value = sys.stdin.read().rstrip()
                    else:
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
        if pos_or_kw_args:
            self.error(f"unrecognized arguments: {', '.join(pos_or_kw_args)}")

        for param in self.params.keyword_only:
            if param.name in cmd_args:
                kwargs[param.name] = cmd_args[param.name]

        for param in self.params.required:
            if param.name not in cmd_args:
                self.error(f"the following arguments are required: {param.name}")
        print('end', args, kwargs)
        return tuple(args), kwargs


    def generate_arg_options(self, param: Parameter) -> Dict[str, Any]:
        options: ArgOptions = {}
        helptext = []

        typecast = typecast_factory(param)
        if typecast is not None:
            helptext.append(typecast.__name__)

        # Boolean actions are incompatible with type options
        if param.annotation == bool or isinstance(param.default, bool):
            if param in self.params.positional_only:
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
        elif param in self.params.positional_or_keyword:
            # Try to make it more obvious these can also be positional
            options['metavar'] = f'/ {param.name}'
        elif param in self.params.keyword_only:
            options['metavar'] = ''

        options['help'] = ' '.join(helptext)
        return options


class ParamSigMap:
    def __init__(self, fn: Callable) -> None:
        self._param_signatures = inspect.signature(fn).parameters

        self.all = []
        self.positional_only = []
        self.positional_or_keyword = []
        self.keyword_only = []
        self.required = []
        self.stdin = None
        self.stdin_index = None
        for i, param in enumerate(self._param_signatures.values()):
            self.all.append(param)
            if param.kind == ParameterKind.POSITIONAL_ONLY:
                self.positional_only.append(param)
            if param.kind == ParameterKind.POSITIONAL_OR_KEYWORD:
                self.positional_or_keyword.append(param)
            if param.kind == ParameterKind.KEYWORD_ONLY:
                self.keyword_only.append(param)
            if self.stdin is None and param.annotation in (TextIO, TextIOWrapper):
                self.stdin = param
            if param.default is param.empty:
                self.required.append(param)

        # If no param has claimed TextIO stream data
        # only assign if we have non-kw-only params
        if self.stdin is None and self.keyword_only != self.all:
            self.stdin = self.all[0]

        # If stdin param is positional only, record the correct index
        # for stdin args (we'll append as kwarg otherwise)
        if self.stdin is not None and self.stdin not in self.keyword_only:
            self.stdin_index = self.all.index(self.stdin)


def insert_stdin(raw_args: List[str], params: ParamSigMap) -> List[str]:

    if sys.stdin.isatty() or params.stdin is None:
        return raw_args
    if params.stdin_index is not None:
        raw_args.insert(params.stdin_index, STDIN)
    else:
        name = '--' + params.stdin.name.replace('_', '-')
        raw_args.append(name)
        raw_args.append(STDIN)
    return raw_args

