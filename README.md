# Sourcepy

**Sourcepy** is a tool that allows you to `source` Python files straight from
your shell, and use their functions and variables natively. It uses Python's
inspect and importlib machinery to transform plain Python functions into
fully featured shell programs without requiring custom code, and leverages
powerful type hint introspection to convert shell values into Python objects.


## Example

```python
# pygrep.py
from re import Pattern
from typing import TextIO

def pygrep(pattern: Pattern, grepdata: list[TextIO]):
    """A minimal grep implementation in Python
    """
    for file in grepdata:
        prefix = f'{file.name}:' if len(grepdata) > 1 else ''
        for line in file:
            if pattern.search(line):
                yield prefix + line
```
```shell
$ source pygrep.py
$ pygrep "implementation" pygrep.py
    """A minimal grep implementation in Python
$ pygrep --help
usage: pygrep [-h] [-p Pattern] [-g [file/stdin ...]]

A minimal grep implementation in Python

options:
  -h, --help                 show this help message and exit

positional or keyword args:
  pattern (-p, --pattern)    Pattern (required)
  grepdata (-g, --grepdata)  [file/stdin ...] (required)
$ echo "one\ntwo\nthree" | pygrep --pattern "o"
one
two
$ MYVAR=$(echo $RANDOM | pygrep "\d")
$ echo $MYVAR
26636
$ MYVAR=$(pygrep "I hope errors go to stderr" thisfiledoesnotexist)
usage: pygrep [-h] [-p Pattern] [-g [file/stdin ...]]
pygrep: error: argument grepdata: invalid [file/stdin ...] value: ("thisfiledoesnotexist")
$ echo $MYVAR

$
```


## Features

Sourcepy provides a number of features to bridge the gap between Python and
shell semantics to give you the full power and flexibility of your Python
functions natively from your shell.

### Source python functions & variables natively in your shell

Functions and variables sourced from Python files are available directly in the
shell, just as though you'd sourced a regular shell script. Where possible,
variables are converted into supported shell equivalents: strings, integers,
arrays and associative arrays.

Even class objects are supported, with namespaced methods available from the
shell and values/properties available in an associative array named for the
instance.

### Dynamically generated argument parsing

Function parameters are automatically converted into command line options.
Sourcepy supports positional only arguments, positional or keyword arguments and
keyword only arguments, and implements specialised handling for each type.
Where python requires specific ordering for positional arguments vs keyword
arguments, shell programs often allow these to be intermixed.

### Type handling

Type hints can be used to coerce input values into their corresponding types.
Sourcepy provides extensive support for many possible use cases, including
collections (`list`s, `set`s, `tuple`s etc), `Union`s, IO streams (files and
stdin)

### Stdin support

Sourcepy will detect stdin and implicitly route its contents to the first
parameter of functions. Where greater control is desired, standard `IO` type
hints can be used to target stdin at different arguments and to receive the
`sys.stdin` (text IO) or `sys.stdin.buffer` (binary IO) handles directly.

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

Sourcepy is not a normal package that is installed into a specific environment.
It has no dependencies and can be run by any Python 3.8+ interpreter, so a
more typical use case is to simply `source` files no matter which environment
or virtualenv is active at the time. Sourced files will always call back to the
interpreter that originally sourced them, so you can use it in an environment
agnostic way.

## More examples

### Type casting

```python
# demo.py
def multiply(x: int, y: int) -> int:
    """Sourcepy will coerce incoming values to ints
    or fail if input is invalid"""
    return x * y
```
```shell
$ source demo.py
$ multiply 3 4
12
$ multiply a b
usage: multiply [-h] [-x int] [-y int]
multiply: error: argument x: invalid int value: "a"
```
```python
# demo.py
def fileexists(file: Path) -> bool:
    """Values will be converted into Path objects. Booleans
    will be converted to shell equivalents (lowercase)"""
    return file.exists()
```
```shell
$ fileexists demo.py
true
$ fileexists nemo.py
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

### Variables

```python
# demo.py
MY_INT = 3 * 7
FAB_FOUR = ['John', 'Paul', 'George', 'Ringo']
PROJECT = {'name': 'Sourcepy', 'purpose': 'unknown'}
```
```shell
$ source demo.py
$ echo $MY_INT
21
$ MY_INT=6*7
$ echo $MY_INT
42
$ echo "My favourite drummer is ${FAB_FOUR[-1]}"
My favourite drummer is Ringo
$ echo "This is ${PROJECT[name]} and its primary purpose is ${PROJECT[purpose]}"
This is Sourcepy and its primary purpose is unknown
```

### Class instances

```python
# demo.py
from typing import Optional, Literal

