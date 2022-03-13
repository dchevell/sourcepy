# Sourcepy

**Sourcepy** is a tool that allows you to `source` Python files straight from your shell,
and use their functions and variables natively. It uses Python's inspect and importlib
machinery to build shims and can leverage type hints for additional features.


```python
$ cat pagetitle.py
import lxml.html

def getpagetitle(html: str, kwarg: str = None) -> str:
    """ This function receives an HTML document and returns the title tag text """
    if kwarg is not None:
        print(kwarg)
    root = lxml.html.fromstring(html)
    title = root.find('.//title')
    return title.text

$ source pagetitle.py
$ getpagetitle "<html><title>This is pretty nifty</title></html>"
This is pretty nifty
$ getpagetitle --help
usage: getpagetitle [-h] [--html / html] [--kwarg / kwarg]

This function receives an HTML document and returns the title tag text

options:
  -h, --help       show this help message and exit

positional or keyword args:
  --html / html    str (required)
  --kwarg / kwarg  str (default: None)
$ getpagetitle "<html><title>This is pretty nifty</title></html>" --kwarg Hello
Hello
This is pretty nifty
$ TITLE=$(getpagetitle "<html><title>This is pretty nifty</title></html>" \
    --kwarg "I hope print goes to stderr")
I hope print goes to stderr
$ echo $TITLE
This is pretty nifty
$ curl -s https://github.com | getpagetitle --kwarg "Piping from stdin works"
Piping from stdin works
GitHub: Where the world builds software · GitHub
```

Sourcepy can use type hint annotations to support type coercion of command line arguments
into native types. It understands positional-only, positional-or-keyword, and keyword-only
arguments to give you the full power and flexibility of your Python functions natively from
your shell.

## Features

Sourcepy provides a number of features to bridge the gap between Python and shell
semantics to give you the full power and flexibility of your Python functions natively
from your shell.

* Function parameters are automatically converted into command line options
* positional, positional-or-keyword, and keyword-only args are natively supported
* Type hints can be used to coerce command line arguments into their corresponding types

## Requirements

Sourcepy requires 3.8+ or greater. It has no external dependencies and relies only on
importlib, inspect & typing machinery from the standard library.

## Installation

### Clone this repository - recommended

The easiest way to install Sourcepy is to clone this repository to a folder on your local
machine:

```
git clone https://github.com/dchevell/sourcepy.git ~/.sourcepy
```

Then simply add `source ~/.sourcepy/sourcepy.sh` to your shell profile, e.g. `.zprofile`
or `.bash_profile`. If you'd prefer to clone this folder to a different location you can,
however a `~/.sourcepy` folder will still be created to generate module stubs when
sourcing python files.

## Further examples

You can do a lot with Sourcepy. Here's an example of using type hints to coerce shell
arguments into native types:

```python
$ cat domath.py
# Sourcepy will coerce incoming values to ints, or fail if input is invalid
def multiply(a: int, b: int) -> int:
    return a * b

$ source domath.py
$ multiply 3 4
12
```

For data types that can't be loaded directly with a call to `mytype(arg)`, you can create
a class that takes a single `__init__` parameter to do this for you. Let's say we wanted
to build an alternative to `jq` to parse some JSON, rather than build this logic into our
function we could create a `JSON` type that subclasses `dict` and loads the incoming data
for us:

```python
$ cat jqmakesmesad.py
import json

class JSONList(list): # json container could be list or dict
    def __init__(self, raw_json):
        data = json.loads(raw_json)
        super().__init__(data)

def github_orgs(data: JSONList) -> str:
    logins = [org['login'] for org in data]
    return '\n'.join(logins)

$ source jqmakesmesad.py
$ github_orgs --help
usage: github_orgs [-h] [--data / data]

options:
  -h, --help     show this help message and exit

positional or keyword args:
  --data / data  JSONList (required)
$ curl -s https://api.github.com/organizations | github_orgs
<list of github org names>
```

Sourcepy also supports returning data from generators. If your function requires some
additional processing time and you want to print new values to stdout as you go, rather
than leaving the user to wait, you can `yield` them instead:

```python
import json
from typing import Generator

class JSONList(list): # json container could be list or dict
    ...

def github_orgs(data: JSONList) -> Generator:
    for org in data:
        yield org['login']
```

