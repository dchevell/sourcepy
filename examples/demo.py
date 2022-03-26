def stdout_stderr():
    """Sourcepy implicitly redirects messages from functions to stderr.
    Return values are printed to stdout. This is helpful when running
    functions from the shell and assigning them to a variable:

        `$ MYVAR=$(stdout_sterr)`

    This would print the `print()` text below to the user but assign
    the `return` text to `MYVAR`
    """
    print('emitted messages should go to stderr')
    return 'returned values should go to stdout'
