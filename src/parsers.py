import argparse
import inspect
import sys

from argparse import Action, _ArgumentGroup as ArgumentGroup
from collections.abc import Callable, ValuesView
from inspect import Parameter
from io import TextIOWrapper
from typing import (
    Any, Dict, List, Literal, Optional, TextIO, Tuple, Type,
    TypedDict, Union, get_args, get_origin
)

from casters import typecast_factory

# Fall back on regular boolean action < Python 3.9
if sys.version_info >= (3, 9):
    from argparse import BooleanOptionalAction
else:
    BooleanOptionalAction = 'store_true'



STDIN = '==STDIN==' # placeholder for stdin


class ArgOptions(TypedDict, total=False):
    default: Optional[str]
    action: Union[str, Type[Action]]
    choices: Optional[List]
    metavar: str
    type: Union[Callable[[str], Any], argparse.FileType]
    help: str


class FunctionSignatureParser(argparse.ArgumentParser):

    def __init__(self, fn: Callable, /, *args: Any, **kwargs: Any) -> None:
        if 'prog' not in kwargs:
            kwargs['prog'] = fn.__name__
        if 'description' not in kwargs:
            kwargs['description'] = inspect.getdoc(fn)
        super().__init__(*args, **kwargs)
        self.params = inspect.signature(fn).parameters.values()
        self.groups: Dict[str, ArgumentGroup] = {}
        self.generate_args()

    def generate_args(self) -> None:
        if params := positional_only(self.params):
            title = 'positional only'
            self.groups[title] = self.make_args_group(title, params)

        if params := positional_or_keyword(self.params):
            title = 'positional or keyword'
            self.groups[title] = self.make_args_group(title, params)

        if params := keyword_only(self.params):
            title = 'keyword only'
            self.groups[title] = self.make_args_group(title, params)

    def make_args_group(self, title: str, params: List[Parameter]) -> ArgumentGroup:
        group = self.add_argument_group(f'{title} args')
        for param in params:
            if param in positional_only(params) and param is not stdin_target(params):
                # If stdin is targeting a positional only arg, make into
                # option (i.e. --foo) to avoid positional parsing ambiguities.
                # We'll restore position during parsing
                name = param.name
            else:
                name = '--' + param.name.replace('_', '-')
            options: ArgOptions = {}
            options['default'] = self.options_default(param)
            if (action := self.options_action(param)) is not None:
                options['action'] = action
            options['choices'] = self.options_choices(param)
            options['metavar'] = self.options_metavar(param)

#             if options.get('action') != BooleanOptionalAction:
#                 if (option_type := self.options_type(param)) is not None:
#                     options['type'] = option_type

            helptext = []
            if option_type := options.get('type'):
                helptext.append(option_type.__name__)
            if param.default is not param.empty:
                helptext.append(f'(default: {param.default})')
            else:
                helptext.append('(required)')
            options['help'] = ' '.join(helptext)

            group.add_argument(name, **options)
        return group

    def options_default(self, param: Parameter) -> Optional[str]:
        if param is stdin_target(self.params):
            return STDIN
        # work around https://bugs.python.org/issue46080
        if set(sys.argv).isdisjoint({'-h', '--help'}):
            return argparse.SUPPRESS
        return None

    def options_action(self, param: Parameter) -> Optional[Union[str, Type[Action]]]:
        if bool in (param.annotation, type(param.default)):
            if param not in positional_only(self.params):
                return BooleanOptionalAction
        return None

    def options_choices(self, param: Parameter) -> Optional[List]:
        if bool in (param.annotation, type(param.default)):
            if param in positional_only(self.params):
                choices = ['true', 'false']
                return choices
        if get_origin(param.annotation) is Literal:
            choices = list(get_args(param.annotation))
            return choices
        return None

    def options_metavar(self, param: Parameter) -> str:
        if param in positional_only(self.params):
            return param.name
        if param in positional_or_keyword(self.params):
            return f'/ {param.name}'
        return ''

    def options_type(self, param: Parameter) -> Optional[Callable]:
        is_stdin = param is stdin_target(self.params)
        typecast = typecast_factory(param, is_stdin)
        return typecast

    def make_raw_arg(self, param: Parameter, value: str) -> List[str]:
        # Inspect options args (self._action_groups[1]) to determine type & flag name
        action_group = self.groups['positional or keyword']
        target = next(a for a in action_group._actions if a.dest == param.name)
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
        name = next(iter(names))
        return [name, value]

    def parse_ambiguous_args(self, raw_args: List[str]) -> Dict[str, Any]:
        known, unknown = self.parse_known_args(raw_args)
        # pos_or_kw args passed as positional args will likely end up in "unknown"
        # We determine what they are here, then re-parse those args in order to
        # re-run argparse's built in type casting & error checking
        remaining = []
        for param in positional_or_keyword(self.params):
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
        for param in required(self.params):
            if param.name not in parsed:
                self.error(f"the following arguments are required: {param.name}")

        args: List = []
        kwargs: Dict[str, Any] = {}
        for param in self.params:
            if param.name not in parsed:
                continue
            value = parsed[param.name]
            if isinstance(value, str):
                typecast = self.options_type(param)
                try:
                    value = typecast(value)
                except (TypeError, ValueError):
                    self.error(f"invalid {typecast.__name__} value: {value}")
            if param not in positional_only(self.params):
                kwargs[param.name] = value
            elif param is stdin_target(self.params):
                    # Put pos only stdin arg back where it belongs
                target_index = positional_only(self.params).index(param)
                args.insert(target_index, value)
            else:
                args.append(value)

        return tuple(args), kwargs


def positional_only(params: Union[List, ValuesView]) -> List[Parameter]:
    return [p for p in params if p.kind is p.POSITIONAL_ONLY]


def positional_or_keyword(params: Union[List, ValuesView]) -> List[Parameter]:
    return [p for p in params if p.kind is p.POSITIONAL_OR_KEYWORD]


def keyword_only(params: Union[List, ValuesView]) -> List[Parameter]:
    return [p for p in params if p.kind is p.KEYWORD_ONLY]


def required(params: Union[List, ValuesView]) -> List[Parameter]:
    return [p for p in params if p.default is p.empty]


def stdin_target(params: Union[List, ValuesView]) -> Optional[Parameter]:
    for p in params:
        if sys.stdin.isatty():
            return None
        if p.annotation in (TextIO, TextIOWrapper):
            return p
    if len(params) == len(keyword_only(params)):
        return None
    return next(iter(params))
