import sys
from pathlib import Path



# allow importing local packages
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))
