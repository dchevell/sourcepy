def stdout_stderr() -> str:
    """Sourcepy redirects all output from sourced files to stderr.
    Return values are printed to stdout. This is helpful when running
    functions from the shell and assigning them to a variable:

        `$ MYVAR=$(stdout_sterr)`

    This would print the `print()` text below to the console but assign
    the `return` text to `MYVAR`
    """
    print('emitted messages should go to stderr')
    return 'returned values should go to stdout'


def multiply(a: int, b: int) -> int:
    """Sourcepy will coerce incoming values to ints
    or fail if input is invalid"""
    return a * b


from pathlib import Path

def fileexists(file: Path) -> bool:
    """Values will be converted into Path objects. Booleans
    will be converted to shell equivalents (lowercase)"""
    return file.exists()

