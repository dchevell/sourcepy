import argparse
import inspect
import sys

from argparse import Action
from collections.abc import Callable, Collection
from inspect import _ParameterKind as ParameterKind, Parameter
from io import TextIOWrapper
from typing import Any, Dict, List, Literal, Union, TextIO, Tuple, Type, get_args, get_origin

# Fall back on regular boolean action < Python 3.9
if sys.version_info >= (3, 9):
    from argparse import BooleanOptionalAction
else:
    BooleanOptionalAction = 'store_true'

from casters import typecast_factory



STDIN = '==STDIN==' # placeholder for stdin


ArgOptions = Dict[str, Union[str, Type[Action], Callable, Collection]]


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
        if self.params.pos_only:
            self.generate_pos_only_args()

        if self.params.pos_or_kw:
            self.generate_pos_or_kw_args()

        if self.params.kw_only:
            self.generate_kw_only_args()

    def generate_pos_only_args(self) -> None:
        group = self.add_argument_group('positional only args')
        for param in self.params.pos_only:
            if param is self.params.stdin_target:
                 # If stdin is targeting a positional only arg, make into
                 # option (i.e. --foo) to avoid positional parsing ambiguities.
                 # We'll restore position during parsing
                name = '--' + param.name.replace('_', '-')
            else:
                name = param.name
            options = self.generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_pos_or_kw_args(self) -> None:
        group = self.add_argument_group('positional or keyword args')
        for param in self.params.pos_or_kw:
            name = '--' + param.name.replace('_', '-')
            options = self.generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_kw_only_args(self) -> None:
        group = self.add_argument_group('keyword only args')
        for param in self.params.kw_only:
            name = '--' + param.name.replace('_', '-')
            options = self.generate_arg_options(param)
            group.add_argument(name, **options)

    def generate_arg_options(self, param: Parameter) -> Dict[str, Any]:
        options: ArgOptions = {}
        helptext = []

        is_stdin = param is self.params.stdin_target
        if is_stdin:
             # We use this placeholder rather than sys.stdin so we can choose whether
             # to return an open handle or resolve its content implicitly
            options['default'] = STDIN
        # work around https://bugs.python.org/issue46080
        elif set(sys.argv).isdisjoint({'-h', '--help'}):
            options['default'] = argparse.SUPPRESS

        typecast = typecast_factory(param, is_stdin)
        if typecast is not None:
            helptext.append(typecast.__name__)

        # Boolean actions are incompatible with type options
        if param.annotation == bool or isinstance(param.default, bool):
            if param in self.params.pos_only:
                options['choices'] = ['true', 'false']
                options['metavar'] = param.name
            else:
                # this nicer --option / --no-option helper
                # can only be usedwith kwargs
                options['action'] = BooleanOptionalAction
        elif typecast is not None and options.get('type') is None:
            options['type'] = typecast

        if get_origin(param.annotation) is Literal:
            options['choices'] = get_args(param.annotation)

        if param.default is not param.empty:
            helptext.append(f'(default: {param.default})')
        else:
            helptext.append('(required)')


        if options.get('action') == BooleanOptionalAction:
            pass # Don't set metavar for bools
        elif param in self.params.pos_or_kw:
            # Try to make it more obvious these can also be positional
            options['metavar'] = f'/ {param.name}'
        elif param in self.params.kw_only:
            options['metavar'] = ''

        options['help'] = ' '.join(helptext)
        return options

    def make_raw_arg(self, param: Parameter, value: str) -> List[str]:
        # Inspect options args (self._action_groups[1]) to determine type & flag name
        [target] = [a for a in self._action_groups[1]._actions if a.dest == param.name]
        names: List = list(target.option_strings)
        # Don't use isinstance, we've replaced BooleanOptionalAction with str < 3.9
        if type(target) in (BooleanOptionalAction, argparse._StoreTrueAction):
            valid = ['true', 'false']
            arg_key = dict(zip(valid, names))
            try:
                arg = arg_key[value]
                return [arg]
            except KeyError:
                self.error(f"argument {param.name}: invalid choice: {value} "
                           f"(choose from {', '.join(valid + names)})")
        name = names[0]
        return [name, value]

    def parse_ambiguous_args(self, raw_args: List[str]) -> Dict[str, Any]:
        known, unknown = self.parse_known_args(raw_args)
        # pos_or_kw args passed as positional args will likely end up in "unknown"
        # We determine what they are here, then re-parse those args in order to
        # re-run argparse's built in type casting & error checking
        remaining = []
        for param in self.params.pos_or_kw:
            if hasattr(known, param.name):
                continue
            try:
                value = unknown.pop(0)
            except IndexError:
                break
            arg = self.make_raw_arg(param, value)
            remaining.extend(arg)
        # if more values exist, too many args were supplied
        if unknown:
            self.error(f"unrecognised arguments: {' '.join(unknown)}")
        raw_args.extend(remaining)
        # reparse to complete populating the `known` Namespace
        self.parse_known_args(raw_args, namespace=known)
        return vars(known)

    def parse_fn_args(self, raw_args: List[str]) -> Tuple[Tuple, Dict[str, Any]]:
        parsed = self.parse_ambiguous_args(raw_args)
        for param in self.params.required:
            if param.name not in parsed:
                self.error(f"the following arguments are required: {param.name}")

        args: List = []
        kwargs: Dict[str, Any] = {}
        for param in self.params.all:
            if param.name not in parsed:
                continue
            value = parsed[param.name]
            if param not in self.params.pos_only:
                kwargs[param.name] = value
            elif param is self.params.stdin_target:
                    # Put pos only stdin arg back where it belongs
                target_index = self.params.pos_only.index(param)
                args.insert(target_index, value)
            else:
                args.append(value)

        return tuple(args), kwargs


class ParamSigMap:
    def __init__(self, fn: Callable) -> None:
        self._param_signatures = inspect.signature(fn).parameters
        self.all = []
        self.pos_only = []
        self.pos_or_kw = []
        self.kw_only = []
        self.required = []
        self.stdin_target = None
        for param in self._param_signatures.values():
            self.all.append(param)
            if param.kind == ParameterKind.POSITIONAL_ONLY:
                self.pos_only.append(param)
            if param.kind == ParameterKind.POSITIONAL_OR_KEYWORD:
                self.pos_or_kw.append(param)
            if param.kind == ParameterKind.KEYWORD_ONLY:
                self.kw_only.append(param)
            if param.default is param.empty:
                self.required.append(param)
            if (
                self.stdin_target is None
                and param.annotation in (TextIO, TextIOWrapper)
                and sys.stdin.isatty() is False
            ):
                self.stdin_target = param
        # If no param has claimed TextIO stream data
        # and there are non-kw-only params, assign
        # the first one to be implicit stdin
        if (
            self.stdin_target is None
            and self.kw_only != self.all
            and sys.stdin.isatty() is False
        ):
            self.stdin_target = self.all[0]
