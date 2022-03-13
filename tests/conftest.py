import sys

from pathlib import Path
from typing import Optional, TextIO

import pytest

# allow importing local packages
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))


@pytest.fixture
def typed_fn():
    def myfn(one: str, two: int, three: bool = False, four: Optional[list] = None):
        return one, two, three, four
    return myfn

@pytest.fixture
def stdin_implicit_int_fn():
    def myfn(one: int, two: str, three: bool, four: list):
        return one, two, three, four
    return myfn


@pytest.fixture
def stdin_explicit_fn():
    def myfn(one: int, two: TextIO, three: bool, four: Optional[list] = None):
        return one, two.read().rstrip(), three, four
    return myfn

@pytest.fixture
def pos_kw_fn():
    def myfn(one: str, two: int, /, three: bool = False, *, four: Optional[list] = None):
        return one, two, three, four
    return myfn

@pytest.fixture
def pos_kw_explicit_stdin_fn():
    def myfn(one: str, two: TextIO, /, three: bool = False, *, four: Optional[list] = None):
        return one, two.read().rstrip(), three, four
    return myfn
