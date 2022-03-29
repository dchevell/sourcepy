"""pygrep is a minimal grep implementation that illustrates a number of
interesting Sourcepy features.

Note that aside from declaring its argument types accurately the
`pygrep` function contains no special implementation details related to
Sourcepy. As presented below, it's a plain python function that expects
to receive a re.Pattern object and a list of file handles / IO text
streams.

Type annotations

    Type annotations allow for values passed from the command line to be
    cast to appropriate types automatically. They are also used in the
    generation of help messages (described further below).

    There are only two type annotations required for this example:

        re.Pattern
            The command line argument passed for this value will be
            compiled into a re.Pattern object.
            Note: re.Pattern[str/bytes], typing.Pattern, and
            typing.Pattern[str/bytes] are also supported, although
            typing.Pattern is deprecated in Python 3.10).

        list[typing.TextIO]
            Command line arguments passed for this value will be checked
            for valid file paths, and returned as a container of open
            file handles inside the specified container type. If passing
            data via stdin, a single item container with the stdin
            handle will be returned. When run from the command line
            Sourcepy will wrap the function call inside a context
            manager that opens and closes file handles is handled
            automatically.
            Note: typing.IO[str], io.TextIOBase, and io.TextIOWrapper
            are also supported, as are their binary/bytes equivalents.

    Return types of functions can generally be inferred automatically,
    and the type annotations supplied for the `_highlight` helper
    function are included in this example only for completeness.

Iterators and Generators

    If a function returns an iterator or generator, i.e. it yields
    values as it runs rather than returning a value after completion,
    Sourcepy will print each yielded value to stdout as it is received.
    In this example, piping the live output of another function (e.g.
    tailing logs) would result in the expected behaviour of a stream of
    grep matches being printed in real time.

Parameter kinds

    Python function parameters allow arguments to be specified by
    position or keyword, but may be set to positional only or keyword
    only. Sourcepy will detect these and require them to be specified as
    their shell-native equivalents, where positional arguments are
    passed directly and keyword arguments are passed with an option flag
    (e.g. passing a value for param_name as a keyword argument would
    require setting `--param-name value` or `--param-name=value` in the
    shell). Positional or keyword arguments can be specified in either
    fashion and Sourcepy will reconcile these as needed.
    Note: whilst Python does not allow keyword arguments to be specified
    in front of positional arguments, shell programs generally do allow
    this and Sourcepy allows for this as well to provide semantically
    correct behaviour in the shell. This can create some ambiguous cases
    where multiple list types are involved. These are difficult to
    detect and exhaustive coverage of edge cases is not possible.
    Sourcepy will not prevent the usage of such functions and avoiding
    problematic function signatures is left as an exercise to the
    reader.

Help

    Functions or methods sourced to the shell will generate a `--help`
    flag that prints information about the function:

        Description
            If the function contains a docstring this will be printed at
            the beginning of the help message.

        Parameter kinds:
            If parameters have been specified as positional only or
            keyword only, they will be listed as separate arguments
            groups.

        Defaults
            If a parameter contains a default value, this will be printed in the
            option help text. If no default value exists, that option will be
            noted as required.

        Types
            Parameters annotated with type hints will show a readable text string
            next to their option help text showing the acceptable type(s).

Sourceable objects

    Sourcepy will attempt to exclude any names that were imported from
    being sourced. There are some edge cases, e.g. importing raw string
    values, that cannot easily be excluded in this way, however these
    are only likely to occur when using star imports (`from module
    import *`). If there are names that are not intended to be available
    from the shell, they can be excluded in one of two ways:

        1. Protected and private names (those beginning with '_' or
        '__') are automatically excluded by default. This can be seen in
        the example below: the constants and helper function used to
        allow pygrep to highlight matches are prefixed with underscores,
        so `source pygrep.py` will only source the `pygrep` function.

        2. If more explicit control is desired, defining the standard
        `__all__` variable with a list of names to be exported will
        cause Sourcepy to source all names defined here (including
        protected and private names)

"""

from re import Match, Pattern
from typing import TextIO, Iterator


_CSI = '\x1B['
_HL_START = _CSI + '\033[1m\033[91m'
_HL_END = _CSI + '0m'


def _highlight(matchobj: Match) -> str:
    """Simple highlighter for our grep function"""
    return _HL_START + matchobj.group(0) + _HL_END


def pygrep(pattern: Pattern, grepdata: list[TextIO]) -> Iterator[str]:
    """A minimal grep implementation in python that illustrates
    some interesting Sourcepy features"""
    for file in grepdata:
        prefix = f'{file.name}:' if len(grepdata) > 1 else ''
        for line in file:
            if pattern.search(line):
                yield prefix + pattern.sub(_highlight, line)
