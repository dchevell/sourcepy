# Sourcepy

**Sourcepy** is a tool that allows you to `source` Python files straight from
your shell, and use their functions and variables natively. It uses Python's
inspect and importlib machinery to build shims and can leverage type hints for
additional features.

Sourcepy can use type hint annotations to support type coercion of command line
arguments into native types. It understands positional-only,
positional-or-keyword, and keyword-only arguments to give you the full power
and flexibility of your Python functions natively from your shell.

## Example

```python
# pygrep.py
from re import Pattern
from typing import TextIO

def pygrep(pattern: Pattern, grepdata: list[TextIO]):
    """
    A minimal grep implementation in Python
    illustrating some of Sourcepy's features.
    """
    for file in grepdata:
        prefix = f'{file.name}:' if len(grepdata) > 1 else ''
        for line in file:
            if pattern.search(line):
                yield line
```
```shell
$ source pygrep.py
$ pygrep "implementation" pygrep.py
    A minimal grep implementation in Python
$ pygrep --help
usage: pygrep [-h] [--pattern / pattern] [--grepdata [/ grepdata ...]]

A minimal grep implementation in python that illustrates some
interesting Sourcepy features

options:
  -h, --help                   show this help message and exit

positional or keyword args:
  --pattern / pattern          Pattern (required)
  --grepdata [/ grepdata ...]  file(s) / stdin (required)
$ echo "one\ntwo\nthree" | pygrep --pattern "o"
one
two
$ MYVAR=$(echo $RANDOM | pygrep "\d")
$ echo $MYVAR
26636
$ MYVAR=$(pygrep "I hope errors go to stderr" thisfiledoesnotexist)
usage: pygrep [-h] [--pattern / pattern] [--grepdata [/ grepdata ...]]
pygrep: error: invalid literal for list[typing.TextIO]: ['thisfiledoesnotexist']
$ echo $MYVAR

$
```

## Features

Sourcepy provides a number of features to bridge the gap between Python and
shell semantics to give you the full power and flexibility of your Python
functions natively from your shell.

### Dynamically generated argument parsing

Function parameters are automatically converted into command line options.
Sourcepy supports positional only arguments, positional or keyword arguments and
keyword only arguments, and implements specialised handling for each type.
Where python requires specific ordering for positional arguments vs keyword
arguments, shell programs often allow these to be intermixed.

### Type handling

Type hints can be used to coerce command line arguments into their
corresponding types

### IO

Sourcepy allows implicit support for stdin for any function without requiring
explicit annotations, and will read and pass text stream data to the first
non-keyword-only parameter. Explicitly supplying IO typehints (e.g.
`typing.TextIO`, `typing.IO[bytes]`, `io.TextIOBase`, etc.) allows for
supporting some advanced features:
* File paths passed as function arguments are converted into open file handles.
  Function calls are wrapped inside a context manager that safely opens and
  closes file handles outside of the lifecycle of the function.
* Text and binary data are both supported, using the appropriate types from the
  `typing` or `io` modules.
* When an IO typehint is supplied, stdin will be routed to that argument instead
  of the first whenever a tty is not detected. If multiple typehints have IO
  annotations the first one will be selected.
* IO type annotations can be wrapped in Sequence or Set containers, e.g.
  `list[typing.IO[str]]` or `tuple[typing.TextIO, typing.BinaryIO]`. If stdin
  targets an IO type inside a container, only a single item container will be
  supplied (note that the tuple example here would fail in this scenario).

* Positional, positional-or-keyword, and keyword-only args are natively
  supported


## Requirements

Sourcepy requires 3.8+ or greater. It has no external dependencies and relies
only on importlib, inspect & typing machinery from the standard library.

Sourcepy works best with modern shells, e.g. Zsh or Bash 4+

## Installation

### Clone this repository - recommended

The easiest way to install Sourcepy is to clone this repository to a folder on
your local machine:

```
git clone https://github.com/dchevell/sourcepy.git ~/.sourcepy
```

Then simply add `source ~/.sourcepy/sourcepy.sh` to your shell profile, e.g.
`.zprofile` or `.bash_profile`. If you'd prefer to clone this folder to a
different location you can, however a `~/.sourcepy` folder will still be
created to generate module stubs when sourcing python files.

## More examples

You can do a lot with Sourcepy. Here's an example of using type hints to coerce
shell arguments into native types:

```python
# demo.py
def multiply(a: int, b: int) -> int:
    """Sourcepy will coerce incoming values to ints
    or fail if input is invalid"""
    return a * b
```
```shell
$ source demo.py
$ multiply 3 4
12

$ multiply a b
usage: multiply [-h] [--a / a] [--b / b]
multiply: error: invalid literal for <class 'int'>: a
```
```python
# demo.py
def fileexists(file: Path) -> bool:
    """Values will be converted into Path objects. Booleans
    will be converted to shell equivalents (lowercase)"""
    return file.exists()
```
```shell
$ fileexists domath.py
true
$ fileexists dontmath.py
false
```

For data types that can't be loaded directly with a single argument constructor
(`mytype(arg)`), you can create a class that takes a single
parameter to do this for you. There are many potential approaches to this,
whether you're constructing an object in an `__init__` method or subclassing
an object and overriding `__new__`

```python
# pagetitle.py
from lxml.html import HtmlElement, fromstring as htmlfromstring

__all__ = ['pagetitle']

class HTML(HtmlElement):
    def __new__(cls, html_string, *args, **kwargs) -> HtmlElement:
        return htmlfromstring(html_string)

def pagetitle(html: HTML) -> str:
    return html.find('.//title').text
```
```shell
$ source pagetitle.py
$ pagetitle "<html><title>This is pretty nifty</title></html>"
This is pretty nifty
$ curl -s https://github.com | pagetitle
GitHub: Where the world builds software · GitHub
```



