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


def multiply(x: int, y: int) -> int:
    """Sourcepy will coerce incoming values to ints
    or fail if input is invalid"""
    return x * y



from pathlib import Path

def fileexists(file: Path) -> bool:
    """Values will be converted into Path objects. Booleans
    will be converted to shell equivalents (lowercase)"""
    return file.exists()



# Variables
MY_INT = 3 * 7
FAB_FOUR = ['John', 'Paul', 'George', 'Ringo']
PROJECT = {'name': 'Sourcepy', 'purpose': 'unknown'}



from typing import Literal, Optional

DogActions = Optional[Literal['sit', 'speak', 'drop']]

class Dog:
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    def do(self, action: DogActions = None) -> str:
        if action == 'sit':
            return f"{self.name} sat down"
        if action == 'speak':
            return f"{self.name} said: bark bark bark"
        if action == 'drop':
            return f"{self.name} said: Drop what?"
        return f"{self.name} looked at you expectantly"

pretzel = Dog('Pretzel', 7)



from enum import Enum

class Colour(Enum):
    RED = 'red'
    GREEN = 'green'
    BLUE = 'blue'

def favouritecolour(colour: Colour) -> str:
    if colour is Colour.RED:
        return "I like the colour red"
    if colour is Colour.GREEN:
        return "Green is my favourite colour"
    if colour is Colour.BLUE:
        return "I prefer the colour blue"
    raise ValueError("I see too many colours")
