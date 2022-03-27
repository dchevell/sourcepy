import argparse
import contextlib
import inspect
import sys

from argparse import Action, _ArgumentGroup as ArgumentGroup
from collections.abc import Callable, ValuesView
from inspect import Parameter
from pathlib import Path
from typing import (
    Any, Dict, IO, Iterator, List, Literal, Optional,
    Tuple, Type, TypedDict, Union, get_args, get_origin
)

from casters import cast_to_type, issubtype, isio, istextio, get_typehint_name

# Fall back on regular boolean action < Python 3.9
if sys.version_info >= (3, 9):
    from argparse import BooleanOptionalAction
else:
    BooleanOptionalAction = 'store_true'



STDIN = '==STDIN==' # placeholder for stdin

Mode = Literal['r', 'rb', 'w', 'wb']
FileHandles = Union[IO[Any], List[IO[Any]]]
FilePaths = Union[Path, List[Path]]
NumArgs = Optional[Union[int, Literal['*']]]
OptionsAction = Optional[Union[str, Type[Action]]]
OptionsNargs = Optional[Union[int, str]]
ParamsList = Union[List[Parameter], ValuesView[Parameter]]
ParserContextManager = Iterator[Tuple[Tuple[Any, ...], Dict[str, Any]]]


class ArgOptions(TypedDict, total=False):
    default: str
    action: Union[str, Type[Action]]
    choices: List[Any]
    metavar: str
    nargs: Union[int, str]
    help: str


class MoreIndentFormatter(argparse.RawTextHelpFormatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if 'max_help_position' not in kwargs:
            kwargs['max_help_position'] = 36
        super().__init__(*args, **kwargs)


class FunctionParameterParser(argparse.ArgumentParser):

    def __init__(self, fn: Callable[[Any], Any], /, *args: Any, **kwargs: Any) -> None:
        if 'prog' not in kwargs:
            kwargs['prog'] = fn.__name__
        if 'description' not in kwargs:
            kwargs['description'] = inspect.getdoc(fn)
        if 'formatter_class' not in kwargs:
            kwargs['formatter_class'] = MoreIndentFormatter
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
            if default := self.options_default(param):
                options['default'] = default
            if action := self.options_action(param):
                options['action'] = action
            if choices := self.options_choices(param):
                options['choices'] = choices
            if metavar := self.options_metavar(param):
                options['metavar'] = metavar
            if nargs := self.options_nargs(param):
                options['nargs'] = nargs
            if helptext := self.options_help(param):
                options['help'] = helptext
            group.add_argument(name, **options)
        return group

    def options_default(self, param: Parameter) -> Optional[str]:
        if param is stdin_target(self.params):
            return STDIN
        # work around https://bugs.python.org/issue46080
        if set(sys.argv).isdisjoint({'-h', '--help'}):
            return argparse.SUPPRESS
        return None

    def options_action(self, param: Parameter) -> OptionsAction:
        if isbooleanaction(param) and param not in positional_only(self.params):
            return BooleanOptionalAction
        return None

    def options_choices(self, param: Parameter) -> Optional[List[Any]]:
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

    def options_nargs(self, param: Parameter) -> OptionsNargs:
        nargs = get_nargs(param)
        if nargs == '*' and param not in positional_only(self.params)[:-1]:
            return '*'
        return nargs

    # pylint: disable=R0201
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

    @contextlib.contextmanager
    def parse_fn_args(self, raw_args: List[str]) -> ParserContextManager:
        parsed = self.parse_ambiguous_args(raw_args)
        for param in required(self.params):
            if param.name not in parsed:
                self.error(f"the following arguments are required: {param.name}")

        open_handles = []
        args: List[Any] = []
        kwargs: Dict[str, Any] = {}
        for param in self.params:
            if param.name not in parsed:
                continue
            try:
                value = self.typecaster(parsed[param.name], param)
            except (ValueError, TypeError) as e:
                self.error(str(e))
            if isio(param.annotation) and sys.stdin.isatty():
                mode: Mode = 'r' if istextio(param.annotation) else 'rb'
                value = open_file_args(value, mode=mode)
                open_handles.extend(value if isinstance(value, list) else [value])

            if param not in positional_only(self.params):
                kwargs[param.name] = value
            elif param is stdin_target(self.params):
                    # Put pos only stdin arg back where it belongs
                target_index = positional_only(self.params).index(param)
                args.insert(target_index, value)
            else:
                args.append(value)
        try:
            yield tuple(args), kwargs
        finally:
            for handle in open_handles:
                handle.close()

    def parse_ambiguous_args(self, raw_args: List[str]) -> Dict[str, Any]:
        known, unknown = self.parse_known_args(raw_args)
        parsed = vars(known)
        # pos_or_kw args passed as positional args will end up in "unknown"
        # We determine what they are here and manually add them to our parsed args
        unused_params = []
        for param in positional_or_keyword(self.params):
            if param.name not in parsed:
                unused_params.append(param)
        for param in unused_params:
            nargs = get_nargs(param)
            if nargs is None:
                try:
                    parsed[param.name] = unknown.pop(0)
                except IndexError:
                    break
            else:
                args_range = None if nargs == '*' else nargs
                value = unknown[:args_range]
                del unknown[:args_range]
                if value:
                    parsed[param.name] = value

        # if more values exist, too many args were supplied
        if unknown:
            self.error(f"unrecognised arguments: {' '.join(unknown)}")
        return parsed

    def typecaster(self, value: Any, param: Parameter) -> Any:
        if not isinstance(value, (str, list)):
            return value
        typehint = get_typehint(param)
        strict = typehint is param.annotation
        implicit_stdin = None
        if param is stdin_target(self.params) and not isio(typehint):
            implicit_stdin = sys.stdin.read().rstrip()
        if implicit_stdin is not None:
            value = implicit_stdin
        return cast_to_type(value, typehint, strict=strict)


def positional_only(params: ParamsList) -> List[Parameter]:
    return [p for p in params if p.kind is p.POSITIONAL_ONLY]


def positional_or_keyword(params: ParamsList) -> List[Parameter]:
    return [p for p in params if p.kind is p.POSITIONAL_OR_KEYWORD]


def keyword_only(params: ParamsList) -> List[Parameter]:
    return [p for p in params if p.kind is p.KEYWORD_ONLY]


def required(params: ParamsList) -> List[Parameter]:
    return [p for p in params if p.default is p.empty]


def stdin_target(params: ParamsList) -> Optional[Parameter]:
    for param in params:
        if sys.stdin.isatty():
            return None
        if isio(param.annotation):
            return param
    if len(params) == len(keyword_only(params)):
        return None
    return next(iter(params))


def isbooleanaction(param: Parameter) -> bool:
    return bool in (param.annotation, type(param.default))


def get_nargs(param: Parameter) -> NumArgs:
    typehint = get_typehint(param)
    if issubtype(typehint, (list, set)):
        return '*'
    if issubtype(typehint, tuple):
        member_types = None
        types = [typehint]
        while member_types is None:
            _type = types.pop(0)
            args = get_args(_type)
            if get_origin(_type) is tuple:
                member_types = args
                break
            types.extend(args)
        if Ellipsis in member_types or len(member_types) == 0:
            return '*'
        return len(member_types)
    return None


def get_typehint(param: Parameter) -> Type[Any]:
    if param.annotation not in(param.empty, Any):
        return param.annotation
    if param.default is not param.empty:
        return type(param.default)
    return param.empty


def open_file_args(value: FilePaths, mode: Mode = 'r') -> FileHandles:
    if isinstance(value, list):
        return [v.open(mode=mode) for v in value]
    return value.open(mode=mode)
