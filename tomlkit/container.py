from __future__ import unicode_literals

from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple

from ._compat import decode
from .exceptions import NonExistentKey
from .items import AoT
from .items import Comment
from .items import Item
from .items import Key
from .items import Null
from .items import Table
from .items import Trivia
from .items import Whitespace


class Container(dict):
    """
    A container for items within a TOMLDocument.
    """

    def __init__(self):  # type: () -> None
        self._map = {}  # type: Dict[Key, int]
        self._body = []  # type: List[Tuple[Optional[Key], Item]]

    @property
    def body(self):  # type: () -> List[Tuple[Optional[Key], Item]]
        return self._body

    @property
    def value(self):  # type: () -> Dict[Any, Any]
        return {k: v for k, v in self.items()}

    def add(
        self, key, item=None
    ):  # type: (Union[Key, Item, str], Optional[Item]) -> Item
        """
        Adds an item to the current Container.
        """
        if item is None:
            if not isinstance(key, (Comment, Whitespace)):
                raise ValueError(
                    "Non comment/whitespace items must have an associated key"
                )

            key, item = None, key

        return self.append(key, item)

    def append(self, key, item):  # type: (Key, Item) -> None
        from .api import item as _item

        if not isinstance(key, Key) and key is not None:
            key = Key(key)

        if not isinstance(item, Item):
            item = _item(item)

        if isinstance(item, (AoT, Table)) and item.name != key.key:
            item.name = key.key

        self._map[key] = len(self._body)

        self._body.append((key, item))

        if key is not None:
            super(Container, self).__setitem__(key.key, item.value)

        return item

    def remove(self, key):  # type: (Key) -> None
        if not isinstance(key, Key):
            key = Key(key)

        idx = self._map.pop(key, None)
        if idx is None:
            raise NonExistentKey(key)

        self._body[idx] = (None, Null())

        super(Container, self).__delitem__(key.key)

    def last_item(self):  # type: () -> Optional[Item]
        if self._body:
            return self._body[-1][1]

    def as_string(self, prefix=None):  # type: () -> str
        s = ""
        for k, v in self._body:
            if k is not None:
                if isinstance(v, Table):
                    if v.is_super_table():
                        s += v.as_string(prefix=prefix)

                        continue

                    if prefix is not None:
                        k = Key(prefix + "." + k.as_string())

                    open_, close = "[", "]"
                    if v.is_aot_element():
                        open_, close = "[[", "]]"

                    cur = "{}{}{}{}{}{}{}{}".format(
                        v.trivia.indent,
                        open_,
                        decode(k.as_string()),
                        close,
                        v.trivia.comment_ws,
                        decode(v.trivia.comment),
                        v.trivia.trail,
                        v.as_string(prefix=prefix),
                    )
                elif isinstance(v, AoT):
                    if prefix is not None:
                        k = Key(prefix + "." + k.as_string())

                    cur = ""
                    key = decode(k.as_string())
                    for table in v.body:
                        if table.is_super_table():
                            cur += table.as_string(prefix=prefix)
                        else:
                            cur += "{}[[{}]]{}{}{}".format(
                                table.trivia.indent,
                                key,
                                table.trivia.comment_ws,
                                decode(table.trivia.comment),
                                table.trivia.trail,
                            )
                            cur += table.as_string(prefix=k.key)
                else:
                    cur = "{}{}{}{}{}{}{}".format(
                        v.trivia.indent,
                        decode(k.as_string()),
                        k.sep,
                        decode(v.as_string()),
                        v.trivia.comment_ws,
                        decode(v.trivia.comment),
                        v.trivia.trail,
                    )
            else:
                cur = v.as_string()

            s += cur

        return s

    # Dictionary methods

    def keys(self):  # type: () -> Generator[Key]
        for k, _ in self._body:
            if k is None:
                continue

            yield k.key

    def values(self):  # type: () -> Generator[Item]
        for k, v in self._body:
            if k is None:
                continue

            yield v.value

    def items(self):  # type: () -> Generator[Item]
        for k, v in self._body:
            if k is None:
                continue

            yield k.key, v.value

    def __contains__(self, key):  # type: (Key) -> bool
        if not isinstance(key, Key):
            key = Key(key)

        return key in self._map

    def __getitem__(self, key):  # type: (Key) -> Item
        if not isinstance(key, Key):
            key = Key(key)

        idx = self._map.get(key, None)
        if idx is None:
            raise NonExistentKey(key)

        return self._body[idx][1].value

    def __setitem__(self, key, value):  # type: (Union[Key, str], Any) -> None
        if key is not None and key in self:
            self._replace(key, key, value)
        else:
            self.append(key, value)

    def __delitem__(self, key):  # type: (Union[Key, str]) -> None
        self.remove(key)

    def _replace(self, key, new_key, value):  # type: (Key, Key, Item) -> None
        if not isinstance(key, Key):
            key = Key(key)

        if not isinstance(new_key, Key):
            new_key = Key(new_key)

        idx = self._map.get(key, None)
        if idx is None:
            raise NonExistentKey(key)

        self._replace_at(idx, new_key, value)

    def _replace_at(self, idx, new_key, value):  # type: (int, Key, Item) -> None
        from .api import item as _item

        k, v = self._body[idx]

        self._map[new_key] = self._map.pop(k)

        value = _item(value)

        # Copying trivia
        value.trivia.indent = v.trivia.indent
        value.trivia.comment_ws = v.trivia.comment_ws
        value.trivia.comment = v.trivia.comment
        value.trivia.trail = v.trivia.trail

        self._body[idx] = (new_key, value)

        super(Container, self).__setitem__(new_key.key, value.value)

    def __str__(self):  # type: () -> str
        return str(self.value)

    def __eq__(self, other):  # type: (Dict) -> bool
        if not isinstance(other, dict):
            return NotImplemented

        return self.value == other