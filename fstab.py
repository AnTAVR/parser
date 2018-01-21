from typing import List, Union, Iterable, Generator

from . import Comment, LineError, NoOptionError, UnitBase, LineInterface


class Option(LineInterface):
    """Класс линии опции."""
    DEFAULT_OPTIONS = 'defaults,lazytime,noauto,x-systemd.automount'

    file_system: str = None
    dir_: str = None
    type_: str = None
    options: str = None
    dump: int = None
    pass_: int = None

    @classmethod
    def test(cls, line: str) -> bool:
        line = line.strip().split()
        if len(line) == 6:
            line = tuple(map(str.strip, line))
            try:
                int(line[4])
                int(line[5])
            except ValueError:
                pass
            else:
                return True
        return False

    def __init__(self, line: str, dir_: str = None, type_: str = None,
                 options: str = DEFAULT_OPTIONS, dump: int = 0, pass_: int = 0, *, test: bool = False):
        """
        :raise: LineError
        """
        # line: Union[str, tuple]

        line = line.strip()
        if not self.test(line):
            if test:
                raise LineError
            assert dir_
            assert type_

            self.file_system = line  # type: str
            self.dir_ = dir_  # type: str
            self.type_ = type_  # type: str
            self.options = options  # type: str
            self.dump = dump  # type: int
            self.pass_ = pass_  # type: int
            return

        line = line.split()
        line = tuple(map(str.strip, line))

        self.file_system = line[0]  # type: str
        self.dir_ = line[1]  # type: str
        self.type_ = line[2]  # type: str
        self.options = line[3]  # type: str
        self.dump = int(line[4])  # type: int
        self.pass_ = int(line[5])  # type: int

    def __repr__(self) -> str:
        return '{}({!r} {!r} {!r} {!r} {!r} {!r})'.format(self.__class__.__name__, self.file_system, self.dir_,
                                                          self.type_, self.options, self.dump, self.pass_)

    def __str__(self) -> str:
        return '{}\t{}\t{}\t{}\t{}\t{}'.format(self.file_system, self.dir_,
                                               self.type_, self.options, self.dump, self.pass_) + '\n'


class Unit(UnitBase):
    """Класс парсера ini файла."""

    _lines: List[Union[Option, Comment]]

    def new(self):
        comment = """#
# /etc/fstab: static file system information
#
# <file system>\t<dir>\t<type>\t<options>\t<dump>\t<pass>
"""
        self.read_text(comment)
        return self

    def read(self, lines: Iterable[str]):
        # Определяем тип строки.
        for line in self._line_split_backslash(lines):
            token = self.__line_to_type(line)
            if token is None:
                pass
            else:
                self.append(token)

    # noinspection PyMethodMayBeStatic
    def _line_split_backslash(self, lines: Iterable[str]) -> Generator[str, None, None]:
        return (x.strip() for x in lines)

    @staticmethod
    def __line_to_type(line: str) -> Union[Comment, Option, None]:
        if not line:
            return

        try:
            token = Comment(line, test=True)
        except LineError:
            try:
                token = Option(line, test=True)
            except LineError:
                token = Comment(line)
        return token

    def append(self, token: Union[Option, Comment], file_system: str = None, before: bool = True):
        index = None
        option = None

        if file_system is not None:
            index = self._lines.index(self.get(file_system))
            if not before:
                index += 1

        if isinstance(token, Option):
            try:
                option = self.get(token.file_system)
            except NoOptionError:
                pass
            else:
                index = self._lines.index(option)

        if index is None:
            self._lines.append(token)
        else:
            if option:
                self._lines[index] += token
            else:
                self._lines.insert(index, token)

    @property
    def comments(self) -> Generator[Comment, None, None]:
        return (x for x in self._lines if isinstance(x, Comment))

    @property
    def options(self) -> Generator[Option, None, None]:
        return (x for x in self._lines if isinstance(x, Option))

    def get(self, file_system: str) -> Option:
        """
        :raise: NoOptionError
        """
        for value in self.options:
            if value.file_system == file_system:
                return value
        raise NoOptionError(file_system)

    def remove(self, token: Union[Option, Comment]):
        self._lines.remove(token)
