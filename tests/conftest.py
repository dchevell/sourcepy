import sys

from pathlib import Path

import pytest

# allow importing local packages
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))


@pytest.fixture
def typed_fn():
    def myfn(one: str, two: int, three: bool, four: list):
        return one, two, three, four
