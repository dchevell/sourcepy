from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple, Union


type_hints = [
    # Native types
    (int,   'int'),         (bool,  'bool'),
    (float, 'float'),       (str,   'str'),
    (tuple, 'tuple'),       (list,  'list'),
    (set,   'set'),         (dict,  'dict'),

    # typing module built in generics
    (Dict,  'dict'),        (List,  'list'),
    (Set,   'set'),         (Tuple, 'tuple'),
    (DefaultDict, 'defaultdict'),

    # Union types
    (Optional[int], 'int'),
    (Optional[List], 'list'),
    (list | dict, 'list | dict'),
    (Union[int, str], 'int | str'),
    (dict | int | List, 'dict | int | list'),
    (Union[Set, list, DefaultDict], 'set | list | defaultdict'),
]
