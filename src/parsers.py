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

from casters import cast_to_type, islist, get_typehint_name

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
    nargs: Union[int, str]
    help: str


class FunctionParameterParser(argparse.ArgumentParser):

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
            options['action'] = self.options_action(param)
            options['choices'] = self.options_choices(param)
            options['metavar'] = self.options_metavar(param)
            options['nargs'] = self.options_nargs(param)
            options['help'] = self.options_help(param)
            options = {k:v for k,v in options.items() if v is not None}
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
        if isbooleanaction(param) and param not in positional_only(self.params):
            return BooleanOptionalAction
        return None

    def options_choices(self, param: Parameter) -> Optional[List]:
        if isbooleanaction(param) and param in positional_only(self.params):
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

    def options_nargs(self, param: Parameter) -> Union[int, str]:
        is_kwarg = param not in positional_only(self.params)
        if islistarg(param) and is_kwarg:
            return '*'
        return None

    def options_help(self, param: Parameter) -> str:
        helptext = []
        typehint = get_typehint(param)
        if typehint:
            name = get_typehint_name(typehint)
            helptext.append(name)
        if param.default is not param.empty:
            helptext.append(f'(default: {param.default})')
        else:
            helptext.append('(required)')
        return ' '.join(helptext)

    def typecast_factory(self, param: Parameter) -> Optional[Callable]:
        typehint = get_typehint(param)
        strict = typehint is param.annotation

        # if implicit stdin, read the value inside closure so we can
        # call it multiple times without getting an empty buffer
        implicit_stdin = None
        if param is stdin_target(self.params) and typehint not in (TextIO, TextIOWrapper):
            implicit_stdin = sys.stdin.read().rstrip()

        def typecaster(value: str) -> Any:
            if implicit_stdin is not None:
                value = implicit_stdin
            return cast_to_type(value, typehint, strict=strict)

        typecaster.__name__ = get_typehint_name(typehint)
        return typecaster


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
        print(known, unknown)
        # pos_or_kw args passed as positional args will likely end up in "unknown"
        # We determine what they are here, then re-parse those args in order to
        # re-run argparse's built in type casting & error checking
        remaining = []
        unused_params = []
        print(known, unknown)
        for param in positional_or_keyword(self.params):
            if not hasattr(known, param.name):
                unused_params.append(param)
        print('unused', unused_params)
        for param in unused_params:
            print('unused loop', param)
            try:
                value = unknown.pop(0)
            except IndexError:
                break
            arg = self.make_raw_arg(param, value)
            remaining.extend(arg)
            print('islast', param is unused_params[-1])
            print('islistarg', islistarg(param))
            if param is unused_params[-1] and islistarg(param):
                remaining.extend(unknown)
                print(param, unknown)
                print('remain', remaining)
                unknown.clear()
        # if more values exist, too many args were supplied
        print(unknown)
        if unknown:
            self.error(f"unrecognised arguments: {' '.join(unknown)}")
        raw_args.extend(remaining)
        # reparse to complete populating the `known` Namespace
        self.parse_known_args(raw_args, namespace=known)
        print(known)
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
            if isinstance(value, (str, list)):
                typecast = self.typecast_factory(param)
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


def get_typehint(param: Parameter) -> Type:
    if param.annotation not in(param.empty, Any):
        return param.annotation
    if param.default is not param.empty:
        return type(param.default)
    return None


def isbooleanaction(param: Parameter) -> bool:
    return bool in (param.annotation, type(param.default))

def islistarg(param: Parameter) -> bool:
    typehint = get_typehint(param)
    return islist(typehint)