DogActions = Optional[Literal['sit', 'speak', 'drop']]

class Dog:
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    def do(self, action: DogActions = None) -> str:
        if action == 'sit':
            return f'{self.name} sat down'
        if action == 'speak':
            return f'{self.name} said: bark bark bark'
        if action == 'drop':
            return f'{self.name} said: Drop what?'
        return f'{self.name} looked at you expectantly'

pretzel = Dog('Pretzel', 7)
```
```shell
$ source examples/demo.py
$ pretzel.do speak
Pretzel said: bark bark bark
$ pretzel.do
Pretzel looked at you expectantly
$ echo "My dog ${pretzel[name]} is ${pretzel[age]} years old"
My dog Pretzel is 7 years old
$ pretzel.do -h
usage: pretzel.do [-h] [-a {"sit", "speak", "drop"}]

options:
  -h, --help             show this help message and exit

positional or keyword args:
  action (-a, --action)  {"sit", "speak", "drop"} (default: None)
```


## Supported types

Sourcepy provides special handling for many different types to cover a variety
of use cases; some of these are listed below.

Note on typing strictness:

* When explicit type hints exist, if Sourcepy knows the value is invalid for its
target type it will fail and raise an error. If Sourcepy does not know (e.g. a
custom type that does not support a single-argument constructor) then the
original string value will be returned.

* Where no type hints exist, Sourcepy will infer types from any default values.
If the input value can be cast to that type, it will be; if not, the original
string value will be returned.

#### Common types

Sourcepy will cast the vast majority of built in types: `int`, `bool`, `float`,
`str`, `bytes`, etc. Bools are recognised from their lowercase shell form
(`true` or `false`). Arguments that support keyword argumentscan also be set via
special flag-only command-line options, e.g. `--my-arg` or `--no-my-arg`.


#### Collections (lists, tuples, sets, etc)

Sourcepy allows multiple values to be passed for arguments annotated with a
valid collection type such as `list`, `set` or `tuple`. If these contain nested
types, e.g. `list[int]` or `tuple[bool, str]` incoming values will be cast
through the same type introspection pipeline before being returned in the
specified container. `tuple`s, which allow set lengths and multiple nested
types, are fully supported.

For abstract collection-like types (i.e. those defined in `collections.abc`), if
one of these is used rather than a concrete type Sourcepy will return a `list`.

#### JSON

If a single value is passed for a `list` or `dict` annotation (including
`Optional`s or general `Union`s), Sourcepy will attempt to convert the value to
JSON. If successful, and if the resulting value matches the original type, this
is returned (e.g. a `list` type that receives a JSON dictionary will fail).
Otherwise, the value is returned according to general Collections typing rules.
Whilst Collections typing rules allow for subtypes and matching abstract types,
JSON casting will only occur when `list` or `dict` is explicitly present.

#### Unions

Unions are unwrapped and values are tested in order. For example, given the
type `Union[int, str]`, Sourcepy would first attempt to return `int('hello')`,
detect the `ValueError` and subsequently attempt `str('hello')`. If `int` and
`float` are both detected, a tie breaker occurs to ensure `float` wins when the
original value contains decimals.

#### IO

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

#### Literals

Sourcepy supports `typing.Literal` to constrain input values, similar to an
enum. For example, the annotation `operation: Literal['get', 'set', 'del']`
would only accept the listed input values and would raise an error for any
other input values to the `operation` argument.

#### Datetime objects

Sourcepy can cast `datetime.date`, `datetime.datetime` and `datetime.time`
objects from input values. All three types support ISO format strings (i.e.
calling `.fromisoformat(value)` (limited to what the native type supports), and
`date`/`datetime` objects support unix timestamps (i.e. calling
`.fromtimestamp(value)`)

#### Unknown types

If Sourcepy doesn't recognise a type, it will attempt to unwrap the base type
from `Optional`s or `Union`s and pass the raw string value to it as a single
argument. For example, although Sourcepy contains no special handling to
recognise `pathlib.Path` objects, values passed to an argument annotated as
`Path` will be converted to `Path` objects containing the string value (ideally
a valid file path, but that's up to you).

#### Untyped arguments

Where no type annotations are provided, Sourcepy will apply limited casting
behaviour. If a default value is provided, Sourcepy will infer the type from
this value and attempt to cast input to this type, but will return
the original string value in the event of an error. Additionally, values
detected to be integers (`value.isdigit()`) or shell booleans
(`value in ['true', 'false']`) will be cast to these types. This behaviour is
subject to change based on user feedback.
