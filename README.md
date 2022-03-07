# Sourcepy

**Sourcepy** is a tool that allows you to `source` Python files straight from your shell,
and use its functions and variables natively. It uses Python's inspect and importlib
machinery to build shims and can leverage type hints for additional features.


```python
$ cat pagetitle.py
import lxml.html

def getpagetitle(html, kwarg=None) -> str:
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
  --html / html    (required)
  --kwarg / kwarg  NoneType (default: None)
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
and also understands positional-only, positional-or-keyword, and keyword-only arguments
to give you the full power and flexibility of your Python functions natively from your
shell.

## Requirements

Sourcepy requires 3.8+ or greater. It has no external dependencies and relies only on
importlib & inspect machinery from the standard library.

## Installation

### Clone this repository - recommended

The easiest way to install Sourcepy is to clone this repository to a folder on your local
machine:

```
git clone https://github.com/dchevell/sourcepy.git ~/.sourcepy
```

Then simply add `source ~/.sourcepy/sourcepy.sh` to your shell profile, e.g. `.zprofile`
or `.bash_profile`. You can place this folder anywhere, however a `~/.sourcepy` folder
will still be created to generate module stubs whenever you source python files.

Sourcepy requires no dependencies to run.
