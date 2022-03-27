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

* Function parameters are automatically converted into command line options
* Type hints can be used to coerce command line arguments into their
corresponding types
* Data can be passed to functions from stdin, either implicitly or explicitly
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
def fileexists(file: Path):
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
import lxml.html # requires lxml to be installed

__all__ = ['pagetitle']

class HTML(lxml.html.HtmlElement):
    def __new__(cls, html_string, *args, **kwargs):
        return lxml.html.fromstring(html_string)

def pagetitle(html: HTML):
    return html.find('.//title').text
```
```shell
$ source pagetitle.py
$ pagetitle "<html><title>This is pretty nifty</title></html>"
This is pretty nifty
$ curl -s https://github.com | pagetitle
GitHub: Where the world builds software · GitHub
```



