import os
from abc import ABCMeta, abstractclassmethod, abstractmethod
from io import StringIO
from typing import Union, Iterable


class NoOptionError(Exception):
    """Исключение, возникающее при отсутствующей опции."""

    def __init__(self, option: str):
        super().__init__('No option {!r}'.format(option))


class LineError(Exception):
    """Исключение, возникающее при неправильном типе строки."""
    pass


class LineInterface(metaclass=ABCMeta):
    # noinspection PyMethodParameters
    @abstractclassmethod
    def test(cls, string: Union[bytes, str]) -> bool:
        return False


class Comment(LineInterface):
    """Класс линии комментария."""
    COMMENT_CHARS = ('#',)

    value: str = None

    @classmethod
    def test(cls, line: str) -> bool:
        line = line.strip()
        return line.startswith(cls.COMMENT_CHARS)

    def __init__(self, line: str, *, test: bool = False):
        """
        :raise: LineError
        """
        line = line.strip()
        if not self.test(line):
            if test:
                raise LineError
        else:
            line = line[1:].strip()
        self.value = line

    def __str__(self) -> str:
        return '{} {}'.format(self.COMMENT_CHARS[0], self.value) + '\n'

    def __repr__(self) -> str:
        return '{}({!r})'.format(self.__class__.__name__, self.value)


class UnitBase(metaclass=ABCMeta):
    """Базовый класс парсера."""

    _lines: list

    def __init__(self):
        self._lines = []

    def write_file(self, fname: Union[str, bytes, os.PathLike]) -> int:
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, 'w+') as f:
            return f.write(str(self))

    def read_file(self, fname: Union[str, bytes, os.PathLike]):
        with open(fname) as f:
            self.read(f)

    def read_text(self, text: str):
        self.read(StringIO(text))

    @abstractmethod
    def read(self, lines: Iterable[str]):
        pass

    def __str__(self) -> str:
        return ''.join(map(lambda x: str(x), filter(lambda x: x, self._lines)))

    def __repr__(self) -> str:
        return '{}({!r})'.format(self.__class__.__name__, self._lines)
