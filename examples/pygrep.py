from re import Match, Pattern # typing.Match/Pattern also works
from typing import TextIO, Iterator # io.TextIOBase/TextIOWrapper also works


# Protected & private names (prefixed with _ or __) won't be sourced by default
# We can also use `__all__` to achieve the same effect
_CSI = '\x1B['
_HL_START = _CSI + '\033[1m\033[91m'
_HL_END = _CSI + '0m'

def _highlight(matchobj: Match) -> str:
    """Simple highlighter for our grep function"""
    return _HL_START + matchobj.group(0) + _HL_END



def pygrep(pattern: Pattern, grepdata: list[TextIO]) -> Iterator[str]:
    """A tiny grep implementation. When run as a 'shell-native' function via
    Sourcepy, arguments will be converted to their annotated types automatically.
    The function doesn't need to implement 'how', it specifies the kinds of
    objects it expects and Sourcepy will take care of the rest.

    Usage:
        `$ pygrep [pattern] [file(s)...]`
        `$ pygrep [pattern] < [stdin]`
        `$ [stdin] | pygrep [pattern]`
        `$ pygrep --help`

    Args:
        pattern (Pattern): The first cmd argument will be compiled into a re.Pattern
            object and passed into this function
        grepdata (list[TextIO]): The second argument will turn any number of filepaths
            into open file handles. Sourcepy runs functions inside a context manager
            that can safely open and close file handles, so we don't need to worry about
            it here. If data is passed via stdin, it will be used instead - in this
            case it will appear as a single item list to match the expected type.

    Returns:
        Iterator[str]: A return type isn't actually required for Sourcepy here, the return
        types of objects can generally be inferred automatically. In the case of iterators
        or generators, each item yielded will be printed to the console.
    """
    for file in grepdata:
        prefix = f'{file.name}:' if len(grepdata) > 1 else ''
        for line in file:
            if pattern.search(line):
                yield prefix + pattern.sub(_highlight, line.rstrip())
