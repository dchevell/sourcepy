import sys
from pathlib import Path

import pytest

from constants import type_hints

src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from converters import get_type_hint_name



@pytest.mark.parametrize('type_hint,name', type_hints)
def test_get_type_hint_name(type_hint, name):
    assert get_type_hint_name(type_hint) == name

