from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple, Union


type_hints = [
    # Native types
    (int, 'int'),
    (str, 'str'),
    (float, 'float'),
    (bool, 'bool'),
    (list, 'list'),
    (tuple, 'tuple'),
    (set, 'set'),
    (dict, 'dict'),

    # typing module generics
    (DefaultDict, 'defaultdict'),
    (Dict, 'dict'),
    (List, 'list'),
    (Set, 'set'),
    (Tuple, 'tuple'),

    # Union types
    (Optional[int], 'int'),
    (Optional[List], 'list'),
    (Union[int, str], 'int | str'),
    (Union[Set, list, DefaultDict], 'set | list | defaultdict'),
    (list | dict, 'list | dict'),
    (dict | int | List, 'dict | int | list'),
]
